"""
健康检查API
"""
from fastapi import APIRouter
from loguru import logger

from app.models.paper import HealthCheck, ApiResponse
from app.clients.redis_client import redis_client
from app.clients.neo4j_client import neo4j_client
from app.clients.s2_client import s2_client
from app import __version__

router = APIRouter()


@router.get("", response_model=ApiResponse)
async def health_check():
    """基础健康检查"""
    return ApiResponse(
        success=True,
        data=HealthCheck(
            status="healthy",
            version=__version__
        ),
        message="服务运行正常"
    )


@router.get("/detailed", response_model=ApiResponse)
async def detailed_health_check():
    """详细健康检查"""
    services = {}
    
    # 检查Redis
    try:
        services["redis"] = await redis_client.health_check()
    except Exception as e:
        logger.error(f"Redis健康检查失败: {e}")
        services["redis"] = False
    
    # 检查Neo4j
    try:
        services["neo4j"] = await neo4j_client.health_check()
    except Exception as e:
        logger.error(f"Neo4j健康检查失败: {e}")
        services["neo4j"] = False
    
    # 检查S2 API
    try:
        services["s2_api"] = await s2_client.health_check()
    except Exception as e:
        logger.error(f"S2 API健康检查失败: {e}")
        services["s2_api"] = False
    
    # 获取系统指标
    metrics = {}
    try:
        # Neo4j统计信息
        if services.get("neo4j"):
            metrics["neo4j_stats"] = await neo4j_client.get_stats()
    except Exception as e:
        logger.error(f"获取系统指标失败: {e}")
    
    # 判断整体健康状态
    all_healthy = all(services.values())
    status = "healthy" if all_healthy else "degraded"
    
    return ApiResponse(
        success=all_healthy,
        data=HealthCheck(
            status=status,
            version=__version__,
            services=services,
            metrics=metrics
        ),
        message="详细健康检查完成"
    )
