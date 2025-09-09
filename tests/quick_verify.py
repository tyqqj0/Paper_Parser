#!/usr/bin/env python3
"""
快速验证脚本 - 测试核心功能
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath('.'))

from app.services.core_paper_service import CorePaperService

async def main():
    print("🚀 快速验证 Paper Parser 系统")
    print("=" * 40)
    
    try:
        # 初始化服务
        service = CorePaperService()
        print("✅ 服务初始化成功")
        
        # 测试搜索
        print("🔍 测试搜索功能...")
        results = await service.search_papers("attention is all you need", limit=3)
        
        if results and isinstance(results, dict) and 'data' in results:
            data = results['data']
            print(f"✅ 搜索成功! 找到 {len(data)} 篇论文")
            print(f"📊 总计可用: {results.get('total', 0)} 篇")
            
            if data:
                first_paper = data[0]
                print(f"📄 第一篇: {first_paper.get('title', 'N/A')}")
                print(f"👥 作者数: {len(first_paper.get('authors', []))}")
                print(f"📅 年份: {first_paper.get('year', 'N/A')}")
                print(f"📈 引用数: {first_paper.get('citationCount', 'N/A')}")
        else:
            print("❌ 搜索失败或返回格式错误")
            print(f"返回类型: {type(results)}")
            print(f"返回内容: {results}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 40)
    print("🏁 快速验证完成")

if __name__ == "__main__":
    asyncio.run(main())

