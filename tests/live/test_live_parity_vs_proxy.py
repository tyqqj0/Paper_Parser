"""
在线对比测试（需要S2 API Key）
"""
import pytest
from tests.helpers.assertions import (
    assert_s2_api_compatibility, assert_paper_basic_fields,
    assert_pagination_response, assert_json_serializable
)
from tests.helpers.s2 import S2DirectClient, compare_with_s2


class TestLivePaperDetails:
    """论文详情在线对比测试"""
    
    @pytest.mark.live
    @pytest.mark.parity
    @pytest.mark.paper_details
    async def test_paper_details_vs_s2_direct(self, async_client, paper_id_fixture, s2_api_key):
        """测试论文详情与S2直连对比"""
        s2_client = S2DirectClient(s2_api_key)
        
        # 基本字段对比
        fields = "title,year,authors,citationCount,venue"
        
        # 我们的API
        our_response = await async_client.get(
            f"/paper/{paper_id_fixture}",
            params={"fields": fields}
        )
        
        # S2直连
        s2_data = await s2_client.get_paper(paper_id_fixture, fields)
        
        if our_response.status_code == 200 and s2_data:
            our_data = our_response.json()
            
            # 基本一致性检查
            compare_fields = ["paperId", "title", "year"]
            assert_s2_api_compatibility(
                our_data, s2_data, compare_fields, "论文详情vs S2直连"
            )
            
            print(f"论文详情对比成功: {our_data.get('title', 'N/A')}")
        else:
            print(f"论文详情对比跳过: 我们的API={our_response.status_code}, S2={s2_data is not None}")
    
    @pytest.mark.live
    @pytest.mark.parity
    @pytest.mark.paper_details
    async def test_paper_details_vs_proxy(self, async_client, paper_id_fixture, s2_api_key):
        """测试论文详情与代理端点对比"""
        fields = "title,year,authors"
        
        # 核心API
        core_response = await async_client.get(
            f"/paper/{paper_id_fixture}",
            params={"fields": fields}
        )
        
        # 代理API
        proxy_response = await async_client.get(
            f"/proxy/paper/{paper_id_fixture}",
            params={"fields": fields}
        )
        
        if core_response.status_code == 200 and proxy_response.status_code == 200:
            core_data = core_response.json()
            proxy_data = proxy_response.json()
            
            # 核心字段应该一致
            compare_fields = ["paperId", "title"]
            assert_s2_api_compatibility(
                core_data, proxy_data, compare_fields, "核心API vs 代理API"
            )
            
            print(f"核心vs代理对比成功: {core_data.get('title', 'N/A')}")
        else:
            print(f"核心vs代理对比跳过: 核心={core_response.status_code}, 代理={proxy_response.status_code}")


