#!/usr/bin/env python3
"""
测试完整的外部ID映射场景
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

# 设置工作目录为项目根目录（模拟应用程序环境）
os.chdir(Path(__file__).parent)

from app.services.external_id_mapping import external_id_mapping, ExternalIdMappingService
from app.core.config import settings

async def test_global_instance():
    """测试全局实例"""
    print("🔍 测试全局external_id_mapping实例")
    
    # 检查配置
    print(f"📂 配置的数据库路径: {settings.external_id_mapping_db_path}")
    print(f"📂 实例的数据库路径: {external_id_mapping.db_path}")
    print(f"📁 当前工作目录: {os.getcwd()}")
    print(f"📄 数据库文件是否存在: {external_id_mapping.db_path.exists()}")
    
    # 初始化
    await external_id_mapping.initialize()
    
    # 测试查询
    external_id = "conf/naacl/AmmarGBBCDDEFHK18"
    external_type = "DBLP"
    
    print(f"\n🔍 测试查询: {external_id}, {external_type}")
    
    try:
        result = await external_id_mapping.get_paper_id(external_id, external_type)
        if result:
            print(f"✅ 查询成功: {result}")
        else:
            print("❌ 查询失败: 未找到记录")
            
    except Exception as e:
        print(f"❌ 查询异常: {e}")
        import traceback
        traceback.print_exc()

async def test_direct_database():
    """直接测试数据库连接"""
    import aiosqlite
    
    print("\n🔍 直接测试数据库连接")
    db_path = Path("data/external_id_mapping.db")
    
    try:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute(
                "SELECT paper_id FROM external_id_mappings WHERE external_id = ? AND external_type = ?",
                ("conf/naacl/AmmarGBBCDDEFHK18", "DBLP")
            )
            result = await cursor.fetchone()
            
            if result:
                print(f"✅ 直接查询成功: {result[0]}")
            else:
                print("❌ 直接查询失败: 未找到记录")
                
    except Exception as e:
        print(f"❌ 直接查询异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_global_instance())
    asyncio.run(test_direct_database())
