"""
核心论文服务 - 实现三级缓存策略
"""
import asyncio
import json
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from fastapi import HTTPException
from loguru import logger

from app.core.config import settings, CacheKeys, ErrorCodes
from app.clients.redis_client import redis_client
from app.clients.neo4j_client import neo4j_client
from app.clients.s2_client import s2_client
from app.models.paper import EnhancedPaper, PaperFieldsConfig, SearchResult, BatchResult
from app.models.exception import S2ApiException


class CorePaperService:
    """核心论文服务 - 三级缓存策略"""
    
    def __init__(self):
        self.redis = redis_client
        self.neo4j = neo4j_client
        self.s2 = s2_client
    
    async def get_paper(self, paper_id: str, fields: Optional[str] = None) -> Dict[str, Any]:
        """
        获取论文信息 - 三级缓存策略
        
        1. Redis缓存查询 (毫秒级)
        2. Neo4j持久化查询 (10ms级)  
        3. S2 API调用 (秒级)
        """
        try:
            # 1. Redis缓存查询
            cache_key = self._get_cache_key(paper_id, fields)
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                logger.debug(f"Redis缓存命中: {paper_id}")
                return cached_data
            
            # 2. Neo4j持久化查询
            neo4j_data = await self._get_from_neo4j(paper_id)
            if neo4j_data and self._is_data_fresh(neo4j_data):
                logger.debug(f"Neo4j数据命中: {paper_id}")
                
                # 异步更新Redis缓存
                asyncio.create_task(
                    self.redis.set_paper(paper_id, neo4j_data, fields)
                )
                
                return self._format_response(neo4j_data, fields)
            
            # 3. 检查是否正在处理
            task_status = await self.redis.get_task_status(paper_id)
            if task_status == "processing":
                # 等待最多3秒
                for i in range(6):
                    await asyncio.sleep(0.5)
                    cached_data = await self.redis.get(cache_key)
                    if cached_data:
                        logger.debug(f"等待后获取到缓存: {paper_id}")
                        return cached_data
                
                # 超时返回错误
                raise HTTPException(status_code=408, detail="请求处理超时，请稍后重试")
            
            # 4. 调用S2 API
            return await self._fetch_from_s2(paper_id, fields)
            
        except HTTPException:
            raise
        except S2ApiException as e:
            # 根据错误类型返回相应的HTTP状态码
            logger.error(f"获取论文上游失败 paper_id={paper_id}: {e.error_code} - {e.message}")
            
            if e.error_code == ErrorCodes.NOT_FOUND:
                raise HTTPException(status_code=404, detail=f"论文不存在: {paper_id}")
            elif e.error_code == ErrorCodes.S2_RATE_LIMITED:
                raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
            elif e.error_code == ErrorCodes.TIMEOUT:
                raise HTTPException(status_code=408, detail="请求超时")
            elif e.error_code == ErrorCodes.S2_NETWORK_ERROR:
                raise HTTPException(status_code=502, detail="网络连接失败")
            elif e.error_code == ErrorCodes.S2_AUTH_ERROR:
                raise HTTPException(status_code=401, detail="API认证失败")
            elif e.error_code == ErrorCodes.S2_UNAVAILABLE:
                raise HTTPException(status_code=503, detail="上游API服务不可用")
            else:
                raise HTTPException(status_code=500, detail=f"S2 API错误: {e.message}")
        except Exception as e:
            logger.error(f"获取论文失败 paper_id={paper_id}: {e}")
            raise HTTPException(status_code=500, detail="内部服务器错误")
    
    async def get_paper_citations(
        self, 
        paper_id: str, 
        offset: int = 0, 
        limit: int = 10,
        fields: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取论文引用 - 缓存策略"""
        cache_key = f"paper:{paper_id}:citations:{offset}:{limit}:{fields or 'default'}"
        
        # 尝试从缓存获取
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.debug(f"引用缓存命中: {paper_id}")
            return cached_data
        
        try:
            # 处理fields参数 - 转换为列表格式
            fields_list = None
            if fields:
                fields_list = [f.strip() for f in fields.split(',')]
            
            # 从S2 API获取
            citations_data = await self.s2.get_paper_citations(
                paper_id, limit, offset, fields_list
            )
            
            # 标准化空结果，避免缓存None
            if not citations_data:
                citations_data = {
                    'total': 0,
                    'offset': offset,
                    'data': []
                }

            # 统一输出字段
            shaped = {
                'total': citations_data.get('total', 0),
                'offset': citations_data.get('offset', offset),
                'citations': citations_data.get('data', []),
            }

            # 缓存结果
            await self.redis.set(cache_key, shaped, settings.cache_paper_ttl)
            
            return shaped
            
        except S2ApiException as e:
            raise HTTPException(status_code=500, detail=f"获取引用失败: {e.message}")
    
    async def get_paper_references(
        self, 
        paper_id: str, 
        offset: int = 0, 
        limit: int = 10,
        fields: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取论文参考文献 - 缓存策略"""
        cache_key = f"paper:{paper_id}:references:{offset}:{limit}:{fields or 'default'}"
        
        # 尝试从缓存获取
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.debug(f"参考文献缓存命中: {paper_id}")
            return cached_data
        
        try:
            # 处理fields参数 - 转换为列表格式
            fields_list = None
            if fields:
                fields_list = [f.strip() for f in fields.split(',')]
            
            # 从S2 API获取
            references_data = await self.s2.get_paper_references(
                paper_id, limit, offset, fields_list
            )
            
            # 标准化空结果
            if not references_data:
                references_data = {
                    'total': 0,
                    'offset': offset,
                    'data': []
                }

            # 统一输出字段
            shaped = {
                'total': references_data.get('total', 0),
                'offset': references_data.get('offset', offset),
                'references': references_data.get('data', []),
            }

            # 缓存结果
            await self.redis.set(cache_key, shaped, settings.cache_paper_ttl)
            
            return shaped
            
        except S2ApiException as e:
            raise HTTPException(status_code=500, detail=f"获取参考文献失败: {e.message}")
    
    async def search_papers(
        self,
        query: str,
        offset: int = 0,
        limit: int = 10,
        fields: Optional[str] = None,
        year: Optional[str] = None,
        venue: Optional[str] = None,
        fields_of_study: Optional[str] = None
    ) -> Dict[str, Any]:
        """搜索论文 - 缓存策略"""
        # 上层API已做空查询校验；此处不再拦截，确保空结果只因上游无匹配
        # 生成查询哈希
        query_hash = self.s2.generate_query_hash(
            query, 
            offset=offset, 
            limit=limit,
            fields=fields,
            year=year,
            venue=venue,
            fields_of_study=fields_of_study
        )
        
        cache_key = CacheKeys.SEARCH_QUERY.format(query_hash=query_hash)
        
        # 尝试从缓存获取
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.debug(f"搜索缓存命中: {query}")
            return cached_data
        
        try:
            # 处理fields参数 - 转换为列表格式
            fields_list = None
            if fields:
                fields_list = [f.strip() for f in fields.split(',')]
            
            # 处理venue和fields_of_study参数 - 转换为列表格式
            venue_list = None
            if venue:
                venue_list = [v.strip() for v in venue.split(',')]
                
            fields_of_study_list = None
            if fields_of_study:
                fields_of_study_list = [f.strip() for f in fields_of_study.split(',')]
            
            # 从S2 API搜索
            search_results = await self.s2.search_papers(
                query=query,
                offset=offset,
                limit=limit,
                fields=fields_list,
                year=year,
                venue=venue_list,
                fields_of_study=fields_of_study_list
            )
            
            # 标准化真正的空结果（上游成功但无数据）
            if not search_results:
                search_results = {
                    'total': 0,
                    'offset': offset,
                    'data': []
                }
                logger.info(f"搜索成功但无结果 - query='{query}', offset={offset}, limit={limit}")

            # 统一输出字段
            shaped = {
                'total': search_results.get('total', 0),
                'offset': search_results.get('offset', offset),
                'papers': search_results.get('data', []),
            }
            # 兼容字段：同时暴露 data 键，满足历史测试/脚本
            shaped['data'] = shaped['papers']

            # 缓存搜索结果
            await self.redis.set(cache_key, shaped, settings.cache_search_ttl)
            
            return shaped
            
        except S2ApiException as e:
            # 根据错误类型返回相应的HTTP状态码
            logger.error(f"搜索上游失败 - query='{query}': {e.error_code} - {e.message}")
            
            if e.error_code == ErrorCodes.S2_RATE_LIMITED:
                raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
            elif e.error_code == ErrorCodes.TIMEOUT:
                raise HTTPException(status_code=408, detail="搜索请求超时")
            elif e.error_code == ErrorCodes.S2_NETWORK_ERROR:
                raise HTTPException(status_code=502, detail="网络连接失败")
            elif e.error_code == ErrorCodes.S2_AUTH_ERROR:
                raise HTTPException(status_code=401, detail="API认证失败")
            elif e.error_code == ErrorCodes.S2_UNAVAILABLE:
                raise HTTPException(status_code=503, detail="上游API服务不可用")
            else:
                raise HTTPException(status_code=500, detail=f"搜索失败: {e.message}")
    
    async def get_papers_batch(
        self, 
        paper_ids: List[str], 
        fields: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """批量获取论文 - 缓存策略"""
        results = []
        uncached_ids = []
        
        # 1. 批量检查缓存
        cache_keys = [self._get_cache_key(pid, fields) for pid in paper_ids]
        cached_data = await self.redis.mget(cache_keys)
        
        for i, (paper_id, cached) in enumerate(zip(paper_ids, cached_data)):
            if cached:
                results.append(cached)
                logger.debug(f"批量缓存命中: {paper_id}")
            else:
                results.append(None)  # 占位符
                uncached_ids.append((i, paper_id))
        
        # 2. 批量获取未缓存的数据
        if uncached_ids:
            try:
                # 处理fields参数 - 转换为列表格式
                fields_list = None
                if fields:
                    fields_list = [f.strip() for f in fields.split(',')]
                
                batch_ids = [pid for _, pid in uncached_ids]
                batch_data = await self.s2.get_papers_batch(batch_ids, fields_list)
                
                # 更新结果和缓存
                cache_mapping = {}
                for j, paper_data in enumerate(batch_data):
                    if paper_data:  # S2可能返回null
                        idx, paper_id = uncached_ids[j]
                        results[idx] = paper_data
                        
                        # 准备批量缓存
                        cache_key = self._get_cache_key(paper_id, fields)
                        cache_mapping[cache_key] = paper_data
                
                # 批量写入缓存
                if cache_mapping:
                    await self.redis.mset(cache_mapping, settings.cache_paper_ttl)
                    
            except S2ApiException as e:
                raise HTTPException(status_code=500, detail=f"批量获取失败: {e.message}")
        
        # 保持与请求数量一致（即使有None）
        return results
    
    async def clear_cache(self, paper_id: str) -> bool:
        """清除指定论文的缓存"""
        try:
            # 清除所有相关缓存键
            cache_patterns = [
                f"paper:{paper_id}:*",
            ]
            
            # 这里简化处理，实际可能需要scan操作
            keys_to_delete = [
                self._get_cache_key(paper_id, None),
                self._get_cache_key(paper_id, "basic"),
                f"paper:{paper_id}:citations:*",
                f"paper:{paper_id}:references:*"
            ]
            
            for key in keys_to_delete:
                await self.redis.delete(key)
            
            logger.info(f"清除缓存成功: {paper_id}")
            return True
            
        except Exception as e:
            logger.error(f"清除缓存失败 paper_id={paper_id}: {e}")
            return False
    
    async def warm_cache(self, paper_id: str, fields: Optional[str] = None) -> bool:
        """预热指定论文的缓存"""
        try:
            # 处理fields参数 - 转换为列表格式
            fields_list = None
            if fields:
                fields_list = [f.strip() for f in fields.split(',')]
            
            # 强制从S2获取最新数据
            paper_data = await self.s2.get_paper(paper_id, fields_list)
            
            # 写入缓存
            await self.redis.set_paper(paper_id, paper_data, fields)
            
            # 异步写入Neo4j
            asyncio.create_task(self.neo4j.merge_paper(paper_data))
            
            logger.info(f"缓存预热成功: {paper_id}")
            return True
            
        except Exception as e:
            logger.error(f"缓存预热失败 paper_id={paper_id}: {e}")
            return False
    
    # 私有方法
    def _get_cache_key(self, paper_id: str, fields: Optional[str] = None) -> str:
        """生成缓存键"""
        if fields:
            return f"paper:{paper_id}:{fields}"
        return CacheKeys.PAPER_FULL.format(paper_id=paper_id)
    
    async def _get_from_neo4j(self, paper_id: str) -> Optional[Dict]:
        """从Neo4j获取数据"""
        try:
            # 支持不同ID格式
            if paper_id.startswith("10."):  # DOI
                return await self.neo4j.get_paper_by_external_id("DOI", paper_id)
            elif "/" not in paper_id and "." in paper_id:  # 可能是ArXiv
                return await self.neo4j.get_paper_by_external_id("ArXiv", paper_id)
            else:  # Semantic Scholar ID
                return await self.neo4j.get_paper(paper_id)
        except Exception as e:
            logger.error(f"Neo4j查询失败 paper_id={paper_id}: {e}")
            return None
    
    def _is_data_fresh(self, data: Dict, max_age_hours: int = 24) -> bool:
        """检查数据是否新鲜"""
        try:
            last_updated = data.get('lastUpdated')
            if not last_updated:
                return False
            
            if isinstance(last_updated, str):
                last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            
            age = datetime.now() - last_updated.replace(tzinfo=None)
            return age.total_seconds() < max_age_hours * 3600
            
        except Exception as e:
            logger.error(f"检查数据新鲜度失败: {e}")
            return False
    
    def _format_response(self, data: Dict, fields: Optional[str] = None) -> Dict:
        """格式化响应数据"""
        if not fields:
            return data
        
        # 如果指定了字段，只返回这些字段
        field_list = [f.strip() for f in fields.split(',')]
        filtered_data = {}
        
        for field in field_list:
            if field in data:
                filtered_data[field] = data[field]
        
        return filtered_data if filtered_data else data
    
    async def _fetch_from_s2(self, paper_id: str, fields: Optional[str] = None) -> Dict[str, Any]:
        """从S2 API获取数据"""
        # 设置处理状态
        await self.redis.set_task_status(paper_id, "processing")
        
        try:
            # 处理fields参数 - 转换为列表格式
            fields_list = None
            if fields:
                fields_list = [f.strip() for f in fields.split(',')]
            
            # 调用S2 API
            s2_data = await self.s2.get_paper(paper_id, fields_list)
            
            # 如果S2返回为空，则抛404，不缓存None
            if not s2_data:
                raise HTTPException(status_code=404, detail="未找到论文")

            # 立即写入Redis缓存
            cache_key = self._get_cache_key(paper_id, fields)
            await self.redis.set(cache_key, s2_data, settings.cache_paper_ttl)
            
            # 异步写入Neo4j
            if not fields or "paperId" in fields:  # 只有完整数据才入库
                asyncio.create_task(self.neo4j.merge_paper(s2_data))
            
            # 清除处理状态
            await self.redis.delete_task_status(paper_id)
            
            logger.info(f"从S2获取数据成功: {paper_id}")
            return s2_data
            
        except Exception as e:
            # 设置失败状态
            await self.redis.set_task_status(paper_id, "failed", ttl=60)
            raise


# 全局服务实例
core_paper_service = CorePaperService()