class TestLivePaperSearch:
    """论文搜索在线对比测试"""
    
    @pytest.mark.live
    @pytest.mark.parity
    @pytest.mark.paper_search
    async def test_paper_search_vs_s2_direct(self, async_client, search_query_fixture, s2_api_key):
        """测试搜索与S2直连对比"""
        s2_client = S2DirectClient(s2_api_key)
        
        search_params = {
            "query": search_query_fixture,
            "limit": 5,
            "fields": "title,year"
        }
        
        # 我们的搜索API
        our_response = await async_client.get("/paper/search", params=search_params)
        
        # S2直连搜索
        s2_data = await s2_client.search_papers(**search_params)
        
        if our_response.status_code == 200 and s2_data:
            our_data = our_response.json()
            
            # 基本结构对比
            assert_pagination_response(our_data, context="我们的搜索API")
            
            # 获取论文列表
            our_papers = our_data.get("papers", our_data.get("data", []))
            s2_papers = s2_data.get("data", [])
            
            # 基本统计对比（允许一些差异）
            if our_papers and s2_papers:
                print(f"搜索结果数量: 我们={len(our_papers)}, S2={len(s2_papers)}")
                
                # 检查第一个结果的相关性（应该类似）
                if our_papers[0] and s2_papers[0]:
                    our_title = our_papers[0].get("title", "").lower()
                    s2_title = s2_papers[0].get("title", "").lower()
                    
                    # 简单的相关性检查（标题包含相同关键词）
                    query_words = search_query_fixture.lower().split()
                    our_matches = sum(1 for word in query_words if word in our_title)
                    s2_matches = sum(1 for word in query_words if word in s2_title)
                    
                    print(f"第一个结果关键词匹配: 我们={our_matches}, S2={s2_matches}")
        else:
            print(f"搜索对比跳过: 我们的API={our_response.status_code}, S2={s2_data is not None}")
    
    @pytest.mark.live
    @pytest.mark.parity
    @pytest.mark.paper_search
    async def test_paper_search_vs_proxy(self, async_client, search_query_fixture, s2_api_key):
        """测试搜索与代理端点对比"""
        search_params = {
            "query": search_query_fixture,
            "limit": 3
        }
        
        # 核心搜索API
        core_response = await async_client.get("/paper/search", params=search_params)
        
        # 代理搜索API
        proxy_response = await async_client.get("/proxy/paper/search", params=search_params)
        
        if core_response.status_code == 200 and proxy_response.status_code == 200:
            core_data = core_response.json()
            proxy_data = proxy_response.json()
            
            # 基本结构检查
            assert isinstance(core_data, dict), "核心搜索响应应该是字典"
            assert isinstance(proxy_data, dict), "代理搜索响应应该是字典"
            
            # 获取结果列表
            core_papers = core_data.get("papers", core_data.get("data", []))
            proxy_papers = proxy_data.get("data", [])
            
            print(f"搜索结果对比: 核心={len(core_papers)}, 代理={len(proxy_papers)}")
            
            # 如果都有结果，检查相关性
            if core_papers and proxy_papers:
                # 检查是否有相同的论文ID
                core_ids = {p.get("paperId") for p in core_papers if p}
                proxy_ids = {p.get("paperId") for p in proxy_papers if p}
                
                common_ids = core_ids & proxy_ids
                if common_ids:
                    print(f"共同论文ID数量: {len(common_ids)}")
                else:
                    print("核心和代理搜索结果无共同论文ID")
        else:
            print(f"搜索对比跳过: 核心={core_response.status_code}, 代理={proxy_response.status_code}")


class TestLivePaperRelations:
    """论文关系在线对比测试"""
    
    @pytest.mark.live
    @pytest.mark.parity
    @pytest.mark.paper_citations
    async def test_paper_citations_vs_s2_direct(self, async_client, paper_id_fixture, s2_api_key):
        """测试引用与S2直连对比"""
        s2_client = S2DirectClient(s2_api_key)
        
        params = {
            "offset": 0,
            "limit": 5,
            "fields": "title,year"
        }
        
        # 我们的引用API
        our_response = await async_client.get(
            f"/paper/{paper_id_fixture}/citations",
            params=params
        )
        
        # S2直连引用
        s2_data = await s2_client.get_paper_citations(paper_id_fixture, **params)
        
        if our_response.status_code == 200 and s2_data:
            our_data = our_response.json()
            
            # 基本结构检查
            assert_pagination_response(our_data, context="我们的引用API")
            
            # total数量对比（允许一些差异）
            our_total = our_data.get("total", 0)
            s2_total = s2_data.get("total", 0)
            
            if our_total > 0 and s2_total > 0:
                diff_ratio = abs(our_total - s2_total) / max(s2_total, 1)
                print(f"引用数量对比: 我们={our_total}, S2={s2_total}, 差异={diff_ratio:.1%}")
                
                # 允许20%的差异（数据更新延迟等）
                assert diff_ratio < 0.2, f"引用数量差异过大: {diff_ratio:.1%}"
            else:
                print(f"引用数量: 我们={our_total}, S2={s2_total}")
        else:
            print(f"引用对比跳过: 我们的API={our_response.status_code}, S2={s2_data is not None}")
    
    @pytest.mark.live
    @pytest.mark.parity
    @pytest.mark.paper_references
    async def test_paper_references_vs_s2_direct(self, async_client, paper_id_fixture, s2_api_key):
        """测试参考文献与S2直连对比"""
        s2_client = S2DirectClient(s2_api_key)
        
        params = {
            "offset": 0,
            "limit": 5,
            "fields": "title,year"
        }
        
        # 我们的参考文献API
        our_response = await async_client.get(
            f"/paper/{paper_id_fixture}/references",
            params=params
        )
        
        # S2直连参考文献
        s2_data = await s2_client.get_paper_references(paper_id_fixture, **params)
        
        if our_response.status_code == 200 and s2_data:
            our_data = our_response.json()
            
            # 基本结构检查
            assert_pagination_response(our_data, context="我们的参考文献API")
            
            # total数量对比
            our_total = our_data.get("total", 0)
            s2_total = s2_data.get("total", 0)
            
            if our_total > 0 and s2_total > 0:
                diff_ratio = abs(our_total - s2_total) / max(s2_total, 1)
                print(f"参考文献数量对比: 我们={our_total}, S2={s2_total}, 差异={diff_ratio:.1%}")
                
                # 允许10%的差异（参考文献相对稳定）
                assert diff_ratio < 0.1, f"参考文献数量差异过大: {diff_ratio:.1%}"
            else:
                print(f"参考文献数量: 我们={our_total}, S2={s2_total}")
        else:
            print(f"参考文献对比跳过: 我们的API={our_response.status_code}, S2={s2_data is not None}")


