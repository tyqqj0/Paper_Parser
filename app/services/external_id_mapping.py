"""
统一外部ID映射服务 - SQLite实现
"""
import sqlite3
import asyncio
import aiosqlite
from typing import Optional, Dict, List, Tuple, Set, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from loguru import logger
import json
from app.core.config import settings

@dataclass(frozen=True)
class ExternalId:
    """
    外部ID实体，包含两个参数：
    - external_type: 使用 `ExternalIdTypes` 中的值
    - external_id: 具体的ID字符串
    """
    external_type: str
    external_id: str

    def __post_init__(self):
        # 规范化类型名
        normalized_type = ExternalIdTypes.normalize_type(self.external_type)
        object.__setattr__(self, "external_type", normalized_type)

        # 校验类型合法性
        if not ExternalIdTypes.is_valid_type(normalized_type):
            raise ValueError(f"无效的外部ID类型: {self.external_type}")

        # 校验ID有效性
        if not isinstance(self.external_id, str) or not self.external_id.strip():
            raise ValueError("external_id 不能为空")

    def to_tuple(self) -> Tuple[str, str]:
        """以(external_type, external_id)形式返回"""
        return self.external_type, self.external_id

    def __str__(self) -> str:
        return f"{self.external_type}:{self.external_id}"
    @staticmethod
    def _normalize_doi(doi: str) -> Optional[str]:
        try:
            value = doi.strip().lower()
            return value if value else None
        except Exception:
            return None
    @staticmethod
    def _normalize_arxiv(arxiv_id: str) -> Optional[str]:
        try:
            import re
            s = str(arxiv_id).strip()
            s = re.sub(r"(?i)^arxiv:", "", s).strip()
            s = re.sub(r"(?i)v\d+$", "", s).strip()
            m = re.match(r"^\d{4}\.\d{4,5}$", s)
            if m:
                return s
            m2 = re.search(r"(\d{4}\.\d{4,5})", s)
            if m2:
                return m2.group(1)
            return s if s else None
        except Exception:
            return None
    @staticmethod
    def _normalize_url(url: str) -> Optional[str]:
        try:
            from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
            u = urlparse(url.strip())
            scheme = u.scheme.lower() or 'http'
            netloc = u.netloc.lower()
            path = u.path.rstrip('/') or '/'
            q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=False) if not k.lower().startswith('utm_')]
            query = urlencode(q)
            return urlunparse((scheme, netloc, path, '', query, ''))
        except Exception:
            return None

    @staticmethod
    def _normalize_title_norm(title: str) -> Optional[str]:
        try:
            return normalize_title_norm(title)
        except Exception:
            return None

    @staticmethod
    def _normalize_corpus_id(value: Any) -> str:
        return str(int(value))

    @staticmethod
    def _normalize_mag(value: Any) -> str:
        return str(int(value))

    @staticmethod
    def _normalize_pmid(value: Any) -> str:
        return str(int(value))

    @staticmethod
    def _normalize_pmcid(value: Any) -> str:
        try:
            s = str(value).strip().upper()
            if s.startswith('PMC'):
                s = s[3:]
            return str(int(s))
        except Exception:
            return str(int(value))

    @staticmethod
    def _normalize_acl(value: str) -> Optional[str]:
        try:
            v = value.strip().upper()
            v = v.replace('_', '-').replace(' ', '')
            return v if v else None
        except Exception:
            return None

    @staticmethod
    def _normalize_external_id(id_type: str, value: Any) -> Optional[str]:
        try:
            if id_type == ExternalIdTypes.DOI:
                return ExternalId._normalize_doi(str(value))
            elif id_type == ExternalIdTypes.ARXIV:
                return ExternalId._normalize_arxiv(str(value))
            elif id_type == ExternalIdTypes.CORPUS_ID:
                return ExternalId._normalize_corpus_id(value)
            elif id_type == ExternalIdTypes.MAG:
                return ExternalId._normalize_mag(value)
            elif id_type == ExternalIdTypes.ACL:
                return ExternalId._normalize_acl(str(value))
            elif id_type == ExternalIdTypes.PMID:
                return ExternalId._normalize_pmid(value)
            elif id_type == ExternalIdTypes.PMCID:
                return ExternalId._normalize_pmcid(value)
            elif id_type == ExternalIdTypes.URL:
                return ExternalId._normalize_url(str(value))
            elif id_type == ExternalIdTypes.TITLE_NORM:
                return ExternalId._normalize_title_norm(str(value))
            elif id_type == ExternalIdTypes.PAPER_ID:
                s = str(value).strip()
                return s if s else None
            else:
                return str(value).strip() if value else None
        except Exception:
            return None
    @staticmethod
    def from_tuple(external_type:str, external_id:str):
        normalized_type = ExternalIdTypes.normalize_type(external_type)
        normalized_id = ExternalId._normalize_external_id(normalized_type, external_id)
        if normalized_id and normalized_type:
            return ExternalId(external_type=normalized_type, external_id=normalized_id)
        return None
    @staticmethod
    def from_raw(raw:str):
        try:
            s = (raw or "").strip()
            if not s:
                return None

            # 1) 显式前缀 TYPE:value
            if ":" in s:
                head, tail = s.split(":", 1)
                t = ExternalIdTypes.from_prefix(head.strip())
                v = tail.strip()
                if t:
                    return ExternalId.from_tuple(t, v)
            # 2) 启发式识别
            # DOI
            if s.startswith("10."):
                v = ExternalId._normalize_doi(s)
                if v:
                    return ExternalId(external_type=ExternalIdTypes.DOI, external_id=v)
            # URL
            low = s.lower()
            if low.startswith("http"):
                v = ExternalId._normalize_url(s)
                if v:
                    return ExternalId(external_type=ExternalIdTypes.URL, external_id=v)
                try:
                    if v and v.endswith('/'):
                        v2 = v[:-1]
                        if v2:
                            return ExternalId(external_type=ExternalIdTypes.URL, external_id=v2)
                except Exception:
                    pass
            # ArXiv
            import re as _re
            if "arxiv" in low or _re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", s):
                v = ExternalId._normalize_arxiv(s)
                if v:
                    return ExternalId(external_type=ExternalIdTypes.ARXIV, external_id=v)
            # CorpusId（纯数字）
            if s.isdigit():
                try:
                    v = ExternalId._normalize_corpus_id(s)
                    return ExternalId(external_type=ExternalIdTypes.CORPUS_ID, external_id=v)
                except Exception:
                    pass
            # S2 sha（40位十六进制）→ 认为是 PAPER_ID
            try:
                import re as _re2
                if _re2.fullmatch(r"[0-9a-fA-F]{40}", s):
                    return ExternalId(external_type=ExternalIdTypes.PAPER_ID, external_id=s)
            except Exception:
                pass
            # TITLE_NORM 强匹配
            tnorm = ExternalId._normalize_title_norm(s)
            if tnorm:
                return ExternalId(external_type=ExternalIdTypes.TITLE_NORM, external_id=tnorm)

            return None
        except Exception:
            return None
