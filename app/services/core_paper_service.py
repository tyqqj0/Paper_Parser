"""
核心论文服务 - 实现三级缓存策略
"""
import json
import asyncio
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
from app.tasks.queue import task_queue
from app.services.external_id_mapping import ExternalIds, external_id_mapping


class CorePaperService:
    """核心论文服务 - 三级缓存策略"""
    
    def __init__(self):
        self.redis = redis_client
        self.neo4j = neo4j_client
        self.s2 = s2_client
        self.external_mapping = external_id_mapping
        # 关系抓取策略
        self.relations_page_size = int(getattr(settings, 'relations_page_size', 200) or 200)
        self.relations_full_fetch_threshold = int(getattr(settings, 'relations_full_fetch_threshold', 200) or 200)
    
    async def get_paper(self, paper_id: str, fields: Optional[str] = None, disable_cache: bool = False) -> Dict[str, Any]:
        """
        获取论文信息 - 三级缓存策略
        
        0. 外部ID映射解析（如果是带前缀的外部ID）
        1. Redis缓存查询 (毫秒级)
        2. Neo4j持久化查询 (10ms级)  
        3. S2 API调用 (秒级)
        
        Args:
            paper_id: 论文ID
            fields: 要返回的字段，逗号分隔
            disable_cache: 是否禁用缓存，为True时直接从S2 API获取
        """
        try:
            if disable_cache:
                logger.debug(f"禁用缓存，直接从S2获取: {paper_id}")
                return await self._fetch_from_s2(paper_id, fields)
            # 0. 处理外部ID映射
            resolved_paper_id = await self.external_mapping.resolve_paper_id(paper_id)
            if resolved_paper_id != paper_id:
                logger.debug(f"外部ID映射解析: {paper_id} -> {resolved_paper_id}")
                paper_id = resolved_paper_id
            else:
                logger.debug(f"未解析: {paper_id} -> {paper_id}")
            # 如果禁用缓存，直接调用S2 API
            logger.info(f"get_paper查询: {paper_id}")
            # 1. Redis缓存查询（统一使用 full 视图键）
            full_cache_key = CacheKeys.PAPER_FULL.format(paper_id=paper_id)
            cached_data = await self.redis.get(full_cache_key)
            
            if cached_data:
                logger.debug(f"Redis缓存命中: {paper_id}")
                return self._format_response(cached_data, fields)
            
            # 2. Neo4j持久化查询（支持 alias 识别）
            neo4j_data = await self._get_from_neo4j(paper_id)
            if neo4j_data:
                logger.debug(f"Neo4j数据命中: {paper_id}")
                
                # 异步更新Redis缓存
                await task_queue.enqueue_set_paper_cache(paper_id, neo4j_data, None)
                
                return self._format_response(neo4j_data, fields)
            """
            # 3. 检查是否正在处理
            task_status = await self.redis.get_task_status(paper_id)
            if task_status == "processing":
                # 等待最多3秒
                for _ in range(6):
                    await asyncio.sleep(0.5)
                    cached_data = await self.redis.get(full_cache_key)
                    if cached_data:
                        logger.debug(f"等待后获取到缓存: {paper_id}")
                        return self._format_response(cached_data, fields)
                # 若仍在processing，改为删除僵尸状态并继续走S2获取，避免返回408
                logger.warning(f"处理状态超时，清理僵尸状态后直接抓取: {paper_id}")
                await self.redis.delete_task_status(paper_id)
            """
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
        # 0. 处理外部ID映射
        resolved_paper_id = await self.external_mapping.resolve_paper_id(paper_id)
        if resolved_paper_id != paper_id:
            logger.debug(f"外部ID映射解析: {paper_id} -> {resolved_paper_id}")
            paper_id = resolved_paper_id
            
        cache_key = f"paper:{paper_id}:citations:{offset}:{limit}:{fields or 'default'}"
        
        # 优先从 full 视图裁剪，避免重复上游调用
        try:
            full_cache_key = CacheKeys.PAPER_FULL.format(paper_id=paper_id)
            full_cached = await self.redis.get(full_cache_key)
            if isinstance(full_cached, dict) and isinstance(full_cached.get('citations'), list):
                citations_list = full_cached['citations']
                total = full_cached.get('citationCount', len(citations_list))
                sliced = citations_list[offset: offset + limit] if offset or limit else citations_list
                shaped = {
                    'total': total,
                    'offset': offset,
                    'citations': sliced,
                }
                await self.redis.set(cache_key, shaped, settings.cache_paper_ttl)
                logger.debug(f"引用从full缓存裁剪命中: {paper_id}")
                return shaped
        except Exception:
            pass

        # 尝试从细粒度缓存获取
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
            else:
                logger.info(f"S2 API获取引用: {paper_id}")
            # 统一输出字段（对齐S2：使用 data 键）
            shaped = {
                'total': citations_data.get('total', 0),
                'offset': citations_data.get('offset', offset),
                'data': citations_data.get('data', []),
            }

            # 缓存结果
            await self.redis.set(cache_key, shaped, settings.cache_paper_ttl)
            
            return shaped
            
        except HTTPException:
            raise
        except S2ApiException as e:
            # 根据错误类型返回相应的HTTP状态码
            logger.error(f"获取引用上游失败 paper_id={paper_id}: {e.error_code} - {e.message}")
            
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
            logger.error(f"获取引用失败 paper_id={paper_id}: {e}")
            raise HTTPException(status_code=500, detail="内部服务器错误")
    
    async def get_paper_references(
        self, 
        paper_id: str, 
        offset: int = 0, 
        limit: int = 10,
        fields: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取论文参考文献 - 缓存策略"""
        # 0. 处理外部ID映射
        resolved_paper_id = await self.external_mapping.resolve_paper_id(paper_id)
        if resolved_paper_id != paper_id:
            logger.info(f"外部ID映射解析: {paper_id} -> {resolved_paper_id}")
            paper_id = resolved_paper_id
            
        cache_key = f"paper:{paper_id}:references:{offset}:{limit}:{fields or 'default'}"
        logger.info(f"尝试参考文献缓存获取: {cache_key}")
        # 优先从 full 视图裁剪
        try:
            full_cache_key = CacheKeys.PAPER_FULL.format(paper_id=paper_id)
            full_cached = await self.redis.get(full_cache_key)
            if isinstance(full_cached, dict) and isinstance(full_cached.get('references'), list):
                references_list = full_cached['references']
                total = full_cached.get('referenceCount', len(references_list))
                sliced = references_list[offset: offset + limit] if offset or limit else references_list
                shaped = {
                    'total': total,
                    'offset': offset,
                    'references': sliced,
                }
                await self.redis.set(cache_key, shaped, settings.cache_paper_ttl)
                logger.info(f"参考文献从full缓存裁剪命中: {paper_id}")
                return shaped
        except Exception:
            pass

        # 尝试从细粒度缓存获取
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.info(f"参考文献缓存命中: {paper_id}")
            return cached_data
        
        try:
            # 处理fields参数 - 转换为列表格式
            fields_list = None
            if fields:
                fields_list = [f.strip() for f in fields.split(',')]
            logger.info(f"尝试参考文献Neo4j获取: {paper_id}, offset={offset}, limit={limit}")
            # 优先尝试从 Neo4j 获取（Redis 未命中时的本地持久化回退）
            try:
                neo4j_refs = await self.neo4j.get_references(paper_id, limit=limit, offset=offset)
                if isinstance(neo4j_refs, list) and len(neo4j_refs) > 0:
                    total_refs = await self.neo4j.get_references_total(paper_id)
                    shaped = {
                        'total': total_refs,
                        'offset': offset,
                        'data': neo4j_refs,
                    }
                    await self.redis.set(cache_key, shaped, settings.cache_paper_ttl)
                    logger.info(f"参考文献Neo4j命中: {paper_id}")
                    return shaped
            except Exception:
                # 忽略 Neo4j 异常，继续回退到 S2
                pass

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

            # 统一输出字段（对齐S2：使用 data 键）
            shaped = {
                'total': references_data.get('total', 0),
                'offset': references_data.get('offset', offset),
                'data': references_data.get('data', []),
            }

            # 缓存结果
            await self.redis.set(cache_key, shaped, settings.cache_paper_ttl)
            
            return shaped
            
        except HTTPException:
            raise
        except S2ApiException as e:
            # 根据错误类型返回相应的HTTP状态码
            logger.error(f"获取参考文献上游失败 paper_id={paper_id}: {e.error_code} - {e.message}")
            
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
            logger.error(f"获取参考文献失败 paper_id={paper_id}: {e}")
            raise HTTPException(status_code=500, detail="内部服务器错误")
    
    async def search_papers(
        self,
        query: str,
        offset: int = 0,
        limit: int = 10,
        fields: Optional[str] = None,
        year: Optional[str] = None,
        venue: Optional[str] = None,
        fields_of_study: Optional[str] = None,
        *,
        match_title: bool = False,
        prefer_local: bool = True,
        fallback_to_s2: bool = True,
    ) -> Dict[str, Any]:
        """搜索论文 - 缓存策略"""
        # 上层API已做空查询校验；此处不再拦截，确保空结果只因上游无匹配
        # 生成查询哈希
        logger.info(f"a搜索论文: {query}, offset={offset}, limit={limit}, fields={fields}, year={year}, venue={venue}, fields_of_study={fields_of_study}, match_title={match_title}, prefer_local={prefer_local}, fallback_to_s2={fallback_to_s2}")
        query_hash = self.s2.generate_query_hash(
            query, 
            offset=offset, 
            limit=limit,
            fields=fields,
            year=year,
            venue=venue,
            fields_of_study=fields_of_study,
            match_title=match_title,
            prefer_local=prefer_local,
            fallback_to_s2=fallback_to_s2,
        )
        
        cache_key = CacheKeys.SEARCH_QUERY.format(query_hash=query_hash)
        
        # 尝试从缓存获取
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.info(f"搜索缓存命中: {query}")
            # 条件刷新：当缓存存在时，选取前 N 个 paperId 进行后台刷新
            try:
                if getattr(settings, 'enable_search_background_ingest', True):
                    top_n = max(0, int(getattr(settings, 'search_background_ingest_top_n', 3) or 0))
                    if top_n > 0:
                        items = (cached_data.get('papers') or [])
                        for item in items[: min(len(items), top_n)]:
                            if isinstance(item, dict) and item.get('paperId'):
                                pid = item.get('paperId')
                                await task_queue.enqueue_fetch_from_s2(pid, None)
            except Exception:
                pass
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
            
            # 标题精准匹配模式（最多返回1条）
            if match_title:
                if prefer_local:
                    try:
                        candidates = await self.neo4j.find_papers_by_title_norm_contains(query, limit=3)
                    except Exception:
                        candidates = None
                    if candidates:
                        query = candidates[0].get("paperId")
                    logger.info(f"a本地命中: {query}")
                    try:
                        projected=await self.get_paper(query, fields, disable_cache=False)
                    except Exception:
                        projected = None
                    if projected:
                        logger.info(f"标题精准匹配模式本地命中: {query}")
                        shaped = {
                            'total': 1,
                            'offset': 0,
                            'papers': [projected],
                        }
                        shaped['data'] = shaped['papers']
                        await self.redis.set(cache_key, shaped, settings.cache_search_ttl)
                        return shaped

                # 3) 未命中且允许回退到S2精准匹配
                if fallback_to_s2:
                    search_results = await self.s2.search_papers(
                        query=query,
                        offset=0,
                        limit=1,
                        fields=fields_list,
                        year=None,
                        venue=None,
                        fields_of_study=None,
                        match_title=True,
                    )
                else:
                    search_results = {
                        'total': 0,
                        'offset': 0,
                        'data': []
                    }

                if not search_results:
                    search_results = {
                        'total': 0,
                        'offset': 0,
                        'data': []
                    }

                shaped = {
                    'total': search_results.get('total', 0),
                    'offset': 0,
                    'papers': search_results.get('data', [])[:1],
                }
                shaped['data'] = shaped['papers']

                # 异步触发按paper端点逻辑的全量抓取与入库，避免部分字段不一致
                try:
                    top_items = shaped.get('papers') or []
                    for item in top_items:
                        if isinstance(item, dict) and item.get('paperId'):
                            pid = item.get('paperId')
                            await task_queue.enqueue_fetch_from_s2(pid, None)
                except Exception:
                    pass

                await self.redis.set(cache_key, shaped, settings.cache_search_ttl)
                return shaped
            
            # prefer_local：优先使用本地Neo4j全文索引
            if prefer_local:
                try:
                    local_hits = await self.neo4j.search_papers(query=query, limit=limit, offset=offset)
                except Exception:
                    local_hits = []
                if local_hits:
                    try:
                        projected_local = [self._format_response(hit, fields) if fields else hit for hit in local_hits]
                    except Exception:
                        projected_local = local_hits
                    shaped_local = {
                        'total': len(projected_local),
                        'offset': offset,
                        'papers': projected_local,
                    }
                    shaped_local['data'] = shaped_local['papers']
                    await self.redis.set(cache_key, shaped_local, settings.cache_search_ttl)
                    return shaped_local

                # 若本地未命中且不允许回退，则直接返回空结果
                if not fallback_to_s2:
                    empty_shaped = {
                        'total': 0,
                        'offset': offset,
                        'papers': [],
                    }
                    empty_shaped['data'] = empty_shaped['papers']
                    await self.redis.set(cache_key, empty_shaped, settings.cache_search_ttl)
                    return empty_shaped

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

            # 异步触发按paper端点逻辑的全量抓取与入库（限制前3条），提高一致性
            try:
                candidates = shaped.get('papers') or []
                for item in candidates[: min(len(candidates), 3)]:
                    if isinstance(item, dict) and item.get('paperId'):
                        pid = item.get('paperId')
                        await task_queue.enqueue_fetch_from_s2(pid, None)
            except Exception:
                pass

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
        cache_keys = [CacheKeys.PAPER_FULL.format(paper_id=pid) for pid in paper_ids]
        cached_data = await self.redis.mget(cache_keys)
        
        for i, (paper_id, cached) in enumerate(zip(paper_ids, cached_data)):
            if cached:
                results.append(self._format_response(cached, fields))
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
                        projected = self._format_response(paper_data, fields)
                        results[idx] = projected
                        
                        # 准备批量缓存
                        cache_key = CacheKeys.PAPER_FULL.format(paper_id=paper_id)
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
            await self.redis.set_paper(paper_id, paper_data, None)
            
            # 异步写入Neo4j（优先入队）
            await task_queue.enqueue_neo4j_merge(paper_data)
            
            logger.info(f"缓存预热成功: {paper_id}")
            return True
            
        except Exception as e:
            logger.error(f"缓存预热失败 paper_id={paper_id}: {e}")
            return False

    def _get_cache_key(self, paper_id: str, fields: Optional[str] = None) -> str:
        """生成缓存键"""
        if fields:
            return f"paper:{paper_id}:{fields}"
        return CacheKeys.PAPER_FULL.format(paper_id=paper_id)
    
    async def _get_from_neo4j(self, paper_id: str) -> Optional[Dict]:
        """从Neo4j获取数据"""
        try:
            got = self.neo4j.ensure_fresh(await self.neo4j.get_paper(paper_id))
            return got
        except Exception as e:
            logger.error(f"Neo4j查询失败 paper_id={paper_id}: {e}")
            return None

    def _build_field_tree(self, fields: str) -> Dict[str, Dict]:
        """将逗号分隔的字段列表构建为嵌套字段树，支持 authors.name 这类路径"""
        field_tree: Dict[str, Dict] = {}
        for raw in fields.split(','):
            part = raw.strip()
            if not part:
                continue
            node = field_tree
            for token in part.split('.'):
                node = node.setdefault(token, {})
        return field_tree

    def _project_by_field_tree(self, value: Any, tree: Dict[str, Dict]) -> Any:
        """根据字段树对给定值进行投影（裁剪）。空树表示直接返回原值。"""
        if not isinstance(tree, dict) or len(tree) == 0:
            return value
        if isinstance(value, dict):
            projected: Dict[str, Any] = {}
            for key, sub_tree in tree.items():
                if key in value:
                    projected[key] = self._project_by_field_tree(value[key], sub_tree)
            return projected
        if isinstance(value, list):
            # 对列表内的字典元素递归裁剪；非字典元素原样返回
            return [
                self._project_by_field_tree(item, tree) if isinstance(item, dict) else item
                for item in value
            ]
        # 基础类型，无法继续下钻，直接返回
        return value

    def _format_response(self, data: Dict, fields: Optional[str] = None) -> Dict:
        """格式化响应数据，支持嵌套字段路径裁剪（如 authors.name、citations.title）。"""
        if not fields:
            return data
        try:
            field_tree = self._build_field_tree(fields)
            # 始终包含 paperId 以对齐S2并便于调用方识别
            if 'paperId' not in field_tree:
                field_tree['paperId'] = {}
            # 顶层按字段树选择
            shaped: Dict[str, Any] = {}
            for top_key, sub_tree in field_tree.items():
                if top_key in data:
                    shaped[top_key] = self._project_by_field_tree(data[top_key], sub_tree)
            # 若请求包含关系字段但数据中缺失，返回空列表对齐S2形态
            requested_top_keys = set(field_tree.keys())
            if 'citations' in requested_top_keys and 'citations' not in shaped:
                shaped['citations'] = []
            if 'references' in requested_top_keys and 'references' not in shaped:
                shaped['references'] = []
            return shaped if shaped else data
        except Exception as _:
            # 任意裁剪异常时回退到原始数据，避免影响主流程
            return data
    
    async def _fetch_from_s2(self, paper_id: str, fields: Optional[str] = None, skip_neo4j_enqueue: bool = False) -> Dict[str, Any]:
        """从S2 API获取数据（主体全量 + 可选关系分页）
        
        Args:
            paper_id: 论文ID
            fields: 指定返回字段
            skip_neo4j_enqueue: 是否跳过Neo4j入队（用于ARQ worker环境）
        """
        # 设置处理状态
        await self.redis.set_task_status(paper_id, "processing")

        try:
            # 1) 抓取主体（扩展级，不包含大列表）
            body = await self._fetch_paper_body_full(paper_id)
            if not body:
                raise HTTPException(status_code=404, detail=f"论文不存在: {paper_id}")
            """
            # 2) 判断是否需要抓取关系
            should_fetch_citations = False
            should_fetch_references = True
            if fields:
                requested = {f.strip() for f in fields.split(',') if f.strip()}
                if 'citations' in requested:
                    should_fetch_citations = True
                if 'references' in requested:
                    should_fetch_references = True
            # 若计数不大，也进行全量抓取以便后续直接切片
            try:
                if isinstance(body.get('citationCount'), int) and body['citationCount'] <= self.relations_full_fetch_threshold:
                    should_fetch_citations = True
                if isinstance(body.get('referenceCount'), int) and body['referenceCount'] <= self.relations_full_fetch_threshold:
                    should_fetch_references = True
            except Exception:
                pass
            # 全局开关强制抓取（即使超过阈值）
            try:
                if getattr(settings, 'force_fetch_citations', False):
                    should_fetch_citations = True
                if getattr(settings, 'force_fetch_references', False):
                    should_fetch_references = True
            except Exception:
                pass
            relations: Dict[str, Any] = {}
            if should_fetch_citations or should_fetch_references:
                relations = await self._fetch_relations_segmented(
                    paper_id,
                    fetch_citations=should_fetch_citations,
                    fetch_references=should_fetch_references
                )
            """
            #2) 抓取引用,不抓取被引
            relations = await self._fetch_relations_segmented(
                    paper_id,
                    fetch_citations=False,
                    fetch_references=True
                )
            # 3) 合并并写缓存
            full_data = {**body, **relations}
            await self.redis.set_paper(paper_id, full_data, None)
           
            logger.info(f"存储外部id映射关系: {paper_id}")
            # 3.5) 存储外部ID映射关系
            await self.external_mapping.batch_set_mappings(ExternalIds.from_dict(full_data.get('externalIds', {})), full_data.get('paperId'))
            # 4) 异步写入Neo4j：主节点 + 别名 + 数据块 + （小规模）关系/计划
            async def _async_neo4j_ingest(data):
                try:
                    # 未连接Neo4j时静默跳过
                    if getattr(self.neo4j, "driver", None) is None:
                        logger.info("Neo4j未连接，跳过异步入库")
                        return
                    ok = await self.neo4j.merge_paper(data)
                    if not ok:
                        return
                    #从顶层 corpusId、url、title 补全并规范化为 externalIds
                    await self.neo4j.merge_aliases_from_paper(data)
                    await self.neo4j.merge_data_chunks_from_full_data(data)
                    # 根据是否已抓取关系决定是否立即合并 CITES，并为大规模被引创建计划
                    try:
                        c_count = int(data.get('citationCount') or 0)
                    except Exception:
                        c_count = 0
                    try:
                        r_count = int(data.get('referenceCount') or 0)
                    except Exception:
                        r_count = 0
                    await self.neo4j.merge_cites_from_full_data(data)
                    """
                    # 若任一关系已抓取，则直接落库对应的 CITES 边
                    if should_fetch_citations or should_fetch_references:
                        await self.neo4j.merge_cites_from_full_data(data)

                    # 若被引量大且本次未抓取，则创建分页抓取计划（避免 else 误判）
                    if (not should_fetch_citations) and c_count > self.relations_full_fetch_threshold:
                        await self.neo4j.create_citations_ingest_plan(
                            data.get('paperId'), c_count, self.relations_page_size
                        )
                    """
                except Exception as e:
                    logger.error(f"异步Neo4j入库失败 paper_id={data.get('paperId')}: {e}")
            
            # 入队后台 Neo4j 入库任务（除非在ARQ worker环境中）
            if not skip_neo4j_enqueue:
                await task_queue.enqueue_neo4j_merge(full_data)

            logger.info(f"从S2获取数据成功: {paper_id}")
            return full_data if not fields else self._format_response(full_data, fields)
        except HTTPException:
            # 标记失败，避免遗留processing状态导致后续408
            try:
                await self.redis.set_task_status(paper_id, "failed", ttl=60)
            except Exception:
                pass
            raise
        except Exception:
            # 设置失败状态
            try:
                await self.redis.set_task_status(paper_id, "failed", ttl=60)
            except Exception:
                pass
            raise
        finally:
            # 无论成功或失败都清理处理状态，避免僵尸状态
            try:
                await self.redis.delete_task_status(paper_id)
            except Exception:
                pass

    async def _fetch_paper_body_full(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """抓取论文主体（扩展级字段，不包含大列表关系）。"""
        try:
            fields_list = PaperFieldsConfig.get_fields_for_level('extended')
            # 移除关系字段，避免大列表
            fields_list = [f for f in fields_list if not f.startswith('citations') and not f.startswith('references')]
            return await self.s2.get_paper(paper_id, fields_list)
        except Exception as e:
            logger.error(f"抓取论文主体失败 paper_id={paper_id}: {e}")
            return None

    async def _fetch_relations_segmented(
        self,
        paper_id: str,
        *,
        fetch_citations: bool = True,
        fetch_references: bool = True,
    ) -> Dict[str, Any]:
        """分页抓取引用与参考文献并合并。"""
        result: Dict[str, Any] = {}
        try:
            if fetch_citations:
                citations: List[Dict[str, Any]] = []
                offset = 0
                while True:
                    chunk = await self.s2.get_paper_citations(
                        paper_id,
                        limit=self.relations_page_size,
                        offset=offset,
                        fields=None
                    )
                    data = (chunk or {}).get('data', [])
                    citations.extend(data)
                    total = (chunk or {}).get('total', 0)
                    offset += self.relations_page_size
                    if not data or len(citations) >= total:
                        break
                result['citations'] = citations

            if fetch_references:
                references: List[Dict[str, Any]] = []
                offset = 0
                while True:
                    chunk = await self.s2.get_paper_references(
                        paper_id,
                        limit=self.relations_page_size,
                        offset=offset,
                        fields=None
                    )
                    data = (chunk or {}).get('data', [])
                    references.extend(data)
                    total = (chunk or {}).get('total', 0)
                    offset += self.relations_page_size
                    if not data or len(references) >= total:
                        break
                result['references'] = references
        except Exception as e:
            logger.error(f"分页抓取关系失败 paper_id={paper_id}: {e}")
        return result


# 全局服务实例
core_paper_service = CorePaperService()
