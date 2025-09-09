"""
代理服务 - 直接转发到Semantic Scholar API
"""
from typing import Optional, Dict, Any

from fastapi import HTTPException
from loguru import logger

from app.clients.s2_client import s2_client
from app.models import S2ApiException
from app.core.config import ErrorCodes


class ProxyService:
    """代理服务 - 直接转发S2 API"""
    
    def __init__(self):
        self.s2 = s2_client
    
    async def proxy_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        代理请求到S2 API
        
        Args:
            method: HTTP方法
            path: API路径
            params: 查询参数
            json_data: JSON数据
            
        Returns:
            S2 API的原始响应
        """
        try:
            logger.debug(f"代理请求: {method} {path}")
            
            # 直接调用S2客户端
            result = await self.s2.proxy_request(
                method=method,
                endpoint=path,
                params=params,
                json_data=json_data
            )
            
            logger.debug(f"代理请求成功: {method} {path}")
            return result
            
        except S2ApiException as e:
            logger.error(f"S2 API错误: {e.error_code} - {e.message}")
            
            # 根据错误类型返回相应的HTTP状态码
            if e.error_code == ErrorCodes.NOT_FOUND:
                raise HTTPException(status_code=404, detail=e.message)
            elif e.error_code == ErrorCodes.S2_RATE_LIMITED:
                raise HTTPException(status_code=429, detail=e.message)
            elif e.error_code == ErrorCodes.TIMEOUT:
                raise HTTPException(status_code=408, detail=e.message)
            else:
                raise HTTPException(status_code=500, detail=f"上游API错误: {e.message}")
                
        except Exception as e:
            logger.error(f"代理请求失败 {method} {path}: {e}")
            raise HTTPException(status_code=500, detail="代理服务错误")


# 全局代理服务实例
proxy_service = ProxyService()
