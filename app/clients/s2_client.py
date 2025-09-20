"""
基于官方SDK的Semantic Scholar客户端封装
"""
from typing import Optional, List, Dict, Any, Union
import hashlib
import json
import asyncio
from loguru import logger
from ..utils.semanticscholar import AsyncSemanticScholar
from ..utils.semanticscholar import Paper as S2Paper
from ..utils.semanticscholar import Author as S2Author

from app.core.config import settings, ErrorCodes
from app.models import S2ApiException
from aiohttp.client_exceptions import ClientError


class S2SDKClient:
    """
    基于官方SDK的Semantic Scholar客户端
    提供统一的异步接口和错误处理
    """
    
    def __init__(self):
        logger.info(f"[S2 DEBUG] 初始化S2客户端...")
        logger.info(f"[S2 DEBUG] API Key状态: {'已设置' if settings.s2_api_key else '未设置'}")
        logger.info(f"[S2 DEBUG] 超时设置: {settings.s2_timeout}秒")
        logger.info(f"[S2 DEBUG] 基础URL: {getattr(settings, 's2_base_url', 'default')}")
        
        self.client = AsyncSemanticScholar(
            api_key=settings.s2_api_key,
            timeout=settings.s2_timeout,
            retry=True
        )
        logger.info("[S2 INFO] S2 SDK客户端初始化完成")
    
    async def disconnect(self):
        try:
            await self.client.close()
        except Exception:
            pass

    async def health_check(self) -> bool:
        """简易健康检查：尝试一次极小代价请求或利用SDK状态。"""
        try:
            # 使用一个轻量健康检查：检查根 endpoints 可达性
            # SDK 没有直接健康检查接口，尝试一次极小limit的搜索
            _ = await self.client.search_paper(query="test", limit=1)
            return True
        except ClientError:
            return False
        except Exception:
            return False

    def generate_query_hash(
        self,
        query: str,
        *,
        offset: int = 0,
        limit: int = 10,
        fields: Optional[str] = None,
        year: Optional[str] = None,
        venue: Optional[str] = None,
        fields_of_study: Optional[str] = None,
        match_title: bool = False,
        prefer_local: bool = True,
        fallback_to_s2: bool = True,
    ) -> str:
        """生成稳定的搜索查询哈希，用于缓存键。

        说明：对参数进行规范化与排序，避免同义参数顺序导致的缓存击穿。
        """
        normalized = {
            'query': query or '',
            'offset': int(offset or 0),
            'limit': int(limit or 10),
            'fields': ','.join(sorted([f.strip() for f in fields.split(',')])) if fields else None,
            'year': str(year) if year else None,
            'venue': ','.join(sorted([v.strip() for v in venue.split(',')])) if venue else None,
            'fields_of_study': ','.join(sorted([f.strip() for f in fields_of_study.split(',')])) if fields_of_study else None,
            'match_title': bool(match_title),
            'prefer_local': bool(prefer_local),
            'fallback_to_s2': bool(fallback_to_s2),
        }
        payload = json.dumps(normalized, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()
    
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
        logger.debug(f"[S2 DEBUG] 开始获取论文详情 - paper_id='{paper_id}'")
        
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
            
            logger.debug(f"[S2 DEBUG] 使用字段: {fields}")
            logger.info(f"[S2 API] 调用获取论文接口 - paper_id='{paper_id}'")
            
            paper: S2Paper = await self.client.get_paper(
                paper_id=paper_id,
                fields=fields
            )
            logger.debug(f"[S2 DEBUG] API响应论文对象类型: {type(paper)}")
            logger.debug(f"[S2 DEBUG] paper是否为None: {paper is None}")
            if paper:
                logger.debug(f"[S2 DEBUG] 论文标题: {getattr(paper, 'title', 'N/A')}")
                logger.info(f"[S2 API] 成功获取论文 - {paper.title}")
                return paper.raw_data
            else:
                logger.warning(f"[S2 API] 论文未找到 - paper_id='{paper_id}'")
                return None
            
        except S2ApiException:
            # 直接重新抛出S2ApiException，保持原始错误码
            raise
        except Exception as e:
            logger.error(f"[S2 ERROR] SDK获取论文失败 paper_id='{paper_id}': {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"[S2 DEBUG] 完整错误堆栈:\n{traceback.format_exc()}")
            
            # 区分不同类型的错误并抛出相应的异常
            error_msg = str(e).lower()
            if '404' in error_msg or 'not found' in error_msg or 'objectnotfoundexception' in str(type(e)).lower():
                raise S2ApiException(f"论文不存在: {paper_id}", ErrorCodes.NOT_FOUND)
            elif 'rate limit' in error_msg or '429' in error_msg:
                raise S2ApiException("请求过于频繁，请稍后再试", ErrorCodes.S2_RATE_LIMITED)
            elif 'timeout' in error_msg or 'timed out' in error_msg:
                raise S2ApiException("请求超时", ErrorCodes.TIMEOUT)
            elif 'network' in error_msg or 'connection' in error_msg or 'unreachable' in error_msg:
                raise S2ApiException("网络连接失败", ErrorCodes.S2_NETWORK_ERROR)
            elif '401' in error_msg or '403' in error_msg or 'unauthorized' in error_msg:
                raise S2ApiException("API认证失败", ErrorCodes.S2_AUTH_ERROR)
            elif '503' in error_msg or '502' in error_msg or 'unavailable' in error_msg:
                raise S2ApiException("上游API服务不可用", ErrorCodes.S2_UNAVAILABLE)
            else:
                raise S2ApiException(f"获取论文失败: {e}", ErrorCodes.S2_API_ERROR)
    
    async def search_papers(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        fields: Optional[List[str]] = None,
        year: Optional[str] = None,
        venue: Optional[List[str]] = None,
        fields_of_study: Optional[List[str]] = None,
        match_title: bool = False,
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
        logger.debug(f"[S2 DEBUG] 开始搜索论文 - query='{query}', limit={limit}, offset={offset}")
        logger.debug(f"[S2 DEBUG] 搜索参数 - year={year}, venue={venue}, fields_of_study={fields_of_study}")
        
        try:
            if not fields:
                fields = [
                    'paperId', 'title', 'abstract', 'year', 'authors',
                    'citationCount', 'venue', 'fieldsOfStudy', 'url'
                ]
            
            logger.debug(f"[S2 DEBUG] 使用字段: {fields}")
            
            # 标题精准匹配模式：返回最佳1条
            if match_title:
                logger.info(f"[S2 API] 调用精准匹配接口 - query='{query}'")
                paper = await self.client.search_paper(
                    query=query,
                    limit=1,
                    fields=fields,
                    match_title=True
                )
                if paper:
                    return {
                        'total': 1,
                        'offset': 0,
                        'data': [paper.raw_data]
                    }
                return {
                    'total': 0,
                    'offset': 0,
                    'data': []
                }

            # SDK 不支持 offset 入参，使用分页+本地切片实现
            needed_count = max(0, offset) + max(0, limit)
            page_size = min(100, max(1, needed_count))  # search 接口单页上限 100
            
            logger.debug(f"[S2 DEBUG] 计算分页 - needed_count={needed_count}, page_size={page_size}")

            logger.info(f"[S2 API] 调用搜索接口 - query='{query}', page_size={page_size}")
            
            # SDK 目前接受逗号分隔字符串，确保将列表参数规范化
            venue_param: Optional[Union[str, List[str]]]
            fos_param: Optional[Union[str, List[str]]]
            try:
                venue_param = ','.join(venue) if isinstance(venue, list) else venue
            except Exception:
                venue_param = venue
            try:
                fos_param = ','.join(fields_of_study) if isinstance(fields_of_study, list) else fields_of_study
            except Exception:
                fos_param = fields_of_study

            results = await self.client.search_paper(
                query=query,
                limit=page_size,
                fields=fields,
                year=year,
                venue=venue_param,
                fields_of_study=fos_param
            )
            logger.debug(f"[S2 DEBUG] API响应结果类型: {type(results)}")
            logger.debug(f"[S2 DEBUG] results是否为None: {results is None}")
            if results:
                logger.debug(f"[S2 DEBUG] results.total: {getattr(results, 'total', 'N/A')}")
                items: List[Dict[str, Any]] = []
                item_count = 0
                logger.debug(f"[S2 DEBUG] 开始遍历结果...")
                for paper in (results.items if hasattr(results, 'items') else results):
                    item_count += 1
                    logger.debug(f"[S2 DEBUG] 处理第{item_count}篇论文: {paper.title if hasattr(paper, 'title') else 'N/A'}")
                    items.append(paper.raw_data)
                    if len(items) >= needed_count:
                        logger.debug(f"[S2 DEBUG] 已获取足够结果，停止遍历")
                        break
                logger.info(f"[S2 API] 获取到{len(items)}篇论文")
                sliced_items = items[offset:offset + limit] if offset else items[:limit]
                result = {
                    'total': results.total,
                    'offset': offset,
                    'data': sliced_items
                }
                logger.debug(f"[S2 DEBUG] 返回结果 - total={result['total']}, 实际返回={len(result['data'])}篇")
                return result
            else:
                logger.warning(f"[S2 API] 搜索无结果 - query='{query}'")
                return {
                    'total': 0,
                    'offset': offset,
                    'data': []
                }
            
        except Exception as e:
            logger.error(f"[S2 ERROR] SDK搜索论文失败 query='{query}': {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"[S2 DEBUG] 完整错误堆栈:\n{traceback.format_exc()}")
            
            # 区分不同类型的错误并抛出相应的异常
            error_msg = str(e).lower()
            if 'rate limit' in error_msg or '429' in error_msg:
                raise S2ApiException("搜索请求过于频繁，请稍后再试", ErrorCodes.S2_RATE_LIMITED)
            elif 'timeout' in error_msg or 'timed out' in error_msg:
                raise S2ApiException("搜索请求超时", ErrorCodes.TIMEOUT)
            elif 'network' in error_msg or 'connection' in error_msg or 'unreachable' in error_msg:
                raise S2ApiException("网络连接失败", ErrorCodes.S2_NETWORK_ERROR)
            elif '401' in error_msg or '403' in error_msg or 'unauthorized' in error_msg:
                raise S2ApiException("API认证失败", ErrorCodes.S2_AUTH_ERROR)
            elif '503' in error_msg or '502' in error_msg or 'unavailable' in error_msg:
                raise S2ApiException("上游API服务不可用", ErrorCodes.S2_UNAVAILABLE)
            else:
                raise S2ApiException(f"搜索失败: {e}", ErrorCodes.S2_API_ERROR)
    
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
            
            # SDK 不支持 offset 入参，使用分页+本地切片实现
            needed_count = max(0, offset) + max(0, limit)
            page_size = min(1000, max(1, needed_count))  # citations 单页上限 1000

            citations = await self.client.get_paper_citations(
                paper_id=paper_id,
                limit=page_size,
                fields=fields
            )
            if citations:
                items: List[Dict[str, Any]] = []
                for citation in (citations.items if hasattr(citations, 'items') else citations):
                    paper_obj = getattr(citation, 'paper', None)
                    if paper_obj is not None and hasattr(paper_obj, 'raw_data'):
                        items.append(paper_obj.raw_data)
                    if len(items) >= needed_count:
                        break
                
                # 确定真实的总数
                if hasattr(citations, 'total'):
                    total_count = citations.total
                else:
                    # 如果没有total字段，需要获取所有数据来确定真实总数
                    if len(items) < needed_count:
                        # 如果获取的数据少于需要的数量，说明已经是全部数据
                        total_count = len(items)
                    else:
                        # 需要获取更多数据来确定真实总数
                        all_citations = await self.client.get_paper_citations(
                            paper_id=paper_id,
                            limit=10000,  # 获取足够多的数据
                            fields=fields
                        )
                        all_items: List[Dict[str, Any]] = []
                        for citation in (all_citations.items if hasattr(all_citations, 'items') else all_citations):
                            paper_obj = getattr(citation, 'paper', None)
                            if paper_obj is not None and hasattr(paper_obj, 'raw_data'):
                                all_items.append(paper_obj.raw_data)
                        total_count = len(all_items)
                        # 使用所有数据进行切片
                        items = all_items
                
                sliced_items = items[offset:offset + limit] if offset else items[:limit]
                return {
                    'total': total_count,
                    'offset': offset,
                    'data': sliced_items
                }
            return {'total': 0, 'offset': offset, 'data': []}
            
        except S2ApiException:
            # 直接重新抛出S2ApiException，保持原始错误码
            raise
        except Exception as e:
            logger.error(f"[S2 ERROR] SDK获取引用失败 paper_id='{paper_id}': {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"[S2 DEBUG] 完整错误堆栈:\n{traceback.format_exc()}")
            
            # 区分不同类型的错误并抛出相应的异常
            error_msg = str(e).lower()
            if '404' in error_msg or 'not found' in error_msg or 'objectnotfoundexception' in str(type(e)).lower():
                raise S2ApiException(f"论文不存在: {paper_id}", ErrorCodes.NOT_FOUND)
            elif 'rate limit' in error_msg or '429' in error_msg:
                raise S2ApiException("请求过于频繁，请稍后再试", ErrorCodes.S2_RATE_LIMITED)
            elif 'timeout' in error_msg or 'timed out' in error_msg:
                raise S2ApiException("请求超时", ErrorCodes.TIMEOUT)
            elif 'network' in error_msg or 'connection' in error_msg or 'unreachable' in error_msg:
                raise S2ApiException("网络连接失败", ErrorCodes.S2_NETWORK_ERROR)
            elif '401' in error_msg or '403' in error_msg or 'unauthorized' in error_msg:
                raise S2ApiException("API认证失败", ErrorCodes.S2_AUTH_ERROR)
            elif '503' in error_msg or '502' in error_msg or 'unavailable' in error_msg:
                raise S2ApiException("上游API服务不可用", ErrorCodes.S2_UNAVAILABLE)
            else:
                raise S2ApiException(f"获取引用失败: {e}", ErrorCodes.S2_API_ERROR)
    
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
            
            # SDK 不支持 offset 入参，使用分页+本地切片实现
            needed_count = max(0, offset) + max(0, limit)
            page_size = min(1000, max(1, needed_count))  # references 单页上限 1000

            references = await self.client.get_paper_references(
                paper_id=paper_id,
                limit=page_size,
                fields=fields
            )
            if references:
                items: List[Dict[str, Any]] = []
                for ref in (references.items if hasattr(references, 'items') else references):
                    paper_obj = getattr(ref, 'paper', None)
                    if paper_obj is not None and hasattr(paper_obj, 'raw_data'):
                        items.append(paper_obj.raw_data)
                    if len(items) >= needed_count:
                        break
                
                # 确定真实的总数
                if hasattr(references, 'total'):
                    total_count = references.total
                else:
                    # 如果没有total字段，需要获取所有数据来确定真实总数
                    if len(items) < needed_count:
                        # 如果获取的数据少于需要的数量，说明已经是全部数据
                        total_count = len(items)
                    else:
                        # 需要获取更多数据来确定真实总数
                        all_references = await self.client.get_paper_references(
                            paper_id=paper_id,
                            limit=10000,  # 获取足够多的数据
                            fields=fields
                        )
                        all_items: List[Dict[str, Any]] = []
                        for ref in (all_references.items if hasattr(all_references, 'items') else all_references):
                            paper_obj = getattr(ref, 'paper', None)
                            if paper_obj is not None and hasattr(paper_obj, 'raw_data'):
                                all_items.append(paper_obj.raw_data)
                        total_count = len(all_items)
                        # 使用所有数据进行切片
                        items = all_items
                
                sliced_items = items[offset:offset + limit] if offset else items[:limit]
                return {
                    'total': total_count,
                    'offset': offset,
                    'data': sliced_items
                }
            return {'total': 0, 'offset': offset, 'data': []}
            
        except S2ApiException:
            # 直接重新抛出S2ApiException，保持原始错误码
            raise
        except Exception as e:
            logger.error(f"[S2 ERROR] SDK获取参考文献失败 paper_id='{paper_id}': {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"[S2 DEBUG] 完整错误堆栈:\n{traceback.format_exc()}")
            
            # 区分不同类型的错误并抛出相应的异常
            error_msg = str(e).lower()
            if '404' in error_msg or 'not found' in error_msg or 'objectnotfoundexception' in str(type(e)).lower():
                raise S2ApiException(f"论文不存在: {paper_id}", ErrorCodes.NOT_FOUND)
            elif 'rate limit' in error_msg or '429' in error_msg:
                raise S2ApiException("请求过于频繁，请稍后再试", ErrorCodes.S2_RATE_LIMITED)
            elif 'timeout' in error_msg or 'timed out' in error_msg:
                raise S2ApiException("请求超时", ErrorCodes.TIMEOUT)
            elif 'network' in error_msg or 'connection' in error_msg or 'unreachable' in error_msg:
                raise S2ApiException("网络连接失败", ErrorCodes.S2_NETWORK_ERROR)
            elif '401' in error_msg or '403' in error_msg or 'unauthorized' in error_msg:
                raise S2ApiException("API认证失败", ErrorCodes.S2_AUTH_ERROR)
            elif '503' in error_msg or '502' in error_msg or 'unavailable' in error_msg:
                raise S2ApiException("上游API服务不可用", ErrorCodes.S2_UNAVAILABLE)
            else:
                raise S2ApiException(f"获取参考文献失败: {e}", ErrorCodes.S2_API_ERROR)
    
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
