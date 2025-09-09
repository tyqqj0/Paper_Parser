#!/usr/bin/env python3
"""
API诊断脚本 - 检查各种服务状态
"""
import asyncio
import httpx
import redis
from neo4j import GraphDatabase
from loguru import logger

BASE_URL = "http://localhost:8000"

async def check_redis():
    """检查Redis连接"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=2)
        r.ping()
        logger.success("✅ Redis连接正常")
        return True
    except Exception as e:
        logger.error(f"❌ Redis连接失败: {e}")
        return False

async def check_neo4j():
    """检查Neo4j连接"""
    try:
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        with driver.session() as session:
            result = session.run("RETURN 1")
            result.single()
        driver.close()
        logger.success("✅ Neo4j连接正常")
        return True
    except Exception as e:
        logger.error(f"❌ Neo4j连接失败: {e}")
        return False

async def check_s2_direct():
    """直接检查Semantic Scholar API"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # 直接调用S2 API
            response = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": "test", "limit": 1}
            )
            logger.info(f"S2 API直接调用: {response.status_code}")
            if response.status_code == 200:
                logger.success("✅ Semantic Scholar API可访问")
                return True
            else:
                logger.error(f"❌ S2 API返回: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ S2 API调用失败: {e}")
        return False

async def test_api_with_details():
    """详细测试API端点"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # 测试搜索端点
            response = await client.get(f"{BASE_URL}/api/v1/paper/search?query=test&limit=1")
            logger.info(f"搜索API状态: {response.status_code}")
            logger.info(f"搜索API响应头: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"搜索API错误响应: {response.text}")
            
        except Exception as e:
            logger.error(f"搜索API测试失败: {e}")

async def main():
    logger.info("开始API诊断...")
    
    # 检查外部依赖
    logger.info("\n=== 检查外部服务 ===")
    redis_ok = await check_redis()
    neo4j_ok = await check_neo4j() 
    s2_ok = await check_s2_direct()
    
    # 测试API
    logger.info("\n=== 测试API端点 ===")
    await test_api_with_details()
    
    # 总结
    logger.info("\n=== 诊断总结 ===")
    logger.info(f"Redis: {'✅' if redis_ok else '❌'}")
    logger.info(f"Neo4j: {'✅' if neo4j_ok else '❌'}")
    logger.info(f"Semantic Scholar API: {'✅' if s2_ok else '❌'}")
    
    if not redis_ok:
        logger.warning("建议: 启动Redis服务 - sudo systemctl start redis")
    if not neo4j_ok:
        logger.warning("建议: 启动Neo4j服务或检查连接配置")
    if not s2_ok:
        logger.warning("建议: 检查网络连接或S2 API状态")

if __name__ == "__main__":
    asyncio.run(main())
