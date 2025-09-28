"""
Redis客户端封装
"""
import json
import asyncio
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta

import redis.asyncio as redis
from loguru import logger

from app.core.config import settings, CacheKeys


class RedisClient:
    """Redis异步客户端"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        """连接Redis"""
        try:
            self._connection_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=True
            )
            self.redis = redis.Redis(connection_pool=self._connection_pool)
            
            # 测试连接
            await self.redis.ping()
            logger.info("Redis连接成功")
            
        except Exception as e:
            # 降级为禁用缓存模式：不抛出异常，允许应用继续运行
            self.redis = None
            self._connection_pool = None
            logger.warning(f"Redis不可用，已降级为无缓存模式: {e}")
    
    async def disconnect(self):
        """断开连接"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis连接已关闭")
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            if self.redis is None:
                # 未连接时，优雅降级为未命中
                return None
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis获取失败 key={key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """设置缓存值"""
        try:
            if self.redis is None:
                # 未连接时直接返回False，不抛异常
                return False
            json_value = json.dumps(value, ensure_ascii=False, default=str)
            if ttl:
                result = await self.redis.setex(key, ttl, json_value)
            else:
                result = await self.redis.set(key, json_value)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis设置失败 key={key}: {e}")
            return False
    
    async def setex(self, key: str, ttl: int, value: Any) -> bool:
        """设置带过期时间的缓存"""
        return await self.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            if self.redis is None:
                return False
            result = await self.redis.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis删除失败 key={key}: {e}")
            return False

    async def delete_by_pattern(self, pattern: str) -> int:
        """按模式删除缓存键，返回删除数量。"""
        try:
            if self.redis is None:
                return 0
            total_deleted = 0
            keys_batch: list[str] = []
            # scan_iter 是异步生成器
            async for key in self.redis.scan_iter(match=pattern, count=500):
                keys_batch.append(key)
                if len(keys_batch) >= 500:
                    total_deleted += int(await self.redis.delete(*keys_batch))
                    keys_batch.clear()
            if keys_batch:
                total_deleted += int(await self.redis.delete(*keys_batch))
            return total_deleted
        except Exception as e:
            logger.error(f"Redis按模式删除失败 pattern={pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            if self.redis is None:
                return False
            result = await self.redis.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis检查存在失败 key={key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """设置过期时间"""
        try:
            if self.redis is None:
                return False
            result = await self.redis.expire(key, ttl)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis设置过期时间失败 key={key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        try:
            if self.redis is None:
                return -1
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Redis获取TTL失败 key={key}: {e}")
            return -1
    
    async def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """批量获取"""
        try:
            if self.redis is None:
                return [None] * len(keys)
            values = await self.redis.mget(keys)
            results = []
            for value in values:
                if value:
                    results.append(json.loads(value))
                else:
                    results.append(None)
            return results
        except Exception as e:
            logger.error(f"Redis批量获取失败 keys={keys}: {e}")
            return [None] * len(keys)
    
    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置"""
        try:
            if self.redis is None:
                return False
            # 转换为JSON字符串
            json_mapping = {
                key: json.dumps(value, ensure_ascii=False, default=str)
                for key, value in mapping.items()
            }
            
            # 批量设置
            result = await self.redis.mset(json_mapping)
            
            # 如果有TTL，批量设置过期时间
            if ttl and result:
                pipe = self.redis.pipeline()
                for key in mapping.keys():
                    pipe.expire(key, ttl)
                await pipe.execute()
            
            return bool(result)
        except Exception as e:
            logger.error(f"Redis批量设置失败: {e}")
            return False
    
    # 论文缓存相关方法
    async def get_paper(self, paper_id: str, fields: Optional[str] = None) -> Optional[Dict]:
        """获取论文缓存"""
        cache_key = CacheKeys.PAPER_FULL.format(paper_id=paper_id)
        if fields:
            cache_key = f"paper:{paper_id}:{fields}"
        return await self.get(cache_key)
    async def mset_paper(self, paper_mapping: Dict[str, Dict], fields: Optional[str] = None, ttl: Optional[int] = None) -> bool:
        """批量设置论文缓存"""
        if fields:
            logger.debug(f"批量设置字段论文缓存: {fields}")
            cache_mapping = {
                f"paper:{paper_id}:{fields}": paper_data
                for paper_id, paper_data in paper_mapping.items()
            }
        else:
            logger.debug(f"批量设置论文缓存: full")
            cache_mapping = {
                CacheKeys.PAPER_FULL.format(paper_id=paper_id): paper_data
                for paper_id, paper_data in paper_mapping.items()
            }
        return await self.mset(cache_mapping, ttl)
    async def set_paper(
        self, 
        paper_id: str, 
        paper_data: Dict, 
        fields: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """设置论文缓存"""
        cache_key = CacheKeys.PAPER_FULL.format(paper_id=paper_id)
        if fields:
            cache_key = f"paper:{paper_id}:{fields}"
        
        # 添加缓存时间戳
        paper_data["cached_at"] = datetime.now().isoformat()
        
        return await self.set(
            cache_key, 
            paper_data, 
            ttl or settings.cache_paper_ttl
        )
    
    async def get_search_result(self, query_hash: str) -> Optional[Dict]:
        """获取搜索结果缓存"""
        cache_key = CacheKeys.SEARCH_QUERY.format(query_hash=query_hash)
        return await self.get(cache_key)
    
    async def set_search_result(self, query_hash: str, result: Dict) -> bool:
        """设置搜索结果缓存"""
        cache_key = CacheKeys.SEARCH_QUERY.format(query_hash=query_hash)
        return await self.set(cache_key, result, settings.cache_search_ttl)
    
    # 任务状态相关方法
    async def get_task_status(self, paper_id: str) -> Optional[str]:
        """获取任务状态"""
        cache_key = CacheKeys.TASK_STATUS.format(paper_id=paper_id)
        return await self.get(cache_key)
    
    async def set_task_status(
        self, 
        paper_id: str, 
        status: str, 
        ttl: Optional[int] = None
    ) -> bool:
        """设置任务状态"""
        cache_key = CacheKeys.TASK_STATUS.format(paper_id=paper_id)
        return await self.set(
            cache_key, 
            status, 
            ttl or settings.cache_task_ttl
        )
    
    async def delete_task_status(self, paper_id: str) -> bool:
        """删除任务状态"""
        cache_key = CacheKeys.TASK_STATUS.format(paper_id=paper_id)
        return await self.delete(cache_key)
    
    # 系统状态相关方法
    async def get_system_status(self) -> Optional[Dict]:
        """获取系统状态"""
        cache_key = CacheKeys.SYSTEM_S2_STATUS
        return await self.get(cache_key)
    
    async def set_system_status(self, status: Dict, ttl: int = 300) -> bool:
        """设置系统状态 (5分钟TTL)"""
        cache_key = CacheKeys.SYSTEM_S2_STATUS
        return await self.set(cache_key, status, ttl)
    
    # 健康检查
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis健康检查失败: {e}")
            return False
    
    # 通用缓存方法（向后兼容）
    async def set_cache(self, key: str, value: Any, expire_seconds: int = None) -> bool:
        """设置缓存（通用方法）"""
        return await self.set(key, value, expire_seconds or 3600)
    
    async def get_cache(self, key: str) -> Any:
        """获取缓存（通用方法）"""
        return await self.get(key)
    
    async def delete_cache(self, key: str) -> bool:
        """删除缓存（通用方法）"""
        return await self.delete(key)


# 全局Redis客户端实例
redis_client = RedisClient()
