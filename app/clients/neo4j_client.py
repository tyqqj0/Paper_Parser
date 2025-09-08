"""
Neo4j客户端封装
"""
import json
from typing import Optional, Dict, List, Any
from datetime import datetime

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from loguru import logger

from app.core.config import settings
from app.models.paper import EnhancedPaper


class Neo4jClient:
    """Neo4j异步客户端"""
    
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None
    
    async def connect(self):
        """连接Neo4j"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            
            # 测试连接
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
            
            logger.info("Neo4j连接成功")
            
            # 创建索引
            await self._create_indexes()
            
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}")
            raise
    
    async def disconnect(self):
        """断开连接"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j连接已关闭")
    
    async def _create_indexes(self):
        """创建必要的索引"""
        indexes = [
            # 论文索引
            "CREATE INDEX paper_id IF NOT EXISTS FOR (p:Paper) ON (p.paperId)",
            "CREATE INDEX corpus_id IF NOT EXISTS FOR (p:Paper) ON (p.corpusId)",
            "CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title)",
            "CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.year)",
            
            # 外部ID索引
            "CREATE INDEX external_doi IF NOT EXISTS FOR (e:ExternalId) ON (e.value)",
            "CREATE INDEX external_arxiv IF NOT EXISTS FOR (e:ExternalId) ON (e.type)",
            
            # 作者索引
            "CREATE INDEX author_id IF NOT EXISTS FOR (a:Author) ON (a.authorId)",
            "CREATE INDEX author_name IF NOT EXISTS FOR (a:Author) ON (a.name)",
        ]
        
        async with self.driver.session() as session:
            for index_query in indexes:
                try:
                    await session.run(index_query)
                except Exception as e:
                    logger.warning(f"创建索引失败: {index_query}, 错误: {e}")
    
    async def get_paper(self, paper_id: str) -> Optional[Dict]:
        """根据paperId获取论文"""
        query = """
        MATCH (p:Paper {paperId: $paper_id})
        RETURN p
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, paper_id=paper_id)
                record = await result.single()
                if record:
                    paper_node = record["p"]
                    return dict(paper_node)
                return None
            except Exception as e:
                logger.error(f"Neo4j获取论文失败 paper_id={paper_id}: {e}")
                return None
    
    async def get_paper_by_external_id(self, id_type: str, id_value: str) -> Optional[Dict]:
        """根据外部ID获取论文"""
        query = """
        MATCH (p:Paper)-[:HAS_EXTERNAL_ID]->(e:ExternalId {type: $id_type, value: $id_value})
        RETURN p
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, id_type=id_type, id_value=id_value)
                record = await result.single()
                if record:
                    paper_node = record["p"]
                    return dict(paper_node)
                return None
            except Exception as e:
                logger.error(f"Neo4j根据外部ID获取论文失败 {id_type}={id_value}: {e}")
                return None
    
    async def merge_paper(self, paper_data: Dict) -> bool:
        """插入或更新论文数据"""
        query = """
        MERGE (p:Paper {paperId: $paper_id})
        SET p += $properties,
            p.lastUpdated = datetime(),
            p.dataJson = $data_json
        RETURN p.paperId as paperId
        """
        
        async with self.driver.session() as session:
            try:
                # 准备数据
                paper_id = paper_data.get("paperId")
                if not paper_id:
                    logger.error("论文数据缺少paperId")
                    return False
                
                # 分离JSON数据和属性
                data_json = json.dumps(paper_data, ensure_ascii=False, default=str)
                properties = {
                    key: value for key, value in paper_data.items()
                    if key not in ["externalIds", "authors", "citations", "references"]
                    and value is not None
                }
                
                # 执行合并
                result = await session.run(
                    query,
                    paper_id=paper_id,
                    properties=properties,
                    data_json=data_json
                )
                
                record = await result.single()
                if record:
                    # 处理外部ID
                    if "externalIds" in paper_data and paper_data["externalIds"]:
                        await self._merge_external_ids(session, paper_id, paper_data["externalIds"])
                    
                    # 处理作者关系
                    if "authors" in paper_data and paper_data["authors"]:
                        await self._merge_authors(session, paper_id, paper_data["authors"])
                    
                    return True
                return False
                
            except Exception as e:
                logger.error(f"Neo4j合并论文失败 paper_id={paper_data.get('paperId')}: {e}")
                return False
    
    async def _merge_external_ids(self, session: AsyncSession, paper_id: str, external_ids: Dict):
        """处理外部ID关系"""
        for id_type, id_value in external_ids.items():
            if id_value:
                query = """
                MATCH (p:Paper {paperId: $paper_id})
                MERGE (e:ExternalId {type: $id_type, value: $id_value})
                MERGE (p)-[:HAS_EXTERNAL_ID]->(e)
                """
                try:
                    await session.run(
                        query,
                        paper_id=paper_id,
                        id_type=id_type,
                        id_value=str(id_value)
                    )
                except Exception as e:
                    logger.error(f"创建外部ID关系失败 {id_type}={id_value}: {e}")
    
    async def _merge_authors(self, session: AsyncSession, paper_id: str, authors: List[Dict]):
        """处理作者关系"""
        for author in authors:
            if author.get("authorId") and author.get("name"):
                query = """
                MATCH (p:Paper {paperId: $paper_id})
                MERGE (a:Author {authorId: $author_id})
                SET a.name = $author_name
                MERGE (p)-[:AUTHORED_BY]->(a)
                """
                try:
                    await session.run(
                        query,
                        paper_id=paper_id,
                        author_id=author["authorId"],
                        author_name=author["name"]
                    )
                except Exception as e:
                    logger.error(f"创建作者关系失败 author_id={author.get('authorId')}: {e}")
    
    async def create_citation_relation(self, citing_paper_id: str, cited_paper_id: str) -> bool:
        """创建引用关系"""
        query = """
        MATCH (citing:Paper {paperId: $citing_paper_id})
        MATCH (cited:Paper {paperId: $cited_paper_id})
        MERGE (citing)-[:CITES]->(cited)
        """
        
        async with self.driver.session() as session:
            try:
                await session.run(
                    query,
                    citing_paper_id=citing_paper_id,
                    cited_paper_id=cited_paper_id
                )
                return True
            except Exception as e:
                logger.error(f"创建引用关系失败 {citing_paper_id} -> {cited_paper_id}: {e}")
                return False
    
    async def get_citations(self, paper_id: str, limit: int = 100) -> List[Dict]:
        """获取论文的引用文献"""
        query = """
        MATCH (p:Paper {paperId: $paper_id})<-[:CITES]-(citing:Paper)
        RETURN citing
        ORDER BY citing.citationCount DESC
        LIMIT $limit
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, paper_id=paper_id, limit=limit)
                citations = []
                async for record in result:
                    citations.append(dict(record["citing"]))
                return citations
            except Exception as e:
                logger.error(f"获取引用文献失败 paper_id={paper_id}: {e}")
                return []
    
    async def get_references(self, paper_id: str, limit: int = 100) -> List[Dict]:
        """获取论文的参考文献"""
        query = """
        MATCH (p:Paper {paperId: $paper_id})-[:CITES]->(referenced:Paper)
        RETURN referenced
        ORDER BY referenced.citationCount DESC
        LIMIT $limit
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, paper_id=paper_id, limit=limit)
                references = []
                async for record in result:
                    references.append(dict(record["referenced"]))
                return references
            except Exception as e:
                logger.error(f"获取参考文献失败 paper_id={paper_id}: {e}")
                return []
    
    async def search_papers(
        self, 
        query: str, 
        limit: int = 10, 
        offset: int = 0
    ) -> List[Dict]:
        """搜索论文"""
        cypher_query = """
        CALL db.index.fulltext.queryNodes('paperFulltext', $query)
        YIELD node, score
        RETURN node
        ORDER BY score DESC
        SKIP $offset
        LIMIT $limit
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(
                    cypher_query, 
                    query=query, 
                    offset=offset, 
                    limit=limit
                )
                papers = []
                async for record in result:
                    papers.append(dict(record["node"]))
                return papers
            except Exception as e:
                logger.error(f"搜索论文失败 query={query}: {e}")
                return []
    
    async def get_popular_papers(self, limit: int = 100) -> List[Dict]:
        """获取热门论文"""
        query = """
        MATCH (p:Paper)
        WHERE p.citationCount IS NOT NULL
        RETURN p
        ORDER BY p.citationCount DESC
        LIMIT $limit
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, limit=limit)
                papers = []
                async for record in result:
                    papers.append(dict(record["p"]))
                return papers
            except Exception as e:
                logger.error(f"获取热门论文失败: {e}")
                return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        queries = {
            "total_papers": "MATCH (p:Paper) RETURN count(p) as count",
            "total_authors": "MATCH (a:Author) RETURN count(a) as count",
            "total_citations": "MATCH ()-[:CITES]->() RETURN count(*) as count",
            "total_external_ids": "MATCH (e:ExternalId) RETURN count(e) as count"
        }
        
        stats = {}
        async with self.driver.session() as session:
            for stat_name, query in queries.items():
                try:
                    result = await session.run(query)
                    record = await result.single()
                    stats[stat_name] = record["count"] if record else 0
                except Exception as e:
                    logger.error(f"获取统计信息失败 {stat_name}: {e}")
                    stats[stat_name] = 0
        
        return stats
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
                return True
        except Exception as e:
            logger.error(f"Neo4j健康检查失败: {e}")
            return False


# 全局Neo4j客户端实例
neo4j_client = Neo4jClient()
