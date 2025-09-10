"""
延迟和缓存性能测试
"""
import pytest
import asyncio
from tests.helpers.assertions import (
    assert_latency_improves, assert_process_time_header,
    assert_paper_basic_fields
)


class TestColdVsWarmLatency:
    """冷启动vs热缓存延迟测试"""
    
    @pytest.mark.perf
    @pytest.mark.paper_details
    async def test_paper_details_cold_vs_warm(self, async_client, paper_id_fixture, clean_cache):
        """测试论文详情冷启动vs热缓存"""
        # 清理缓存
        await clean_cache()
        
        # 第一次访问（冷启动）
        response1 = await async_client.get(f"/paper/{paper_id_fixture}")
        assert response1.status_code == 200
        time1 = float(response1.headers.get("x-process-time", "0"))
        
        # 第二次访问（热缓存）
        response2 = await async_client.get(f"/paper/{paper_id_fixture}")
        assert response2.status_code == 200
        time2 = float(response2.headers.get("x-process-time", "0"))
        
        # 验证数据一致性
        data1 = response1.json()
        data2 = response2.json()
        assert data1["paperId"] == data2["paperId"]
        assert data1["title"] == data2["title"]
        
        # 验证性能改善
        if time1 > 0 and time2 > 0:
            assert_latency_improves(
                time1, time2,
                factor=2.0,  # 至少2倍改善
                absolute_ms=500.0,  # 缓存后应该<=500ms
                context="论文详情冷启动vs热缓存"
            )
            
            print(f"论文详情性能改善: {time1:.3f}s -> {time2:.3f}s ({time1/time2:.1f}x)")
    
    @pytest.mark.perf
    @pytest.mark.paper_citations
    async def test_paper_citations_cold_vs_warm(self, async_client, paper_id_fixture, clean_cache):
        """测试论文引用冷启动vs热缓存"""
        # 清理缓存
        await clean_cache()
        
        # 第一次访问（冷启动）
        response1 = await async_client.get(
            f"/paper/{paper_id_fixture}/citations",
            params={"limit": 10}
        )
        
        if response1.status_code != 200:
            pytest.skip("论文引用不可用，跳过性能测试")
            
        time1 = float(response1.headers.get("x-process-time", "0"))
        
        # 第二次访问（热缓存）
        response2 = await async_client.get(
            f"/paper/{paper_id_fixture}/citations",
            params={"limit": 10}
        )
        assert response2.status_code == 200
        time2 = float(response2.headers.get("x-process-time", "0"))
        
        # 验证数据一致性
        data1 = response1.json()
        data2 = response2.json()
        assert data1["total"] == data2["total"]
        assert data1["offset"] == data2["offset"]
        
        # 验证性能改善
        if time1 > 0 and time2 > 0:
            assert_latency_improves(
                time1, time2,
                factor=1.5,  # 引用查询改善可能较小
                absolute_ms=800.0,  # 缓存后应该<=800ms
                context="论文引用冷启动vs热缓存"
            )
            
            print(f"论文引用性能改善: {time1:.3f}s -> {time2:.3f}s ({time1/time2:.1f}x)")
    
    @pytest.mark.perf
    @pytest.mark.paper_search
    async def test_paper_search_cold_vs_warm(self, async_client, search_query_fixture):
        """测试论文搜索冷启动vs热缓存"""
        search_params = {"query": search_query_fixture, "limit": 10}
        
        # 第一次搜索（冷启动）
        response1 = await async_client.get("/paper/search", params=search_params)
        assert response1.status_code == 200
        time1 = float(response1.headers.get("x-process-time", "0"))
        
        # 第二次搜索（热缓存）
        response2 = await async_client.get("/paper/search", params=search_params)
        assert response2.status_code == 200
        time2 = float(response2.headers.get("x-process-time", "0"))
        
        # 验证数据一致性
        data1 = response1.json()
        data2 = response2.json()
        assert data1.get("total") == data2.get("total")
        
        # 搜索缓存改善可能不如详情查询明显
        if time1 > 0 and time2 > 0:
            improvement_ratio = time1 / time2
            print(f"搜索性能改善: {time1:.3f}s -> {time2:.3f}s ({improvement_ratio:.1f}x)")
            
            # 搜索缓存要求较宽松
            assert time2 <= time1 * 1.2, (
                f"搜索缓存后性能没有改善: {time1:.3f}s -> {time2:.3f}s"
            )


