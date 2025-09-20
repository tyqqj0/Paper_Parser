"""
ARQ worker 实现

- 定义后台任务：fetch_from_s2 / neo4j_merge / set_paper_cache
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from loguru import logger
from arq.connections import RedisSettings

from app.clients.redis_client import redis_client
from app.clients.neo4j_client import neo4j_client
from app.services.core_paper_service import core_paper_service


class WorkerSettings:
    # 函数列表将在文件末尾赋值
    functions = []
    
    # Redis连接配置 - 使用Docker网络中的服务名
    redis_settings = RedisSettings(
        host='redis',
        port=6379,
        database=0,
    )


async def startup(ctx: Dict[str, Any]):
    try:
        await redis_client.connect()
    except Exception as e:
        logger.warning(f"ARQ worker Redis 连接失败：{e}")
    try:
        await neo4j_client.connect()
    except Exception as e:
        logger.warning(f"ARQ worker Neo4j 连接失败：{e}")


async def shutdown(ctx: Dict[str, Any]):
    try:
        await redis_client.disconnect()
    except Exception:
        pass
    try:
        await neo4j_client.disconnect()
    except Exception:
        pass


async def fetch_from_s2(ctx: Dict[str, Any], paper_id: str, fields: Optional[str] = None) -> Dict[str, Any]:
    """后台抓取全量数据并写缓存/入库。"""
    try:
        # 在ARQ worker环境中，跳过Neo4j入队，因为会直接调用neo4j_merge任务
        return await core_paper_service._fetch_from_s2(paper_id, fields, skip_neo4j_enqueue=True)
    except Exception as e:
        logger.error(f"ARQ fetch_from_s2 执行失败 paper_id={paper_id}: {e}")
        raise


async def neo4j_merge(ctx: Dict[str, Any], full_data: Dict[str, Any]) -> bool:
    """后台合并论文节点、别名、数据块及关系/计划。"""
    try:
        ok = await neo4j_client.merge_paper(full_data)
        if not ok:
            return False
        await neo4j_client.merge_aliases_from_paper(full_data)
        await neo4j_client.merge_data_chunks_from_full_data(full_data)
        try:
            await neo4j_client.merge_cites_from_full_data(full_data)
        except Exception:
            pass
        return True
    except Exception as e:
        safe_id = None
        try:
            safe_id = full_data.get("paperId")
        except Exception:
            pass
        logger.error(f"ARQ neo4j_merge 执行失败 paper_id={safe_id}: {e}")
        return False


# 绑定生命周期钩子
WorkerSettings.on_startup = startup  # type: ignore[attr-defined]
WorkerSettings.on_shutdown = shutdown  # type: ignore[attr-defined]


async def set_paper_cache(ctx: Dict[str, Any], paper_id: str, data: Dict[str, Any], fields: Optional[str] = None) -> bool:
    """后台设置论文缓存。"""
    try:
        return await redis_client.set_paper(paper_id, data, fields)
    except Exception as e:
        logger.error(f"ARQ set_paper_cache 执行失败 paper_id={paper_id}: {e}")
        return False


# 使用可调用对象注册任务函数，确保与 enqueue_job('function_name') 匹配
WorkerSettings.functions = [
    fetch_from_s2,
    neo4j_merge,
    set_paper_cache,
]


