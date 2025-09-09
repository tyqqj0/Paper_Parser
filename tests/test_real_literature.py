#!/usr/bin/env python3
"""
真实文献测试脚本
测试Paper Parser系统的核心功能
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.abspath('.'))

from app.clients.s2_client import S2SDKClient
from app.services.core_paper_service import CorePaperService
from app.core.config import ErrorCodes
from fastapi import HTTPException


class RealLiteratureTest:
    def __init__(self):
        self.s2_client = S2SDKClient()
        self.paper_service = CorePaperService()
        self.test_results = []
        
    def log_test(self, test_name: str, status: str, details: dict = None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status}")
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
        print()

    async def test_paper_search(self):
        """测试论文搜索功能"""
        print("=== 测试论文搜索功能 ===")
        
        # 测试用例1: 搜索经典论文
        test_queries = [
            {
                "query": "attention is all you need",
                "description": "经典Transformer论文",
                "expected_min_results": 1
            },
            {
                "query": "BERT: Pre-training of Deep Bidirectional Transformers",
                "description": "BERT论文",
                "expected_min_results": 1
            },
            {
                "query": "machine learning",
                "description": "通用机器学习搜索",
                "expected_min_results": 10
            }
        ]
        
        for test_case in test_queries:
            try:
                print(f"搜索: {test_case['query']}")
                results = await self.paper_service.search_papers(
                    query=test_case['query'],
                    limit=10
                )
                
                # 检查返回结果格式
                if results and isinstance(results, dict) and 'data' in results:
                    data = results['data']
                    if data and len(data) >= test_case['expected_min_results']:
                        self.log_test(
                            f"搜索测试: {test_case['description']}", 
                            "PASS",
                            {
                                "query": test_case['query'],
                                "results_count": len(data),
                                "total_available": results.get('total', 0),
                                "first_title": data[0].get('title', 'N/A')[:50] + "..." if data and data[0] and data[0].get('title') else 'N/A'
                            }
                        )
                    else:
                        self.log_test(
                            f"搜索测试: {test_case['description']}", 
                            "FAIL",
                            {
                                "query": test_case['query'],
                                "results_count": len(data) if data else 0,
                                "expected_min": test_case['expected_min_results'],
                                "total_available": results.get('total', 0)
                            }
                        )
                else:
                    self.log_test(
                        f"搜索测试: {test_case['description']}", 
                        "FAIL",
                        {
                            "query": test_case['query'],
                            "error": f"返回格式错误: {type(results)}" if results else "无结果",
                            "expected_min": test_case['expected_min_results']
                        }
                    )
                    
            except HTTPException as e:
                self.log_test(
                    f"搜索测试: {test_case['description']}", 
                    "FAIL",
                    {
                        "error": f"HTTP {e.status_code}: {e.detail}",
                        "query": test_case['query']
                    }
                )
            except Exception as e:
                self.log_test(
                    f"搜索测试: {test_case['description']}", 
                    "FAIL",
                    {
                        "error": str(e),
                        "query": test_case['query']
                    }
                )

    async def test_paper_details(self):
        """测试论文详情获取"""
        print("=== 测试论文详情获取 ===")
        
        # 首先搜索一篇论文获取paper_id
        try:
            search_results = await self.paper_service.search_papers(
                query="attention is all you need",
                limit=1
            )
            
            if not search_results or not search_results.get('data'):
                self.log_test("获取测试论文ID", "FAIL", {"error": "搜索结果为空"})
                return
                
            paper_id = search_results['data'][0].get('paperId')
            if not paper_id:
                self.log_test("获取测试论文ID", "FAIL", {"error": "论文ID为空"})
                return
                
            print(f"使用论文ID: {paper_id}")
            
            # 测试获取论文详情
            paper_details = await self.s2_client.get_paper(paper_id)
            
            if paper_details:
                # 验证关键字段
                required_fields = ['title', 'abstract', 'authors', 'year']
                missing_fields = []
                present_fields = {}
                
                for field in required_fields:
                    if field in paper_details and paper_details[field]:
                        present_fields[field] = "✓"
                    else:
                        missing_fields.append(field)
                        present_fields[field] = "✗"
                
                if not missing_fields:
                    self.log_test(
                        "论文详情获取", 
                        "PASS",
                        {
                            "paper_id": paper_id,
                            "title": paper_details.get('title', 'N/A')[:50] + "...",
                            "authors_count": len(paper_details.get('authors', [])),
                            "year": paper_details.get('year', 'N/A'),
                            "citation_count": paper_details.get('citationCount', 'N/A')
                        }
                    )
                else:
                    self.log_test(
                        "论文详情获取", 
                        "WARN",
                        {
                            "paper_id": paper_id,
                            "missing_fields": missing_fields,
                            "present_fields": present_fields
                        }
                    )
            else:
                self.log_test(
                    "论文详情获取", 
                    "FAIL",
                    {"paper_id": paper_id, "error": "返回结果为空"}
                )
                
        except Exception as e:
            self.log_test(
                "论文详情获取", 
                "FAIL",
                {"error": str(e)}
            )

    async def test_citation_relationships(self):
        """测试引用关系获取"""
        print("=== 测试引用关系获取 ===")
        
        try:
            # 搜索一篇有引用的论文
            search_results = await self.paper_service.search_papers(
                query="attention is all you need",
                limit=1
            )
            
            if not search_results or not search_results.get('data'):
                self.log_test("引用关系测试", "FAIL", {"error": "无法找到测试论文"})
                return
                
            paper_id = search_results['data'][0].get('paperId')
            
            # 测试获取引用
            citations = await self.s2_client.get_paper_citations(paper_id, limit=5)
            references = await self.s2_client.get_paper_references(paper_id, limit=5)
            
            citation_count = len(citations) if citations else 0
            reference_count = len(references) if references else 0
            
            if citation_count > 0 or reference_count > 0:
                self.log_test(
                    "引用关系获取", 
                    "PASS",
                    {
                        "paper_id": paper_id,
                        "citations_found": citation_count,
                        "references_found": reference_count
                    }
                )
            else:
                self.log_test(
                    "引用关系获取", 
                    "WARN",
                    {
                        "paper_id": paper_id,
                        "message": "未找到引用或参考文献（可能是API限制）"
                    }
                )
                
        except Exception as e:
            self.log_test(
                "引用关系获取", 
                "FAIL",
                {"error": str(e)}
            )

    async def test_error_handling(self):
        """测试错误处理"""
        print("=== 测试错误处理 ===")
        
        # 测试无效论文ID
        try:
            result = await self.s2_client.get_paper("invalid_paper_id_12345")
            self.log_test(
                "无效ID错误处理", 
                "FAIL",
                {"error": "应该抛出异常但没有"}
            )
        except HTTPException as e:
            if e.status_code == 404:
                self.log_test(
                    "无效ID错误处理", 
                    "PASS",
                    {"status_code": e.status_code, "detail": e.detail}
                )
            else:
                self.log_test(
                    "无效ID错误处理", 
                    "WARN",
                    {"status_code": e.status_code, "detail": e.detail}
                )
        except Exception as e:
            self.log_test(
                "无效ID错误处理", 
                "WARN",
                {"error": str(e), "type": type(e).__name__}
            )
        
        # 测试空查询
        try:
            result = await self.paper_service.search_papers(query="", limit=10)
            if not result or not result.get('data'):
                self.log_test(
                    "空查询处理", 
                    "PASS",
                    {"message": "正确返回空结果"}
                )
            else:
                self.log_test(
                    "空查询处理", 
                    "WARN",
                    {"message": "空查询返回了结果", "count": len(result.get('data', []))}
                )
        except Exception as e:
            self.log_test(
                "空查询处理", 
                "WARN",
                {"error": str(e)}
            )

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始真实文献测试")
        print("=" * 50)
        
        start_time = datetime.now()
        
        # 运行各项测试
        await self.test_paper_search()
        await self.test_paper_details()
        await self.test_citation_relationships()
        await self.test_error_handling()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warned_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        print("=" * 50)
        print("📊 测试结果汇总")
        print(f"总测试数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"❌ 失败: {failed_tests}")
        print(f"⚠️  警告: {warned_tests}")
        print(f"⏱️  耗时: {duration:.2f}秒")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"🎯 成功率: {success_rate:.1f}%")
        
        # 保存详细结果
        with open('test_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'warned': warned_tests,
                    'success_rate': success_rate,
                    'duration_seconds': duration,
                    'timestamp': start_time.isoformat()
                },
                'details': self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        print("\n📁 详细结果已保存到 test_results.json")


async def main():
    """主函数"""
    tester = RealLiteratureTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
