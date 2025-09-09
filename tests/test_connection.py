#!/usr/bin/env python3
"""
简单的网络连接测试
"""
import asyncio
import aiohttp
import time
from loguru import logger

async def test_basic_connection():
    """测试基本网络连接"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        'query': 'machine learning',
        'limit': 1,
        'fields': 'paperId,title'
    }
    
    print("=== 基本连接测试 ===")
    print(f"URL: {url}")
    print(f"参数: {params}")
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10秒超时
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print("发送请求...")
            start_time = time.time()
            
            async with session.get(url, params=params) as response:
                elapsed = time.time() - start_time
                print(f"响应状态: {response.status}")
                print(f"响应时间: {elapsed:.2f}秒")
                print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"返回数据结构: {type(data)}")
                    print(f"数据键: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                    
                    if isinstance(data, dict) and 'data' in data:
                        papers = data['data']
                        print(f"论文数量: {len(papers)}")
                        if papers:
                            print(f"第一篇论文: {papers[0].get('title', 'N/A')}")
                    
                    return True
                else:
                    text = await response.text()
                    print(f"错误响应: {text[:200]}")
                    return False
                    
    except asyncio.TimeoutError:
        print("请求超时!")
        return False
    except Exception as e:
        print(f"连接错误: {type(e).__name__}: {e}")
        return False

async def test_sdk_basic():
    """测试SDK基本功能"""
    print("\n=== SDK基本测试 ===")
    
    try:
        from semanticscholar import AsyncSemanticScholar
        
        client = AsyncSemanticScholar(timeout=10)
        print("SDK客户端创建成功")
        
        start_time = time.time()
        print("调用search_paper...")
        
        results = await client.search_paper(
            query='machine learning',
            limit=1,
            fields=['paperId', 'title']
        )
        
        elapsed = time.time() - start_time
        print(f"SDK调用时间: {elapsed:.2f}秒")
        print(f"结果类型: {type(results)}")
        print(f"results是否为None: {results is None}")
        
        if results:
            print(f"results.total: {getattr(results, 'total', 'N/A')}")
            
            # 测试异步遍历
            print("开始遍历结果...")
            count = 0
            async for paper in results:
                count += 1
                print(f"论文{count}: {paper.title}")
                break  # 只取第一个
            
            print(f"成功遍历{count}篇论文")
            return True
        else:
            print("SDK返回None")
            return False
            
    except Exception as e:
        print(f"SDK测试失败: {type(e).__name__}: {e}")
        import traceback
        print(traceback.format_exc())
        return False

async def main():
    print("开始连接测试...\n")
    
    # 测试1: 直接HTTP请求
    http_ok = await test_basic_connection()
    
    # 测试2: SDK调用
    sdk_ok = await test_sdk_basic()
    
    print(f"\n=== 测试结果 ===")
    print(f"HTTP请求: {'✓' if http_ok else '✗'}")
    print(f"SDK调用: {'✓' if sdk_ok else '✗'}")

if __name__ == "__main__":
    asyncio.run(main())

