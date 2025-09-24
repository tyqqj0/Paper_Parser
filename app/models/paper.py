"""
基于官方SDK的增强数据模型
结合Pydantic验证和官方SDK的完整字段定义
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from pydantic import BaseModel, Field, validator
from app.utils.semanticscholar.Paper import Paper as S2Paper


class PaperFieldsConfig:
    """
    论文字段配置 - 基于官方SDK的完整字段列表
    用于动态构建API请求和缓存策略
    """
    ATOMIC_DOTTED_FIELDS = [
        'embedding.specter_v2'
    ]
    EMBEDDING_FIELDS = [
        'embedding.specter_v2'
    ]
    # 核心字段 - 最常用，优先缓存
    CORE_FIELDS = [
        'paperId', 'title', 'abstract', 'year', 'authors',
        'citationCount', 'referenceCount', 'influentialCitationCount',
        'venue', 'fieldsOfStudy', 'url'
    ]
    
    # 扩展字段 - 详情页面需要
    EXTENDED_FIELDS = [
        'publicationDate', 'publicationTypes', 'publicationVenue',
        'journal', 'externalIds', 'openAccessPdf', 'isOpenAccess',
        's2FieldsOfStudy', 'citationStyles', 'corpusId'
    ]
    
    # 关系字段 - 引用和参考文献 (按需加载)
    RELATION_FIELDS = [
        'citations', 'references'
    ]
    
    # 嵌套字段 - 作者详情
    AUTHOR_FIELDS = [
        'authors.authorId', 'authors.name', 'authors.affiliations',
        'authors.citationCount', 'authors.hIndex', 'authors.paperCount'
    ]
    
    # 引用详情字段
    CITATION_FIELDS = [
        'citations.paperId', 'citations.title', 'citations.year',
        'citations.authors', 'citations.citationCount', 'citations.venue'
    ]
    
    # 参考文献详情字段  
    REFERENCE_FIELDS = [
        'references.paperId', 'references.title', 'references.year',
        'references.authors', 'references.citationCount', 'references.venue'
    ]
    
    @classmethod
    def get_fields_for_level(cls, level: str) -> List[str]:
        """
        根据缓存级别获取字段列表
        
        Args:
            level: 'core', 'extended', 'full'
        """
        if level == 'core':
            return cls.CORE_FIELDS
        elif level == 'extended':
            return cls.CORE_FIELDS + cls.EXTENDED_FIELDS + cls.AUTHOR_FIELDS
        elif level == 'full':
            return (cls.CORE_FIELDS + cls.EXTENDED_FIELDS + 
                   cls.AUTHOR_FIELDS + cls.CITATION_FIELDS + cls.REFERENCE_FIELDS)
        else:
            return cls.CORE_FIELDS
    @classmethod
    def param_str_to_list(cls, param) -> Optional[List[str]]:
        """将参数转换为列表"""
        if param is None:
            return None
        if isinstance(param, str):
            return [p.strip() for p in param.split(',')]
        return param
    @classmethod
    def param_list_to_str(cls, param) -> Optional[str]:
        """将参数转换为字符串"""
        if param is None:
            return None
        if isinstance(param, list):
            return ','.join(param)
        return param
    @classmethod
    def get_normal_fields(cls) -> List[str]:
        return cls.get_fields_for_level('extended')+cls.EMBEDDING_FIELDS
    @classmethod
    def normalize_fields(cls,fields=None) -> List[str]:
        if fields:
            fields = cls.param_str_to_list(fields)
            return list(set(cls.param_str_to_list(fields)+cls.get_normal_fields()))
        else:   
            return cls.get_normal_fields()
    @classmethod
    def is_in_noraml_fields(cls,fields=None) -> bool:
        if not fields:
            return True
        fields = cls.param_str_to_list(fields)
        return set(fields).issubset(set(cls.get_normal_fields()))
    @classmethod
    def remove_relations_fields(cls, fields: List[str]) -> List[str]:
        """移除关系字段"""
        return [f for f in fields if not f.startswith('citations') and not f.startswith('references')]
    

class EnhancedPaper(BaseModel):
    """
    增强的论文模型
    结合Pydantic验证和官方SDK的数据结构
    """
    
    # === 核心字段 ===
    paperId: str
    title: Optional[str] = None
    abstract: Optional[str] = None
    year: Optional[int] = None
    
    # === 统计字段 ===
    citationCount: Optional[int] = 0
    referenceCount: Optional[int] = 0
    influentialCitationCount: Optional[int] = 0
    
    # === 发表信息 ===
    venue: Optional[str] = None
    publicationDate: Optional[str] = None
    publicationTypes: Optional[List[str]] = None
    journal: Optional[Dict[str, Any]] = None
    publicationVenue: Optional[Dict[str, Any]] = None
    
    # === 分类和标识 ===
    fieldsOfStudy: Optional[List[str]] = None
    s2FieldsOfStudy: Optional[List[Dict[str, Any]]] = None
    externalIds: Optional[Dict[str, Any]] = None
    corpusId: Optional[str] = None
    
    # === 访问信息 ===
    url: Optional[str] = None
    openAccessPdf: Optional[Dict[str, Any]] = None
    isOpenAccess: Optional[bool] = None
    
    # === 作者信息 ===
    authors: Optional[List[Dict[str, Any]]] = None
    
    # === 引用信息 (可选，按需加载) ===
    citations: Optional[List[Dict[str, Any]]] = None
    references: Optional[List[Dict[str, Any]]] = None
    
    # === 其他字段 ===
    citationStyles: Optional[Dict[str, Any]] = None
    embedding: Optional[Dict[str, Any]] = None
    tldr: Optional[Dict[str, Any]] = None
    
    # === 缓存元数据 ===
    cached_at: Optional[datetime] = Field(default_factory=datetime.now)
    cache_level: Optional[str] = 'core'  # core, extended, full
    
    class Config:
        # 允许额外字段，保持与S2 API的完全兼容
        extra = "allow"
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('year')
    def validate_year(cls, v):
        """验证年份合理性"""
        if v is not None and (v < 1900 or v > 2030):
            return None
        return v
    
    @validator('citationCount', 'referenceCount', 'influentialCitationCount')
    def validate_counts(cls, v):
        """验证计数字段非负"""
        if v is not None and v < 0:
            return 0
        return v
    
    @classmethod
    def from_s2_paper(cls, s2_paper: S2Paper, cache_level: str = 'core') -> 'EnhancedPaper':
        """从官方SDK的Paper对象创建"""
        data = s2_paper.raw_data.copy()
        data['cache_level'] = cache_level
        return cls(**data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], cache_level: str = 'core') -> 'EnhancedPaper':
        """从字典创建"""
        data = data.copy()
        data['cache_level'] = cache_level
        return cls(**data)
    
    def to_dict(self, include_meta: bool = False) -> Dict[str, Any]:
        """转换为字典"""
        data = self.dict(exclude_none=True)
        if not include_meta:
            # 移除缓存元数据
            data.pop('cached_at', None)
            data.pop('cache_level', None)
        return data
    
    def get_cache_key(self) -> str:
        """获取缓存键"""
        return f"paper:{self.paperId}"
    
    def is_cache_expired(self, ttl_seconds: int = 3600) -> bool:
        """检查缓存是否过期"""
        if not self.cached_at:
            return True
        
        age = (datetime.now() - self.cached_at).total_seconds()
        return age > ttl_seconds
    
    def merge_with_fresh_data(self, fresh_data: Dict[str, Any]) -> 'EnhancedPaper':
        """与新数据合并，保留更完整的字段"""
        current_data = self.to_dict(include_meta=True)
        
        # 合并策略：新数据覆盖，但保留已有的非空字段
        for key, value in fresh_data.items():
            if value is not None:
                current_data[key] = value
            # 如果新数据为空但当前有值，保留当前值
        
        # 更新缓存时间
        current_data['cached_at'] = datetime.now()
        
        return self.__class__(**current_data)


class SearchResult(BaseModel):
    """搜索结果模型"""
    total: int
    offset: int = 0
    next: Optional[int] = None
    data: List[EnhancedPaper]
    
    @classmethod
    def from_s2_result(cls, s2_result: Any) -> 'SearchResult':
        """从S2搜索结果创建"""
        papers = []
        for paper_data in s2_result.get('data', []):
            if isinstance(paper_data, dict):
                papers.append(EnhancedPaper.from_dict(paper_data))
        
        return cls(
            total=s2_result.get('total', len(papers)),
            offset=s2_result.get('offset', 0),
            next=s2_result.get('next'),
            data=papers
        )


class BatchResult(BaseModel):
    """批量查询结果"""
    requested_ids: List[str]
    found_papers: List[EnhancedPaper]
    missing_ids: List[str]
    
    @classmethod
    def from_results(
        cls, 
        requested_ids: List[str], 
        results: List[Optional[Dict[str, Any]]]
    ) -> 'BatchResult':
        """从结果列表创建"""
        found_papers = []
        missing_ids = []
        
        for i, result in enumerate(results):
            if result:
                found_papers.append(EnhancedPaper.from_dict(result))
            else:
                missing_ids.append(requested_ids[i])
        
        return cls(
            requested_ids=requested_ids,
            found_papers=found_papers,
            missing_ids=missing_ids
        )


class BatchRequest(BaseModel):
    """批量查询请求"""
    ids: List[str]
    fields: Optional[str] = None


class ApiResponse(BaseModel):
    """API响应格式"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None


@dataclass
class HealthCheck:
    """健康检查响应"""
    status: str
    version: Optional[str] = None
    timestamp: Optional[str] = None
    services: Optional[Dict[str, str]] = None
    metrics: Optional[Dict[str, Any]] = None