class ExternalIds:
    def __init__(self, external_ids: List[ExternalId]):
        self._external_ids: Dict[str, ExternalId] = {eid.external_type: eid for eid in external_ids}
    def to_dict(self) -> Dict[str, str]:
        return {eid.external_type: eid.external_id for eid in self._external_ids.values()}

    def to_list(self) -> List[ExternalId]:
        return list(self._external_ids.values())

    def to_tuple(self) -> List[Tuple[str, str]]:
        return [(eid.external_type, eid.external_id) for eid in self._external_ids.values()]

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_string(self):
        return "\n".join([f"{eid.external_type}:{eid.external_id}" for eid in self._external_ids.values()])

    @staticmethod
    def from_dict(external_ids: Dict[str, Any]) -> "ExternalIds":
        return ExternalIds([ExternalId.from_tuple(external_type, external_id) for external_type, external_id in external_ids.items()])
    
    def __getitem__(self, key: str) -> ExternalId:
        return self._external_ids[key]

    def __contains__(self, key: str) -> bool:
        return key in self._external_ids

    def __len__(self) -> int:
        return len(self._external_ids)

    def __iter__(self):
        return iter(self._external_ids.values())

    def get(self, key: str, default: Any = None) -> Optional[ExternalId]:
        return self._external_ids.get(key, default)


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
    
    async def get_paper_id(self, eid: ExternalId) -> Optional[str]:
        """通过外部ID获取论文ID"""
        if not self._initialized:
            await self.initialize()
        logger.info(f"查询外部ID映射: {eid.external_id}, {eid.external_type}")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT paper_id FROM external_id_mappings WHERE external_id = ? AND external_type = ?",
                    (eid.external_id, eid.external_type)
                )
                result = await cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"查询外部ID映射失败 {eid.external_type}:{eid.external_id}: {e}")
            return None
    
    async def set_mapping(self, eid: ExternalId, paper_id: str) -> bool:
       """设置外部ID映射 - 使用 ON CONFLICT 保证原子性"""
       if not self._initialized:
           await self.initialize()
           
       try:
           async with aiosqlite.connect(self.db_path) as db:
               now = int(datetime.now().timestamp())
               
               # 使用 INSERT ... ON CONFLICT ... DO UPDATE ... 实现原子性的 "upsert"
               # 这避免了 "SELECT then INSERT/UPDATE" 模式下的竞态条件
               # 当 paper_id 和 external_type 组合已存在时，会触发 UPDATE
               # 这样可以保留原记录的 created_at 时间戳
               await db.execute("""
                   INSERT INTO external_id_mappings 
                   (external_id, external_type, paper_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(paper_id, external_type) DO UPDATE SET
                       external_id = excluded.external_id,
                       updated_at = excluded.updated_at
               """, (eid.external_id, eid.external_type, paper_id, now, now))
               
               await db.commit()
               logger.info(f"设置外部ID映射成功: {eid.external_type}:{eid.external_id} -> {paper_id}")
               return True
               
       except Exception as e:
           logger.error(f"设置外部ID映射失败 {eid.external_type}:{eid.external_id} -> {paper_id}: {e}")
           return False
    async def batch_set_mappings(self, external_ids: ExternalIds, paper_id: str) -> bool:
        """从字典设置外部ID映射"""
        if not self._initialized:
            await self.initialize()
        if not external_ids or not paper_id:
            return False
        for eid in external_ids:
            await self.set_mapping(eid, paper_id)
        return True
    
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
    async def resolve_paper_id(self, raw: str) -> Optional[str]:
        """将任意字符串解析为 ExternalId 并从映射表解析为 paper_id。

        规则：
        - 解析为 PAPER_ID 则直接返回其值
        - 其他类型通过映射表查找
        """
        ext = ExternalId.from_raw(raw)
        if not ext:
            return None
        if ext.external_type == ExternalIdTypes.PAPER_ID:
            return ext.external_id
        try:
            return await self.get_paper_id(ext)
        except Exception:
            return None
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
    PAPER_ID = "PaperId"
    
    # 所有有效类型的集合
    ALL_TYPES = {
        DOI, ARXIV, CORPUS_ID, MAG, ACL, PMID, PMCID, URL, TITLE_NORM, DBLP, PAPER_ID
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
            "dblp": cls.DBLP,
            "paper": cls.PAPER_ID,
            "paper_id": cls.PAPER_ID,
            "paperid": cls.PAPER_ID
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
            "DBLP": cls.DBLP,
            "PAPER": cls.PAPER_ID,
            "PAPER_ID": cls.PAPER_ID,
            "PAPERID": cls.PAPER_ID
        }
        return prefix_mapping.get(prefix.upper())
    
    @classmethod
    def get_allowed_prefixes(cls) -> set:
        """获取所有允许的前缀（大写）"""
        return {
            "DOI", "ARXIV", "MAG", "ACL", "PMID", "PMCID", 
            "CORPUSID", "CORPUS", "URL", "DBLP", "PAPER", "PAPER_ID", "PAPERID"
        }

def normalize_title_norm(title: str) -> Optional[str]:
    """Normalize a title for strong matching.

    Rules:
    - lower-case
    - collapse whitespace to single space
    - strip Unicode punctuation and symbols
    - trim
    Returns None if the result is empty.
    """
    try:
        import re
        t = str(title).lower()
        # replace tabs with space to match Cypher inline used before
        t = t.replace("\t", " ")
        t = re.sub(r"\s+", " ", t)
        # remove punctuation and symbols (Unicode classes P and S)
        t = re.sub(r"[\p{P}\p{S}]", "", t)
        t = t.strip()
        return t if t else None
    except Exception:
        try:
            t = str(title).strip().lower()
            return t or None
        except Exception:
            return None