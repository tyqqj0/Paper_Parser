#!/usr/bin/env python3
"""
端到端API测试脚本
测试所有修复后的API端点
"""

import asyncio
import json
import time
from typing import Dict, Any, List
import httpx
from loguru import logger

# 配置日志
logger.remove()
logger.add("test_results.log", rotation="1 MB", retention="1 day")
logger.add(lambda msg: print(msg, end=""), colorize=True)

BASE_URL = "http://localhost:8000/api/v1/paper"

class APITester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_result(self, test_name: str, success: bool, response_data: Dict[Any, Any] = None, error: str = None):
        """记录测试结果"""
        result = {
            "test": test_name,
            "success": success,
            "timestamp": time.time(),
            "response_data": response_data,
            "error": error
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if error:
            logger.error(f"    Error: {error}")
        if response_data:
            logger.info(f"    Response: {json.dumps(response_data, ensure_ascii=False, indent=2)[:200]}...")
    
    async def test_search_papers(self):
        """测试论文搜索API"""
        logger.info("🔍 测试论文搜索API...")
        
        try:
            # 基础搜索测试
            response = await self.client.get(
                f"{BASE_URL}/search",
                params={
                    "query": "machine learning",
                    "limit": 3,
                    "fields": "title,authors,year,abstract"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    self.log_result("搜索API - 基础功能", True, data)
                    return True
                else:
                    self.log_result("搜索API - 基础功能", False, data, "响应数据格式错误")
            else:
                self.log_result("搜索API - 基础功能", False, None, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("搜索API - 基础功能", False, None, str(e))
        
        return False
    
    async def test_search_with_filters(self):
        """测试带过滤条件的搜索"""
        logger.info("🔍 测试带过滤条件的搜索...")
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/search",
                params={
                    "query": "neural networks",
                    "year": "2020-2023",
                    "limit": 2,
                    "fields": "title,year,venue"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_result("搜索API - 过滤条件", True, data)
                    return True
                else:
                    self.log_result("搜索API - 过滤条件", False, data, "搜索失败")
            else:
                self.log_result("搜索API - 过滤条件", False, None, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("搜索API - 过滤条件", False, None, str(e))
        
        return False
    
    async def test_get_paper_by_id(self):
        """测试根据ID获取论文"""
        logger.info("📄 测试获取单篇论文...")
        
        # 使用一个已知的论文ID进行测试
        test_paper_ids = [
            "649def34f8be52c8b66281af98ae884c09aef38b",  # Semantic Scholar ID
            "10.1038/nature14539",  # DOI
            "1706.03762"  # ArXiv ID (Attention is All You Need)
        ]
        
        for paper_id in test_paper_ids:
            try:
                response = await self.client.get(
                    f"{BASE_URL}/{paper_id}",
                    params={"fields": "title,authors,year,abstract,citationCount"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("data"):
                        self.log_result(f"获取论文 - {paper_id[:20]}...", True, data)
                        return True
                    else:
                        self.log_result(f"获取论文 - {paper_id[:20]}...", False, data, "论文数据为空")
                elif response.status_code == 404:
                    logger.warning(f"论文 {paper_id} 未找到，尝试下一个...")
                    continue
                else:
                    self.log_result(f"获取论文 - {paper_id[:20]}...", False, None, f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_result(f"获取论文 - {paper_id[:20]}...", False, None, str(e))
        
        return False
    
    async def test_batch_papers(self):
        """测试批量获取论文"""
        logger.info("📚 测试批量获取论文...")
        
        try:
            # 使用一些测试ID
            test_ids = [
                "649def34f8be52c8b66281af98ae884c09aef38b",
                "1706.03762",
                "10.1038/nature14539"
            ]
            
            response = await self.client.post(
                f"{BASE_URL}/batch",
                json={
                    "paper_ids": test_ids,
                    "fields": "title,authors,year"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    self.log_result("批量获取论文", True, data)
                    return True
                else:
                    self.log_result("批量获取论文", False, data, "批量获取失败")
            else:
                self.log_result("批量获取论文", False, None, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("批量获取论文", False, None, str(e))
        
        return False
    
    async def test_citations_and_references(self):
        """测试引用和参考文献API"""
        logger.info("🔗 测试引用和参考文献API...")
        
        # 使用一个有引用数据的论文ID
        paper_id = "1706.03762"  # Attention is All You Need
        
        try:
            # 测试获取引用
            citations_response = await self.client.get(
                f"{BASE_URL}/{paper_id}/citations",
                params={"limit": 3, "fields": "title,year"}
            )
            
            if citations_response.status_code == 200:
                data = citations_response.json()
                if data.get("success"):
                    self.log_result("获取论文引用", True, data)
                else:
                    self.log_result("获取论文引用", False, data, "获取引用失败")
            else:
                self.log_result("获取论文引用", False, None, f"HTTP {citations_response.status_code}")
            
            # 测试获取参考文献
            references_response = await self.client.get(
                f"{BASE_URL}/{paper_id}/references",
                params={"limit": 3, "fields": "title,year"}
            )
            
            if references_response.status_code == 200:
                data = references_response.json()
                if data.get("success"):
                    self.log_result("获取参考文献", True, data)
                    return True
                else:
                    self.log_result("获取参考文献", False, data, "获取参考文献失败")
            else:
                self.log_result("获取参考文献", False, None, f"HTTP {references_response.status_code}")
                
        except Exception as e:
            self.log_result("引用和参考文献", False, None, str(e))
        
        return False
    
    async def test_cache_management(self):
        """测试缓存管理API"""
        logger.info("🗄️ 测试缓存管理API...")
        
        paper_id = "1706.03762"
        
        try:
            # 测试缓存预热
            warm_response = await self.client.post(
                f"{BASE_URL}/{paper_id}/cache/warm",
                params={"fields": "title,authors"}
            )
            
            if warm_response.status_code == 200:
                data = warm_response.json()
                self.log_result("缓存预热", data.get("success", False), data)
            else:
                self.log_result("缓存预热", False, None, f"HTTP {warm_response.status_code}")
            
            # 测试缓存清除
            clear_response = await self.client.delete(f"{BASE_URL}/{paper_id}/cache")
            
            if clear_response.status_code == 200:
                data = clear_response.json()
                self.log_result("缓存清除", data.get("success", False), data)
                return True
            else:
                self.log_result("缓存清除", False, None, f"HTTP {clear_response.status_code}")
                
        except Exception as e:
            self.log_result("缓存管理", False, None, str(e))
        
        return False
    
    async def test_error_handling(self):
        """测试错误处理"""
        logger.info("⚠️ 测试错误处理...")
        
        try:
            # 测试无效的论文ID
            response = await self.client.get(f"{BASE_URL}/invalid_paper_id_12345")
            
            if response.status_code == 404:
                self.log_result("错误处理 - 无效ID", True, {"status": 404})
            else:
                self.log_result("错误处理 - 无效ID", False, None, f"期望404，得到{response.status_code}")
            
            # 测试无效的搜索参数
            response = await self.client.get(
                f"{BASE_URL}/search",
                params={"limit": 1000}  # 超过限制
            )
            
            if response.status_code == 422:
                self.log_result("错误处理 - 无效参数", True, {"status": 422})
                return True
            else:
                self.log_result("错误处理 - 无效参数", False, None, f"期望422，得到{response.status_code}")
                
        except Exception as e:
            self.log_result("错误处理", False, None, str(e))
        
        return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始端到端API测试...")
        logger.info("=" * 60)
        
        # 等待服务启动
        logger.info("⏳ 等待服务启动...")
        await asyncio.sleep(3)
        
        tests = [
            ("搜索API基础功能", self.test_search_papers),
            ("搜索API过滤功能", self.test_search_with_filters),
            ("获取单篇论文", self.test_get_paper_by_id),
            ("批量获取论文", self.test_batch_papers),
            ("引用和参考文献", self.test_citations_and_references),
            ("缓存管理", self.test_cache_management),
            ("错误处理", self.test_error_handling)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n{'=' * 20} {test_name} {'=' * 20}")
            try:
                success = await test_func()
                if success:
                    passed += 1
            except Exception as e:
                logger.error(f"测试 {test_name} 异常: {e}")
        
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 测试完成: {passed}/{total} 通过")
        
        # 保存详细结果
        with open("test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        logger.info("📁 详细结果已保存到 test_results.json")
        
        return passed, total

async def main():
    """主函数"""
    async with APITester() as tester:
        passed, total = await tester.run_all_tests()
        
        if passed == total:
            logger.success("🎉 所有测试通过！")
            return 0
        else:
            logger.warning(f"⚠️ {total - passed} 个测试失败")
            return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
