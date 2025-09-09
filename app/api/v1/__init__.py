"""
API v1 路由模块
"""
from fastapi import APIRouter

from app.api.v1 import paper, health, proxy

# 创建v1路由器
api_router = APIRouter()

# 注册子路由
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(paper.router, prefix="/paper", tags=["Paper"])
api_router.include_router(proxy.router, prefix="/proxy", tags=["Proxy"])
