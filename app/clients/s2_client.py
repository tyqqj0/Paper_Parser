"""
Semantic Scholar API客户端
"""
import asyncio
import hashlib
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

import httpx
from loguru import logger

from app.core.config import settings, ErrorCodes


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """获取请求许可"""
        async with self.lock:
            now = datetime.now()
            # 清理过期的请求记录
            self.requests = [
                req_time for req_time in self.requests
                if now - req_time < timedelta(seconds=self.time_window)
            ]
            
            if len(self.requests) >= self.max_requests:
                # 计算需要等待的时间
                oldest_request = min(self.requests)
                wait_time = self.time_window - (now - oldest_request).total_seconds()
                if wait_time > 0:
                    logger.warning(f"达到速率限制，等待 {wait_time:.2f} 秒")
                    await asyncio.sleep(wait_time)
                    return await self.acquire()
            
            self.requests.append(now)


class S2ApiClient:
    """Semantic Scholar API客户端"""
    
    def __init__(self):
        self.base_url = settings.s2_base_url
        self.api_key = settings.s2_api_key
        self.rate_limiter = RateLimiter(settings.s2_rate_limit)
        self.client: Optional[httpx.AsyncClient] = None
        
        # 默认请求头
        self.headers = {
            "User-Agent": "PaperParser/1.0 (https://github.com/your-org/paper-parser)"
        }
        if self.api_key:
            self.headers["x-api-key"] = self.api_key
    
    async def connect(self):
        """初始化HTTP客户端"""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.s2_timeout),
            limits=httpx.Limits(
                max_connections=settings.max_concurrent_requests,
                max_keepalive_connections=10
            ),
            headers=self.headers
        )
        logger.info("S2 API客户端初始化完成")
    
    async def disconnect(self):
        """关闭HTTP客户端"""
        if self.client:
            await self.client.aclose()
            logger.info("S2 API客户端已关闭")
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """发送HTTP请求"""
        if not self.client:
            await self.connect()
        
        # 速率限制
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            logger.debug(f"S2 API请求: {method} {url}, params={params}")
            
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=json_data
            )
            
            # 处理响应
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # 速率限制
                retry_after = int(response.headers.get("Retry-After", 60))
                if retry_count < settings.retry_attempts:
                    logger.warning(f"S2 API速率限制，等待 {retry_after} 秒后重试")
                    await asyncio.sleep(retry_after)
                    return await self._request(method, endpoint, params, json_data, retry_count + 1)
                else:
                    raise S2ApiException(ErrorCodes.S2_RATE_LIMITED, "API rate limit exceeded")
            elif response.status_code == 404:
                raise S2ApiException(ErrorCodes.NOT_FOUND, "Resource not found")
            elif response.status_code >= 500:
                # 服务器错误，重试
                if retry_count < settings.retry_attempts:
                    wait_time = settings.retry_backoff ** retry_count
                    logger.warning(f"S2 API服务器错误 {response.status_code}，{wait_time}秒后重试")
                    await asyncio.sleep(wait_time)
                    return await self._request(method, endpoint, params, json_data, retry_count + 1)
                else:
                    raise S2ApiException(ErrorCodes.S2_API_ERROR, f"Server error: {response.status_code}")
            else:
                raise S2ApiException(ErrorCodes.S2_API_ERROR, f"HTTP {response.status_code}: {response.text}")
                
        except httpx.TimeoutException:
            if retry_count < settings.retry_attempts:
                wait_time = settings.retry_backoff ** retry_count
                logger.warning(f"S2 API超时，{wait_time}秒后重试")
                await asyncio.sleep(wait_time)
                return await self._request(method, endpoint, params, json_data, retry_count + 1)
            else:
                raise S2ApiException(ErrorCodes.TIMEOUT, "Request timeout")
        except httpx.RequestError as e:
            raise S2ApiException(ErrorCodes.S2_API_ERROR, f"Request error: {str(e)}")
    
    async def get_paper(
        self, 
        paper_id: str, 
        fields: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取论文详情"""
        params = {}
        if fields:
            params["fields"] = fields
        
        return await self._request("GET", f"paper/{paper_id}", params=params)
    
    async def get_paper_citations(
        self,
        paper_id: str,
        offset: int = 0,
        limit: int = 100,
        fields: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取论文引用"""
        params = {
            "offset": offset,
            "limit": min(limit, 1000)  # S2 API限制
        }
        if fields:
            params["fields"] = fields
        
        return await self._request("GET", f"paper/{paper_id}/citations", params=params)
    
    async def get_paper_references(
        self,
        paper_id: str,
        offset: int = 0,
        limit: int = 100,
        fields: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取论文参考文献"""
        params = {
            "offset": offset,
            "limit": min(limit, 1000)  # S2 API限制
        }
        if fields:
            params["fields"] = fields
        
        return await self._request("GET", f"paper/{paper_id}/references", params=params)
    
    async def search_papers(
        self,
        query: str,
        offset: int = 0,
        limit: int = 10,
        fields: Optional[str] = None,
        year: Optional[str] = None,
        venue: Optional[str] = None,
        fields_of_study: Optional[str] = None
    ) -> Dict[str, Any]:
        """搜索论文"""
        params = {
            "query": query,
            "offset": offset,
            "limit": min(limit, 100)  # S2 API限制
        }
        
        if fields:
            params["fields"] = fields
        if year:
            params["year"] = year
        if venue:
            params["venue"] = venue
        if fields_of_study:
            params["fieldsOfStudy"] = fields_of_study
        
        return await self._request("GET", "paper/search", params=params)
    
    async def get_papers_batch(
        self,
        paper_ids: List[str],
        fields: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """批量获取论文"""
        if len(paper_ids) > 500:
            raise ValueError("批量请求最多支持500个论文ID")
        
        json_data = {"ids": paper_ids}
        if fields:
            json_data["fields"] = fields
        
        return await self._request("POST", "paper/batch", json_data=json_data)
    
    async def get_author(self, author_id: str, fields: Optional[str] = None) -> Dict[str, Any]:
        """获取作者信息"""
        params = {}
        if fields:
            params["fields"] = fields
        
        return await self._request("GET", f"author/{author_id}", params=params)
    
    async def proxy_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """代理请求 - 用于转发非核心API"""
        return await self._request(method, endpoint, params, json_data)
    
    # 工具方法
    def generate_query_hash(self, query: str, **kwargs) -> str:
        """生成查询哈希用于缓存键"""
        query_string = f"{query}:{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()) if v is not None)}"
        return hashlib.md5(query_string.encode()).hexdigest()
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 使用一个已知存在的论文ID进行测试
            await self.get_paper("649def34f8be52c8b66281af98ae884c09aef38b", fields="paperId,title")
            return True
        except Exception as e:
            logger.error(f"S2 API健康检查失败: {e}")
            return False


class S2ApiException(Exception):
    """S2 API异常"""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(message)


# 全局S2客户端实例
s2_client = S2ApiClient()
