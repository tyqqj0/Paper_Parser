"""
调试与缓存管理API
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.services.core_paper_service import core_paper_service
from app.api.v1.paper import _validate_paper_identifier_strict
from app.clients.redis_client import redis_client


router = APIRouter()


@router.delete("/{paper_id:path}/cache")
async def clear_paper_cache(paper_id: str):
    """清除指定论文的缓存"""
    try:
        _validate_paper_identifier_strict(paper_id)
        success = await core_paper_service.clear_cache(paper_id)

        if not success:
            raise HTTPException(status_code=500, detail="缓存清除失败")
        return {"success": True}
    except HTTPException:
        # 直接透传，例如无效ID应返回400
        raise
    except Exception as e:
        logger.error(f"清除缓存失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{paper_id:path}/cache/warm")
async def warm_paper_cache(
    paper_id: str,
    fields: Optional[str] = Query(None, description="要预热的字段"),
):
    """预热指定论文的缓存"""
    try:
        _validate_paper_identifier_strict(paper_id)
        success = await core_paper_service.warm_cache(paper_id, fields)

        if not success:
            raise HTTPException(status_code=500, detail="缓存预热失败")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"缓存预热失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")



@router.delete("/cache")
async def clear_all_cache():
    """清空所有Redis缓存（谨慎操作）"""
    try:
        # 使用按模式删除来避免需要FLUSHDB权限
        deleted = await redis_client.delete_by_pattern("*")
        return {"success": True, "deleted": int(deleted)}
    except Exception as e:
        logger.error(f"清空所有缓存失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

