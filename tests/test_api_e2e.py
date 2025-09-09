#!/usr/bin/env python3
"""
Paper Parser API 端到端测试
通过HTTP请求测试完整的后端API服务
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    status: str  # PASS, FAIL, WARN
    timestamp: str
    duration: float
    details: Dict[str, Any]
    error: Optional[str] = None


class PaperParserAPITester:
    """Paper Parser API 端到端测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_prefix = "/api/v1"
        self.session = None
        self.results: List[TestResult] = []
    
    def _print_preview(self, label: str, data: Any, max_chars: int = 1200):
        """控制台打印数据预览，自动截断避免刷屏"""
        try:
            text = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            text = str(data)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... 省略 ..."
        print(f"   {label}:\n{text}")

    def _get_header(self, headers: Dict[str, Any], name: str, default: Any = None) -> Any:
        """不区分大小写获取响应头"""
        if not headers:
            return default
        for k, v in headers.items():
            if k.lower() == name.lower():
                return v
        return default
    
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
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        async with self.session.request(method, url, **kwargs) as response:
            response_data = await response.json()
            return {
                "status_code": response.status,
                "data": response_data,
                "headers": dict(response.headers)
            }
    
    async def _run_test(self, test_name: str, test_func):
        """运行单个测试"""
        print(f"\n🧪 {test_name}")
        start_time = time.time()
        
        try:
            result = await test_func()
            duration = time.time() - start_time
            
            test_result = TestResult(
                test_name=test_name,
                status="PASS",
                timestamp=datetime.now().isoformat(),
                duration=duration,
                details=result
            )
            
            print(f"✅ {test_name}: PASS ({duration:.2f}s)")
            # 打印更丰富的返回预览
            if isinstance(result, dict) and result:
                self._print_preview("返回详情预览", result)
            
        except AssertionError as e:
            duration = time.time() - start_time
            test_result = TestResult(
                test_name=test_name,
                status="FAIL",
                timestamp=datetime.now().isoformat(),
                duration=duration,
                details={},
                error=str(e)
            )
            
            print(f"❌ {test_name}: FAIL - {e}")
            
        except Exception as e:
            duration = time.time() - start_time
            test_result = TestResult(
                test_name=test_name,
                status="WARN",
                timestamp=datetime.now().isoformat(),
                duration=duration,
                details={},
                error=f"{type(e).__name__}: {str(e)}"
            )
            
            print(f"⚠️  {test_name}: WARN - {e}")
        
        self.results.append(test_result)
        return test_result
    
    async def test_service_health(self):
        """测试服务健康状态"""
        # 测试根路径
        response = await self._make_request("GET", "")
        # 根路径是 / 不是 /api/v1，所以直接请求
        root_response = await self.session.get(f"{self.base_url}/")
        root_data = await root_response.json()
        
        assert root_response.status == 200, f"根路径返回状态码: {root_response.status}"
        assert root_data["success"] is True, "根路径响应success字段不为True"
        assert "Paper Parser API" in root_data["data"]["service"], "服务名称不正确"
        
        return {
            "root_status": root_response.status,
            "service_info": root_data["data"],
            "response_time": root_data.get("response_time", "N/A")
        }
    
    async def test_paper_search(self):
        """测试论文搜索API"""
        # 测试经典论文搜索
        response = await self._make_request(
            "GET", 
            "/paper/search",
            params={
                "query": "attention is all you need",
                "limit": 5
            }
        )
        
        assert response["status_code"] == 200, f"搜索API状态码: {response['status_code']}"
        
        data = response["data"]
        assert data["success"] is True, "搜索响应success字段不为True"
        assert "data" in data, "搜索响应缺少data字段"
        
        search_results = data["data"]
        assert "papers" in search_results, "搜索结果缺少papers字段"
        assert "total" in search_results, "搜索结果缺少total字段"
        assert len(search_results["papers"]) > 0, "搜索结果为空"
        
        # 验证第一篇论文的字段
        first_paper = search_results["papers"][0]
        required_fields = ["paperId", "title", "authors", "year"]
        for field in required_fields:
            assert field in first_paper, f"论文缺少必需字段: {field}"
        
        preview = {
            "query": "attention is all you need",
            "results_count": len(search_results["papers"]),
            "total_available": search_results["total"],
            "first_paper": {
                "paperId": first_paper.get("paperId"),
                "title": first_paper.get("title"),
                "year": first_paper.get("year"),
                "authors": [a.get("name") for a in first_paper.get("authors", [])][:5]
            },
            "headers": {
                "x-process-time": self._get_header(response["headers"], "x-process-time", "N/A"),
                "x-cache": self._get_header(response["headers"], "x-cache", "N/A")
            }
        }
        return preview
    
    async def test_paper_detail(self):
        """测试论文详情API"""
        # 先搜索获取一个论文ID
        search_response = await self._make_request(
            "GET",
            "/paper/search",
            params={"query": "attention is all you need", "limit": 1}
        )
        
        paper_id = search_response["data"]["data"]["papers"][0]["paperId"]
        
        # 获取论文详情
        response = await self._make_request("GET", f"/paper/{paper_id}")
        
        assert response["status_code"] == 200, f"论文详情API状态码: {response['status_code']}"
        
        data = response["data"]
        assert data["success"] is True, "论文详情响应success字段不为True"
        assert "data" in data, "论文详情响应缺少data字段"
        
        paper_data = data["data"]
        required_fields = ["paperId", "title", "authors", "year", "citationCount"]
        for field in required_fields:
            assert field in paper_data, f"论文详情缺少必需字段: {field}"
        
        return {
            "paper_id": paper_id,
            "title": paper_data.get("title"),
            "authors_count": len(paper_data.get("authors", [])),
            "year": paper_data.get("year"),
            "citation_count": paper_data.get("citationCount"),
            "headers": {
                "x-process-time": self._get_header(response["headers"], "x-process-time", "N/A"),
                "x-cache": self._get_header(response["headers"], "x-cache", "N/A")
            }
        }
    
    async def test_paper_citations(self):
        """测试论文引用API"""
        # 先搜索获取一个论文ID
        search_response = await self._make_request(
            "GET",
            "/paper/search", 
            params={"query": "attention is all you need", "limit": 1}
        )
        
        paper_id = search_response["data"]["data"]["papers"][0]["paperId"]
        
        # 获取论文引用
        response = await self._make_request(
            "GET",
            f"/paper/{paper_id}/citations",
            params={"limit": 3}
        )
        
        assert response["status_code"] == 200, f"论文引用API状态码: {response['status_code']}"
        
        data = response["data"]
        assert data["success"] is True, "论文引用响应success字段不为True"
        assert "data" in data, "论文引用响应缺少data字段"
        
        citations_data = data["data"]
        assert "citations" in citations_data, "引用数据缺少citations字段"
        
        return {
            "paper_id": paper_id,
            "citations_found": len(citations_data["citations"]),
            "total_citations": citations_data.get("total", 0),
            "headers": {
                "x-process-time": self._get_header(response["headers"], "x-process-time", "N/A"),
                "x-cache": self._get_header(response["headers"], "x-cache", "N/A")
            }
        }
    
    async def test_paper_references(self):
        """测试论文参考文献API"""
        # 先搜索获取一个论文ID
        search_response = await self._make_request(
            "GET",
            "/paper/search",
            params={"query": "attention is all you need", "limit": 1}
        )
        
        paper_id = search_response["data"]["data"]["papers"][0]["paperId"]
        
        # 获取论文参考文献
        response = await self._make_request(
            "GET",
            f"/paper/{paper_id}/references",
            params={"limit": 3}
        )
        
        assert response["status_code"] == 200, f"论文参考文献API状态码: {response['status_code']}"
        
        data = response["data"]
        assert data["success"] is True, "论文参考文献响应success字段不为True"
        assert "data" in data, "论文参考文献响应缺少data字段"
        
        references_data = data["data"]
        assert "references" in references_data, "参考文献数据缺少references字段"
        
        return {
            "paper_id": paper_id,
            "references_found": len(references_data["references"]),
            "total_references": references_data.get("total", 0),
            "headers": {
                "x-process-time": self._get_header(response["headers"], "x-process-time", "N/A"),
                "x-cache": self._get_header(response["headers"], "x-cache", "N/A")
            }
        }
    
    async def test_batch_papers(self):
        """测试批量获取论文API"""
        # 先搜索获取一些论文ID
        search_response = await self._make_request(
            "GET",
            "/paper/search",
            params={"query": "machine learning", "limit": 3}
        )
        
        papers = search_response["data"]["data"]["papers"]
        paper_ids = [paper["paperId"] for paper in papers]
        
        # 批量获取论文
        response = await self._make_request(
            "POST",
            "/paper/batch",
            json={
                "ids": paper_ids,
                "fields": "paperId,title,authors,year,citationCount"
            }
        )
        
        assert response["status_code"] == 200, f"批量获取API状态码: {response['status_code']}"
        
        data = response["data"]
        assert data["success"] is True, "批量获取响应success字段不为True"
        assert "data" in data, "批量获取响应缺少data字段"
        
        batch_data = data["data"]
        assert isinstance(batch_data, list), "批量数据应该是列表"
        assert len(batch_data) == len(paper_ids), f"返回数量不匹配: 期望{len(paper_ids)}, 实际{len(batch_data)}"
        
        return {
            "requested_count": len(paper_ids),
            "returned_count": len(batch_data),
            "paper_ids": paper_ids,
            "headers": {
                "x-process-time": self._get_header(response["headers"], "x-process-time", "N/A"),
                "x-cache": self._get_header(response["headers"], "x-cache", "N/A")
            }
        }
    
    async def test_error_handling(self):
        """测试错误处理"""
        # 测试无效论文ID
        response = await self._make_request("GET", "/paper/invalid_paper_id_12345")
        
        # 应该返回错误但不应该是500
        assert response["status_code"] in [400, 404], f"无效ID应返回400或404，实际: {response['status_code']}"
        
        data = response["data"]
        assert data["success"] is False, "错误响应success字段应为False"
        
        # 测试空查询
        empty_query_response = await self._make_request(
            "GET",
            "/paper/search",
            params={"query": "", "limit": 5}
        )
        
        # 空查询应该返回错误
        assert empty_query_response["status_code"] in [400, 422], f"空查询应返回400或422，实际: {empty_query_response['status_code']}"
        
        return {
            "invalid_id_status": response["status_code"],
            "invalid_id_error": data.get("message", "N/A"),
            "empty_query_status": empty_query_response["status_code"],
            "empty_query_error": empty_query_response["data"].get("message", "N/A")
        }
    
    async def test_search_with_filters(self):
        """测试带过滤条件的搜索"""
        response = await self._make_request(
            "GET",
            "/paper/search",
            params={
                "query": "transformer",
                "year": "2017-2020",
                "limit": 5
            }
        )
        
        assert response["status_code"] == 200, f"过滤搜索API状态码: {response['status_code']}"
        
        data = response["data"]
        assert data["success"] is True, "过滤搜索响应success字段不为True"
        
        search_results = data["data"]
        papers = search_results["papers"]
        
        # 验证年份过滤
        for paper in papers:
            if paper.get("year"):
                assert 2017 <= paper["year"] <= 2020, f"论文年份不在过滤范围内: {paper['year']}"
        
        return {
            "query": "transformer",
            "year_filter": "2017-2020",
            "results_count": len(papers),
            "years_found": [p.get("year") for p in papers if p.get("year")],
            "response_time": response["headers"].get("x-process-time", "N/A")
        }
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始API端到端测试")
        print("=" * 50)
        
        test_cases = [
            ("服务健康检查", self.test_service_health),
            ("论文搜索API", self.test_paper_search),
            ("论文详情API", self.test_paper_detail),
            ("论文引用API", self.test_paper_citations),
            ("论文参考文献API", self.test_paper_references),
            ("批量获取论文API", self.test_batch_papers),
            ("带过滤条件搜索", self.test_search_with_filters),
            ("错误处理测试", self.test_error_handling),
        ]
        
        for test_name, test_func in test_cases:
            await self._run_test(test_name, test_func)
        
        # 生成测试报告
        await self._generate_report()
    
    async def _generate_report(self):
        """生成测试报告"""
        total = len(self.results)
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        warned = len([r for r in self.results if r.status == "WARN"])
        
        success_rate = (passed / total * 100) if total > 0 else 0
        total_duration = sum(r.duration for r in self.results)
        
        print("\n" + "=" * 50)
        print("📊 API端到端测试报告")
        print("=" * 50)
        print(f"总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"警告: {warned}")
        print(f"成功率: {success_rate:.1f}%")
        print(f"总耗时: {total_duration:.2f}秒")
        print("=" * 50)
        
        # 详细结果
        for result in self.results:
            status_emoji = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}
            print(f"{status_emoji[result.status]} {result.test_name}: {result.status}")
            if result.error:
                print(f"   错误: {result.error}")
        
        # 保存详细报告到文件
        report_data = {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "warned": warned,
                "success_rate": success_rate,
                "duration_seconds": total_duration,
                "timestamp": datetime.now().isoformat()
            },
            "details": [
                {
                    "test_name": r.test_name,
                    "status": r.status,
                    "timestamp": r.timestamp,
                    "duration": r.duration,
                    "details": r.details,
                    "error": r.error
                }
                for r in self.results
            ]
        }
        
        with open("api_test_results.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: api_test_results.json")


async def main():
    """主函数"""
    async with PaperParserAPITester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
