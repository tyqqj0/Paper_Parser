"""
论文数据模型
基于Semantic Scholar API规范
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ExternalIds(BaseModel):
    """外部ID模型"""
    ArXiv: Optional[str] = None
    MAG: Optional[str] = None
    ACL: Optional[str] = None
    PubMed: Optional[str] = None
    Medline: Optional[str] = None
    PubMedCentral: Optional[str] = None
    DBLP: Optional[str] = None
    DOI: Optional[str] = None


class PublicationVenue(BaseModel):
    """发表场所模型"""
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    alternate_names: Optional[List[str]] = None
    url: Optional[str] = None


class OpenAccessPdf(BaseModel):
    """开放获取PDF模型"""
    url: Optional[str] = None
    status: Optional[str] = None


class S2FieldOfStudy(BaseModel):
    """S2研究领域模型"""
    category: str
    source: str


class Journal(BaseModel):
    """期刊信息模型"""
    name: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None


class CitationStyles(BaseModel):
    """引用格式模型"""
    bibtex: Optional[str] = None


class AuthorInfo(BaseModel):
    """作者信息模型"""
    authorId: Optional[str] = None
    name: Optional[str] = None


class PaperInfo(BaseModel):
    """论文基础信息模型 (用于引用和参考文献)"""
    paperId: Optional[str] = None
    corpusId: Optional[int] = None
    externalIds: Optional[ExternalIds] = None
    url: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    venue: Optional[str] = None
    year: Optional[int] = None
    referenceCount: Optional[int] = None
    citationCount: Optional[int] = None
    influentialCitationCount: Optional[int] = None
    isOpenAccess: Optional[bool] = None
    fieldsOfStudy: Optional[List[str]] = None
    s2FieldsOfStudy: Optional[List[S2FieldOfStudy]] = None
    publicationTypes: Optional[List[str]] = None
    publicationDate: Optional[str] = None
    authors: Optional[List[AuthorInfo]] = None


class Paper(BaseModel):
    """完整论文模型"""
    paperId: str
    corpusId: Optional[int] = None
    externalIds: Optional[ExternalIds] = None
    url: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    venue: Optional[str] = None
    publicationVenue: Optional[PublicationVenue] = None
    year: Optional[int] = None
    referenceCount: Optional[int] = None
    citationCount: Optional[int] = None
    influentialCitationCount: Optional[int] = None
    isOpenAccess: Optional[bool] = None
    openAccessPdf: Optional[OpenAccessPdf] = None
    fieldsOfStudy: Optional[List[str]] = None
    s2FieldsOfStudy: Optional[List[S2FieldOfStudy]] = None
    publicationTypes: Optional[List[str]] = None
    publicationDate: Optional[str] = None
    journal: Optional[Journal] = None
    citationStyles: Optional[CitationStyles] = None
    authors: Optional[List[AuthorInfo]] = None
    citations: Optional[List[PaperInfo]] = None
    references: Optional[List[PaperInfo]] = None
    
    # 内部元数据
    last_updated: Optional[datetime] = Field(default_factory=datetime.now)
    source: str = "s2"
    cached_at: Optional[datetime] = None


class SearchResult(BaseModel):
    """搜索结果模型"""
    total: int
    offset: int
    next: Optional[int] = None
    data: List[PaperInfo]


class BatchRequest(BaseModel):
    """批量请求模型"""
    ids: List[str] = Field(..., max_items=500, description="论文ID列表，最多500个")
    fields: Optional[str] = None


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str
    status: str  # processing, completed, failed
    progress: int = 0
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ApiResponse(BaseModel):
    """统一API响应模型"""
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthCheck(BaseModel):
    """健康检查模型"""
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, bool] = {}
    metrics: Optional[Dict[str, Any]] = None
