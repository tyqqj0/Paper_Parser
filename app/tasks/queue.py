"""
ARQ任务队列封装（统一使用ARQ，确保任务队列始终可用）

- 提供 enqueue 接口给服务层调用
- 统一使用ARQ，不再支持降级到本地异步任务
"""
from __future__ import annotations

from typing import Optional, Any, Dict
from urllib.parse import urlparse
from datetime import datetime, date

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

    def _json_safe(self, value: Any) -> Any:
        """将对象转换为可被 msgpack/JSON 序列化的形式。

        处理：
        - Neo4j/pendulum/内置 datetime/date -> ISO8601 字符串
        - 集合/元组 -> 列表
        - 映射/列表 -> 递归处理
        - 其他不可序列化对象 -> str(value)
        """
        try:
            if hasattr(value, 'to_native') and callable(getattr(value, 'to_native')):
                try:
                    native = value.to_native()
                    if isinstance(native, (datetime, date)):
                        return native.isoformat()
                    return self._json_safe(native)
                except Exception:
                    return str(value)
            if hasattr(value, 'to_iso8601_string') and callable(getattr(value, 'to_iso8601_string')):
                try:
                    return value.to_iso8601_string()
                except Exception:
                    return str(value)
            if isinstance(value, (datetime, date)):
                return value.isoformat()
            if isinstance(value, dict):
                return {self._json_safe(k): self._json_safe(v) for k, v in value.items()}
            if isinstance(value, (list, tuple, set)):
                return [self._json_safe(item) for item in value]
            if isinstance(value, (str, int, float, bool)) or value is None:
                return value
            return str(value)
        except Exception:
            return str(value)

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
            await self._arq_pool.enqueue_job('neo4j_merge', self._json_safe(full_data))
            paper_id = full_data.get('paperId', 'unknown')
            logger.debug(f"ARQ任务入队成功: neo4j_merge({paper_id})")
        except Exception as e:
            logger.error(f"ARQ入队 neo4j_merge 失败: {e}")
            raise

# 全局任务队列实例
task_queue = TaskQueue()


