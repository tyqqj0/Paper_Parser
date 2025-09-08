"""
API v1 路由模块
"""
from fastapi import APIRouter

from app.api.v1 import paper, health, proxy

# 创建v1路由器
api_router = APIRouter()

# 注册子路由
api_router.include_router(health.router, prefix="/health", tags=["健康检查"])
api_router.include_router(paper.router, prefix="/paper", tags=["论文API"])
api_router.include_router(proxy.router, prefix="/proxy", tags=["代理API"])
