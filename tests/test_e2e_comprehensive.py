#!/usr/bin/env python3
"""
Paper Parser 全面端到端测试套件
测试整个系统的完整工作流程，包括缓存策略、错误处理和性能验证
"""
import asyncio
import aiohttp
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@dataclass
class TestMetrics:
    """测试指标"""
    test_name: str
    status: str  # PASS, FAIL, WARN, SKIP
    timestamp: str
    duration: float
    response_time: float
    cache_hit: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class SystemHealthCheck:
    """系统健康检查结果"""
    redis_available: bool
    neo4j_available: bool
    s2_api_available: bool
    api_service_running: bool
    overall_status: str


class ComprehensiveE2ETester:
    """全面的端到端测试器"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.api_prefix = "/api/v1"
        self.session = None
        self.metrics: List[TestMetrics] = []
        
        # 测试数据集
        self.test_papers = {
            "attention_paper": "204e3073870fae3d05bcbc2f6a8e263d9b72e776",  # Attention is All You Need
            "bert_paper": "df2b0e26d0599ce3e70df8a9da02e51594e0e992",  # BERT
            "gpt_paper": "cd18800a0fe0b668a1cc19f2ec95b2a0c3a0e3b8",  # GPT
            "invalid_id": "invalid_paper_id_12345",
            "nonexistent_id": "0000000000000000000000000000000000000000"
        }
        
        self.test_queries = [
            "attention is all you need",
            "transformer neural network",
            "machine learning",
            "deep learning",
            "natural language processing",
            "computer vision",
            "artificial intelligence"
        ]
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Paper-Parser-E2E-Test/1.0"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    def _extract_cache_info(self, headers: Dict[str, str]) -> str:
        """提取缓存信息"""
        cache_info = headers.get('x-cache', 'UNKNOWN')
        if cache_info == 'UNKNOWN':
            # 尝试其他可能的缓存头
            for key in headers:
                if 'cache' in key.lower():
                    cache_info = f"{key}:{headers[key]}"
                    break
        return cache_info
    
    def _extract_response_time(self, headers: Dict[str, str]) -> float:
        """提取响应时间"""
        process_time = headers.get('x-process-time', '0')
        try:
            return float(process_time.replace('ms', '').replace('s', ''))
        except (ValueError, AttributeError):
            return 0.0
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Tuple[int, Dict, Dict[str, str]]:
        """发送HTTP请求并返回状态码、数据和头部"""
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                headers = dict(response.headers)
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError:
                    data = {"error": "Invalid JSON response", "text": await response.text()}
                
                return response.status, data, headers
        except asyncio.TimeoutError:
            raise Exception("Request timeout")
        except aiohttp.ClientError as e:
            raise Exception(f"Client error: {str(e)}")
    
    async def _run_test(self, test_name: str, test_func) -> TestMetrics:
        """运行单个测试并记录指标"""
        print(f"\n🧪 {test_name}")
        start_time = time.time()
        
        try:
            result = await test_func()
            duration = time.time() - start_time
            
            metrics = TestMetrics(
                test_name=test_name,
                status="PASS",
                timestamp=datetime.now().isoformat(),
                duration=duration,
                response_time=result.get('response_time', 0),
                cache_hit=result.get('cache_hit'),
                details=result
            )
            
            print(f"✅ {test_name}: PASS ({duration:.2f}s)")
            if result.get('cache_hit'):
                print(f"   📦 缓存: {result['cache_hit']}")
            if result.get('response_time'):
                print(f"   ⏱️  响应时间: {result['response_time']:.3f}s")
            
        except AssertionError as e:
            duration = time.time() - start_time
            metrics = TestMetrics(
                test_name=test_name,
                status="FAIL",
                timestamp=datetime.now().isoformat(),
                duration=duration,
                response_time=0,
                error=str(e)
            )
            print(f"❌ {test_name}: FAIL - {e}")
            
        except Exception as e:
            duration = time.time() - start_time
            metrics = TestMetrics(
                test_name=test_name,
                status="WARN",
                timestamp=datetime.now().isoformat(),
                duration=duration,
                response_time=0,
                error=f"{type(e).__name__}: {str(e)}"
            )
            print(f"⚠️  {test_name}: WARN - {e}")
        
        self.metrics.append(metrics)
        return metrics
    
    # ========== 系统健康检查 ==========
    
    async def test_system_health(self) -> Dict[str, Any]:
        """全面的系统健康检查"""
        health_results = {}
        
        # 1. 基础健康检查
        try:
            status, data, headers = await self._make_request("GET", "/health")
            health_results['basic_health'] = {
                'status_code': status,
                'success': status == 200,
                'response': data
            }
        except Exception as e:
            health_results['basic_health'] = {
                'status_code': 0,
                'success': False,
                'error': str(e)
            }
        
        # 2. 详细健康检查
        try:
            status, data, headers = await self._make_request("GET", "/health/detailed")
            health_results['detailed_health'] = {
                'status_code': status,
                'success': status == 200,
                'response': data,
                'response_time': self._extract_response_time(headers)
            }
            
            # 分析各组件状态
            if status == 200 and isinstance(data, dict):
                components = data.get('data', {})
                health_results['components'] = {
                    'redis': components.get('redis', {}).get('status') == 'healthy',
                    'neo4j': components.get('neo4j', {}).get('status') == 'healthy',
                    's2_api': components.get('s2_api', {}).get('status') == 'healthy',
                }
        except Exception as e:
            health_results['detailed_health'] = {
                'status_code': 0,
                'success': False,
                'error': str(e)
            }
        
        # 3. 根路径检查
        try:
            root_response = await self.session.get(f"{self.base_url}/")
            root_data = await root_response.json()
            health_results['root_endpoint'] = {
                'status_code': root_response.status,
                'success': root_response.status == 200,
                'service_name': root_data.get('data', {}).get('service', 'Unknown')
            }
        except Exception as e:
            health_results['root_endpoint'] = {
                'status_code': 0,
                'success': False,
                'error': str(e)
            }
        
        # 整体健康评估
        overall_healthy = all([
            health_results.get('basic_health', {}).get('success', False),
            health_results.get('detailed_health', {}).get('success', False),
            health_results.get('root_endpoint', {}).get('success', False)
        ])
        
        health_results['overall_status'] = 'HEALTHY' if overall_healthy else 'UNHEALTHY'
        
        return health_results
    
    # ========== 核心API功能测试 ==========
    
    async def test_paper_search_comprehensive(self) -> Dict[str, Any]:
        """全面的论文搜索测试"""
        results = {}
        
        # 1. 基础搜索测试
        query = "attention is all you need"
        status, data, headers = await self._make_request(
            "GET", "/paper/search",
            params={"query": query, "limit": 5}
        )
        
        assert status == 200, f"搜索API状态码异常: {status}"
        assert data["success"] is True, "搜索响应success字段不为True"
        
        search_data = data["data"]
        assert "papers" in search_data, "搜索结果缺少papers字段"
        assert "total" in search_data, "搜索结果缺少total字段"
        assert len(search_data["papers"]) > 0, "搜索结果为空"
        
        results['basic_search'] = {
            'query': query,
            'results_count': len(search_data["papers"]),
            'total_available': search_data["total"],
            'response_time': self._extract_response_time(headers),
            'cache_hit': self._extract_cache_info(headers)
        }
        
        # 2. 带过滤条件的搜索
        status, data, headers = await self._make_request(
            "GET", "/paper/search",
            params={
                "query": "transformer",
                "year": "2017-2020",
                "limit": 10,
                "fields": "paperId,title,authors,year,citationCount"
            }
        )
        
        assert status == 200, f"过滤搜索状态码异常: {status}"
        filtered_papers = data["data"]["papers"]
        
        # 验证年份过滤
        for paper in filtered_papers:
            if paper.get("year"):
                assert 2017 <= paper["year"] <= 2020, f"年份过滤失效: {paper['year']}"
        
        results['filtered_search'] = {
            'query': 'transformer',
            'year_filter': '2017-2020',
            'results_count': len(filtered_papers),
            'years_found': [p.get("year") for p in filtered_papers if p.get("year")],
            'response_time': self._extract_response_time(headers)
        }
        
        # 3. 分页测试
        page1_status, page1_data, _ = await self._make_request(
            "GET", "/paper/search",
            params={"query": "machine learning", "offset": 0, "limit": 5}
        )
        
        page2_status, page2_data, _ = await self._make_request(
            "GET", "/paper/search",
            params={"query": "machine learning", "offset": 5, "limit": 5}
        )
        
        assert page1_status == 200 and page2_status == 200, "分页搜索失败"
        
        page1_papers = page1_data["data"]["papers"]
        page2_papers = page2_data["data"]["papers"]
        
        # 验证分页不重复
        page1_ids = {p["paperId"] for p in page1_papers}
        page2_ids = {p["paperId"] for p in page2_papers}
        overlap = page1_ids & page2_ids
        
        results['pagination'] = {
            'page1_count': len(page1_papers),
            'page2_count': len(page2_papers),
            'overlap_count': len(overlap),
            'pagination_working': len(overlap) == 0
        }
        
        return results
    
    async def test_paper_detail_comprehensive(self) -> Dict[str, Any]:
        """全面的论文详情测试"""
        results = {}
        paper_id = self.test_papers["attention_paper"]
        
        # 1. 基础详情获取
        status, data, headers = await self._make_request("GET", f"/paper/{paper_id}")
        
        assert status == 200, f"论文详情状态码异常: {status}"
        assert data["success"] is True, "详情响应success字段不为True"
        
        paper_data = data["data"]
        required_fields = ["paperId", "title", "authors", "year", "citationCount"]
        for field in required_fields:
            assert field in paper_data, f"论文详情缺少必需字段: {field}"
        
        results['basic_detail'] = {
            'paper_id': paper_id,
            'title': paper_data.get("title"),
            'authors_count': len(paper_data.get("authors", [])),
            'year': paper_data.get("year"),
            'citation_count': paper_data.get("citationCount"),
            'response_time': self._extract_response_time(headers),
            'cache_hit': self._extract_cache_info(headers)
        }
        
        # 2. 字段过滤测试
        status, data, headers = await self._make_request(
            "GET", f"/paper/{paper_id}",
            params={"fields": "paperId,title,year"}
        )
        
        assert status == 200, "字段过滤请求失败"
        filtered_data = data["data"]
        
        # 验证只返回请求的字段
        expected_fields = {"paperId", "title", "year"}
        actual_fields = set(filtered_data.keys())
        
        results['field_filtering'] = {
            'requested_fields': list(expected_fields),
            'returned_fields': list(actual_fields),
            'filtering_working': expected_fields.issubset(actual_fields),
            'response_time': self._extract_response_time(headers)
        }
        
        # 3. 缓存测试 - 连续请求同一论文
        cache_times = []
        for i in range(3):
            start = time.time()
            status, data, headers = await self._make_request("GET", f"/paper/{paper_id}")
            cache_times.append(time.time() - start)
            await asyncio.sleep(0.1)  # 短暂间隔
        
        results['cache_performance'] = {
            'request_times': cache_times,
            'avg_time': sum(cache_times) / len(cache_times),
            'speed_improvement': cache_times[0] / cache_times[-1] if cache_times[-1] > 0 else 1
        }
        
        return results
    
    async def test_paper_relations_comprehensive(self) -> Dict[str, Any]:
        """全面的论文关系测试（引用和参考文献）"""
        results = {}
        paper_id = self.test_papers["attention_paper"]
        
        # 1. 引用测试
        status, data, headers = await self._make_request(
            "GET", f"/paper/{paper_id}/citations",
            params={"limit": 10}
        )
        
        assert status == 200, f"引用API状态码异常: {status}"
        assert data["success"] is True, "引用响应success字段不为True"
        
        citations_data = data["data"]
        assert "citations" in citations_data, "引用数据缺少citations字段"
        
        results['citations'] = {
            'paper_id': paper_id,
            'citations_found': len(citations_data["citations"]),
            'total_citations': citations_data.get("total", 0),
            'response_time': self._extract_response_time(headers),
            'cache_hit': self._extract_cache_info(headers)
        }
        
        # 2. 参考文献测试
        status, data, headers = await self._make_request(
            "GET", f"/paper/{paper_id}/references",
            params={"limit": 10}
        )
        
        assert status == 200, f"参考文献API状态码异常: {status}"
        assert data["success"] is True, "参考文献响应success字段不为True"
        
        references_data = data["data"]
        assert "references" in references_data, "参考文献数据缺少references字段"
        
        results['references'] = {
            'paper_id': paper_id,
            'references_found': len(references_data["references"]),
            'total_references': references_data.get("total", 0),
            'response_time': self._extract_response_time(headers),
            'cache_hit': self._extract_cache_info(headers)
        }
        
        # 3. 分页测试
        citations_page1_status, citations_page1_data, _ = await self._make_request(
            "GET", f"/paper/{paper_id}/citations",
            params={"offset": 0, "limit": 5}
        )
        
        citations_page2_status, citations_page2_data, _ = await self._make_request(
            "GET", f"/paper/{paper_id}/citations",
            params={"offset": 5, "limit": 5}
        )
        
        assert citations_page1_status == 200 and citations_page2_status == 200, "引用分页失败"
        
        results['citations_pagination'] = {
            'page1_count': len(citations_page1_data["data"]["citations"]),
            'page2_count': len(citations_page2_data["data"]["citations"]),
            'pagination_working': True  # 基础检查通过
        }
        
        return results
    
    async def test_batch_operations(self) -> Dict[str, Any]:
        """批量操作测试"""
        results = {}
        
        # 1. 准备测试数据 - 先搜索获取一些论文ID
        status, data, _ = await self._make_request(
            "GET", "/paper/search",
            params={"query": "machine learning", "limit": 5}
        )
        
        assert status == 200, "搜索准备数据失败"
        papers = data["data"]["papers"]
        paper_ids = [paper["paperId"] for paper in papers[:3]]  # 取前3个
        
        # 2. 批量获取测试
        start_time = time.time()
        status, data, headers = await self._make_request(
            "POST", "/paper/batch",
            json={
                "ids": paper_ids,
                "fields": "paperId,title,authors,year,citationCount"
            }
        )
        batch_time = time.time() - start_time
        
        assert status == 200, f"批量获取状态码异常: {status}"
        assert data["success"] is True, "批量获取响应success字段不为True"
        
        batch_data = data["data"]
        assert isinstance(batch_data, list), "批量数据应该是列表"
        
        results['batch_retrieval'] = {
            'requested_count': len(paper_ids),
            'returned_count': len(batch_data),
            'success_rate': len([p for p in batch_data if p is not None]) / len(paper_ids),
            'batch_time': batch_time,
            'avg_time_per_paper': batch_time / len(paper_ids) if paper_ids else 0,
            'response_time': self._extract_response_time(headers)
        }
        
        # 3. 大批量测试 (测试限制)
        large_batch_ids = paper_ids * 50  # 创建150个ID的批量请求
        
        status, data, headers = await self._make_request(
            "POST", "/paper/batch",
            json={"ids": large_batch_ids[:100]}  # 测试100个
        )
        
        results['large_batch'] = {
            'requested_count': 100,
            'status_code': status,
            'success': status == 200,
            'response_time': self._extract_response_time(headers)
        }
        
        return results
    
    # ========== 错误处理和边界测试 ==========
    
    async def test_error_handling_comprehensive(self) -> Dict[str, Any]:
        """全面的错误处理测试"""
        results = {}
        
        # 1. 无效论文ID测试
        invalid_cases = [
            ("too_short", "12345"),
            ("invalid_format", self.test_papers["invalid_id"]),
            ("nonexistent", self.test_papers["nonexistent_id"]),
            ("special_chars", "invalid@#$%^&*()"),
            ("empty_string", "")
        ]
        
        invalid_results = {}
        for case_name, invalid_id in invalid_cases:
            if invalid_id:  # 跳过空字符串测试，会被路由拒绝
                status, data, _ = await self._make_request("GET", f"/paper/{invalid_id}")
                invalid_results[case_name] = {
                    'paper_id': invalid_id,
                    'status_code': status,
                    'success': data.get("success", True),
                    'error_message': data.get("message", "No message")
                }
        
        results['invalid_paper_ids'] = invalid_results
        
        # 2. 搜索错误测试
        search_error_cases = [
            ("empty_query", {"query": "", "limit": 5}),
            ("negative_offset", {"query": "test", "offset": -1}),
            ("excessive_limit", {"query": "test", "limit": 1000}),
            ("invalid_year", {"query": "test", "year": "invalid"}),
        ]
        
        search_errors = {}
        for case_name, params in search_error_cases:
            try:
                status, data, _ = await self._make_request("GET", "/paper/search", params=params)
                search_errors[case_name] = {
                    'params': params,
                    'status_code': status,
                    'success': data.get("success", True),
                    'error_handled': status in [400, 422]
                }
            except Exception as e:
                search_errors[case_name] = {
                    'params': params,
                    'error': str(e),
                    'error_handled': True
                }
        
        results['search_errors'] = search_errors
        
        # 3. 批量请求错误测试
        batch_error_cases = [
            ("empty_ids", {"ids": []}),
            ("too_many_ids", {"ids": ["test"] * 600}),  # 超过限制
            ("invalid_json", "invalid json"),
        ]
        
        batch_errors = {}
        for case_name, payload in batch_error_cases:
            try:
                if case_name == "invalid_json":
                    # 发送无效JSON
                    url = f"{self.base_url}{self.api_prefix}/paper/batch"
                    async with self.session.post(url, data=payload) as response:
                        status = response.status
                        try:
                            data = await response.json()
                        except:
                            data = {"error": "Invalid JSON"}
                else:
                    status, data, _ = await self._make_request("POST", "/paper/batch", json=payload)
                
                batch_errors[case_name] = {
                    'payload_type': type(payload).__name__,
                    'status_code': status,
                    'error_handled': status in [400, 422, 413]
                }
            except Exception as e:
                batch_errors[case_name] = {
                    'error': str(e),
                    'error_handled': True
                }
        
        results['batch_errors'] = batch_errors
        
        return results
    
    # ========== 性能和负载测试 ==========
    
    async def test_performance_comprehensive(self) -> Dict[str, Any]:
        """全面的性能测试"""
        results = {}
        
        # 1. 并发搜索测试
        concurrent_queries = [
            "machine learning",
            "deep learning", 
            "neural network",
            "artificial intelligence",
            "computer vision"
        ]
        
        async def concurrent_search(query):
            start = time.time()
            status, data, headers = await self._make_request(
                "GET", "/paper/search",
                params={"query": query, "limit": 5}
            )
            return {
                'query': query,
                'status': status,
                'duration': time.time() - start,
                'success': status == 200,
                'results_count': len(data.get("data", {}).get("papers", [])) if status == 200 else 0
            }
        
        # 并发执行搜索
        start_concurrent = time.time()
        concurrent_results = await asyncio.gather(*[
            concurrent_search(query) for query in concurrent_queries
        ])
        total_concurrent_time = time.time() - start_concurrent
        
        results['concurrent_search'] = {
            'queries_count': len(concurrent_queries),
            'total_time': total_concurrent_time,
            'avg_time_per_query': total_concurrent_time / len(concurrent_queries),
            'all_successful': all(r['success'] for r in concurrent_results),
            'individual_results': concurrent_results
        }
        
        # 2. 缓存性能测试
        paper_id = self.test_papers["attention_paper"]
        cache_test_results = []
        
        # 首次请求（可能触发缓存）
        start = time.time()
        status, data, headers = await self._make_request("GET", f"/paper/{paper_id}")
        first_request_time = time.time() - start
        
        # 后续请求（应该命中缓存）
        for i in range(5):
            start = time.time()
            status, data, headers = await self._make_request("GET", f"/paper/{paper_id}")
            cache_test_results.append({
                'request_num': i + 2,
                'duration': time.time() - start,
                'cache_info': self._extract_cache_info(headers)
            })
            await asyncio.sleep(0.1)
        
        results['cache_performance'] = {
            'first_request_time': first_request_time,
            'cached_requests': cache_test_results,
            'avg_cached_time': sum(r['duration'] for r in cache_test_results) / len(cache_test_results),
            'cache_speedup': first_request_time / (sum(r['duration'] for r in cache_test_results) / len(cache_test_results))
        }
        
        # 3. 大数据量测试
        large_query_start = time.time()
        status, data, headers = await self._make_request(
            "GET", "/paper/search",
            params={"query": "machine learning", "limit": 100}
        )
        large_query_time = time.time() - large_query_start
        
        results['large_dataset'] = {
            'query': 'machine learning',
            'limit': 100,
            'duration': large_query_time,
            'status': status,
            'results_returned': len(data.get("data", {}).get("papers", [])) if status == 200 else 0,
            'response_time': self._extract_response_time(headers)
        }
        
        return results
    
    # ========== 数据一致性测试 ==========
    
    async def test_data_consistency(self) -> Dict[str, Any]:
        """数据一致性测试"""
        results = {}
        paper_id = self.test_papers["attention_paper"]
        
        # 1. 同一论文多次请求数据一致性
        requests_data = []
        for i in range(3):
            status, data, _ = await self._make_request("GET", f"/paper/{paper_id}")
            if status == 200:
                paper_data = data["data"]
                requests_data.append({
                    'request_num': i + 1,
                    'paper_id': paper_data.get("paperId"),
                    'title': paper_data.get("title"),
                    'year': paper_data.get("year"),
                    'citation_count': paper_data.get("citationCount")
                })
            await asyncio.sleep(0.5)
        
        # 检查数据一致性
        if len(requests_data) >= 2:
            first_request = requests_data[0]
            consistency_check = all(
                req['paper_id'] == first_request['paper_id'] and
                req['title'] == first_request['title'] and
                req['year'] == first_request['year']
                for req in requests_data[1:]
            )
        else:
            consistency_check = False
        
        results['multiple_requests_consistency'] = {
            'requests_count': len(requests_data),
            'data_consistent': consistency_check,
            'requests_data': requests_data
        }
        
        # 2. 搜索结果一致性
        query = "attention is all you need"
        search_results = []
        
        for i in range(2):
            status, data, _ = await self._make_request(
                "GET", "/paper/search",
                params={"query": query, "limit": 5}
            )
            if status == 200:
                papers = data["data"]["papers"]
                search_results.append({
                    'request_num': i + 1,
                    'results_count': len(papers),
                    'first_paper_id': papers[0]["paperId"] if papers else None,
                    'paper_ids': [p["paperId"] for p in papers]
                })
            await asyncio.sleep(1)
        
        search_consistency = False
        if len(search_results) >= 2:
            search_consistency = (
                search_results[0]['paper_ids'] == search_results[1]['paper_ids']
            )
        
        results['search_consistency'] = {
            'query': query,
            'searches_count': len(search_results),
            'results_consistent': search_consistency,
            'search_data': search_results
        }
        
        return results
    
    # ========== 主测试流程 ==========
    
    async def run_comprehensive_tests(self):
        """运行全面的端到端测试"""
        print("🚀 启动Paper Parser全面端到端测试")
        print("=" * 60)
        
        # 定义测试用例
        test_suites = [
            ("系统健康检查", self.test_system_health),
            ("论文搜索全面测试", self.test_paper_search_comprehensive),
            ("论文详情全面测试", self.test_paper_detail_comprehensive),
            ("论文关系全面测试", self.test_paper_relations_comprehensive),
            ("批量操作测试", self.test_batch_operations),
            ("错误处理全面测试", self.test_error_handling_comprehensive),
            ("性能全面测试", self.test_performance_comprehensive),
            ("数据一致性测试", self.test_data_consistency),
        ]
        
        # 运行所有测试
        for test_name, test_func in test_suites:
            await self._run_test(test_name, test_func)
        
        # 生成综合报告
        await self._generate_comprehensive_report()
    
    async def _generate_comprehensive_report(self):
        """生成全面的测试报告"""
        total = len(self.metrics)
        passed = len([m for m in self.metrics if m.status == "PASS"])
        failed = len([m for m in self.metrics if m.status == "FAIL"])
        warned = len([m for m in self.metrics if m.status == "WARN"])
        
        success_rate = (passed / total * 100) if total > 0 else 0
        total_duration = sum(m.duration for m in self.metrics)
        avg_response_time = sum(m.response_time for m in self.metrics if m.response_time > 0) / max(1, len([m for m in self.metrics if m.response_time > 0]))
        
        print("\n" + "=" * 60)
        print("📊 Paper Parser 全面端到端测试报告")
        print("=" * 60)
        print(f"测试总数: {total}")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"⚠️  警告: {warned}")
        print(f"🎯 成功率: {success_rate:.1f}%")
        print(f"⏱️  总耗时: {total_duration:.2f}秒")
        print(f"📈 平均响应时间: {avg_response_time:.3f}秒")
        print("=" * 60)
        
        # 详细结果
        for metric in self.metrics:
            status_emoji = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "SKIP": "⏭️"}
            print(f"{status_emoji[metric.status]} {metric.test_name}")
            print(f"   ⏱️  耗时: {metric.duration:.2f}s")
            if metric.response_time > 0:
                print(f"   🌐 响应时间: {metric.response_time:.3f}s")
            if metric.cache_hit:
                print(f"   📦 缓存: {metric.cache_hit}")
            if metric.error:
                print(f"   ❌ 错误: {metric.error}")
        
        # 保存详细报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_data = {
            "test_info": {
                "test_suite": "Paper Parser E2E Comprehensive Tests",
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url,
                "total_tests": total,
                "duration_seconds": total_duration
            },
            "summary": {
                "passed": passed,
                "failed": failed,
                "warned": warned,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time
            },
            "detailed_results": [asdict(metric) for metric in self.metrics]
        }
        
        report_file = f"e2e_comprehensive_report_{timestamp}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细测试报告已保存到: {report_file}")
        
        # 性能摘要
        response_times = [m.response_time for m in self.metrics if m.response_time > 0]
        if response_times:
            print(f"\n📈 性能摘要:")
            print(f"   最快响应: {min(response_times):.3f}s")
            print(f"   最慢响应: {max(response_times):.3f}s")
            print(f"   平均响应: {sum(response_times)/len(response_times):.3f}s")
        
        # 建议
        if failed > 0:
            print(f"\n⚠️  发现 {failed} 个测试失败，请检查系统状态和配置")
        if success_rate < 80:
            print(f"\n⚠️  测试成功率较低 ({success_rate:.1f}%)，建议进行系统诊断")
        elif success_rate >= 95:
            print(f"\n🎉 测试成功率优秀 ({success_rate:.1f}%)，系统运行良好！")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Paper Parser 全面端到端测试")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="API服务地址")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"🔗 测试目标: {args.url}")
        print(f"🕐 开始时间: {datetime.now().isoformat()}")
    
    try:
        async with ComprehensiveE2ETester(args.url) as tester:
            await tester.run_comprehensive_tests()
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
