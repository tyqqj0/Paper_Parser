"""
代理端点透传测试
"""
import pytest
from tests.helpers.assertions import (
    assert_json_serializable, assert_error_response,
    assert_process_time_header
)


class TestProxyPaperEndpoints:
    """代理论文端点测试"""
    
    @pytest.mark.proxy
    @pytest.mark.integration
    async def test_proxy_paper_autocomplete(self, async_client):
        """测试代理论文自动补全"""
        query = "attention"
        response = await async_client.get(
            "/proxy/paper/autocomplete",
            params={"query": query}
        )
        
        # 应该返回200或与S2相同的错误状态
        assert response.status_code in [200, 400, 404, 429, 500, 503]
        
        if response.status_code == 200:
            data = response.json()
            
            # 应该是列表或S2格式的响应
            assert isinstance(data, (list, dict)), "自动补全响应应该是列表或字典"
            
            # 检查JSON序列化
            assert_json_serializable(data, "代理自动补全响应")
        else:
            # 错误响应应该有合理格式
            data = response.json()
            # S2的错误格式可能不同，这里做宽松检查
            assert isinstance(data, dict), "错误响应应该是字典"
        
        # 检查处理时间头
        assert_process_time_header(response.headers, context="代理自动补全", max_time=10.0)
    
    @pytest.mark.proxy
    @pytest.mark.integration
    async def test_proxy_paper_search(self, async_client, search_query_fixture):
        """测试代理论文搜索"""
        response = await async_client.get(
            "/proxy/paper/search",
            params={"query": search_query_fixture, "limit": 5}
        )
        
        # 应该返回200或与S2相同的错误状态
        assert response.status_code in [200, 400, 404, 429, 500, 503]
        
        if response.status_code == 200:
            data = response.json()
            
            # S2搜索响应格式检查
            assert isinstance(data, dict), "搜索响应应该是字典"
            
            # S2格式通常包含total, offset, data
            if "data" in data:
                assert isinstance(data["data"], list), "data字段应该是列表"
            
            # 检查JSON序列化
            assert_json_serializable(data, "代理搜索响应")
        
        # 检查处理时间头
        assert_process_time_header(response.headers, context="代理搜索", max_time=15.0)
    
    @pytest.mark.proxy
    @pytest.mark.integration
    async def test_proxy_paper_search_match(self, async_client):
        """测试代理论文精准搜索"""
        query = "Attention Is All You Need"
        response = await async_client.get(
            "/proxy/paper/search/match",
            params={"query": query}
        )
        
        # 应该返回200或与S2相同的错误状态
        assert response.status_code in [200, 400, 404, 429, 500, 503]
        
        if response.status_code == 200:
            data = response.json()
            
            # 精准搜索可能返回单个结果或列表
            assert isinstance(data, (dict, list)), "精准搜索响应应该是字典或列表"
            
            # 检查JSON序列化
            assert_json_serializable(data, "代理精准搜索响应")
    
    @pytest.mark.proxy
    @pytest.mark.integration
    async def test_proxy_paper_search_bulk(self, async_client, batch_paper_ids_fixture):
        """测试代理论文批量搜索"""
        payload = {"ids": batch_paper_ids_fixture[:3]}
        
        response = await async_client.post(
            "/proxy/paper/search/bulk",
            json=payload
        )
        
        # 应该返回200或与S2相同的错误状态
        assert response.status_code in [200, 400, 404, 429, 500, 503]
        
        if response.status_code == 200:
            data = response.json()
            
            # 批量搜索响应格式检查
            assert isinstance(data, (list, dict)), "批量搜索响应应该是列表或字典"
            
            # 检查JSON序列化
            assert_json_serializable(data, "代理批量搜索响应")


