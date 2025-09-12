"""
Paper Parser 主应用入口
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys

from app.core.config import settings
from app.clients.redis_client import redis_client
from app.clients.neo4j_client import neo4j_client
from app.clients.s2_client import s2_client
from app.api.v1 import api_router
from app.models.paper import HealthCheck
from app.tasks.queue import task_queue


# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("Paper Parser 启动中...")
    
    try:
        # 初始化数据库连接
        await redis_client.connect()
        await neo4j_client.connect()
        # S2 SDK客户端在初始化时就已经准备就绪，不需要connect
        # 连接任务队列（若不可用将自动降级）
        await task_queue.connect()
        
        logger.info("所有服务连接成功")
        
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        raise
    
    yield
    
    # 关闭时清理资源
    logger.info("Paper Parser 关闭中...")
    await redis_client.disconnect()
    await neo4j_client.disconnect()
    await s2_client.disconnect()
    await task_queue.disconnect()
    logger.info("所有服务连接已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="Paper Parser API",
    description="基于Semantic Scholar的学术论文缓存和代理服务",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理 - 返回S2风格错误"""
    logger.error(f"未处理的异常: {type(exc).__name__}: {str(exc)}")
    return JSONResponse(status_code=500, content={"error": "Internal Server Error"})


# HTTP异常处理器，统一响应格式
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    # 与S2保持一致: 仅返回 {"error": message}
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件"""
    start_time = asyncio.get_event_loop().time()
    
    # 记录请求
    logger.info(f"请求开始: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # 计算处理时间
    process_time = asyncio.get_event_loop().time() - start_time
    
    # 记录响应
    logger.info(
        f"请求完成: {request.method} {request.url} "
        f"状态码: {response.status_code} "
        f"耗时: {process_time:.3f}s"
    )
    
    # 添加响应头
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# 注册路由
app.include_router(api_router, prefix=settings.api_prefix)


# 根路径
@app.get("/")
async def root():
    """根路径 - 服务信息"""
    return {
        "service": "Paper Parser API",
        "version": "0.1.0",
        "description": "基于Semantic Scholar的学术论文缓存和代理服务",
        "docs_url": "/docs",
        "health_url": f"{settings.api_prefix}/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