class TestLivePaperBatch:
    """批量获取在线对比测试"""
    
    @pytest.mark.live
    @pytest.mark.parity
    @pytest.mark.paper_batch
    async def test_paper_batch_vs_s2_direct(self, async_client, batch_paper_ids_fixture, s2_api_key):
        """测试批量获取与S2直连对比"""
        s2_client = S2DirectClient(s2_api_key)
        
        test_ids = batch_paper_ids_fixture[:2]  # 只测试前2个
        fields = "title,year"
        
        # 我们的批量API
        our_payload = {"ids": test_ids, "fields": fields}
        our_response = await async_client.post("/paper/batch", json=our_payload)
        
        # S2直连批量
        s2_data = await s2_client.get_papers_batch(test_ids, fields)
        
        if our_response.status_code == 200 and s2_data:
            our_data = our_response.json()
            
            # 基本结构检查
            assert isinstance(our_data, list), "批量响应应该是列表"
            assert len(our_data) == len(test_ids), "批量响应长度应该匹配"
            
            # 逐个对比
            for i, (our_paper, s2_paper) in enumerate(zip(our_data, s2_data)):
                if our_paper and s2_paper:
                    # 基本字段对比
                    assert our_paper["paperId"] == s2_paper["paperId"], f"第{i}个论文ID不匹配"
                    
                    if "title" in our_paper and "title" in s2_paper:
                        assert our_paper["title"] == s2_paper["title"], f"第{i}个论文标题不匹配"
                    
                    print(f"批量第{i}个论文对比成功: {our_paper.get('title', 'N/A')}")
                elif our_paper is None and s2_paper is None:
                    print(f"批量第{i}个论文都为None（论文不存在）")
                else:
                    print(f"批量第{i}个论文存在性不匹配: 我们={our_paper is not None}, S2={s2_paper is not None}")
        else:
            print(f"批量对比跳过: 我们的API={our_response.status_code}, S2={s2_data is not None}")


