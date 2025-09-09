#!/usr/bin/env python3
"""
简单API测试 - 不依赖外部服务
"""
import asyncio
import httpx
import json
from loguru import logger

BASE_URL = "http://localhost:8000"

async def test_health():
    """测试健康检查端点"""
    async with httpx.AsyncClient() as client:
        try:
            # 测试正确的健康检查路径
            response = await client.get(f"{BASE_URL}/api/v1/health")
            logger.info(f"健康检查: {response.status_code}")
            if response.status_code == 200:
                logger.info(f"响应: {response.json()}")
                return True
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
        return False

async def test_docs():
    """测试文档端点"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/docs")
            logger.info(f"文档端点: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"文档端点失败: {e}")
        return False

async def test_paper_endpoint():
    """测试论文端点的错误处理"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # 测试一个明显无效的论文ID
            response = await client.get(f"{BASE_URL}/api/v1/paper/invalid_id")
            logger.info(f"无效ID测试: {response.status_code}")
            logger.info(f"响应: {response.text}")
            
            # 应该返回404或500，但不应该是空响应
            return response.status_code in [404, 500] and response.text.strip()
            
        except httpx.TimeoutException:
            logger.error(f"论文端点测试超时")
            return False
        except Exception as e:
            logger.error(f"论文端点测试失败: {e}")
        return False

async def test_root_endpoint():
    """测试根端点"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/")
            logger.info(f"根端点: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"服务信息: {data.get('data', {}).get('service', 'Unknown')}")
                return True
        except Exception as e:
            logger.error(f"根端点测试失败: {e}")
        return False

async def test_search_endpoint():
    """测试搜索端点"""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # 测试搜索功能
            params = {"query": "machine learning", "limit": 1}
            response = await client.get(f"{BASE_URL}/api/v1/paper/search", params=params)
            logger.info(f"搜索端点: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data", {}).get("total", 0) > 0:
                    logger.info(f"搜索成功，找到 {data['data']['total']} 篇论文")
                    return True
            logger.warning(f"搜索响应: {response.text[:200]}...")
        except httpx.TimeoutException:
            logger.error("搜索端点超时")
        except Exception as e:
            logger.error(f"搜索端点测试失败: {e}")
        return False

async def main():
    logger.info("开始简单API测试...")
    
    tests = [
        ("根端点", test_root_endpoint),
        ("健康检查", test_health),
        ("文档端点", test_docs), 
        ("搜索端点", test_search_endpoint),
        ("论文端点", test_paper_endpoint)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        logger.info(f"\n=== 测试 {test_name} ===")
        try:
            if await test_func():
                logger.success(f"✅ {test_name} 通过")
                passed += 1
            else:
                logger.error(f"❌ {test_name} 失败")
        except Exception as e:
            logger.error(f"❌ {test_name} 异常: {e}")
    
    logger.info(f"\n总结: {passed}/{len(tests)} 测试通过")

if __name__ == "__main__":
    asyncio.run(main())
