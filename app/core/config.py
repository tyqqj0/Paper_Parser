"""
应用配置管理
"""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用设置"""
    
    # API配置
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")  
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    
    # Semantic Scholar API配置
    s2_api_key: Optional[str] = Field(default=None, alias="S2_API_KEY")
    s2_base_url: str = Field(
        default="https://api.semanticscholar.org/graph/v1", 
        alias="S2_BASE_URL"
    )
    s2_rate_limit: int = Field(default=100, alias="S2_RATE_LIMIT")
    s2_timeout: int = Field(default=60, alias="S2_TIMEOUT")
    
    # Redis配置
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_max_connections: int = Field(default=20, alias="REDIS_MAX_CONNECTIONS")
    redis_default_ttl: int = Field(default=3600, alias="REDIS_DEFAULT_TTL")
    
    # Neo4j配置
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="password", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")
    
    # Celery配置
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", 
        alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", 
        alias="CELERY_RESULT_BACKEND"
    )
    
    # 监控配置
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # 开发配置
    debug: bool = Field(default=False, alias="DEBUG")
    reload: bool = Field(default=False, alias="RELOAD")
    
    # 缓存配置
    cache_paper_ttl: int = Field(default=3600, alias="CACHE_PAPER_TTL")  # 1小时
    cache_search_ttl: int = Field(default=1800, alias="CACHE_SEARCH_TTL")  # 30分钟
    cache_task_ttl: int = Field(default=600, alias="CACHE_TASK_TTL")  # 10分钟
    
    # 性能配置
    max_concurrent_requests: int = Field(default=10, alias="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=25, alias="REQUEST_TIMEOUT")
    retry_attempts: int = Field(default=3, alias="RETRY_ATTEMPTS")
    retry_backoff: float = Field(default=2.0, alias="RETRY_BACKOFF")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局设置实例
settings = Settings()


# 缓存键模板
class CacheKeys:
    """缓存键模板"""
    
    # 论文相关
    PAPER_FULL = "paper:{paper_id}:full"
    PAPER_BASIC = "paper:{paper_id}:basic"
    PAPER_CITATIONS = "paper:{paper_id}:citations"
    PAPER_REFERENCES = "paper:{paper_id}:references"
    
    # 外部ID映射
    PAPER_DOI = "paper:doi:{doi}"
    PAPER_ARXIV = "paper:arxiv:{arxiv_id}"
    PAPER_PUBMED = "paper:pubmed:{pubmed_id}"
    
    # 搜索相关
    SEARCH_QUERY = "search:{query_hash}"
    SEARCH_AUTOCOMPLETE = "autocomplete:{query}"
    
    # 任务状态
    TASK_STATUS = "task:{paper_id}:status"
    TASK_PROGRESS = "task:{task_id}:progress"
    
    # 系统状态
    SYSTEM_S2_STATUS = "system:s2_api_status"
    SYSTEM_METRICS = "system:metrics"


# 错误码定义
class ErrorCodes:
    """错误码定义"""
    
    # 通用错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    
    # S2 API错误
    S2_API_ERROR = "S2_API_ERROR"
    S2_RATE_LIMITED = "S2_RATE_LIMITED"
    S2_UNAVAILABLE = "S2_UNAVAILABLE"
    S2_NETWORK_ERROR = "S2_NETWORK_ERROR"
    S2_AUTH_ERROR = "S2_AUTH_ERROR"
    
    # 缓存错误
    CACHE_ERROR = "CACHE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    
    # 任务错误
    TASK_FAILED = "TASK_FAILED"
    TASK_TIMEOUT = "TASK_TIMEOUT"
