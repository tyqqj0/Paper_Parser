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
            async with self.driver.session(database=settings.neo4j_database) as session:
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
            "CREATE INDEX paper_ingest_status IF NOT EXISTS FOR (p:Paper) ON (p.ingestStatus)",
            # 外部ID唯一约束（type,value）
            "CREATE CONSTRAINT external_id_unique IF NOT EXISTS FOR (e:ExternalId) REQUIRE (e.type, e.value) IS UNIQUE",
            # DataChunk 索引与唯一约束
            "CREATE INDEX datachunk_paper_id IF NOT EXISTS FOR (d:DataChunk) ON (d.paperId)",
            "CREATE CONSTRAINT datachunk_unique IF NOT EXISTS FOR (d:DataChunk) REQUIRE (d.paperId, d.chunkType) IS UNIQUE",
            # Paper 标题全文索引（供搜索使用）
            "CREATE FULLTEXT INDEX paperFulltext IF NOT EXISTS FOR (p:Paper) ON EACH [p.title]",
            # 作者索引
            "CREATE INDEX author_id IF NOT EXISTS FOR (a:Author) ON (a.authorId)",
            "CREATE INDEX author_name IF NOT EXISTS FOR (a:Author) ON (a.name)",
        ]
        
        async with self.driver.session(database=settings.neo4j_database) as session:
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
    
    async def get_paper_by_external_id(self, id_type: str, id_value: str) -> Optional[Dict]:
        """根据外部ID获取论文"""
        query = """
        MATCH (p:Paper)-[:HAS_EXTERNAL_ID]->(e:ExternalId {type: $id_type, value: $id_value})
        RETURN p
        """
        
        async with self.driver.session(database=settings.neo4j_database) as session:
            try:
                result = await session.run(query, id_type=id_type, id_value=id_value)
                record = await result.single()
                if record:
                    paper_node = record["p"]
                    node_props = dict(paper_node)
                    data_json = node_props.get("dataJson")
                    if isinstance(data_json, str) and data_json:
                        try:
                            payload = json.loads(data_json)
                            if node_props.get("lastUpdated") is not None:
                                payload["lastUpdated"] = node_props.get("lastUpdated")
                            return payload
                        except Exception:
                            return node_props
                    return node_props
                return None
            except Exception as e:
                logger.error(f"Neo4j根据外部ID获取论文失败 {id_type}={id_value}: {e}")
                return None

    async def get_paper_by_alias(self, raw_identifier: str) -> Optional[Dict]:
        """根据输入自动识别并通过别名/ID获取论文。

        识别顺序（精确优先）：
        - 显式前缀：DOI:/ARXIV:/MAG:/ACL:/PMID:/PMCID:/CorpusId:/URL:
        - DOI (以 10. 开头)
        - URL (http/https)
        - ArXiv (包含 arxiv 或 形如 1234.56789/v2)
        - CorpusId (纯数字)
        - S2 sha（40位十六进制）
        - 直接当作 paperId 尝试
        - TITLE_NORM（强匹配，不做模糊）
        """
        try:
            s = (raw_identifier or "").strip()
            if not s:
                return None

            # 1) 解析显式类型前缀：TYPE:value
            if ":" in s:
                head, tail = s.split(":", 1)
                t = head.strip().upper()
                v = tail.strip()
                if t == "DOI":
                    norm = self._normalize_doi(v)
                    if norm:
                        hit = await self.get_paper_by_external_id("DOI", norm)
                        if hit:
                            return hit
                elif t in ("ARXIV", "ARXIv"):
                    norm = self._normalize_arxiv(v)
                    if norm:
                        hit = await self.get_paper_by_external_id("ArXiv", norm)
                        if hit:
                            return hit
                elif t in ("CORPUSID", "CORPUS"):
                    norm = self._normalize_corpus_id(v)
                    if norm is not None:
                        hit = await self.get_paper_by_external_id("CorpusId", norm)
                        if hit:
                            return hit
                elif t == "MAG":
                    norm = self._normalize_mag(v)
                    if norm is not None:
                        hit = await self.get_paper_by_external_id("MAG", norm)
                        if hit:
                            return hit
                elif t == "ACL":
                    norm = self._normalize_acl(v)
                    if norm:
                        hit = await self.get_paper_by_external_id("ACL", norm)
                        if hit:
                            return hit
                elif t == "PMID":
                    norm = self._normalize_pmid(v)
                    if norm is not None:
                        hit = await self.get_paper_by_external_id("PMID", norm)
                        if hit:
                            return hit
                elif t == "PMCID":
                    norm = self._normalize_pmcid(v)
                    if norm is not None:
                        hit = await self.get_paper_by_external_id("PMCID", norm)
                        if hit:
                            return hit
                elif t == "URL":
                    norm = self._normalize_url(v)
                    if norm:
                        hit = await self.get_paper_by_external_id("URL", norm)
                        if hit:
                            return hit

            # DOI
            if s.startswith("10."):
                v = self._normalize_doi(s)
                if v:
                    found = await self.get_paper_by_external_id("DOI", v)
                    if found:
                        return found

            # URL
            if s.lower().startswith("http"):
                v = self._normalize_url(s)
                if v:
                    found = await self.get_paper_by_external_id("URL", v)
                    if found:
                        return found
                # 兼容路径末尾含斜杠与无查询的轻微差异：再尝试去除末尾斜杠
                try:
                    if v and v.endswith('/'):
                        v2 = v[:-1]
                        found = await self.get_paper_by_external_id("URL", v2)
                        if found:
                            return found
                except Exception:
                    pass

            # ArXiv
            low = s.lower()
            import re as _re
            if "arxiv" in low or _re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", s):
                v = self._normalize_arxiv(s)
                if v:
                    found = await self.get_paper_by_external_id("ArXiv", v)
                    if found:
                        return found

            # CorpusId（纯数字）
            if s.isdigit():
                try:
                    v = self._normalize_corpus_id(s)
                    found = await self.get_paper_by_external_id("CorpusId", v)
                    if found:
                        return found
                except Exception:
                    pass

            # S2 sha（40位十六进制）
            try:
                import re as _re2
                if _re2.fullmatch(r"[0-9a-fA-F]{40}", s):
                    direct = await self.get_paper(s)
                    if direct:
                        return direct
            except Exception:
                pass

            # 直接按 paperId 获取
            direct = await self.get_paper(s)
            if direct:
                return direct

            # 最后尝试 TITLE_NORM
            tnorm = self._normalize_title_norm(s)
            if tnorm:
                title_hit = await self.get_paper_by_external_id("TITLE_NORM", tnorm)
                if title_hit:
                    return title_hit
        except Exception as e:
            logger.error(f"根据别名获取论文失败 id={raw_identifier}: {e}")
        return None
    
    async def merge_paper(self, paper_data: Dict) -> bool:
        """插入或更新论文数据"""
        query = """
        MERGE (p:Paper {paperId: $paper_id})
        SET p += $properties,
            p.lastUpdated = datetime(),
            p.dataJson = $data_json,
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
        """处理外部ID关系"""
        for id_type, id_value in external_ids.items():
            if not id_value:
                continue

            # 统一归一化，同步与别名合并逻辑，避免重复节点
            normalized_value: Optional[str] = None
            try:
                t = str(id_type).strip()
                if t == "DOI":
                    normalized_value = self._normalize_doi(str(id_value))
                elif t == "ArXiv":
                    normalized_value = self._normalize_arxiv(str(id_value))
                elif t == "CorpusId":
                    normalized_value = self._normalize_corpus_id(id_value)
                elif t == "MAG":
                    normalized_value = self._normalize_mag(id_value)
                elif t == "ACL":
                    normalized_value = self._normalize_acl(str(id_value))
                elif t == "PMID":
                    normalized_value = self._normalize_pmid(id_value)
                elif t == "PMCID":
                    normalized_value = self._normalize_pmcid(id_value)
                elif t == "URL":
                    normalized_value = self._normalize_url(str(id_value))
            except Exception:
                normalized_value = None

            final_value = normalized_value if normalized_value else str(id_value)

            query = """
            MATCH (p:Paper {paperId: $paper_id})
            MERGE (e:ExternalId {type: $id_type, value: $id_value})
            SET e:Alias
            MERGE (p)-[:HAS_EXTERNAL_ID]->(e)
            """
            try:
                await session.run(
                    query,
                    paper_id=paper_id,
                    id_type=id_type,
                    id_value=final_value,
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

    async def merge_aliases_from_paper(self, paper_data: Dict) -> bool:
        """基于论文数据合并规范化的别名。

        支持类型：DOI/ArXiv/CorpusId/URL/TITLE_NORM/MAG/ACL/PMID/PMCID
        """
        try:
            paper_id = paper_data.get("paperId")
            if not paper_id:
                return False

            aliases: List[Dict[str, str]] = []

            # externalIds: DOI / ArXiv / CorpusId
            ext = paper_data.get("externalIds") or {}
            doi = ext.get("DOI")
            if isinstance(doi, str):
                norm = self._normalize_doi(doi)
                if norm:
                    aliases.append({"type": "DOI", "value": norm})
            arxiv = ext.get("ArXiv")
            if isinstance(arxiv, str):
                norm = self._normalize_arxiv(arxiv)
                if norm:
                    aliases.append({"type": "ArXiv", "value": norm})
            corpus = ext.get("CorpusId") or paper_data.get("corpusId")
            if corpus is not None:
                try:
                    aliases.append({"type": "CorpusId", "value": self._normalize_corpus_id(corpus)})
                except Exception:
                    pass
            mag = ext.get("MAG")
            if mag is not None:
                try:
                    aliases.append({"type": "MAG", "value": self._normalize_mag(mag)})
                except Exception:
                    pass
            acl = ext.get("ACL")
            if isinstance(acl, str):
                norm = self._normalize_acl(acl)
                if norm:
                    aliases.append({"type": "ACL", "value": norm})
            pmid = ext.get("PMID")
            if pmid is not None:
                try:
                    aliases.append({"type": "PMID", "value": self._normalize_pmid(pmid)})
                except Exception:
                    pass
            pmcid = ext.get("PMCID")
            if pmcid is not None:
                try:
                    aliases.append({"type": "PMCID", "value": self._normalize_pmcid(pmcid)})
                except Exception:
                    pass

            # URL（优先使用顶层url，其次externalIds.URL）
            url = paper_data.get("url")
            if isinstance(url, str):
                norm = self._normalize_url(url)
                if norm:
                    aliases.append({"type": "URL", "value": norm})
            else:
                url2 = ext.get("URL")
                if isinstance(url2, str):
                    norm2 = self._normalize_url(url2)
                    if norm2:
                        aliases.append({"type": "URL", "value": norm2})

            # TITLE_NORM（强匹配用，避免模糊）
            title = paper_data.get("title")
            if isinstance(title, str):
                norm = self._normalize_title_norm(title)
                if norm:
                    aliases.append({"type": "TITLE_NORM", "value": norm})

            if not aliases:
                return True

            cypher = """
            MATCH (p:Paper {paperId: $paper_id})
            UNWIND $aliases AS a
            MERGE (e:ExternalId {type: a.type, value: a.value})
            SET e:Alias
            MERGE (p)-[:HAS_EXTERNAL_ID]->(e)
            """

            async with self.driver.session(database=settings.neo4j_database) as session:
                await session.run(cypher, paper_id=paper_id, aliases=aliases)
            return True
        except Exception as e:
            safe_id = None
            try:
                safe_id = paper_data.get("paperId")
            except Exception:
                pass
            logger.error(f"合并别名失败 paper_id={safe_id}: {e}")
            return False

    async def merge_data_chunks_from_full_data(self, paper_data: Dict) -> bool:
        """为给定论文写入三类 DataChunk（metadata/citations/references）。"""
        try:
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
                # metadata
                try:
                    q = """
                    MATCH (p:Paper {paperId: $paper_id})
                    MERGE (m:DataChunk:PaperMetadata {paperId: $paper_id, chunkType: 'metadata'})
                    SET m.dataJson = $metadata_json, m.lastUpdated = datetime()
                    MERGE (p)-[:HAS_METADATA]->(m)
                    """
                    await session.run(q, paper_id=paper_id, metadata_json=metadata_json)
                except Exception as e:
                    logger.error(f"写入metadata数据块失败 paper_id={paper_id}: {e}")

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
            paper_id = paper_data.get("paperId")
            if not paper_id:
                return False

            refs_raw = paper_data.get("references") if isinstance(paper_data.get("references"), list) else []
            cites_raw = paper_data.get("citations") if isinstance(paper_data.get("citations"), list) else []

            references = [
                {"paperId": r.get("paperId"), "title": r.get("title")}
                for r in refs_raw if isinstance(r, dict) and r.get("paperId")
            ]
            citations = [
                {"paperId": c.get("paperId"), "title": c.get("title")}
                for c in cites_raw if isinstance(c, dict) and c.get("paperId")
            ]

            async with self.driver.session(database=settings.neo4j_database) as session:
                # references: (p)-[:CITES]->(ref)
                if references:
                    q_ref = """
                    MATCH (p:Paper {paperId: $paper_id})
                    UNWIND $references AS ref
                    MERGE (r:Paper {paperId: ref.paperId})
                    ON CREATE SET r.title = ref.title, r.ingestStatus = 'stub'
                    MERGE (p)-[:CITES]->(r)
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
                    ON CREATE SET c.title = cite.title, c.ingestStatus = 'stub'
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

    def _normalize_doi(self, doi: str) -> Optional[str]:
        try:
            value = doi.strip().lower()
            return value if value else None
        except Exception:
            return None

    def _normalize_arxiv(self, arxiv_id: str) -> Optional[str]:
        try:
            import re
            s = str(arxiv_id).strip()
            # 去除大小写不敏感前缀
            s = re.sub(r"(?i)^arxiv:", "", s).strip()
            # 去除末尾版本标记 vN / VN
            s = re.sub(r"(?i)v\d+$", "", s).strip()
            # 提取标准新格式 1234.56789（4位.4-5位）
            m = re.match(r"^\d{4}\.\d{4,5}$", s)
            if m:
                return s
            m2 = re.search(r"(\d{4}\.\d{4,5})", s)
            if m2:
                return m2.group(1)
            return s if s else None
        except Exception:
            return None

    def _normalize_url(self, url: str) -> Optional[str]:
        try:
            from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
            u = urlparse(url.strip())
            scheme = u.scheme.lower() or 'http'
            netloc = u.netloc.lower()
            path = u.path.rstrip('/') or '/'
            # 过滤追踪参数
            q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=False) if not k.lower().startswith('utm_')]
            query = urlencode(q)
            return urlunparse((scheme, netloc, path, '', query, ''))
        except Exception:
            return None

    def _normalize_title_norm(self, title: str) -> Optional[str]:
        try:
            import re
            t = title.lower()
            t = re.sub(r"\s+", " ", t)
            t = re.sub(r"[\p{P}\p{S}]", "", t)
            t = t.strip()
            return t if t else None
        except Exception:
            try:
                return title.strip().lower() or None
            except Exception:
                return None

    def _normalize_corpus_id(self, value: Any) -> str:
        return str(int(value))

    def _normalize_mag(self, value: Any) -> str:
        return str(int(value))

    def _normalize_pmid(self, value: Any) -> str:
        return str(int(value))

    def _normalize_pmcid(self, value: Any) -> str:
        # 接受 "2323736" 或 "PMC2323736"，统一为数字字符串
        try:
            s = str(value).strip().upper()
            if s.startswith('PMC'):
                s = s[3:]
            return str(int(s))
        except Exception:
            return str(int(value))

    def _normalize_acl(self, value: str) -> Optional[str]:
        try:
            v = value.strip().upper()
            # 规范化连字符等
            v = v.replace('_', '-').replace(' ', '')
            return v if v else None
        except Exception:
            return None
    
    async def create_citation_relation(self, citing_paper_id: str, cited_paper_id: str) -> bool:
        """创建引用关系"""
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
    
    async def get_citations(self, paper_id: str, limit: int = 100) -> List[Dict]:
        """获取论文的引用文献"""
        query = """
        MATCH (p:Paper {paperId: $paper_id})<-[:CITES]-(citing:Paper)
        RETURN citing
        ORDER BY citing.citationCount DESC
        LIMIT $limit
        """
        
        async with self.driver.session(database=settings.neo4j_database) as session:
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
        
        async with self.driver.session(database=settings.neo4j_database) as session:
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
        
        async with self.driver.session(database=settings.neo4j_database) as session:
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
            "total_external_ids": "MATCH (e:ExternalId) RETURN count(e) as count"
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


# 全局Neo4j客户端实例
neo4j_client = Neo4jClient()
