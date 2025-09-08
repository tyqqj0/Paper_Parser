"""
基于官方SDK的Semantic Scholar客户端封装
"""
from typing import Optional, List, Dict, Any, Union
from loguru import logger
from semanticscholar import AsyncSemanticScholar
from semanticscholar.Paper import Paper as S2Paper
from semanticscholar.Author import Author as S2Author

from app.core.config import settings


class S2SDKClient:
    """
    基于官方SDK的Semantic Scholar客户端
    提供统一的异步接口和错误处理
    """
    
    def __init__(self):
        self.client = AsyncSemanticScholar(
            api_key=settings.s2_api_key,
            timeout=settings.s2_timeout,
            retry=True
        )
        logger.info("S2 SDK客户端初始化完成")
    
    async def get_paper(
        self, 
        paper_id: str, 
        fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取论文详情
        
        Args:
            paper_id: 论文ID (支持S2 paperId, DOI, ArXiv等)
            fields: 需要返回的字段列表
            
        Returns:
            论文数据字典，失败返回None
        """
        try:
            # 使用默认字段或自定义字段
            if not fields:
                fields = [
                    'paperId', 'title', 'abstract', 'year', 'authors',
                    'citationCount', 'referenceCount', 'influentialCitationCount',
                    'fieldsOfStudy', 's2FieldsOfStudy', 'publicationDate',
                    'journal', 'venue', 'externalIds', 'url', 'openAccessPdf',
                    'publicationVenue', 'publicationTypes', 'isOpenAccess'
                ]
            
            paper: S2Paper = await self.client.get_paper(
                paper_id=paper_id,
                fields=fields
            )
            
            if paper:
                # 返回原始JSON数据，便于缓存和处理
                return paper.raw_data
            return None
            
        except Exception as e:
            logger.error(f"SDK获取论文失败 paper_id={paper_id}: {e}")
            return None
    
    async def search_papers(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        fields: Optional[List[str]] = None,
        year: Optional[str] = None,
        venue: Optional[List[str]] = None,
        fields_of_study: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        搜索论文
        
        Args:
            query: 搜索查询
            limit: 返回数量限制
            offset: 偏移量
            fields: 返回字段
            year: 年份过滤 (格式: "2020" 或 "2020-2023")
            venue: 会议/期刊过滤
            fields_of_study: 研究领域过滤
            
        Returns:
            搜索结果字典
        """
        try:
            if not fields:
                fields = [
                    'paperId', 'title', 'abstract', 'year', 'authors',
                    'citationCount', 'venue', 'fieldsOfStudy', 'url'
                ]
            
            results = await self.client.search_paper(
                query=query,
                limit=limit,
                offset=offset,
                fields=fields,
                year=year,
                venue=venue,
                fields_of_study=fields_of_study
            )
            
            if results:
                # 转换为统一格式
                return {
                    'total': results.total,
                    'offset': offset,
                    'data': [paper.raw_data for paper in results]
                }
            return None
            
        except Exception as e:
            logger.error(f"SDK搜索论文失败 query={query}: {e}")
            return None
    
    async def get_paper_citations(
        self,
        paper_id: str,
        limit: int = 10,
        offset: int = 0,
        fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """获取论文引用"""
        try:
            if not fields:
                fields = [
                    'paperId', 'title', 'year', 'authors', 'citationCount', 'venue'
                ]
            
            citations = await self.client.get_paper_citations(
                paper_id=paper_id,
                limit=limit,
                offset=offset,
                fields=fields
            )
            
            if citations:
                return {
                    'total': citations.total,
                    'offset': offset,
                    'data': [citation.citingPaper.raw_data for citation in citations]
                }
            return None
            
        except Exception as e:
            logger.error(f"SDK获取引用失败 paper_id={paper_id}: {e}")
            return None
    
    async def get_paper_references(
        self,
        paper_id: str,
        limit: int = 10,
        offset: int = 0,
        fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """获取论文参考文献"""
        try:
            if not fields:
                fields = [
                    'paperId', 'title', 'year', 'authors', 'citationCount', 'venue'
                ]
            
            references = await self.client.get_paper_references(
                paper_id=paper_id,
                limit=limit,
                offset=offset,
                fields=fields
            )
            
            if references:
                return {
                    'total': references.total,
                    'offset': offset,
                    'data': [ref.citedPaper.raw_data for ref in references]
                }
            return None
            
        except Exception as e:
            logger.error(f"SDK获取参考文献失败 paper_id={paper_id}: {e}")
            return None
    
    async def get_papers_batch(
        self,
        paper_ids: List[str],
        fields: Optional[List[str]] = None
    ) -> List[Optional[Dict[str, Any]]]:
        """批量获取论文"""
        try:
            if not fields:
                fields = [
                    'paperId', 'title', 'abstract', 'year', 'authors',
                    'citationCount', 'venue', 'fieldsOfStudy'
                ]
            
            papers = await self.client.get_papers(
                paper_ids=paper_ids,
                fields=fields
            )
            
            # 保持顺序，失败的返回None
            results = []
            for paper in papers:
                if paper:
                    results.append(paper.raw_data)
                else:
                    results.append(None)
            
            return results
            
        except Exception as e:
            logger.error(f"SDK批量获取论文失败: {e}")
            return [None] * len(paper_ids)
    
    async def get_author(
        self,
        author_id: str,
        fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """获取作者信息"""
        try:
            if not fields:
                fields = [
                    'authorId', 'name', 'affiliations', 'homepage', 'paperCount',
                    'citationCount', 'hIndex', 'externalIds'
                ]
            
            author: S2Author = await self.client.get_author(
                author_id=author_id,
                fields=fields
            )
            
            if author:
                return author.raw_data
            return None
            
        except Exception as e:
            logger.error(f"SDK获取作者失败 author_id={author_id}: {e}")
            return None
    
    async def autocomplete_paper(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """论文自动补全"""
        try:
            results = await self.client.get_paper_autocomplete(query=query)
            
            if results:
                return [item.raw_data for item in results]
            return None
            
        except Exception as e:
            logger.error(f"SDK自动补全失败 query={query}: {e}")
            return None


# 全局客户端实例
s2_client = S2SDKClient()
