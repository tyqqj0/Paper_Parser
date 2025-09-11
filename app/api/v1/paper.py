"""
论文核心API - 实现缓存策略
"""
from typing import Optional, List
import re
from fastapi import APIRouter, HTTPException, Query, Body
from loguru import logger

from app.models.paper import EnhancedPaper, SearchResult, BatchRequest
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

# 严格前缀策略：除 40 位 S2 paperId 外，其余均需显式前缀
_ALLOWED_ID_PREFIXES = {
    "DOI", "ARXIV", "MAG", "ACL", "PMID", "PMCID", "CORPUSID", "CORPUS", "URL"
}

def _validate_paper_identifier_strict(paper_id: str):
    s = str(paper_id or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="无效的论文ID格式")
    # 允许裸 40 位十六进制（S2 paperId）
    if re.fullmatch(r"[0-9a-fA-F]{40}", s):
        return
    # 其他必须带前缀
    if ":" in s:
        head = s.split(":", 1)[0].strip().upper()
        if head in _ALLOWED_ID_PREFIXES:
            return
        raise HTTPException(
            status_code=400,
            detail=(
                f"未知ID前缀: {head}. 请使用以下之一: "
                "DOI, ARXIV, MAG, ACL, PMID, PMCID, CorpusId, URL; 或提供40位S2 paperId"
            ),
        )
    # 无前缀且非40位S2 ID：拒绝
    raise HTTPException(
        status_code=400,
        detail=(
            "请使用显式前缀（如 DOI:..., ARXIV:..., CorpusId:..., URL:...）或提供40位S2 paperId"
        ),
    )


@router.get("/search")
async def search_papers(
    query: str = Query(..., min_length=1, description="搜索关键词"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    fields: Optional[str] = Query(None, description="要返回的字段，逗号分隔"),
    year: Optional[str] = Query(None, description="发表年份，如：2020 或 2018-2020"),
    venue: Optional[str] = Query(None, description="发表场所"),
    fields_of_study: Optional[str] = Query(None, description="研究领域"),
    match_title: bool = Query(False, description="启用标题精准匹配模式（仅返回最佳1条）"),
    prefer_local: bool = Query(True, description="本地优先：先查Neo4j，未命中再走S2"),
    fallback_to_s2: bool = Query(True, description="未命中本地时是否回退调用S2")
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
            fields_of_study=fields_of_study,
            match_title=match_title,
            prefer_local=prefer_local,
            fallback_to_s2=fallback_to_s2
        )
        
        return search_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索论文失败 query={query}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/batch")
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
        
        return batch_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量获取论文失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/search/match")
async def match_paper_title(
    query: str = Query(..., min_length=1, description="论文标题（将执行最相近匹配）"),
    fields: Optional[str] = Query(None, description="要返回的字段，逗号分隔"),
    prefer_local: bool = Query(True, description="本地优先：先查Neo4j，未命中再走S2"),
    fallback_to_s2: bool = Query(True, description="未命中本地时是否回退调用S2")
):
    """
    标题精准匹配（/paper/search/match）
    - 流程：本地精确/模糊命中其一 → 直接返回；否则可回退到S2的 match 接口。
    - 语义对齐S2：未命中返回404("Title match not found")；命中仅返回最优1条。
    - 返回形态对齐S2：顶层 {total, offset, data:[paper]}。
    """
    try:
        # 仅用于参数校验；limit固定1
        await pre_check(query, 0, 1, fields, None, None, None)

        search_results = await core_paper_service.search_papers(
            query=query,
            offset=0,
            limit=1,
            fields=fields,
            match_title=True,
            prefer_local=prefer_local,
            fallback_to_s2=fallback_to_s2
        )

        papers = []
        try:
            papers = search_results.get('data') or search_results.get('papers') or []
        except Exception:
            papers = []

        if not papers:
            raise HTTPException(status_code=404, detail="Title match not found")

        return {
            'total': 1,
            'offset': 0,
            'data': [papers[0]]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标题精准匹配失败 query={query}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


## 注意：为确保更具体的路径（如 /citations, /references, /cache）优先匹配，
## 将通配的详情路由放在文件末尾注册。


@router.get("/{paper_id:path}/citations")
async def get_paper_citations(
    paper_id: str,
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    fields: Optional[str] = Query(None, description="要返回的字段，逗号分隔")
):
    """获取论文引用 - 实现缓存策略。对齐S2：顶层返回 {total, offset, data}。"""
    try:
        _validate_paper_identifier_strict(paper_id)
        citations_data = await core_paper_service.get_paper_citations(
            paper_id, offset, limit, fields
        )
        # 对齐S2接口字段命名
        if isinstance(citations_data, dict) and 'citations' in citations_data and 'data' not in citations_data:
            citations_data = {
                'total': citations_data.get('total', 0),
                'offset': citations_data.get('offset', offset),
                'data': citations_data.get('citations', [])
            }
        return citations_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取论文引用失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{paper_id:path}/references")
async def get_paper_references(
    paper_id: str,
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    fields: Optional[str] = Query(None, description="要返回的字段，逗号分隔")
):
    """获取论文参考文献 - 实现缓存策略。对齐S2：顶层返回 {total, offset, data}。"""
    try:
        _validate_paper_identifier_strict(paper_id)
        references_data = await core_paper_service.get_paper_references(
            paper_id, offset, limit, fields
        )
        if isinstance(references_data, dict) and 'references' in references_data and 'data' not in references_data:
            references_data = {
                'total': references_data.get('total', 0),
                'offset': references_data.get('offset', offset),
                'data': references_data.get('references', [])
            }
        return references_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取论文参考文献失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


## 缓存管理API 已迁移至 app/api/v1/debug.py


# 通配的详情路由放在文件末尾，避免与更具体的子路径冲突
@router.get("/{paper_id:path}")
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
        _validate_paper_identifier_strict(paper_id)
        paper_data = await core_paper_service.get_paper(paper_id, fields)
        return paper_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取论文失败 paper_id={paper_id}: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")