class TestProxyAuthorEndpoints:
    """代理作者端点测试"""
    
    @pytest.mark.proxy
    @pytest.mark.integration
    async def test_proxy_author_details(self, async_client):
        """测试代理作者详情"""
        # 使用一个已知的作者ID（Yoshua Bengio）
        author_id = "1699545"  # 示例作者ID
        
        response = await async_client.get(f"/proxy/author/{author_id}")
        
        # 应该返回200或与S2相同的错误状态
        assert response.status_code in [200, 400, 404, 429, 500, 503]
        
        if response.status_code == 200:
            data = response.json()
            
            # 作者响应应该是字典
            assert isinstance(data, dict), "作者详情响应应该是字典"
            
            # 基本字段检查
            if "authorId" in data:
                assert data["authorId"] == author_id
            
            # 检查JSON序列化
            assert_json_serializable(data, "代理作者详情响应")
        
        # 检查处理时间头
        assert_process_time_header(response.headers, context="代理作者详情", max_time=10.0)
    
    @pytest.mark.proxy
    @pytest.mark.integration
    async def test_proxy_author_papers(self, async_client):
        """测试代理作者论文列表"""
        author_id = "1699545"  # 示例作者ID
        
        response = await async_client.get(
            f"/proxy/author/{author_id}/papers",
            params={"limit": 5}
        )
        
        # 应该返回200或与S2相同的错误状态
        assert response.status_code in [200, 400, 404, 429, 500, 503]
        
        if response.status_code == 200:
            data = response.json()
            
            # 作者论文响应格式检查
            assert isinstance(data, dict), "作者论文响应应该是字典"
            
            # S2格式通常包含data字段
            if "data" in data:
                assert isinstance(data["data"], list), "data字段应该是列表"
            
            # 检查JSON序列化
            assert_json_serializable(data, "代理作者论文响应")


class TestProxyErrorHandling:
    """代理端点错误处理测试"""
    
    @pytest.mark.proxy
    @pytest.mark.integration
    async def test_proxy_invalid_endpoints(self, async_client):
        """测试代理无效端点"""
        invalid_endpoints = [
            "/proxy/invalid/endpoint",
            "/proxy/paper/invalid",
            "/proxy/author/invalid/action"
        ]
        
        for endpoint in invalid_endpoints:
            response = await async_client.get(endpoint)
            
            # 应该返回404或405
            assert response.status_code in [404, 405], f"无效端点 {endpoint} 应该返回404或405"
    
    @pytest.mark.proxy
    @pytest.mark.integration
    async def test_proxy_missing_parameters(self, async_client):
        """测试代理缺少必需参数"""
        # 自动补全缺少query参数
        response = await async_client.get("/proxy/paper/autocomplete")
        
        # 应该返回400或422
        assert response.status_code in [400, 422], "缺少必需参数应该返回400或422"
        
        if response.status_code in [400, 422]:
            data = response.json()
            # 错误响应应该是字典
            assert isinstance(data, dict), "错误响应应该是字典"
    
    @pytest.mark.proxy
    @pytest.mark.integration
    async def test_proxy_invalid_parameters(self, async_client):
        """测试代理无效参数"""
        # 使用无效的limit值
        response = await async_client.get(
            "/proxy/paper/search",
            params={"query": "test", "limit": -1}
        )
        
        # 应该返回400或422
        assert response.status_code in [400, 422], "无效参数应该返回400或422"


class TestProxyPerformance:
    """代理端点性能测试"""
    
    @pytest.mark.proxy
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_proxy_response_time(self, async_client, search_query_fixture):
        """测试代理端点响应时间"""
        endpoints_and_params = [
            ("/proxy/paper/autocomplete", {"query": "attention"}),
            ("/proxy/paper/search", {"query": search_query_fixture, "limit": 5}),
        ]
        
        for endpoint, params in endpoints_and_params:
            response = await async_client.get(endpoint, params=params)
            
            if response.status_code == 200:
                # 检查响应时间（代理可能比直接API稍慢）
                process_time = float(response.headers.get("x-process-time", "0"))
                assert process_time < 20.0, f"代理端点 {endpoint} 响应时间过长: {process_time}s"
    
    @pytest.mark.proxy
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_proxy_vs_core_performance(self, async_client, search_query_fixture):
        """测试代理端点vs核心端点性能对比"""
        # 代理搜索
        proxy_response = await async_client.get(
            "/proxy/paper/search",
            params={"query": search_query_fixture, "limit": 5}
        )
        
        # 核心搜索
        core_response = await async_client.get(
            "/paper/search",
            params={"query": search_query_fixture, "limit": 5}
        )
        
        if proxy_response.status_code == 200 and core_response.status_code == 200:
            proxy_time = float(proxy_response.headers.get("x-process-time", "0"))
            core_time = float(core_response.headers.get("x-process-time", "0"))
            
            print(f"性能对比 - 代理: {proxy_time:.3f}s, 核心: {core_time:.3f}s")
            
            # 代理不应该比核心慢太多（考虑到代理是直通，核心有缓存）
            if proxy_time > 0 and core_time > 0:
                ratio = proxy_time / core_time
                # 这个比较比较宽松，因为代理和核心的实现不同
                assert ratio < 5.0, f"代理性能相对核心过差: {ratio:.1f}x"


