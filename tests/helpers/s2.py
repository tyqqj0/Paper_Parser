"""
直连S2 API的工具函数（仅用于在线对比测试）
"""
import httpx
from typing import Dict, Any, Optional, List
import asyncio
from urllib.parse import urlencode


class S2DirectClient:
    """直连S2 API的简单客户端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {
            "x-api-key": api_key,
            "User-Agent": "Paper-Parser-Test/1.0"
        }
    
    async def get_paper(
        self, 
        paper_id: str, 
        fields: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """直接从S2获取论文详情"""
        url = f"{self.base_url}/paper/{paper_id}"
        params = {}
        if fields:
            params["fields"] = fields
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=self.headers, params=params)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    response.raise_for_status()
            except Exception as e:
                print(f"S2 API error: {e}")
                return None
    
    async def get_paper_citations(
        self,
        paper_id: str,
        offset: int = 0,
        limit: int = 10,
        fields: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """直接从S2获取论文引用"""
        url = f"{self.base_url}/paper/{paper_id}/citations"
        params = {"offset": offset, "limit": limit}
        if fields:
            params["fields"] = fields
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=self.headers, params=params)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    response.raise_for_status()
            except Exception as e:
                print(f"S2 API error: {e}")
                return None
    
    async def get_paper_references(
        self,
        paper_id: str,
        offset: int = 0,
        limit: int = 10,
        fields: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """直接从S2获取论文参考文献"""
        url = f"{self.base_url}/paper/{paper_id}/references"
        params = {"offset": offset, "limit": limit}
        if fields:
            params["fields"] = fields
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=self.headers, params=params)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    response.raise_for_status()
            except Exception as e:
                print(f"S2 API error: {e}")
                return None
    
    async def search_papers(
        self,
        query: str,
        offset: int = 0,
        limit: int = 10,
        fields: Optional[str] = None,
        year: Optional[str] = None,
        venue: Optional[str] = None,
        fields_of_study: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """直接从S2搜索论文"""
        url = f"{self.base_url}/paper/search"
        params = {
            "query": query,
            "offset": offset,
            "limit": limit
        }
        
        if fields:
            params["fields"] = fields
        if year:
            params["year"] = year
        if venue:
            params["venue"] = venue
        if fields_of_study:
            params["fieldsOfStudy"] = fields_of_study
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=self.headers, params=params)
                if response.status_code == 200:
                    return response.json()
                else:
                    response.raise_for_status()
            except Exception as e:
                print(f"S2 API error: {e}")
                return None
    
    async def get_papers_batch(
        self,
        paper_ids: List[str],
        fields: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """直接从S2批量获取论文"""
        url = f"{self.base_url}/paper/batch"
        
        # S2批量接口使用POST
        payload = {"ids": paper_ids}
        if fields:
            payload["fields"] = fields
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    url, 
                    headers=self.headers, 
                    json=payload
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    response.raise_for_status()
            except Exception as e:
                print(f"S2 API error: {e}")
                return None
    
    async def autocomplete_paper(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """直接从S2获取自动补全"""
        url = f"{self.base_url}/paper/autocomplete"
        params = {"query": query}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=self.headers, params=params)
                if response.status_code == 200:
                    return response.json()
                else:
                    response.raise_for_status()
            except Exception as e:
                print(f"S2 API error: {e}")
                return None


# 工具函数
async def compare_with_s2(
    our_client,
    s2_client: S2DirectClient,
    endpoint: str,
    params: Dict[str, Any],
    compare_fields: List[str]
) -> Dict[str, Any]:
    """比较我们的API与S2的响应"""
    
    # 调用我们的API
    if endpoint.startswith("/paper/") and endpoint.count("/") == 2:
        # 详情接口
        paper_id = endpoint.split("/")[2]
        our_response = await our_client.get(endpoint, params=params)
        s2_response_data = await s2_client.get_paper(
            paper_id, 
            params.get("fields")
        )
    elif "/citations" in endpoint:
        # 引用接口
        paper_id = endpoint.split("/")[2]
        our_response = await our_client.get(endpoint, params=params)
        s2_response_data = await s2_client.get_paper_citations(
            paper_id,
            params.get("offset", 0),
            params.get("limit", 10),
            params.get("fields")
        )
    elif "/references" in endpoint:
        # 参考文献接口
        paper_id = endpoint.split("/")[2]
        our_response = await our_client.get(endpoint, params=params)
        s2_response_data = await s2_client.get_paper_references(
            paper_id,
            params.get("offset", 0),
            params.get("limit", 10),
            params.get("fields")
        )
    elif "/search" in endpoint:
        # 搜索接口
        our_response = await our_client.get(endpoint, params=params)
        s2_response_data = await s2_client.search_papers(**params)
    else:
        raise ValueError(f"Unsupported endpoint: {endpoint}")
    
    our_data = our_response.json() if our_response.status_code == 200 else None
    
    return {
        "our_response": our_data,
        "s2_response": s2_response_data,
        "our_status": our_response.status_code,
        "comparison_fields": compare_fields
    }
