"""
论文核心API - 实现缓存策略
"""
from typing import Optional, List
import re
from fastapi import APIRouter, HTTPException, Query, Body
from loguru import logger

from app.models.paper import EnhancedPaper, SearchResult, BatchRequest, ApiResponse
from app.services.core_paper_service import core_paper_service

router = APIRouter()


async def pre_check(query: str, offset: int, limit: int, fields: Optional[str], year: Optional[str], venue: Optional[str], fields_of_study: Optional[str]):
    """预校验"""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset cannot be negative")    

def _is_valid_paper_id(paper_id: str) -> bool:
    """校验paper_id格式: 支持 S2ID(40位hex)、DOI、ArXiv、PubMed数字ID"""
    # Semantic Scholar ID: 40位十六进制
    if re.fullmatch(r"[0-9a-fA-F]{40}", paper_id):
        return True
    # DOI: 10.xxxx/...
    if re.fullmatch(r"10\.\d{4,9}/\S+", paper_id, flags=0):
        return True
    # arXiv: 1705.10311 或 arXiv:1705.10311 或带版本 v1
    if re.fullmatch(r"(?:arXiv:)?\d{4}\.\d{4,5}(?:v\d+)?", paper_id):
        return True
    # PubMed: 纯数字，长度>=5
    if re.fullmatch(r"\d{5,}", paper_id):
        return True
    return False


@router.get("/search", response_model=ApiResponse)
async def search_papers(
    query: str = Query(..., min_length=1, description="搜索关键词"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    fields: Optional[str] = Query(None, description="要返回的字段，逗号分隔"),
    year: Optional[str] = Query(None, description="发表年份，如：2020 或 2018-2020"),
    venue: Optional[str] = Query(None, description="发表场所"),
    fields_of_study: Optional[str] = Query(None, description="研究领域")
):
    """搜索论文 - 实现缓存策略"""
    try:
        # 预校验：禁止空白查询
        await pre_check(query, offset, limit, fields, year, venue, fields_of_study)

        search_results = await core_paper_service.search_papers(
            query=query,
            offset=offset,
            limit=limit,
            fields=fields,
            year=year,
            venue=venue,
            fields_of_study=fields_of_study
        )
        
        return ApiResponse(success=True, data=search_results, message="搜索完成")
        
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
        
        return ApiResponse(success=True, data=batch_results, message=f"批量获取完成，共 {len(batch_results)} 篇论文")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量获取论文失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


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
        # 提前校验paper_id格式，避免不必要的上游请求
        if not _is_valid_paper_id(paper_id):
            raise HTTPException(status_code=400, detail="无效的论文ID格式")
        paper_data = await core_paper_service.get_paper(paper_id, fields)
        
        return ApiResponse(success=True, data=paper_data, message="论文信息获取成功")
        
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
        if not _is_valid_paper_id(paper_id):
            raise HTTPException(status_code=400, detail="无效的论文ID格式")
        citations_data = await core_paper_service.get_paper_citations(
            paper_id, offset, limit, fields
        )
        
        return ApiResponse(success=True, data=citations_data, message="引用信息获取成功")
        
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
        if not _is_valid_paper_id(paper_id):
            raise HTTPException(status_code=400, detail="无效的论文ID格式")
        references_data = await core_paper_service.get_paper_references(
            paper_id, offset, limit, fields
        )
        
        return ApiResponse(success=True, data=references_data, message="参考文献获取成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取论文参考文献失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# 缓存管理API
@router.delete("/{paper_id}/cache", response_model=ApiResponse)
async def clear_paper_cache(paper_id: str):
    """清除指定论文的缓存"""
    try:
        success = await core_paper_service.clear_cache(paper_id)
        
        return ApiResponse(success=success, message="缓存清除成功" if success else "缓存清除失败")
        
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
        
        return ApiResponse(success=success, message="缓存预热成功" if success else "缓存预热失败")
        
    except Exception as e:
        logger.error(f"缓存预热失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")