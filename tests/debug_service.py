#!/usr/bin/env python3
"""
调试core_paper_service
"""
import asyncio
import sys
import traceback
from loguru import logger

# 添加项目路径
sys.path.append('/home/parser/code/Paper_Parser')

async def test_service():
    try:
        from app.services.core_paper_service import core_paper_service
        
        logger.info("开始测试core_paper_service...")
        
        # 测试搜索
        logger.info("测试搜索功能...")
        result = await core_paper_service.search_papers(
            query="machine learning",
            limit=2,
            fields="title,authors"
        )
        
        logger.info(f"搜索结果: {result}")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_service())