class TestProxyDataFormat:
    """代理端点数据格式测试"""
    
    @pytest.mark.proxy
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_proxy_response_structure(self, async_client, search_query_fixture):
        """测试代理响应结构"""
        response = await async_client.get(
            "/proxy/paper/search",
            params={"query": search_query_fixture, "limit": 3}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # 代理应该返回S2原始格式
            assert isinstance(data, dict), "代理搜索响应应该是字典"
            
            # 不应该有我们核心API特有的包装
            # （例如不应该同时有papers和data字段，应该只有S2的格式）
            
            # 检查是否是纯S2格式
            if "data" in data:
                papers = data["data"]
                assert isinstance(papers, list), "S2的data字段应该是列表"
                
                # 检查论文结构
                for paper in papers[:2]:  # 只检查前2个
                    if paper:
                        assert isinstance(paper, dict), "论文应该是字典"
                        # S2论文通常有paperId
                        if "paperId" in paper:
                            assert isinstance(paper["paperId"], str)
    
    @pytest.mark.proxy
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_proxy_error_format(self, async_client):
        """测试代理错误响应格式"""
        # 故意发送无效请求
        response = await async_client.get("/proxy/paper/autocomplete")  # 缺少query
        
        if response.status_code in [400, 422]:
            data = response.json()
            
            # 代理错误应该保持S2的格式，或者转换为统一格式
            assert isinstance(data, dict), "代理错误响应应该是字典"
            
            # 可能有error或detail字段
            has_error_field = any(
                field in data for field in ["error", "detail", "message"]
            )
            assert has_error_field, "错误响应应该包含错误信息字段"


class TestProxyReliability:
    """代理端点可靠性测试"""
    
    @pytest.mark.proxy
    @pytest.mark.integration
    @pytest.mark.flaky
    async def test_proxy_handles_upstream_errors(self, async_client):
        """测试代理处理上游错误"""
        # 这个测试可能不稳定，因为依赖外部服务
        
        # 尝试多个端点，看是否能优雅处理各种情况
        test_cases = [
            ("/proxy/paper/autocomplete", {"query": "test"}),
            ("/proxy/paper/search", {"query": "test", "limit": 1}),
        ]
        
        for endpoint, params in test_cases:
            response = await async_client.get(endpoint, params=params)
            
            # 不管上游返回什么，我们的代理都应该返回合理的HTTP状态码
            assert 200 <= response.status_code < 600, f"代理端点 {endpoint} 状态码异常: {response.status_code}"
            
            # 响应应该是有效JSON
            try:
                data = response.json()
                assert_json_serializable(data, f"代理端点 {endpoint} 响应")
            except Exception as e:
                pytest.fail(f"代理端点 {endpoint} 返回无效JSON: {e}")
    
    @pytest.mark.proxy
    @pytest.mark.integration
    async def test_proxy_timeout_handling(self, async_client):
        """测试代理超时处理"""
        # 使用可能导致超时的复杂查询
        complex_query = "machine learning deep learning neural networks artificial intelligence" * 10
        
        response = await async_client.get(
            "/proxy/paper/search",
            params={"query": complex_query, "limit": 100}
        )
        
        # 不管是否超时，都应该返回合理的响应
        assert response.status_code in [200, 400, 408, 429, 500, 503, 504], (
            f"复杂查询返回异常状态码: {response.status_code}"
        )
        
        if response.status_code != 200:
            # 错误响应应该有合理格式
            try:
                data = response.json()
                assert isinstance(data, dict), "错误响应应该是字典"
            except:
                # 如果不是JSON，至少响应应该不为空
                assert len(response.content) > 0, "错误响应不应该为空"
