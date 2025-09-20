"""
统一外部ID映射服务 - SQLite实现
"""
import sqlite3
import asyncio
import aiosqlite
from typing import Optional, Dict, List, Tuple, Set
from datetime import datetime
from pathlib import Path
from loguru import logger

from app.core.config import settings


class ExternalIdMappingService:
    """统一外部ID映射服务"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or settings.external_id_mapping_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
    
    async def initialize(self):
        """初始化数据库和表结构"""
        if self._initialized:
            return
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 创建映射表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS external_id_mappings (
                        external_id TEXT NOT NULL,
                        external_type TEXT NOT NULL,
                        paper_id TEXT NOT NULL,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        updated_at INTEGER DEFAULT (strftime('%s', 'now')),
                        PRIMARY KEY (external_id, external_type)
                    )
                """)
                
                # 创建反向查询索引
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_paper_lookup 
                    ON external_id_mappings(paper_id)
                """)
                
                # 创建类型查询索引
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_type_lookup 
                    ON external_id_mappings(external_type)
                """)
                
                # 提交事务
                await db.commit()
                
                # 创建更新时间索引（用于清理过期数据）
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_updated_at 
                    ON external_id_mappings(updated_at)
                """)
                
                # 在创建唯一索引之前，清理重复的(paper_id, external_type)记录，保留最新的
                await self._cleanup_duplicate_paper_type_mappings(db)
                
                # 创建(paper_id, external_type)的唯一索引，确保同一论文的同一类型只有一条记录
                await db.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_paper_type_unique 
                    ON external_id_mappings(paper_id, external_type)
                """)
                
                await db.commit()
            self._initialized = True
            logger.info(f"外部ID映射数据库初始化成功: {self.db_path}")
            
        except Exception as e:
            logger.error(f"外部ID映射数据库初始化失败: {e}")
            raise
    
    async def _cleanup_duplicate_paper_type_mappings(self, db) -> None:
        """清理重复的(paper_id, external_type)记录，保留最新的记录"""
        try:
            # 查找重复的(paper_id, external_type)组合
            cursor = await db.execute("""
                SELECT paper_id, external_type, COUNT(*) as cnt
                FROM external_id_mappings 
                GROUP BY paper_id, external_type 
                HAVING COUNT(*) > 1
            """)
            duplicates = await cursor.fetchall()
            
            if not duplicates:
                logger.info("没有发现重复的(paper_id, external_type)记录")
                return
                
            logger.info(f"发现 {len(duplicates)} 组重复的(paper_id, external_type)记录，开始清理...")
            
            # 对每组重复记录，只保留最新的（根据updated_at）
            for paper_id, external_type, count in duplicates:
                await db.execute("""
                    DELETE FROM external_id_mappings 
                    WHERE paper_id = ? AND external_type = ?
                    AND (external_id, external_type) NOT IN (
                        SELECT external_id, external_type 
                        FROM external_id_mappings 
                        WHERE paper_id = ? AND external_type = ?
                        ORDER BY updated_at DESC, created_at DESC 
                        LIMIT 1
                    )
                """, (paper_id, external_type, paper_id, external_type))
                
            await db.commit()
            logger.info("重复记录清理完成")
            
        except Exception as e:
            logger.error(f"清理重复记录失败: {e}")
            # 不抛出异常，让初始化继续进行
    
    async def get_paper_id(self, external_id: str, external_type: str) -> Optional[str]:
        """通过外部ID获取论文ID"""
        if not self._initialized:
            await self.initialize()
        logger.info(f"查询外部ID映射: {external_id}, {external_type}")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT paper_id FROM external_id_mappings WHERE external_id = ? AND external_type = ?",
                    (external_id, external_type)
                )
                result = await cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"查询外部ID映射失败 {external_type}:{external_id}: {e}")
            return None
    
    async def set_mapping(self, external_id: str, external_type: str, paper_id: str) -> bool:
        """设置外部ID映射 - 同一paper_id和external_type只保留一条记录"""
        if not self._initialized:
            await self.initialize()
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                now = int(datetime.now().timestamp())
                
                # 检查是否已存在相同的映射
                cursor = await db.execute(
                    "SELECT external_id, created_at FROM external_id_mappings WHERE paper_id = ? AND external_type = ?",
                    (paper_id, external_type)
                )
                existing = await cursor.fetchone()
                
                if existing and existing[0] == external_id:
                    # 如果external_id相同，只更新时间
                    await db.execute(
                        "UPDATE external_id_mappings SET updated_at = ? WHERE paper_id = ? AND external_type = ?",
                        (now, paper_id, external_type)
                    )
                    logger.debug(f"更新现有映射时间: {external_type}:{external_id} -> {paper_id}")
                else:
                    # 删除同一paper_id和external_type的旧记录
                    await db.execute(
                        "DELETE FROM external_id_mappings WHERE paper_id = ? AND external_type = ?",
                        (paper_id, external_type)
                    )
                    
                    # 插入新记录，保留原有的created_at（如果存在）
                    created_at = existing[1] if existing else now
                    await db.execute("""
                        INSERT INTO external_id_mappings 
                        (external_id, external_type, paper_id, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (external_id, external_type, paper_id, created_at, now))
                    
                    if existing:
                        logger.info(f"覆盖外部ID映射: {external_type}:{existing[0]} -> {external_id} (paper_id: {paper_id})")
                    else:
                        logger.info(f"新增外部ID映射: {external_type}:{external_id} -> {paper_id}")
                
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"设置外部ID映射失败 {external_type}:{external_id} -> {paper_id}: {e}")
            return False
    
    async def get_external_ids(self, paper_id: str) -> Dict[str, str]:
        """获取论文的所有外部ID"""
        if not self._initialized:
            await self.initialize()
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT external_type, external_id FROM external_id_mappings WHERE paper_id = ?",
                    (paper_id,)
                )
                results = await cursor.fetchall()
                return {row[0]: row[1] for row in results}
                
        except Exception as e:
            logger.error(f"查询论文外部ID失败 {paper_id}: {e}")
            return {}
    
    async def batch_set_mappings(self, mappings: List[Tuple[str, str, str]]) -> int:
        """批量设置映射 - (external_id, external_type, paper_id)
        确保同一paper_id和external_type只保留一条记录"""
        if not self._initialized:
            await self.initialize()
            
        if not mappings:
            return 0
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                now = int(datetime.now().timestamp())
                success_count = 0
                
                # 分批处理以避免SQL查询过长
                batch_size = 500
                for i in range(0, len(mappings), batch_size):
                    batch = mappings[i:i + batch_size]
                    
                    # 构建查询条件：所有(paper_id, external_type)组合
                    placeholders = ",".join(["(?,?)"] * len(batch))
                    query_params = []
                    for external_id, external_type, paper_id in batch:
                        query_params.extend([paper_id, external_type])
                    
                    # 查询现有映射
                    cursor = await db.execute(f"""
                        SELECT paper_id, external_type, external_id, created_at 
                        FROM external_id_mappings 
                        WHERE (paper_id, external_type) IN ({placeholders})
                    """, query_params)
                    existing_mappings = {(row[0], row[1]): (row[2], row[3]) for row in await cursor.fetchall()}
                    
                    # 分类处理映射
                    updates = []  # 只需要更新时间戳的记录
                    deletes = []  # 需要删除的记录
                    inserts = []  # 需要插入的记录
                    
                    for external_id, external_type, paper_id in batch:
                        key = (paper_id, external_type)
                        if key in existing_mappings:
                            existing_external_id, existing_created_at = existing_mappings[key]
                            if existing_external_id == external_id:
                                # 相同external_id，只更新时间戳
                                updates.append((now, paper_id, external_type))
                            else:
                                # 不同external_id，需要删除旧记录并插入新记录
                                deletes.append((paper_id, external_type))
                                inserts.append((external_id, external_type, paper_id, existing_created_at, now))
                        else:
                            # 新记录，直接插入
                            inserts.append((external_id, external_type, paper_id, now, now))
                    
                    # 执行批量操作
                    if updates:
                        await db.executemany(
                            "UPDATE external_id_mappings SET updated_at = ? WHERE paper_id = ? AND external_type = ?",
                            updates
                        )
                        logger.debug(f"批量更新 {len(updates)} 条记录的时间戳")
                    
                    if deletes:
                        await db.executemany(
                            "DELETE FROM external_id_mappings WHERE paper_id = ? AND external_type = ?",
                            deletes
                        )
                        logger.debug(f"批量删除 {len(deletes)} 条旧记录")
                    
                    if inserts:
                        await db.executemany("""
                            INSERT INTO external_id_mappings 
                            (external_id, external_type, paper_id, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, inserts)
                        logger.debug(f"批量插入 {len(inserts)} 条新记录")
                    
                    success_count += len(batch)
                
                await db.commit()
                logger.info(f"批量设置映射成功，共处理 {success_count} 条记录")
                return success_count
                
        except Exception as e:
            logger.error(f"批量设置映射失败: {e}")
            return 0
    
    async def delete_mapping(self, external_id: str, external_type: str) -> bool:
        """删除特定映射"""
        if not self._initialized:
            await self.initialize()
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM external_id_mappings WHERE external_id = ? AND external_type = ?",
                    (external_id, external_type)
                )
                await db.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"删除映射失败 {external_type}:{external_id}: {e}")
            return False
    
    async def delete_paper_mappings(self, paper_id: str) -> int:
        """删除论文的所有映射"""
        if not self._initialized:
            await self.initialize()
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM external_id_mappings WHERE paper_id = ?",
                    (paper_id,)
                )
                await db.commit()
                return cursor.rowcount
                
        except Exception as e:
            logger.error(f"删除论文映射失败 {paper_id}: {e}")
            return 0
    
    async def get_mappings_by_type(self, external_type: str, limit: int = 1000) -> List[Tuple[str, str]]:
        """按类型获取映射列表 - (external_id, paper_id)"""
        if not self._initialized:
            await self.initialize()
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT external_id, paper_id FROM external_id_mappings WHERE external_type = ? LIMIT ?",
                    (external_type, limit)
                )
                results = await cursor.fetchall()
                return [(row[0], row[1]) for row in results]
                
        except Exception as e:
            logger.error(f"按类型查询映射失败 {external_type}: {e}")
            return []
    
    async def get_statistics(self) -> Dict[str, any]:
        """获取映射统计信息"""
        if not self._initialized:
            await self.initialize()
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 总映射数
                cursor = await db.execute("SELECT COUNT(*) FROM external_id_mappings")
                total_count = (await cursor.fetchone())[0]
                
                # 按类型统计
                cursor = await db.execute("""
                    SELECT external_type, COUNT(*) 
                    FROM external_id_mappings 
                    GROUP BY external_type 
                    ORDER BY COUNT(*) DESC
                """)
                type_stats = dict(await cursor.fetchall())
                
                # 唯一论文数
                cursor = await db.execute("SELECT COUNT(DISTINCT paper_id) FROM external_id_mappings")
                unique_papers = (await cursor.fetchone())[0]
                
                return {
                    "total_mappings": total_count,
                    "unique_papers": unique_papers,
                    "type_statistics": type_stats,
                    "database_path": str(self.db_path)
                }
                
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    async def cleanup_old_mappings(self, days: int = 90) -> int:
        """清理超过指定天数的映射记录"""
        if not self._initialized:
            await self.initialize()
            
        try:
            cutoff_timestamp = int((datetime.now().timestamp() - days * 24 * 3600))
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM external_id_mappings WHERE updated_at < ?",
                    (cutoff_timestamp,)
                )
                await db.commit()
                
                deleted_count = cursor.rowcount
                logger.info(f"清理了 {deleted_count} 条超过 {days} 天的映射记录")
                return deleted_count
                
        except Exception as e:
            logger.error(f"清理旧映射失败: {e}")
            return 0
    
    async def close(self):
        """关闭服务（SQLite是文件数据库，无需显式关闭连接池）"""
        self._initialized = False
        logger.info("外部ID映射服务已关闭")


