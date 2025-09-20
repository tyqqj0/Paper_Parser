"""
ARQ任务队列封装（统一使用ARQ，确保任务队列始终可用）

- 提供 enqueue 接口给服务层调用
- 统一使用ARQ，不再支持降级到本地异步任务
"""
from __future__ import annotations

from typing import Optional, Any, Dict
from urllib.parse import urlparse

from loguru import logger

from app.core.config import settings


class TaskQueue:
    """任务队列统一入口。

    统一使用 ARQ（Redis 作为 broker）。ARQ Worker 作为标准服务启动，
    确保任务队列始终可用，不再支持降级模式。
    """

    def __init__(self) -> None:
        self._arq_pool = None
        self._connected: bool = False

    async def connect(self) -> None:
        """连接 ARQ。"""
        try:
            from arq import create_pool  # type: ignore
            from arq.connections import RedisSettings  # type: ignore

            redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379/0')
            parsed = urlparse(redis_url)
            host = parsed.hostname or 'localhost'
            port = int(parsed.port or 6379)
            # path like '/0'
            try:
                database = int((parsed.path or '/0').lstrip('/') or 0)
            except Exception:
                database = 0
            password = parsed.password

            redis_settings = RedisSettings(host=host, port=port, database=database, password=password)
            self._arq_pool = await create_pool(redis_settings)
            self._connected = True
            logger.info("任务队列(ARQ)连接成功")
        except Exception as e:
            logger.error(f"任务队列(ARQ)连接失败：{e}")
            self._arq_pool = None
            self._connected = False
            raise

    async def disconnect(self) -> None:
        try:
            if self._arq_pool is not None:
                await self._arq_pool.close()
        except Exception:
            pass
        finally:
            self._arq_pool = None
            self._connected = False

    async def enqueue_fetch_from_s2(self, paper_id: str, fields: Optional[str]) -> None:
        """入队抓取 S2 并写缓存/入库。"""
        if not self._connected or self._arq_pool is None:
            raise RuntimeError("ARQ任务队列未连接")
        
        try:
            await self._arq_pool.enqueue_job('fetch_from_s2', paper_id, fields)
            logger.debug(f"ARQ任务入队成功: fetch_from_s2({paper_id})")
        except Exception as e:
            logger.error(f"ARQ入队 fetch_from_s2 失败: {e}")
            raise

    async def enqueue_neo4j_merge(self, full_data: Dict[str, Any]) -> None:
        """入队异步 Neo4j 入库任务。"""
        if not self._connected or self._arq_pool is None:
            raise RuntimeError("ARQ任务队列未连接")
            
        try:
            await self._arq_pool.enqueue_job('neo4j_merge', full_data)
            paper_id = full_data.get('paperId', 'unknown')
            logger.debug(f"ARQ任务入队成功: neo4j_merge({paper_id})")
        except Exception as e:
            logger.error(f"ARQ入队 neo4j_merge 失败: {e}")
            raise

    async def enqueue_set_paper_cache(self, paper_id: str, data: Dict[str, Any], fields: Optional[str] = None) -> None:
        """入队设置论文缓存。"""
        if not self._connected or self._arq_pool is None:
            raise RuntimeError("ARQ任务队列未连接")
            
        try:
            await self._arq_pool.enqueue_job('set_paper_cache', paper_id, data, fields)
            logger.debug(f"ARQ任务入队成功: set_paper_cache({paper_id})")
        except Exception as e:
            logger.error(f"ARQ入队 set_paper_cache 失败: {e}")
            raise


# 全局任务队列实例
task_queue = TaskQueue()


