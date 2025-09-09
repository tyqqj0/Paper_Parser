#!/usr/bin/env python3
"""
最小化测试 - 只验证能否成功获取一个结果
"""
import asyncio
from semanticscholar import AsyncSemanticScholar

async def main():
    print("=== 最小化S2测试 ===")
    
    try:
        # 创建客户端，设置较长的超时时间
        client = AsyncSemanticScholar(timeout=30)
        print("✓ 客户端创建成功")
        
        # 只搜索1个结果，最小字段
        print("开始搜索（limit=1）...")
        results = await client.search_paper(
            query='machine learning',
            limit=1,
            fields=['paperId', 'title']
        )
        
        if results:
            print("✓ 搜索成功，开始获取结果...")
            count = 0
            async for paper in results:
                count += 1
                print(f"✓ 成功获取论文: {paper.title}")
                print(f"✓ Paper ID: {paper.paperId}")
                break  # 只要第一个
            
            if count > 0:
                print("✅ 测试成功！S2 API可以正常访问")
                return True
            else:
                print("❌ 没有获取到任何结果")
                return False
        else:
            print("❌ 搜索返回空结果")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {type(e).__name__}: {e}")
        # 如果是429错误，说明API限流
        if "429" in str(e) or "Too Many Requests" in str(e):
            print("💡 这是API限流错误，说明连接是通的，只是请求太频繁")
            print("💡 建议：等待一段时间后重试，或申请API key")
            return "rate_limited"
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\n最终结果: {result}")

