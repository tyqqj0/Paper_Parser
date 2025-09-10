"""
代理API - 直接转发到Semantic Scholar
"""
from typing import Optional, Any, Dict
from fastapi import APIRouter, HTTPException, Request
from loguru import logger

# 代理路由直接返回S2原始响应
from app.services.proxy_service import proxy_service

router = APIRouter()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(
    request: Request,
    path: str
):
    """
    代理所有非核心API到Semantic Scholar
    
    支持的路径示例：
    - /author/{author_id}
    - /paper/{paper_id}/authors  
    - /paper/search/match
    - /paper/autocomplete
    """
    try:
        # 获取请求参数
        params = dict(request.query_params)
        
        # 获取请求体（如果有）
        json_data = None
        if request.method in ["POST", "PUT"]:
            try:
                json_data = await request.json()
            except:
                pass  # 没有JSON数据或格式错误
        
        # 代理请求
        result = await proxy_service.proxy_request(
            method=request.method,
            path=path,
            params=params,
            json_data=json_data
        )
        
        return result  # 直接返回原始响应，不包装
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"代理请求失败 {request.method} {path}: {e}")
        raise HTTPException(status_code=500, detail="代理服务错误")


# 特殊代理路由 - 作者相关
@router.get("/author/{author_id}")
async def get_author(
    author_id: str,
    fields: Optional[str] = None
):
    """获取作者信息 - 代理到S2"""
    try:
        params = {}
        if fields:
            params["fields"] = fields
        
        result = await proxy_service.proxy_request(
            method="GET",
            path=f"author/{author_id}",
            params=params
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取作者信息失败 author_id={author_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/author/{author_id}/papers")
async def get_author_papers(
    author_id: str,
    offset: int = 0,
    limit: int = 10,
    fields: Optional[str] = None
):
    """获取作者论文列表 - 代理到S2"""
    try:
        params = {
            "offset": offset,
            "limit": limit
        }
        if fields:
            params["fields"] = fields
        
        result = await proxy_service.proxy_request(
            method="GET",
            path=f"author/{author_id}/papers",
            params=params
        )
        
        return result  # 直接返回S2响应格式
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取作者论文失败 author_id={author_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# 自动补全API
@router.get("/paper/autocomplete")
async def autocomplete_papers(
    query: str,
    limit: int = 10
):
    """论文标题自动补全 - 代理到S2"""
    try:
        params = {
            "query": query,
            "limit": limit
        }
        
        result = await proxy_service.proxy_request(
            method="GET",
            path="paper/autocomplete",
            params=params
        )
        
        return result  # 直接返回S2响应格式
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"自动补全失败 query={query}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# 精确匹配API
@router.get("/paper/search/match")
async def match_paper(
    query: str,
    fields: Optional[str] = None
):
    """论文精确匹配 - 代理到S2"""
    try:
        params = {"query": query}
        if fields:
            params["fields"] = fields
        
        result = await proxy_service.proxy_request(
            method="GET",
            path="paper/search/match",
            params=params
        )
        
        return result  # 直接返回S2响应格式
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"论文匹配失败 query={query}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# 批量搜索API
@router.post("/paper/search/bulk")
async def bulk_search_papers(request: Request):
    """批量搜索论文 - 代理到S2"""
    try:
        json_data = await request.json()
        
        result = await proxy_service.proxy_request(
            method="POST",
            path="paper/search/bulk",
            json_data=json_data
        )
        
        return result  # 直接返回S2响应格式
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量搜索失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