class TestAliasPathPerformance:
    """别名路径性能测试"""
    
    @pytest.mark.perf
    @pytest.mark.paper_details
    async def test_alias_path_performance(self, async_client, paper_id_fixture, doi_fixture, clean_cache):
        """测试别名路径性能"""
        # 清理缓存
        await clean_cache()
        
        # 通过S2 ID首次访问（建立缓存）
        response_s2 = await async_client.get(f"/paper/{paper_id_fixture}")
        assert response_s2.status_code == 200
        time_s2 = float(response_s2.headers.get("x-process-time", "0"))
        
        # 通过DOI别名访问（应该命中缓存）
        doi_id = f"DOI:{doi_fixture}"
        response_doi = await async_client.get(f"/paper/{doi_id}")
        
        if response_doi.status_code == 200:
            time_doi = float(response_doi.headers.get("x-process-time", "0"))
            
            # 验证是同一篇论文
            data_s2 = response_s2.json()
            data_doi = response_doi.json()
            
            if data_s2["paperId"] == data_doi["paperId"]:
                # 别名访问应该很快（命中缓存）
                if time_doi > 0:
                    assert time_doi <= 1.0, f"别名路径应该很快: {time_doi:.3f}s"
                    print(f"别名路径性能: S2 ID {time_s2:.3f}s, DOI {time_doi:.3f}s")
        else:
            print(f"DOI别名访问失败: {response_doi.status_code}")


class TestCacheWarmingPerformance:
    """缓存预热性能测试"""
    
    @pytest.mark.perf
    @pytest.mark.cache
    async def test_cache_warming_effect(self, async_client, paper_id_fixture, clean_cache):
        """测试缓存预热效果"""
        # 清理缓存
        await clean_cache()
        
        # 预热缓存
        warm_response = await async_client.post(f"/paper/{paper_id_fixture}/cache/warm")
        assert warm_response.status_code == 200
        warm_time = float(warm_response.headers.get("x-process-time", "0"))
        
        # 预热后访问
        response_after_warm = await async_client.get(f"/paper/{paper_id_fixture}")
        assert response_after_warm.status_code == 200
        time_after_warm = float(response_after_warm.headers.get("x-process-time", "0"))
        
        # 清理缓存，测试冷启动
        await clean_cache()
        
        # 冷启动访问
        response_cold = await async_client.get(f"/paper/{paper_id_fixture}")
        assert response_cold.status_code == 200
        time_cold = float(response_cold.headers.get("x-process-time", "0"))
        
        # 预热后访问应该比冷启动快
        if time_after_warm > 0 and time_cold > 0:
            improvement = time_cold / time_after_warm
            print(f"预热效果: 冷启动 {time_cold:.3f}s, 预热后 {time_after_warm:.3f}s ({improvement:.1f}x)")
            print(f"预热操作耗时: {warm_time:.3f}s")
            
            # 预热应该有效果
            assert time_after_warm <= time_cold * 1.1, (
                f"预热没有效果: {time_cold:.3f}s -> {time_after_warm:.3f}s"
            )


