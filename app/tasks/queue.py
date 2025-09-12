"""
轻量任务队列封装（优先使用 ARQ，失败时优雅降级为 no-op/本地异步）

- 提供 enqueue 接口给服务层调用
"""
from __future__ import annotations

import asyncio
from typing import Optional, Any, Dict
from urllib.parse import urlparse

from loguru import logger

from app.core.config import settings


class TaskQueue:
    """任务队列统一入口。

    优先使用 ARQ（Redis 作为 broker）。若 ARQ 不可用或连接失败，enqueue 将返回 False，
    由调用方决定是否回退到本地 asyncio.create_task。
    """

    def __init__(self) -> None:
        self._arq_pool = None
        self._arq_available: bool = False

    async def connect(self) -> None:
        """尝试连接 ARQ。"""
        try:
            # 延迟导入，避免在未安装 arq 时抛出 ImportError
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
            self._arq_available = True
            logger.info("任务队列(ARQ)连接成功")
        except Exception as e:
            # 不抛出异常，记录并降级
            self._arq_pool = None
            self._arq_available = False
            logger.warning(f"任务队列(ARQ)不可用，已降级：{e}")

    async def disconnect(self) -> None:
        try:
            if self._arq_pool is not None:
                await self._arq_pool.close()
        except Exception:
            pass
        finally:
            self._arq_pool = None
            self._arq_available = False

    async def enqueue_fetch_from_s2(self, paper_id: str, fields: Optional[str]) -> bool:
        """入队抓取 S2 并写缓存/入库。"""
        if self._arq_available and self._arq_pool is not None:
            try:
                await self._arq_pool.enqueue_job('fetch_from_s2', paper_id, fields)
                return True
            except Exception as e:
                logger.warning(f"ARQ入队 fetch_from_s2 失败，将降级: {e}")
        return False

    async def enqueue_neo4j_merge(self, full_data: Dict[str, Any]) -> bool:
        """入队异步 Neo4j 入库任务。"""
        if self._arq_available and self._arq_pool is not None:
            try:
                await self._arq_pool.enqueue_job('neo4j_merge', full_data)
                return True
            except Exception as e:
                logger.warning(f"ARQ入队 neo4j_merge 失败，将降级: {e}")
        return False

    async def enqueue_set_paper_cache(self, paper_id: str, data: Dict[str, Any], fields: Optional[str] = None) -> bool:
        """入队设置论文缓存。"""
        if self._arq_available and self._arq_pool is not None:
            try:
                await self._arq_pool.enqueue_job('set_paper_cache', paper_id, data, fields)
                return True
            except Exception as e:
                logger.warning(f"ARQ入队 set_paper_cache 失败，将降级: {e}")
        return False


# 全局任务队列实例
task_queue = TaskQueue()


