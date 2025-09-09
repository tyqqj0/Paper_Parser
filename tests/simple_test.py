#!/usr/bin/env python3
"""
简单的S2测试，使用和成功测试相同的方式
"""
import asyncio
from semanticscholar import AsyncSemanticScholar

async def main():
    print("=== 简单S2测试 ===")
    
    # 创建客户端（和之前成功的测试一样）
    client = AsyncSemanticScholar(timeout=10)
    print("客户端创建成功")
    
    try:
        print("开始搜索...")
        results = await client.search_paper(
            query='machine learning',
            limit=2,
            fields=['paperId', 'title', 'abstract', 'year']
        )
        
        print(f"结果类型: {type(results)}")
        print(f"results.total: {getattr(results, 'total', 'N/A')}")
        
        if results:
            print("开始遍历结果...")
            papers = []
            count = 0
            async for paper in results:
                count += 1
                print(f"论文{count}: {paper.title}")
                papers.append({
                    'paperId': paper.paperId,
                    'title': paper.title,
                    'year': getattr(paper, 'year', None)
                })
                if count >= 2:  # 只要2篇
                    break
            
            print(f"\n成功获取{len(papers)}篇论文:")
            for i, paper in enumerate(papers, 1):
                print(f"{i}. {paper['title']} ({paper['year']})")
            
            return papers
        else:
            print("无结果")
            return None
            
    except Exception as e:
        print(f"错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\n最终结果: {len(result) if result else 0}篇论文")

