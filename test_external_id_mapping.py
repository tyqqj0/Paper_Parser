#!/usr/bin/env python3
"""
测试外部ID映射服务
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.services.external_id_mapping import ExternalIdMappingService

async def test_get_paper_id():
    """测试get_paper_id方法"""
    
    # 创建服务实例
    service = ExternalIdMappingService("data/external_id_mapping.db")
    
    # 初始化
    await service.initialize()
    
    # 测试查询
    external_id = "conf/naacl/AmmarGBBCDDEFHK18"
    external_type = "DBLP"
    
    print(f"🔍 测试查询: {external_id}, {external_type}")
    
    try:
        result = await service.get_paper_id(external_id, external_type)
        if result:
            print(f"✅ 查询成功: {result}")
        else:
            print("❌ 查询失败: 未找到记录")
            
    except Exception as e:
        print(f"❌ 查询异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_get_paper_id())
