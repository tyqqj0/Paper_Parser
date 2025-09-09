#!/usr/bin/env python3
"""
调试S2 API调用
"""
import asyncio
import os
import sys
sys.path.append('/home/parser/code/Paper_Parser')

from app.clients.s2_client import s2_client
from app.core.config import settings
from loguru import logger

async def test_s2_api():
    """测试S2 API各种调用"""
    
    print("=== S2 API 调试测试 ===")
    print(f"S2_API_KEY: {'已设置' if settings.s2_api_key else '未设置'}")
    print(f"S2_BASE_URL: {settings.s2_base_url}")
    print(f"S2_TIMEOUT: {settings.s2_timeout}")
    print()
    
    # 测试1: 简单搜索
    print("测试1: 搜索 'machine learning'")
    try:
        result = await s2_client.search_papers(
            query="machine learning",
            limit=2,
            offset=0
        )
        print(f"结果: {result}")
        print()
    except Exception as e:
        print(f"错误: {e}")
        print()
    
    # 测试2: 搜索中文
    print("测试2: 搜索 '深度学习'")  
    try:
        result = await s2_client.search_papers(
            query="深度学习",
            limit=2,
            offset=0
        )
        print(f"结果: {result}")
        print()
    except Exception as e:
        print(f"错误: {e}")
        print()
    
    # 测试3: 获取特定论文
    print("测试3: 获取特定论文 (Attention Is All You Need)")
    try:
        result = await s2_client.get_paper("204e3073870fae3d05bcbc2f6a8e263d9b72e776")
        print(f"结果: {result['title'] if result else None}")
        print()
    except Exception as e:
        print(f"错误: {e}")
        print()
        
    # 测试4: 无结果搜索
    print("测试4: 搜索不存在的内容")
    try:
        result = await s2_client.search_papers(
            query="xyzabcdefghijklmnop12345",
            limit=2,
            offset=0
        )
        print(f"结果: {result}")
        print()
    except Exception as e:
        print(f"错误: {e}")
        print()

if __name__ == "__main__":
    asyncio.run(test_s2_api())

