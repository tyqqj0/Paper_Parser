#!/usr/bin/env python3
"""
Paper Parser 快速端到端测试
用于快速验证系统核心功能是否正常工作
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any, Tuple


class QuickE2ETester:
    """快速端到端测试器"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.api_prefix = "/api/v1"
        self.session = None
        self.test_results = []
        
        # 测试用的论文ID（经典论文）
        self.test_paper_id = "204e3073870fae3d05bcbc2f6a8e263d9b72e776"  # Attention is All You Need
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"Content-Type": "application/json"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Tuple[int, Dict, float]:
        """发送请求并返回状态码、数据和响应时间"""
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        start_time = time.time()
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                data = await response.json()
                response_time = time.time() - start_time
                return response.status, data, response_time
        except Exception as e:
            response_time = time.time() - start_time
            return 0, {"error": str(e)}, response_time
    
    def _log_test(self, name: str, success: bool, duration: float, details: str = ""):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name} ({duration:.2f}s) {details}")
        self.test_results.append({
            "name": name,
            "success": success,
            "duration": duration,
            "details": details
        })
    
    async def test_health_check(self):
        """健康检查测试"""
        print("\n🏥 健康检查测试")
        start = time.time()
        
        try:
            # 基础健康检查
            status, data, _ = await self._request("GET", "/health")
            health_ok = status == 200
            
            # 详细健康检查
            detail_status, detail_data, _ = await self._request("GET", "/health/detailed")
            detail_ok = detail_status == 200
            
            # 根路径检查
            root_response = await self.session.get(f"{self.base_url}/")
            root_data = await root_response.json()
            root_ok = root_response.status == 200
            
            overall_success = health_ok and detail_ok and root_ok
            details = f"基础:{status} 详细:{detail_status} 根路径:{root_response.status}"
            
            self._log_test("健康检查", overall_success, time.time() - start, details)
            return overall_success
            
        except Exception as e:
            self._log_test("健康检查", False, time.time() - start, f"异常: {str(e)}")
            return False
    
    async def test_paper_search(self):
        """论文搜索测试"""
        print("\n🔍 论文搜索测试")
        start = time.time()
        
        try:
            status, data, response_time = await self._request(
                "GET", "/paper/search",
                params={"query": "attention is all you need", "limit": 5}
            )
            
            success = (
                status == 200 and
                data.get("success") is True and
                len(data.get("data", {}).get("papers", [])) > 0
            )
            
            results_count = len(data.get("data", {}).get("papers", [])) if success else 0
            details = f"状态码:{status} 结果数:{results_count} 响应时间:{response_time:.3f}s"
            
            self._log_test("论文搜索", success, time.time() - start, details)
            return success
            
        except Exception as e:
            self._log_test("论文搜索", False, time.time() - start, f"异常: {str(e)}")
            return False
    
    async def test_paper_detail(self):
        """论文详情测试"""
        print("\n📄 论文详情测试")
        start = time.time()
        
        try:
            status, data, response_time = await self._request("GET", f"/paper/{self.test_paper_id}")
            
            paper_data = data.get("data", {}) if status == 200 else {}
            required_fields = ["paperId", "title", "authors", "year"]
            has_required_fields = all(field in paper_data for field in required_fields)
            
            success = (
                status == 200 and
                data.get("success") is True and
                has_required_fields
            )
            
            title = paper_data.get("title", "")[:50] + "..." if len(paper_data.get("title", "")) > 50 else paper_data.get("title", "")
            details = f"状态码:{status} 标题:{title} 响应时间:{response_time:.3f}s"
            
            self._log_test("论文详情", success, time.time() - start, details)
            return success
            
        except Exception as e:
            self._log_test("论文详情", False, time.time() - start, f"异常: {str(e)}")
            return False
    
    async def test_paper_citations(self):
        """论文引用测试"""
        print("\n📚 论文引用测试")
        start = time.time()
        
        try:
            status, data, response_time = await self._request(
                "GET", f"/paper/{self.test_paper_id}/citations",
                params={"limit": 5}
            )
            
            citations_data = data.get("data", {}) if status == 200 else {}
            has_citations = "citations" in citations_data
            citations_count = len(citations_data.get("citations", []))
            
            success = (
                status == 200 and
                data.get("success") is True and
                has_citations
            )
            
            details = f"状态码:{status} 引用数:{citations_count} 响应时间:{response_time:.3f}s"
            
            self._log_test("论文引用", success, time.time() - start, details)
            return success
            
        except Exception as e:
            self._log_test("论文引用", False, time.time() - start, f"异常: {str(e)}")
            return False
    
    async def test_paper_references(self):
        """论文参考文献测试"""
        print("\n📖 论文参考文献测试")
        start = time.time()
        
        try:
            status, data, response_time = await self._request(
                "GET", f"/paper/{self.test_paper_id}/references",
                params={"limit": 5}
            )
            
            references_data = data.get("data", {}) if status == 200 else {}
            has_references = "references" in references_data
            references_count = len(references_data.get("references", []))
            
            success = (
                status == 200 and
                data.get("success") is True and
                has_references
            )
            
            details = f"状态码:{status} 参考文献数:{references_count} 响应时间:{response_time:.3f}s"
            
            self._log_test("论文参考文献", success, time.time() - start, details)
            return success
            
        except Exception as e:
            self._log_test("论文参考文献", False, time.time() - start, f"异常: {str(e)}")
            return False
    
    async def test_batch_request(self):
        """批量请求测试"""
        print("\n📦 批量请求测试")
        start = time.time()
        
        try:
            # 先搜索获取一些论文ID
            search_status, search_data, _ = await self._request(
                "GET", "/paper/search",
                params={"query": "machine learning", "limit": 3}
            )
            
            if search_status != 200:
                self._log_test("批量请求", False, time.time() - start, "搜索失败，无法获取测试数据")
                return False
            
            papers = search_data.get("data", {}).get("papers", [])
            if not papers:
                self._log_test("批量请求", False, time.time() - start, "搜索无结果，无法测试批量请求")
                return False
            
            paper_ids = [paper["paperId"] for paper in papers[:2]]
            
            # 批量请求
            status, data, response_time = await self._request(
                "POST", "/paper/batch",
                json={"ids": paper_ids, "fields": "paperId,title,year"}
            )
            
            batch_data = data.get("data", []) if status == 200 else []
            success = (
                status == 200 and
                data.get("success") is True and
                len(batch_data) == len(paper_ids)
            )
            
            details = f"状态码:{status} 请求数:{len(paper_ids)} 返回数:{len(batch_data)} 响应时间:{response_time:.3f}s"
            
            self._log_test("批量请求", success, time.time() - start, details)
            return success
            
        except Exception as e:
            self._log_test("批量请求", False, time.time() - start, f"异常: {str(e)}")
            return False
    
    async def test_error_handling(self):
        """错误处理测试"""
        print("\n⚠️  错误处理测试")
        start = time.time()
        
        try:
            # 测试无效论文ID
            invalid_status, invalid_data, _ = await self._request("GET", "/paper/invalid_id")
            invalid_handled = invalid_status in [400, 404] and invalid_data.get("success") is False
            
            # 测试空查询
            empty_status, empty_data, _ = await self._request(
                "GET", "/paper/search",
                params={"query": "", "limit": 5}
            )
            empty_handled = empty_status in [400, 422]
            
            success = invalid_handled and empty_handled
            details = f"无效ID:{invalid_status} 空查询:{empty_status}"
            
            self._log_test("错误处理", success, time.time() - start, details)
            return success
            
        except Exception as e:
            self._log_test("错误处理", False, time.time() - start, f"异常: {str(e)}")
            return False
    
    async def test_cache_performance(self):
        """缓存性能测试"""
        print("\n🚀 缓存性能测试")
        start = time.time()
        
        try:
            # 第一次请求（可能缓存未命中）
            _, _, first_time = await self._request("GET", f"/paper/{self.test_paper_id}")
            
            # 等待一小段时间
            await asyncio.sleep(0.5)
            
            # 第二次请求（应该缓存命中）
            _, _, second_time = await self._request("GET", f"/paper/{self.test_paper_id}")
            
            # 第三次请求（应该缓存命中）
            _, _, third_time = await self._request("GET", f"/paper/{self.test_paper_id}")
            
            # 判断缓存是否生效（后续请求应该更快）
            avg_cached_time = (second_time + third_time) / 2
            cache_effective = avg_cached_time < first_time or avg_cached_time < 0.1  # 缓存请求应该很快
            
            details = f"首次:{first_time:.3f}s 缓存平均:{avg_cached_time:.3f}s 提速:{first_time/avg_cached_time:.1f}x" if avg_cached_time > 0 else "缓存测试异常"
            
            self._log_test("缓存性能", cache_effective, time.time() - start, details)
            return cache_effective
            
        except Exception as e:
            self._log_test("缓存性能", False, time.time() - start, f"异常: {str(e)}")
            return False
    
    async def run_quick_tests(self):
        """运行快速测试套件"""
        print("🚀 Paper Parser 快速端到端测试")
        print("=" * 50)
        
        test_functions = [
            self.test_health_check,
            self.test_paper_search,
            self.test_paper_detail,
            self.test_paper_citations,
            self.test_paper_references,
            self.test_batch_request,
            self.test_error_handling,
            self.test_cache_performance,
        ]
        
        # 运行所有测试
        results = []
        total_start = time.time()
        
        for test_func in test_functions:
            result = await test_func()
            results.append(result)
        
        total_time = time.time() - total_start
        
        # 生成摘要报告
        self._generate_summary_report(results, total_time)
        
        return all(results)
    
    def _generate_summary_report(self, results: list, total_time: float):
        """生成摘要报告"""
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 50)
        print("📊 快速测试摘要报告")
        print("=" * 50)
        print(f"总测试数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"❌ 失败: {total_tests - passed_tests}")
        print(f"🎯 成功率: {success_rate:.1f}%")
        print(f"⏱️  总耗时: {total_time:.2f}秒")
        print("=" * 50)
        
        # 状态判断
        if success_rate == 100:
            print("🎉 所有测试通过！系统运行正常。")
        elif success_rate >= 80:
            print("⚠️  大部分测试通过，但有少数问题需要关注。")
        else:
            print("❌ 多个测试失败，系统可能存在问题，请检查。")
        
        # 保存简单报告
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "success_rate": success_rate,
                "duration": total_time
            },
            "test_results": self.test_results
        }
        
        with open("quick_e2e_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: quick_e2e_report.json")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Paper Parser 快速端到端测试")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="API服务地址")
    args = parser.parse_args()
    
    print(f"🔗 测试目标: {args.url}")
    print(f"🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        async with QuickE2ETester(args.url) as tester:
            success = await tester.run_quick_tests()
            return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
