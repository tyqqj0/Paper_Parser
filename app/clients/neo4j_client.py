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
from app.services.external_id_mapping import ExternalIds, normalize_title_norm


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
            async with self.driver.session(database=settings.neo4j_database) as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
            
            logger.info("Neo4j连接成功")
            
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}")
            raise
    
    async def disconnect(self):
        """断开连接"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j连接已关闭")
    
    
    async def get_paper(self, paper_id: str) -> Optional[Dict]:
        """根据paperId获取论文"""
        if self.driver is None:
            return None
        query = """
        MATCH (p:Paper {paperId: $paper_id})
        RETURN p
        """
        
        async with self.driver.session(database=settings.neo4j_database) as session:
            try:
                result = await session.run(query, paper_id=paper_id)
                record = await result.single()
                if record:
                    paper_node = record["p"]
                    node_props = dict(paper_node)
                    data_json = node_props.get("dataJson")
                    if isinstance(data_json, str) and data_json:
                        try:
                            # 优先返回完整dataJson（包含authors等），并保留lastUpdated等少量节点字段
                            payload = json.loads(data_json)
                            if node_props.get("lastUpdated") is not None:
                                payload["lastUpdated"] = node_props.get("lastUpdated")
                            return payload
                        except Exception:
                            return node_props
                    return node_props
                return None
            except Exception as e:
                logger.error(f"Neo4j获取论文失败 paper_id={paper_id}: {e}")
                return None
    
    
    async def find_papers_by_title_norm_contains(self, title_fragment: str, limit: int = 3) -> List[Dict]:
        """按 TITLE_NORM contains/prefix 做轻量模糊匹配，返回若干候选。

        说明：TITLE_NORM 为归一化小写、去符号、压缩空格后的强匹配键，适用于 contains 匹配。
        """
        try:
            if self.driver is None:
                return []
            if not title_fragment or not isinstance(title_fragment, str):
                return []
            norm = normalize_title_norm(title_fragment)
            if not norm:
                return []
            cypher = """
            MATCH (p:Paper)
            WHERE p.title_norm CONTAINS $needle OR p.title_norm STARTS WITH $needle
            RETURN p
            LIMIT $limit
            """
            async with self.driver.session(database=settings.neo4j_database) as session:
                result = await session.run(cypher, needle=norm, limit=int(limit or 3))
                hits: List[Dict] = []
                async for record in result:
                    node = record.get("p")
                    if node:
                        props = dict(node)
                        data_json = props.get("dataJson")
                        if isinstance(data_json, str) and data_json:
                            try:
                                payload = json.loads(data_json)
                                if props.get("lastUpdated") is not None:
                                    payload["lastUpdated"] = props.get("lastUpdated")
                                hits.append(payload)
                                continue
                            except Exception:
                                pass
                        hits.append(props)
                return hits
        except Exception as e:
            logger.error(f"TITLE_NORM contains 匹配失败 fragment='{title_fragment}': {e}")
            return []
    
    async def merge_paper(self, paper_data: Dict) -> bool:
        """插入或更新论文数据"""
        if self.driver is None:
            return False
        query = """
        MERGE (p:Paper {paperId: $paper_id})
        SET p += $properties,
            p.lastUpdated = datetime(),
            p.dataJson = $data_json,
            p.authors = $authors_json,
            p.title_norm = $title_norm,
            p.ingestStatus = 'full'
        RETURN p.paperId as paperId
        """
        
        async with self.driver.session(database=settings.neo4j_database) as session:
            try:
                # 入参校验
                if not paper_data or not isinstance(paper_data, dict):
                    logger.error("合并论文失败：paper_data为空或类型错误")
                    return False
                
                # 准备数据
                paper_id = paper_data.get("paperId")
                if not paper_id:
                    logger.error("论文数据缺少paperId")
                    return False
                
                # 分离JSON数据和属性
                data_json = json.dumps(paper_data, ensure_ascii=False, default=str)
                authors_value = paper_data.get("authors")
                authors_json = None
                try:
                    if authors_value is not None:
                        authors_json = json.dumps(authors_value, ensure_ascii=False, default=str)
                except Exception:
                    authors_json = None
                properties_raw = {
                    key: value for key, value in paper_data.items()
                    if key not in ["externalIds", "authors", "citations", "references"]
                    and value is not None
                }

                # 仅保留Neo4j允许的属性类型（原始类型或其列表），过滤掉嵌套对象/列表
                def _is_primitive(v: Any) -> bool:
                    return isinstance(v, (str, int, float, bool))

                def _is_primitive_list(v: Any) -> bool:
                    if not isinstance(v, list):
                        return False
                    return all(isinstance(item, (str, int, float, bool)) for item in v)

                properties: Dict[str, Any] = {}
                for k, v in properties_raw.items():
                    # 跳过常见的嵌套字段
                    if k in {"journal", "publicationVenue", "openAccessPdf", "s2FieldsOfStudy"}:
                        continue
                    if _is_primitive(v) or _is_primitive_list(v):
                        properties[k] = v
                    else:
                        # 其他非原始类型一律忽略，完整对象已写入 dataJson
                        continue
                
                # 计算并传递 title_norm（如果有标题）
                title_norm = None
                try:
                    title_value = paper_data.get("title")
                    if isinstance(title_value, str) and title_value.strip():
                        title_norm = normalize_title_norm(title_value)
                except Exception:
                    title_norm = None

                # 执行合并
                result = await session.run(
                    query,
                    paper_id=paper_id,
                    properties=properties,
                    data_json=data_json,
                    authors_json=authors_json,
                    title_norm=title_norm
                )
                
                record = await result.single()
                if record:
                    # 处理外部ID
                    if isinstance(paper_data.get("externalIds"), dict) and paper_data["externalIds"]:
                        await self._merge_external_ids(session, paper_id, paper_data["externalIds"])
                    
                    # 处理作者关系
                    if isinstance(paper_data.get("authors"), list) and paper_data["authors"]:
                        await self._merge_authors(session, paper_id, paper_data["authors"])
                    
                    return True
                return False
                
            except Exception as e:
                safe_paper_id = None
                try:
                    safe_paper_id = paper_data.get('paperId') if isinstance(paper_data, dict) else None
                except Exception:
                    safe_paper_id = None
                logger.error(f"Neo4j合并论文失败 paper_id={safe_paper_id}: {e}")
                return False
    
    async def _merge_external_ids(self, session: AsyncSession, paper_id: str, external_ids: Dict):
        """处理外部ID，将其存储为Paper节点的externalIds JSON字段"""
        if not external_ids:
            return
            
        # 归一化所有外部ID
        normalized_external_ids = ExternalIds.from_dict(external_ids)
        # 将归一化后的外部ID存储为JSON字符串，并同步 title_norm（若提供）
        if normalized_external_ids:
            external_ids_json = normalized_external_ids.to_json()
            title_norm_value = normalized_external_ids.get("TITLE_NORM")

            query = """
            MATCH (p:Paper {paperId: $paper_id})
            SET p.externalIds = $external_ids_json
            """
            params = {"paper_id": paper_id, "external_ids_json": external_ids_json}
            if title_norm_value:
                query += ", p.title_norm = $title_norm"
                params["title_norm"] = title_norm_value.external_id
            try:
                await session.run(query, **params)
                logger.debug(f"更新外部ID成功 paper_id={paper_id}, 外部ID数量={len(normalized_external_ids)}")
            except Exception as e:
                logger.error(f"更新外部ID属性失败 paper_id={paper_id}: {e}")
    
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

    async def merge_aliases_from_paper(self, paper_data: Dict) -> bool:
        """基于论文数据合并规范化的外部ID到Paper节点属性。

        支持类型：DOI/ArXiv/CorpusId/URL/TITLE_NORM/MAG/ACL/PMID/PMCID
        """
        try:
            if self.driver is None:
                return False
            paper_id = paper_data.get("paperId")
            if not paper_id:
                return False

            # 准备外部ID数据
            external_ids = {}
            ext = paper_data.get("externalIds") or {}
            
            # 添加externalIds中的数据
            for id_type, id_value in ext.items():
                if id_value:
                    external_ids[id_type] = id_value
            
            # 添加corpusId（如果在顶层）
            corpus = paper_data.get("corpusId")
            if corpus is not None:
                external_ids["CorpusId"] = corpus
            
            # 添加URL（优先使用顶层url）
            url = paper_data.get("url")
            if isinstance(url, str) and url.strip():
                external_ids["URL"] = url
            
            # 添加TITLE_NORM
            title = paper_data.get("title")
            if isinstance(title, str) and title.strip():
                external_ids["TITLE_NORM"] = title

            if not external_ids:
                return True

            # 使用已有的_merge_external_ids方法
            async with self.driver.session(database=settings.neo4j_database) as session:
                await self._merge_external_ids(session, paper_id, external_ids)
            
            return True
        except Exception as e:
            safe_id = None
            try:
                safe_id = paper_data.get("paperId")
            except Exception:
                pass
            logger.error(f"合并外部ID失败 paper_id={safe_id}: {e}")
            return False

    async def merge_data_chunks_from_full_data(self, paper_data: Dict) -> bool:
        """为给定论文写入metadata到Paper节点属性，以及citations/references DataChunk。"""
        try:
            if self.driver is None:
                return False
            paper_id = paper_data.get("paperId")
            if not paper_id:
                return False

            # 准备 JSON（字符串）
            metadata = {
                k: v for k, v in paper_data.items() if k not in ("citations", "references")
            }
            metadata_json = json.dumps(metadata, ensure_ascii=False, default=str)

            citations = paper_data.get("citations") if isinstance(paper_data.get("citations"), list) else None
            references = paper_data.get("references") if isinstance(paper_data.get("references"), list) else None
            citations_json = json.dumps(citations, ensure_ascii=False, default=str) if citations is not None else None
            references_json = json.dumps(references, ensure_ascii=False, default=str) if references is not None else None

            async with self.driver.session(database=settings.neo4j_database) as session:
                # metadata - 直接存储到Paper节点属性中
                try:
                    q = """
                    MATCH (p:Paper {paperId: $paper_id})
                    SET p.metadataJson = $metadata_json, p.metadataUpdated = datetime()
                    """
                    await session.run(q, paper_id=paper_id, metadata_json=metadata_json)
                except Exception as e:
                    logger.error(f"写入metadata到Paper节点失败 paper_id={paper_id}: {e}")

                # citations
                if citations_json is not None:
                    try:
                        q = """
                        MATCH (p:Paper {paperId: $paper_id})
                        MERGE (c:DataChunk:PaperCitations {paperId: $paper_id, chunkType: 'citations'})
                        SET c.dataJson = $citations_json, c.lastUpdated = datetime()
                        MERGE (p)-[:HAS_CITATIONS]->(c)
                        """
                        await session.run(q, paper_id=paper_id, citations_json=citations_json)
                    except Exception as e:
                        logger.error(f"写入citations数据块失败 paper_id={paper_id}: {e}")

                # references
                if references_json is not None:
                    try:
                        q = """
                        MATCH (p:Paper {paperId: $paper_id})
                        MERGE (r:DataChunk:PaperReferences {paperId: $paper_id, chunkType: 'references'})
                        SET r.dataJson = $references_json, r.lastUpdated = datetime()
                        MERGE (p)-[:HAS_REFERENCES]->(r)
                        """
                        await session.run(q, paper_id=paper_id, references_json=references_json)
                    except Exception as e:
                        logger.error(f"写入references数据块失败 paper_id={paper_id}: {e}")
            return True
        except Exception as e:
            logger.error(f"写入数据块失败: {e}")
            return False

    async def merge_cites_from_full_data(self, paper_data: Dict) -> bool:
        """根据 full_data 中的 citations/references 批量创建 CITES 关系与 stub 邻居。"""
        try:
            if self.driver is None:
                return False
            paper_id = paper_data.get("paperId")
            if not paper_id:
                return False

            refs_raw = paper_data.get("references") if isinstance(paper_data.get("references"), list) else []
            cites_raw = paper_data.get("citations") if isinstance(paper_data.get("citations"), list) else []

            references = []
            for idx, r in enumerate(refs_raw):
                if isinstance(r, dict) and r.get("paperId"):
                    title_value = r.get("title")
                    # 将 authors 保持为 JSON 字符串以与主节点保持一致
                    authors_json = None
                    try:
                        if isinstance(r.get("authors"), list):
                            authors_json = json.dumps(r.get("authors"), ensure_ascii=False, default=str)
                    except Exception:
                        authors_json = None
                    references.append({
                        "paperId": r.get("paperId"),
                        "title": title_value,
                        "title_norm": normalize_title_norm(title_value) if title_value else None,
                        "position": idx,
                        "venue": r.get("venue"),
                        "year": r.get("year"),
                        "citationCount": r.get("citationCount"),
                        "authors_json": authors_json,
                    })
            citations = []
            for c in cites_raw:
                if isinstance(c, dict) and c.get("paperId"):
                    title_value = c.get("title")
                    authors_json = None
                    try:
                        if isinstance(c.get("authors"), list):
                            authors_json = json.dumps(c.get("authors"), ensure_ascii=False, default=str)
                    except Exception:
                        authors_json = None
                    citations.append({
                        "paperId": c.get("paperId"),
                        "title": title_value,
                        "title_norm": normalize_title_norm(title_value) if title_value else None,
                        "venue": c.get("venue"),
                        "year": c.get("year"),
                        "citationCount": c.get("citationCount"),
                        "authors_json": authors_json,
                    })

            async with self.driver.session(database=settings.neo4j_database) as session:
                # references: (p)-[:CITES]->(ref)
                if references:
                    q_ref = """
                    MATCH (p:Paper {paperId: $paper_id})
                    UNWIND $references AS ref
                    MERGE (r:Paper {paperId: ref.paperId})
                    ON CREATE SET r.title = ref.title,
                                  r.ingestStatus = 'stub',
                                  r.title_norm = ref.title_norm,
                                  r.venue = ref.venue,
                                  r.year = ref.year,
                                  r.citationCount = ref.citationCount,
                                  r.authors = ref.authors_json
                    MERGE (p)-[rel:CITES]->(r)
                    SET rel.position = ref.position
                    """
                    try:
                        await session.run(q_ref, paper_id=paper_id, references=references)
                    except Exception as e:
                        logger.error(f"批量创建references关系失败 paper_id={paper_id}: {e}")

                # citations: (cite)-[:CITES]->(p)
                if citations:
                    q_cite = """
                    MATCH (p:Paper {paperId: $paper_id})
                    UNWIND $citations AS cite
                    MERGE (c:Paper {paperId: cite.paperId})
                    ON CREATE SET c.title = cite.title,
                                  c.ingestStatus = 'stub',
                                  c.title_norm = cite.title_norm,
                                  c.venue = cite.venue,
                                  c.year = cite.year,
                                  c.citationCount = cite.citationCount,
                                  c.authors = cite.authors_json
                    MERGE (c)-[:CITES]->(p)
                    """
                    try:
                        await session.run(q_cite, paper_id=paper_id, citations=citations)
                    except Exception as e:
                        logger.error(f"批量创建citations关系失败 paper_id={paper_id}: {e}")
            return True
        except Exception as e:
            logger.error(f"合并CITES失败: {e}")
            return False

    async def create_citations_ingest_plan(self, paper_id: str, total: int, page_size: int) -> bool:
        """为超大规模被引创建分页抓取计划节点（占位，供后续后台任务消费）。"""
        try:
            if self.driver is None:
                return False
            cypher = """
            MATCH (p:Paper {paperId: $paper_id})
            MERGE (plan:DataChunk:IngestPlan:PaperCitationsPlan {paperId: $paper_id, chunkType: 'citations_plan'})
            SET plan.total = $total,
                plan.pageSize = $page_size,
                plan.status = 'pending',
                plan.createdAt = datetime()
            MERGE (p)-[:HAS_CITATIONS_PLAN]->(plan)
            """
            async with self.driver.session(database=settings.neo4j_database) as session:
                await session.run(cypher, paper_id=paper_id, total=int(total or 0), page_size=int(page_size or 0))
            return True
        except Exception as e:
            logger.error(f"创建Citations抓取计划失败 paper_id={paper_id}: {e}")
            return False

    # 本地归一化/别名逻辑已移除，统一使用 external_id_mapping
    
    async def create_citation_relation(self, citing_paper_id: str, cited_paper_id: str) -> bool:
        """创建引用关系"""
        if self.driver is None:
            return False
        query = """
        MATCH (citing:Paper {paperId: $citing_paper_id})
        MATCH (cited:Paper {paperId: $cited_paper_id})
        MERGE (citing)-[:CITES]->(cited)
        """
        
        async with self.driver.session(database=settings.neo4j_database) as session:
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
    
    async def get_citations(self, paper_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取论文的引用文献"""
        if self.driver is None:
            return []
        query = """
        MATCH (p:Paper {paperId: $paper_id})<-[:CITES]-(citing:Paper)
        RETURN citing
        ORDER BY citing.citationCount DESC
        SKIP $offset
        LIMIT $limit
        """
        
        async with self.driver.session(database=settings.neo4j_database) as session:
            try:
                result = await session.run(query, paper_id=paper_id, limit=limit, offset=offset)
                citations = []
                async for record in result:
                    citations.append(dict(record["citing"]))
                return citations
            except Exception as e:
                logger.error(f"获取引用文献失败 paper_id={paper_id}: {e}")
                return []
    
    async def get_references(self, paper_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取论文的参考文献"""
        if self.driver is None:
            return []
        query = """
        MATCH (p:Paper {paperId: $paper_id})-[rel:CITES]->(referenced:Paper)
        RETURN referenced, rel, p.lastUpdated as last_updated
        ORDER BY coalesce(rel.position, -1) ASC, referenced.citationCount DESC
        SKIP $offset
        LIMIT $limit
        """
        
        async with self.driver.session(database=settings.neo4j_database) as session:
            try:
                result = await session.run(query, paper_id=paper_id, limit=limit, offset=offset)
                references = []
                async for record in result:
                    last_updated = record.get("last_updated")
                    if not self._is_data_fresh(last_updated):
                        continue
                    
                    props = dict(record["referenced"])
                    # 将 authors 从 JSON 字符串解码为列表
                    try:
                        authors_val = props.get("authors")
                        if isinstance(authors_val, str) and authors_val:
                            decoded = json.loads(authors_val)
                            props["authors"] = decoded
                    except Exception:
                        pass
                    references.append(props)
                return references
            except Exception as e:
                logger.error(f"获取参考文献失败 paper_id={paper_id}: {e}")
                return []

    async def get_references_total(self, paper_id: str) -> int:
        """获取论文参考文献的总数"""
        if self.driver is None:
            return 0
        
        # 优先使用节点的 referenceCount 属性，如果不存在则回退到关系计数
        query = """
        MATCH (p:Paper {paperId: $paper_id})
        OPTIONAL MATCH (p)-[rel:CITES]->(referenced:Paper)
        RETURN p.referenceCount AS node_count, count(referenced) AS relation_count
        """
        async with self.driver.session(database=settings.neo4j_database) as session:
            try:
                result = await session.run(query, paper_id=paper_id)
                record = await result.single()
                if record is None:
                    return 0
                
                # 优先使用节点属性
                node_count = record["node_count"]
                if node_count is not None:
                    try:
                        return int(node_count)
                    except (ValueError, TypeError):
                        pass
                
                # 回退到关系计数
                relation_count = record["relation_count"]
                try:
                    return int(relation_count)
                except (ValueError, TypeError):
                    return 0
                    
            except Exception as e:
                logger.error(f"获取参考文献总数失败 paper_id={paper_id}: {e}")
                return 0
    
    async def search_papers(
        self, 
        query: str, 
        limit: int = 10, 
        offset: int = 0
    ) -> List[Dict]:
        """搜索论文"""
        logger.info(f"a搜索论文: {query}, limit={limit}, offset={offset}")
        if self.driver is None:
            return []
        cypher_query = """
        CALL db.index.fulltext.queryNodes('paperFulltext', $query)
        YIELD node, score
        RETURN node
        ORDER BY score DESC
        SKIP $offset
        LIMIT $limit
        """
        
        async with self.driver.session(database=settings.neo4j_database) as session:
            try:
                result = await session.run(
                    cypher_query,
                    {"query": query, "offset": offset, "limit": limit}
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
        
        async with self.driver.session(database=settings.neo4j_database) as session:
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
            "papers_with_doi": "MATCH (p:Paper) WHERE p.doi IS NOT NULL RETURN count(p) as count",
            "papers_with_arxiv": "MATCH (p:Paper) WHERE p.arxiv IS NOT NULL RETURN count(p) as count",
            "papers_with_mag": "MATCH (p:Paper) WHERE p.mag IS NOT NULL RETURN count(p) as count",
            "papers_with_dblp": "MATCH (p:Paper) WHERE p.dblp IS NOT NULL RETURN count(p) as count"
        }
        
        stats = {}
        async with self.driver.session(database=settings.neo4j_database) as session:
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
            async with self.driver.session(database=settings.neo4j_database) as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
                return True
        except Exception as e:
            logger.error(f"Neo4j健康检查失败: {e}")
            return False

    def _is_data_fresh(self, last_updated, max_age_hours: int = 2400) -> bool:
        """检查数据是否新鲜"""
        try:
            if not last_updated:
                return False
            # 转换为 Python datetime 对象
            if isinstance(last_updated, datetime):
                # 已经是 Python datetime 对象
                converted_datetime = last_updated
            elif hasattr(last_updated, 'to_native'):
                # Neo4j DateTime 对象，使用 to_native() 方法
                converted_datetime = last_updated.to_native()
            elif isinstance(last_updated, str):
                # 字符串格式的时间
                converted_datetime = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            else:
                # 其他格式，返回 False 表示数据不新鲜
                logger.warning(f"不支持的时间格式: {type(last_updated)}")
                return False
            
            # 移除时区信息进行比较
            if converted_datetime.tzinfo is not None:
                converted_datetime = converted_datetime.replace(tzinfo=None)
            
            # 计算时间差
            age = datetime.now() - converted_datetime
            return age.total_seconds() < max_age_hours * 3600
            
        except Exception as e:
            logger.error(f"检查数据新鲜度失败: {e}")
            return False
    def ensure_fresh(self, data: Dict) -> Dict:
        """确保数据新鲜"""
        if not data:
            return None
        if not self._is_data_fresh(data.get('lastUpdated')):
            return None
        return data

# 全局Neo4j客户端实例
neo4j_client = Neo4jClient()