class TestConcurrentPerformance:
    """并发性能测试"""
    
    @pytest.mark.perf
    @pytest.mark.slow
    async def test_concurrent_same_paper_requests(self, async_client, paper_id_fixture, clean_cache):
        """测试同一论文的并发请求性能"""
        # 清理缓存
        await clean_cache()
        
        # 并发请求同一论文
        concurrent_count = 5
        tasks = [
            async_client.get(f"/paper/{paper_id_fixture}")
            for _ in range(concurrent_count)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # 所有请求都应该成功
        for i, response in enumerate(responses):
            assert response.status_code == 200, f"并发请求{i}失败"
        
        # 收集处理时间
        times = [
            float(response.headers.get("x-process-time", "0"))
            for response in responses
        ]
        
        valid_times = [t for t in times if t > 0]
        if valid_times:
            avg_time = sum(valid_times) / len(valid_times)
            max_time = max(valid_times)
            min_time = min(valid_times)
            
            print(f"并发性能: 平均 {avg_time:.3f}s, 范围 {min_time:.3f}s-{max_time:.3f}s")
            
            # 最慢的请求不应该比最快的慢太多（考虑到缓存效应）
            if min_time > 0:
                ratio = max_time / min_time
                assert ratio <= 10.0, f"并发请求时间差异过大: {ratio:.1f}x"
        
        # 验证数据一致性
        first_data = responses[0].json()
        for i, response in enumerate(responses[1:], 1):
            data = response.json()
            assert data["paperId"] == first_data["paperId"], f"并发请求{i}数据不一致"
    
    @pytest.mark.perf
    @pytest.mark.slow
    async def test_concurrent_different_papers_requests(self, async_client, batch_paper_ids_fixture):
        """测试不同论文的并发请求性能"""
        test_ids = batch_paper_ids_fixture[:3]
        
        # 并发请求不同论文
        tasks = [
            async_client.get(f"/paper/{paper_id}")
            for paper_id in test_ids
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计成功的请求
        successful_responses = [
            r for r in responses 
            if hasattr(r, 'status_code') and r.status_code == 200
        ]
        
        if len(successful_responses) >= 2:
            times = [
                float(r.headers.get("x-process-time", "0"))
                for r in successful_responses
            ]
            
            valid_times = [t for t in times if t > 0]
            if valid_times:
                avg_time = sum(valid_times) / len(valid_times)
                print(f"不同论文并发平均时间: {avg_time:.3f}s")
                
                # 平均时间应该在合理范围内
                assert avg_time < 10.0, f"并发请求平均时间过长: {avg_time:.3f}s"


class TestBatchVsIndividualPerformance:
    """批量vs单独请求性能测试"""
    
    @pytest.mark.perf
    @pytest.mark.paper_batch
    async def test_batch_vs_individual_efficiency(self, async_client, batch_paper_ids_fixture):
        """测试批量请求vs单独请求的效率"""
        test_ids = batch_paper_ids_fixture[:3]
        
        # 批量请求
        batch_payload = {"ids": test_ids}
        batch_response = await async_client.post("/paper/batch", json=batch_payload)
        assert batch_response.status_code == 200
        batch_time = float(batch_response.headers.get("x-process-time", "0"))
        
        # 单独请求
        individual_times = []
        for paper_id in test_ids:
            response = await async_client.get(f"/paper/{paper_id}")
            if response.status_code == 200:
                time = float(response.headers.get("x-process-time", "0"))
                if time > 0:
                    individual_times.append(time)
        
        if individual_times and batch_time > 0:
            total_individual_time = sum(individual_times)
            efficiency_ratio = total_individual_time / batch_time
            
            print(f"批量效率: {efficiency_ratio:.1f}x")
            print(f"批量: {batch_time:.3f}s, 单独总计: {total_individual_time:.3f}s")
            
            # 批量应该更高效（至少不应该更慢）
            assert batch_time <= total_individual_time * 1.2, (
                f"批量请求效率不足: {batch_time:.3f}s vs {total_individual_time:.3f}s"
            )


class TestFieldsFilteringPerformance:
    """字段过滤性能测试"""
    
    @pytest.mark.perf
    @pytest.mark.paper_details
    async def test_minimal_vs_full_fields_performance(self, async_client, paper_id_fixture, clean_cache):
        """测试最小字段vs完整字段的性能差异"""
        # 清理缓存
        await clean_cache()
        
        # 最小字段请求
        response_minimal = await async_client.get(
            f"/paper/{paper_id_fixture}",
            params={"fields": "title"}
        )
        assert response_minimal.status_code == 200
        time_minimal = float(response_minimal.headers.get("x-process-time", "0"))
        
        # 清理缓存
        await clean_cache()
        
        # 完整字段请求
        response_full = await async_client.get(
            f"/paper/{paper_id_fixture}",
            params={"fields": "title,abstract,authors,citations,references,venue,year"}
        )
        assert response_full.status_code == 200
        time_full = float(response_full.headers.get("x-process-time", "0"))
        
        # 比较性能
        if time_minimal > 0 and time_full > 0:
            ratio = time_full / time_minimal
            print(f"字段过滤性能: 最小 {time_minimal:.3f}s, 完整 {time_full:.3f}s ({ratio:.1f}x)")
            
            # 完整字段不应该比最小字段慢太多
            assert ratio <= 5.0, f"完整字段性能差异过大: {ratio:.1f}x"
    
    @pytest.mark.perf
    @pytest.mark.paper_relations
    async def test_relations_fields_filtering_performance(self, async_client, paper_id_fixture, clean_cache):
        """测试关系查询字段过滤性能"""
        # 清理缓存
        await clean_cache()
        
        # 最小字段的引用查询
        response_minimal = await async_client.get(
            f"/paper/{paper_id_fixture}/citations",
            params={"fields": "title", "limit": 10}
        )
        
        if response_minimal.status_code != 200:
            pytest.skip("论文引用不可用")
            
        time_minimal = float(response_minimal.headers.get("x-process-time", "0"))
        
        # 清理缓存
        await clean_cache()
        
        # 完整字段的引用查询
        response_full = await async_client.get(
            f"/paper/{paper_id_fixture}/citations",
            params={"fields": "title,authors,year,venue", "limit": 10}
        )
        assert response_full.status_code == 200
        time_full = float(response_full.headers.get("x-process-time", "0"))
        
        # 比较性能
        if time_minimal > 0 and time_full > 0:
            ratio = time_full / time_minimal
            print(f"引用字段过滤性能: 最小 {time_minimal:.3f}s, 完整 {time_full:.3f}s ({ratio:.1f}x)")
            
            # 字段过滤应该有效果
            assert ratio <= 3.0, f"引用字段过滤性能差异过大: {ratio:.1f}x"


class TestSearchPerformanceOptimization:
    """搜索性能优化测试"""
    
    @pytest.mark.perf
    @pytest.mark.paper_search
    async def test_search_limit_scaling(self, async_client, search_query_fixture):
        """测试搜索limit对性能的影响"""
        limits = [5, 10, 20, 50]
        times = []
        
        for limit in limits:
            response = await async_client.get(
                "/paper/search",
                params={"query": search_query_fixture, "limit": limit}
            )
            
            if response.status_code == 200:
                time = float(response.headers.get("x-process-time", "0"))
                if time > 0:
                    times.append((limit, time))
                    print(f"搜索 limit={limit}: {time:.3f}s")
        
        # 分析性能扩展性
        if len(times) >= 2:
            # 时间不应该随limit线性增长（应该有优化）
            first_limit, first_time = times[0]
            last_limit, last_time = times[-1]
            
            if first_time > 0:
                linear_ratio = (last_limit / first_limit)
                actual_ratio = (last_time / first_time)
                
                print(f"搜索扩展性: limit {linear_ratio:.1f}x, 时间 {actual_ratio:.1f}x")
                
                # 实际时间增长应该小于线性增长
                assert actual_ratio <= linear_ratio * 1.5, (
                    f"搜索性能扩展性差: limit增长{linear_ratio:.1f}x, 时间增长{actual_ratio:.1f}x"
                )
    
    @pytest.mark.perf
    @pytest.mark.paper_search
    async def test_search_complexity_performance(self, async_client):
        """测试不同复杂度搜索查询的性能"""
        queries = [
            ("simple", "attention"),
            ("medium", "attention mechanism neural networks"),
            ("complex", "attention mechanism in neural networks for natural language processing"),
        ]
        
        for complexity, query in queries:
            response = await async_client.get(
                "/paper/search",
                params={"query": query, "limit": 10}
            )
            
            if response.status_code == 200:
                time = float(response.headers.get("x-process-time", "0"))
                print(f"搜索复杂度 {complexity}: {time:.3f}s")
                
                # 所有查询都应该在合理时间内完成
                assert time < 15.0, f"{complexity}查询时间过长: {time:.3f}s"
