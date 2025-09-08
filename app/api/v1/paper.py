"""
论文核心API - 实现缓存策略
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Body
from loguru import logger

from app.models.paper import EnhancedPaper, SearchResult, BatchRequest, ApiResponse
from app.services.core_paper_service import core_paper_service

router = APIRouter()


@router.get("/{paper_id}", response_model=ApiResponse)
async def get_paper(
    paper_id: str,
    fields: Optional[str] = Query(None, description="要返回的字段，逗号分隔")
):
    """
    获取论文详情 - 核心API，实现三级缓存
    
    支持的paper_id格式：
    - Semantic Scholar ID: 649def34f8be52c8b66281af98ae884c09aef38b
    - DOI: 10.1038/nature14539
    - ArXiv: 1705.10311
    - PubMed: 19872477
    """
    try:
        paper_data = await core_paper_service.get_paper(paper_id, fields)
        
        return ApiResponse(
            success=True,
            data=paper_data,
            message="论文信息获取成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取论文失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{paper_id}/citations", response_model=ApiResponse)
async def get_paper_citations(
    paper_id: str,
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    fields: Optional[str] = Query(None, description="要返回的字段，逗号分隔")
):
    """获取论文引用 - 实现缓存策略"""
    try:
        citations_data = await core_paper_service.get_paper_citations(
            paper_id, offset, limit, fields
        )
        
        return ApiResponse(
            success=True,
            data=citations_data,
            message="引用信息获取成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取论文引用失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{paper_id}/references", response_model=ApiResponse)
async def get_paper_references(
    paper_id: str,
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    fields: Optional[str] = Query(None, description="要返回的字段，逗号分隔")
):
    """获取论文参考文献 - 实现缓存策略"""
    try:
        references_data = await core_paper_service.get_paper_references(
            paper_id, offset, limit, fields
        )
        
        return ApiResponse(
            success=True,
            data=references_data,
            message="参考文献获取成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取论文参考文献失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/search", response_model=ApiResponse)
async def search_papers(
    query: str = Query(..., description="搜索关键词"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    fields: Optional[str] = Query(None, description="要返回的字段，逗号分隔"),
    year: Optional[str] = Query(None, description="发表年份，如：2020 或 2018-2020"),
    venue: Optional[str] = Query(None, description="发表场所"),
    fields_of_study: Optional[str] = Query(None, description="研究领域")
):
    """搜索论文 - 实现缓存策略"""
    try:
        search_results = await core_paper_service.search_papers(
            query=query,
            offset=offset,
            limit=limit,
            fields=fields,
            year=year,
            venue=venue,
            fields_of_study=fields_of_study
        )
        
        return ApiResponse(
            success=True,
            data=search_results,
            message="搜索完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索论文失败 query={query}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/batch", response_model=ApiResponse)
async def get_papers_batch(
    request: BatchRequest = Body(..., description="批量请求参数")
):
    """批量获取论文 - 实现缓存策略"""
    try:
        if len(request.ids) > 500:
            raise HTTPException(status_code=400, detail="批量请求最多支持500个论文ID")
        
        batch_results = await core_paper_service.get_papers_batch(
            paper_ids=request.ids,
            fields=request.fields
        )
        
        return ApiResponse(
            success=True,
            data=batch_results,
            message=f"批量获取完成，共 {len(batch_results)} 篇论文"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量获取论文失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# 缓存管理API
@router.delete("/{paper_id}/cache", response_model=ApiResponse)
async def clear_paper_cache(paper_id: str):
    """清除指定论文的缓存"""
    try:
        success = await core_paper_service.clear_cache(paper_id)
        
        return ApiResponse(
            success=success,
            message="缓存清除成功" if success else "缓存清除失败"
        )
        
    except Exception as e:
        logger.error(f"清除缓存失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{paper_id}/cache/warm", response_model=ApiResponse)
async def warm_paper_cache(
    paper_id: str,
    fields: Optional[str] = Query(None, description="要预热的字段")
):
    """预热指定论文的缓存"""
    try:
        success = await core_paper_service.warm_cache(paper_id, fields)
        
        return ApiResponse(
            success=success,
            message="缓存预热成功" if success else "缓存预热失败"
        )
        
    except Exception as e:
        logger.error(f"缓存预热失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