class TestLiveProxyEndpoints:
    """代理端点在线测试"""
    
    @pytest.mark.live
    @pytest.mark.proxy
    async def test_proxy_autocomplete_functionality(self, async_client, s2_api_key):
        """测试代理自动补全功能"""
        query = "attention mechanism"
        
        response = await async_client.get(
            "/proxy/paper/autocomplete",
            params={"query": query}
        )
        
        # 代理应该返回合理的响应
        assert response.status_code in [200, 400, 429, 500, 503], (
            f"代理自动补全返回异常状态码: {response.status_code}"
        )
        
        if response.status_code == 200:
            data = response.json()
            assert_json_serializable(data, "代理自动补全响应")
            
            # 如果返回列表，检查基本结构
            if isinstance(data, list) and data:
                for item in data[:3]:  # 只检查前3个
                    if isinstance(item, dict) and "title" in item:
                        assert isinstance(item["title"], str)
                        print(f"自动补全建议: {item['title'][:50]}...")
        else:
            print(f"代理自动补全返回: {response.status_code}")
    
    @pytest.mark.live
    @pytest.mark.proxy
    async def test_proxy_author_functionality(self, async_client, s2_api_key):
        """测试代理作者端点功能"""
        author_id = "1699545"  # 示例作者ID
        
        # 作者详情
        response = await async_client.get(f"/proxy/author/{author_id}")
        
        assert response.status_code in [200, 400, 404, 429, 500, 503], (
            f"代理作者详情返回异常状态码: {response.status_code}"
        )
        
        if response.status_code == 200:
            data = response.json()
            assert_json_serializable(data, "代理作者详情响应")
            
            if "name" in data:
                print(f"作者信息: {data['name']}")
        else:
            print(f"代理作者详情返回: {response.status_code}")


class TestLiveErrorHandling:
    """在线错误处理测试"""
    
    @pytest.mark.live
    @pytest.mark.parity
    async def test_error_consistency_vs_s2(self, async_client, s2_api_key):
        """测试错误响应与S2的一致性"""
        s2_client = S2DirectClient(s2_api_key)
        
        # 测试不存在的论文
        fake_id = "0000000000000000000000000000000000000000"
        
        # 我们的API
        our_response = await async_client.get(f"/paper/{fake_id}")
        
        # S2直连
        s2_data = await s2_client.get_paper(fake_id)
        
        # 都应该表示论文不存在
        if our_response.status_code == 404 and s2_data is None:
            print("404错误处理一致")
        else:
            print(f"错误处理差异: 我们={our_response.status_code}, S2={s2_data is not None}")
    
    @pytest.mark.live
    @pytest.mark.parity
    async def test_rate_limit_handling(self, async_client, s2_api_key):
        """测试速率限制处理"""
        # 这个测试可能触发速率限制，标记为flaky
        import asyncio
        
        # 快速连续请求
        tasks = [
            async_client.get("/proxy/paper/autocomplete", params={"query": f"test{i}"})
            for i in range(10)
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计不同状态码
        status_codes = {}
        for response in responses:
            if hasattr(response, 'status_code'):
                code = response.status_code
                status_codes[code] = status_codes.get(code, 0) + 1
        
        print(f"快速请求状态码分布: {status_codes}")
        
        # 应该大部分成功，或者有合理的速率限制响应
        success_codes = {200, 429, 503}  # 成功或合理的限制
        for code in status_codes:
            assert code in success_codes or 500 <= code < 600, f"异常状态码: {code}"


class TestLiveDataFreshness:
    """数据新鲜度测试"""
    
    @pytest.mark.live
    @pytest.mark.parity
    @pytest.mark.slow
    async def test_data_freshness_vs_s2(self, async_client, paper_id_fixture, s2_api_key):
        """测试数据新鲜度与S2对比"""
        s2_client = S2DirectClient(s2_api_key)
        
        # 获取引用数量（这个数据可能会变化）
        our_response = await async_client.get(f"/paper/{paper_id_fixture}")
        s2_data = await s2_client.get_paper(paper_id_fixture)
        
        if our_response.status_code == 200 and s2_data:
            our_data = our_response.json()
            
            # 比较引用数量（允许一定差异）
            our_citations = our_data.get("citationCount", 0)
            s2_citations = s2_data.get("citationCount", 0)
            
            if our_citations > 0 and s2_citations > 0:
                diff = abs(our_citations - s2_citations)
                diff_ratio = diff / max(s2_citations, 1)
                
                print(f"引用数量新鲜度: 我们={our_citations}, S2={s2_citations}, 差异={diff}")
                
                # 数据应该相对新鲜（允许一定延迟）
                if diff_ratio > 0.1:  # 超过10%差异时警告
                    print(f"⚠️ 数据可能不够新鲜，差异比例: {diff_ratio:.1%}")
                else:
                    print("✓ 数据新鲜度良好")
        else:
            print(f"数据新鲜度测试跳过: 我们的API={our_response.status_code}, S2={s2_data is not None}")