# 全局服务实例
external_id_mapping = ExternalIdMappingService()


# 便捷的外部ID类型常量
class ExternalIdTypes:
    """外部ID类型常量"""
    DOI = "DOI"
    ARXIV = "ArXiv" 
    CORPUS_ID = "CorpusId"
    MAG = "MAG"
    ACL = "ACL"
    PMID = "PMID"
    PMCID = "PMCID"
    URL = "URL"
    TITLE_NORM = "TITLE_NORM"
    DBLP = "DBLP"
    
    # 所有有效类型的集合
    ALL_TYPES = {
        DOI, ARXIV, CORPUS_ID, MAG, ACL, PMID, PMCID, URL, TITLE_NORM, DBLP
    }
    
    @classmethod
    def is_valid_type(cls, external_type: str) -> bool:
        """验证外部ID类型是否有效"""
        return external_type in cls.ALL_TYPES
    
    @classmethod
    def normalize_type(cls, external_type: str) -> str:
        """标准化外部ID类型名称"""
        # 处理常见的大小写变体
        type_mapping = {
            "doi": cls.DOI,
            "arxiv": cls.ARXIV,
            "arXiv": cls.ARXIV,
            "corpusid": cls.CORPUS_ID,
            "corpus_id": cls.CORPUS_ID,
            "mag": cls.MAG,
            "acl": cls.ACL,
            "pmid": cls.PMID,
            "pmcid": cls.PMCID,
            "url": cls.URL,
            "title_norm": cls.TITLE_NORM,
            "title": cls.TITLE_NORM,
            "dblp": cls.DBLP
        }
        
        return type_mapping.get(external_type.lower(), external_type)
    
    @classmethod
    def from_s2_api_type(cls, s2_type: str) -> Optional[str]:
        """将S2 API的外部ID类型映射为标准类型"""
        s2_mapping = {
            'DOI': cls.DOI,
            'ArXiv': cls.ARXIV,
            'MAG': cls.MAG,
            'ACL': cls.ACL,
            'PubMed': cls.PMID,
            'PubMedCentral': cls.PMCID,
            'CorpusId': cls.CORPUS_ID,
            'URL': cls.URL,
            'DBLP': cls.DBLP
        }
        return s2_mapping.get(s2_type)
    
    @classmethod
    def from_prefix(cls, prefix: str) -> Optional[str]:
        """将前缀映射为标准类型"""
        prefix_mapping = {
            "DOI": cls.DOI,
            "ARXIV": cls.ARXIV,
            "MAG": cls.MAG,
            "ACL": cls.ACL,
            "PMID": cls.PMID,
            "PMCID": cls.PMCID,
            "CORPUSID": cls.CORPUS_ID,
            "CORPUS": cls.CORPUS_ID,
            "URL": cls.URL,
            "DBLP": cls.DBLP
        }
        return prefix_mapping.get(prefix.upper())
    
    @classmethod
    def get_allowed_prefixes(cls) -> set:
        """获取所有允许的前缀（大写）"""
        return {
            "DOI", "ARXIV", "MAG", "ACL", "PMID", "PMCID", 
            "CORPUSID", "CORPUS", "URL", "DBLP"
        }

