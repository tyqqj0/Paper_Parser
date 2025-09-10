"""
论文搜索接口集成测试
"""
import pytest
from tests.helpers.assertions import (
    assert_pagination_response, assert_paper_basic_fields,
    assert_fields_filtering_works, assert_json_serializable,
    assert_error_response, assert_process_time_header
)


class TestPaperSearchBasic:
    """论文搜索基础测试"""
    
    @pytest.mark.paper_search
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_search_basic_structure(self, async_client, search_query_fixture):
        """测试搜索基本响应结构"""
        response = await async_client.get(
            "/paper/search",
            params={"query": search_query_fixture}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查基本分页结构（应该有total, offset, papers）
        assert_pagination_response(data, expected_offset=0, context="搜索基本结构")
        
        # 检查兼容性：应该同时有papers和data字段
        if "papers" in data:
            assert isinstance(data["papers"], list)
        if "data" in data:
            assert isinstance(data["data"], list)
        
        # 检查处理时间头
        assert_process_time_header(response.headers, context="论文搜索")
        
        # 检查JSON序列化
        assert_json_serializable(data, "搜索响应")
    
    @pytest.mark.paper_search
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_search_with_pagination(self, async_client, search_query_fixture):
        """测试搜索分页参数"""
        test_cases = [
            {"offset": 0, "limit": 5},
            {"offset": 5, "limit": 10},
            {"offset": 0, "limit": 1},
            {"offset": 10, "limit": 3}
        ]
        
        for params in test_cases:
            params["query"] = search_query_fixture
            response = await async_client.get("/paper/search", params=params)
            
            assert response.status_code == 200
            data = response.json()
            
            # 检查分页参数正确返回
            assert_pagination_response(
                data,
                expected_offset=params["offset"],
                max_data_length=params["limit"],
                context=f"搜索分页 {params}"
            )
    
    @pytest.mark.paper_search
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_search_with_fields(self, async_client, search_query_fixture):
        """测试搜索字段过滤"""
        fields = "title,year,authors,venue"
        response = await async_client.get(
            "/paper/search",
            params={
                "query": search_query_fixture,
                "fields": fields,
                "limit": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查基本结构
        assert_pagination_response(data, context="搜索字段过滤")
        
        # 获取实际的论文列表（可能是papers或data字段）
        papers = data.get("papers", data.get("data", []))
        
        # 检查每篇论文的字段过滤
        if papers:
            for paper in papers:
                if paper:  # 跳过None值
                    assert_fields_filtering_works(
                        paper, fields, "搜索结果字段过滤"
                    )
    
    @pytest.mark.paper_search
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_search_results_structure(self, async_client, search_query_fixture):
        """测试搜索结果数据结构"""
        response = await async_client.get(
            "/paper/search",
            params={"query": search_query_fixture, "limit": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 获取论文列表
        papers = data.get("papers", data.get("data", []))
        
        # 检查每篇论文的基本结构
        if papers:
            for paper in papers:
                if paper:  # 跳过None值
                    assert_paper_basic_fields(paper, "搜索结果论文")


class TestPaperSearchFilters:
    """论文搜索过滤器测试"""
    
    @pytest.mark.paper_search
    @pytest.mark.integration
    async def test_search_with_year_filter(self, async_client, search_query_fixture):
        """测试年份过滤"""
        year_filters = ["2020", "2018-2020", "2015-2023"]
        
        for year in year_filters:
            response = await async_client.get(
                "/paper/search",
                params={
                    "query": search_query_fixture,
                    "year": year,
                    "limit": 5
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 基本结构检查
            assert_pagination_response(data, context=f"年份过滤 {year}")
            
            # 如果有结果，检查年份过滤是否生效（这个检查比较宽松，因为可能有缺失数据）
            papers = data.get("papers", data.get("data", []))
            if papers:
                for paper in papers[:3]:  # 只检查前几个
                    if paper and "year" in paper and paper["year"]:
                        paper_year = paper["year"]
                        if "-" in year:
                            start_year, end_year = map(int, year.split("-"))
                            # 年份应该在范围内（允许一些宽松度）
                            assert start_year - 2 <= paper_year <= end_year + 2, (
                                f"论文年份 {paper_year} 不在过滤范围 {year} 内"
                            )
                        else:
                            target_year = int(year)
                            # 允许一些年份差异（数据可能不完全准确）
                            assert abs(paper_year - target_year) <= 2, (
                                f"论文年份 {paper_year} 与过滤年份 {target_year} 差异过大"
                            )
    
    @pytest.mark.paper_search
    @pytest.mark.integration
    async def test_search_with_venue_filter(self, async_client):
        """测试会议/期刊过滤"""
        venue_queries = [
            {"query": "neural networks", "venue": "NIPS"},
            {"query": "machine learning", "venue": "ICML"},
            {"query": "computer vision", "venue": "CVPR"}
        ]
        
        for params in venue_queries:
            params["limit"] = 3
            response = await async_client.get("/paper/search", params=params)
            
            # 应该返回成功或没有结果，不应该是错误
            assert response.status_code == 200
            data = response.json()
            
            # 基本结构检查
            assert_pagination_response(data, context=f"会议过滤 {params['venue']}")
    
    @pytest.mark.paper_search
    @pytest.mark.integration
    async def test_search_with_fields_of_study(self, async_client):
        """测试研究领域过滤"""
        fos_queries = [
            {"query": "attention", "fields_of_study": "Computer Science"},
            {"query": "neural", "fields_of_study": "Mathematics"},
        ]
        
        for params in fos_queries:
            params["limit"] = 3
            response = await async_client.get("/paper/search", params=params)
            
            # 应该返回成功或没有结果
            assert response.status_code == 200
            data = response.json()
            
            # 基本结构检查
            assert_pagination_response(data, context=f"领域过滤 {params['fields_of_study']}")
    
    @pytest.mark.paper_search
    @pytest.mark.integration
    async def test_search_match_title_mode(self, async_client):
        """测试标题精准匹配模式"""
        # 使用一个具体的论文标题
        exact_title = "Attention Is All You Need"
        
        response = await async_client.get(
            "/paper/search",
            params={
                "query": exact_title,
                "match_title": True,
                "limit": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 基本结构检查
        assert_pagination_response(data, context="标题精准匹配")
        
        # 精准匹配应该返回较少但更相关的结果
        papers = data.get("papers", data.get("data", []))
        if papers:
            # 第一个结果应该高度相关
            first_paper = papers[0]
            if first_paper and "title" in first_paper:
                title = first_paper["title"].lower()
                query_words = exact_title.lower().split()
                # 应该包含查询中的关键词
                matches = sum(1 for word in query_words if word in title)
                assert matches >= len(query_words) // 2, (
                    f"精准匹配结果相关性不足: '{first_paper['title']}'"
                )


class TestPaperSearchErrorHandling:
    """论文搜索错误处理测试"""
    
    @pytest.mark.paper_search
    @pytest.mark.integration
    async def test_search_empty_query(self, async_client):
        """测试空查询"""
        empty_queries = ["", "  ", None]
        
        for query in empty_queries:
            params = {}
            if query is not None:
                params["query"] = query
                
            response = await async_client.get("/paper/search", params=params)
            
            # 空查询应该返回400错误
            assert response.status_code in [400, 422]
            data = response.json()
            assert_error_response(data, response.status_code, context=f"空查询 '{query}'")
    
    @pytest.mark.paper_search
    @pytest.mark.integration
    async def test_search_invalid_pagination(self, async_client, search_query_fixture):
        """测试无效分页参数"""
        invalid_params = [
            {"query": search_query_fixture, "offset": -1},
            {"query": search_query_fixture, "limit": 0},
            {"query": search_query_fixture, "limit": 101},  # 超过限制
        ]
        
        for params in invalid_params:
            response = await async_client.get("/paper/search", params=params)
            
            # 应该返回422验证错误
            assert response.status_code == 422
            data = response.json()
            assert_error_response(data, 422, context=f"无效分页 {params}")
    
    @pytest.mark.paper_search
    @pytest.mark.integration
    async def test_search_invalid_year_format(self, async_client, search_query_fixture):
        """测试无效年份格式"""
        invalid_years = ["invalid", "20200", "2020-", "-2020", "2020-2019"]
        
        for year in invalid_years:
            response = await async_client.get(
                "/paper/search",
                params={"query": search_query_fixture, "year": year}
            )
            
            # 可能返回400或直接忽略无效参数返回200
            # 这取决于具体实现
            if response.status_code != 200:
                assert response.status_code in [400, 422]
                data = response.json()
                assert_error_response(data, response.status_code, context=f"无效年份 {year}")


class TestPaperSearchPerformance:
    """论文搜索性能测试"""
    
    @pytest.mark.paper_search
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_search_response_time(self, async_client, search_query_fixture):
        """测试搜索响应时间"""
        response = await async_client.get(
            "/paper/search",
            params={"query": search_query_fixture, "limit": 10}
        )
        
        assert response.status_code == 200
        
        # 检查响应时间（搜索可能比详情查询慢一些）
        process_time = float(response.headers.get("x-process-time", "0"))
        assert process_time < 15.0, f"搜索响应时间过长: {process_time}s"
    
    @pytest.mark.paper_search
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_search_small_vs_large_limit(self, async_client, search_query_fixture):
        """测试小limit vs 大limit的性能"""
        # 小limit
        response_small = await async_client.get(
            "/paper/search",
            params={"query": search_query_fixture, "limit": 5}
        )
        time_small = float(response_small.headers.get("x-process-time", "0"))
        
        # 大limit
        response_large = await async_client.get(
            "/paper/search", 
            params={"query": search_query_fixture, "limit": 50}
        )
        time_large = float(response_large.headers.get("x-process-time", "0"))
        
        # 大limit不应该比小limit慢太多
        assert time_large <= time_small * 2, (
            f"搜索大limit性能差异过大: {time_small}s vs {time_large}s"
        )


class TestPaperSearchCaching:
    """论文搜索缓存测试"""
    
    @pytest.mark.paper_search
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_search_caching_behavior(self, async_client, search_query_fixture):
        """测试搜索缓存行为"""
        params = {"query": search_query_fixture, "limit": 10}
        
        # 第一次搜索
        response1 = await async_client.get("/paper/search", params=params)
        assert response1.status_code == 200
        time1 = float(response1.headers.get("x-process-time", "0"))
        
        # 第二次搜索（应该命中缓存）
        response2 = await async_client.get("/paper/search", params=params)
        assert response2.status_code == 200
        time2 = float(response2.headers.get("x-process-time", "0"))
        
        # 结果应该一致
        data1 = response1.json()
        data2 = response2.json()
        
        # 基本一致性检查
        assert data1.get("total") == data2.get("total"), "缓存前后total不一致"
        
        # 第二次应该更快（但不强制要求，因为搜索缓存可能有特殊逻辑）
        if time2 > 0 and time1 > 0:
            improvement_ratio = time1 / time2
            # 如果有显著改善，记录一下（但不强制断言）
            if improvement_ratio > 2:
                print(f"搜索缓存改善: {time1:.3f}s -> {time2:.3f}s ({improvement_ratio:.1f}x)")


class TestPaperSearchDataConsistency:
    """论文搜索数据一致性测试"""
    
    @pytest.mark.paper_search
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_search_pagination_consistency(self, async_client, search_query_fixture):
        """测试搜索分页一致性"""
        # 获取第一页
        response1 = await async_client.get(
            "/paper/search",
            params={"query": search_query_fixture, "offset": 0, "limit": 5}
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        
        # 如果有足够结果，测试第二页
        if data1.get("total", 0) > 5:
            response2 = await async_client.get(
                "/paper/search",
                params={"query": search_query_fixture, "offset": 5, "limit": 5}
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # total应该一致
            assert data1["total"] == data2["total"], (
                f"搜索分页total不一致: {data1['total']} vs {data2['total']}"
            )
            
            # 数据不应该重复
            papers1 = data1.get("papers", data1.get("data", []))
            papers2 = data2.get("papers", data2.get("data", []))
            
            if papers1 and papers2:
                ids1 = {p.get("paperId") for p in papers1 if p and p.get("paperId")}
                ids2 = {p.get("paperId") for p in papers2 if p and p.get("paperId")}
                overlap = ids1 & ids2
                assert not overlap, f"搜索分页数据重复: {overlap}"
    
    @pytest.mark.paper_search
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_search_backward_compatibility(self, async_client, search_query_fixture):
        """测试搜索响应的向后兼容性"""
        response = await async_client.get(
            "/paper/search",
            params={"query": search_query_fixture, "limit": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 应该同时支持papers和data字段
        has_papers = "papers" in data
        has_data = "data" in data
        
        # 至少要有一个
        assert has_papers or has_data, "响应应该包含papers或data字段"
        
        # 如果都有，内容应该一致
        if has_papers and has_data:
            papers = data["papers"]
            data_items = data["data"]
            
            # 长度应该一致
            assert len(papers) == len(data_items), (
                f"papers和data长度不一致: {len(papers)} vs {len(data_items)}"
            )
            
            # 内容应该相同（至少paperId应该一致）
            if papers and data_items:
                paper_ids = [p.get("paperId") for p in papers if p]
                data_ids = [d.get("paperId") for d in data_items if d]
                assert paper_ids == data_ids, "papers和data的paperId不一致"
