#!/usr/bin/env python3
"""
测试并发访问和异常情况
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

from app.services.external_id_mapping import external_id_mapping

async def simulate_concurrent_access():
    """模拟并发访问"""
    print("🔍 测试并发访问情况")
    
    external_id = "conf/naacl/AmmarGBBCDDEFHK18"
    external_type = "DBLP"
    
    # 模拟多个并发查询
    tasks = []
    for i in range(10):
        task = external_id_mapping.get_paper_id(external_id, external_type)
        tasks.append(task)
    
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ 任务 {i+1} 失败: {result}")
            else:
                print(f"✅ 任务 {i+1} 成功: {result}")
                
    except Exception as e:
        print(f"❌ 并发测试异常: {e}")

async def test_database_lock():
    """测试数据库锁定情况"""
    print("\n🔍 测试数据库锁定情况")
    
    import aiosqlite
    db_path = Path("data/external_id_mapping.db")
    
    try:
        # 创建一个长时间的连接来模拟锁定
        async with aiosqlite.connect(db_path) as db:
            # 开始一个事务但不提交
            await db.execute("BEGIN EXCLUSIVE TRANSACTION")
            
            print("📎 已锁定数据库，现在尝试查询...")
            
            # 在另一个任务中尝试查询
            try:
                result = await external_id_mapping.get_paper_id("conf/naacl/AmmarGBBCDDEFHK18", "DBLP")
                print(f"🎯 查询结果: {result}")
            except Exception as e:
                print(f"❌ 查询失败（可能是锁定导致）: {e}")
            
            # 回滚事务
            await db.execute("ROLLBACK")
            print("🔓 已释放数据库锁")
            
    except Exception as e:
        print(f"❌ 锁定测试异常: {e}")

async def test_missing_database():
    """测试数据库文件不存在的情况"""
    print("\n🔍 测试数据库文件不存在的情况")
    
    # 创建一个指向不存在数据库的服务实例
    from app.services.external_id_mapping import ExternalIdMappingService
    service = ExternalIdMappingService("data/nonexistent.db")
    
    try:
        result = await service.get_paper_id("conf/naacl/AmmarGBBCDDEFHK18", "DBLP")
        print(f"🎯 查询结果: {result}")
    except Exception as e:
        print(f"❌ 不存在数据库查询失败: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_concurrent_access())
    asyncio.run(test_database_lock())
    asyncio.run(test_missing_database())
