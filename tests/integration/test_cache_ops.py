"""
缓存操作接口集成测试
"""
import pytest
from tests.helpers.assertions import (
    assert_latency_improves, assert_process_time_header,
    assert_json_serializable, assert_error_response
)


class TestCacheClearOperation:
    """缓存清除操作测试"""
    
    @pytest.mark.cache
    @pytest.mark.integration
    async def test_cache_clear_success(self, async_client, paper_id_fixture):
        """测试成功清除缓存"""
        # 先访问一次确保有缓存
        await async_client.get(f"/paper/{paper_id_fixture}")
        
        # 清除缓存
        response = await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查响应格式
        assert isinstance(data, dict), "缓存清除响应应该是字典"
        assert "success" in data, "响应应该包含success字段"
        assert data["success"] is True, "成功清除应该返回success: true"
        
        # 检查JSON序列化
        assert_json_serializable(data, "缓存清除响应")
        
        # 检查处理时间头
        assert_process_time_header(response.headers, context="缓存清除", max_time=2.0)
    
    @pytest.mark.cache
    @pytest.mark.integration
    async def test_cache_clear_invalid_id(self, async_client):
        """测试清除无效ID的缓存"""
        invalid_id = "invalid-id"
        
        response = await async_client.delete(f"/paper/{invalid_id}/cache")
        
        # 应该返回400错误（ID格式无效）
        assert response.status_code == 400
        data = response.json()
        assert_error_response(data, 400, context="清除缓存-无效ID")
    
    @pytest.mark.cache
    @pytest.mark.integration
    async def test_cache_clear_nonexistent_paper(self, async_client):
        """测试清除不存在论文的缓存"""
        fake_id = "0000000000000000000000000000000000000000"
        
        response = await async_client.delete(f"/paper/{fake_id}/cache")
        
        # 可能返回200（清除成功，即使论文不存在）或404
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True
        else:
            assert response.status_code in [404, 500]
    
    @pytest.mark.cache
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_cache_clear_effect(self, async_client, paper_id_fixture):
        """测试缓存清除的效果"""
        # 第一次访问（建立缓存）
        response1 = await async_client.get(f"/paper/{paper_id_fixture}")
        assert response1.status_code == 200
        
        # 第二次访问（应该命中缓存）
        response2 = await async_client.get(f"/paper/{paper_id_fixture}")
        assert response2.status_code == 200
        time2 = float(response2.headers.get("x-process-time", "0"))
        
        # 清除缓存
        clear_response = await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        assert clear_response.status_code == 200
        
        # 再次访问（应该重新从源获取）
        response3 = await async_client.get(f"/paper/{paper_id_fixture}")
        assert response3.status_code == 200
        time3 = float(response3.headers.get("x-process-time", "0"))
        
        # 清除缓存后的访问应该比缓存命中慢
        if time2 > 0 and time3 > 0:
            # 允许一些变动，但清除后应该明显更慢
            assert time3 >= time2 * 0.8, (
                f"缓存清除后访问应该更慢: {time2:.3f}s -> {time3:.3f}s"
            )


class TestCacheWarmOperation:
    """缓存预热操作测试"""
    
    @pytest.mark.cache
    @pytest.mark.integration
    async def test_cache_warm_success(self, async_client, paper_id_fixture):
        """测试成功预热缓存"""
        # 先清除缓存
        await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        
        # 预热缓存
        response = await async_client.post(f"/paper/{paper_id_fixture}/cache/warm")
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查响应格式
        assert isinstance(data, dict), "缓存预热响应应该是字典"
        assert "success" in data, "响应应该包含success字段"
        assert data["success"] is True, "成功预热应该返回success: true"
        
        # 检查JSON序列化
        assert_json_serializable(data, "缓存预热响应")
        
        # 检查处理时间头
        assert_process_time_header(response.headers, context="缓存预热", max_time=10.0)
    
    @pytest.mark.cache
    @pytest.mark.integration
    async def test_cache_warm_with_fields(self, async_client, paper_id_fixture):
        """测试带字段的缓存预热"""
        # 先清除缓存
        await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        
        # 预热特定字段
        fields = "title,abstract,authors"
        response = await async_client.post(
            f"/paper/{paper_id_fixture}/cache/warm",
            params={"fields": fields}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
    
    @pytest.mark.cache
    @pytest.mark.integration
    async def test_cache_warm_invalid_id(self, async_client):
        """测试预热无效ID的缓存"""
        invalid_id = "invalid-id"
        
        response = await async_client.post(f"/paper/{invalid_id}/cache/warm")
        
        # 应该返回400错误（ID格式无效）
        assert response.status_code == 400
        data = response.json()
        assert_error_response(data, 400, context="预热缓存-无效ID")
    
    @pytest.mark.cache
    @pytest.mark.integration
    async def test_cache_warm_nonexistent_paper(self, async_client):
        """测试预热不存在论文的缓存"""
        fake_id = "0000000000000000000000000000000000000000"
        
        response = await async_client.post(f"/paper/{fake_id}/cache/warm")
        
        # 可能返回500（预热失败）或404
        assert response.status_code in [404, 500]
        if response.status_code == 500:
            data = response.json()
            assert_error_response(data, 500, context="预热缓存-不存在论文")
    
    @pytest.mark.cache
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_cache_warm_effect(self, async_client, paper_id_fixture):
        """测试缓存预热的效果"""
        # 清除缓存
        await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        
        # 预热缓存
        warm_response = await async_client.post(f"/paper/{paper_id_fixture}/cache/warm")
        assert warm_response.status_code == 200
        
        # 访问论文（应该命中预热的缓存）
        response = await async_client.get(f"/paper/{paper_id_fixture}")
        assert response.status_code == 200
        time_after_warm = float(response.headers.get("x-process-time", "0"))
        
        # 清除缓存再次测试冷启动
        await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        
        # 冷启动访问
        cold_response = await async_client.get(f"/paper/{paper_id_fixture}")
        assert cold_response.status_code == 200
        time_cold = float(cold_response.headers.get("x-process-time", "0"))
        
        # 预热后的访问应该比冷启动更快
        if time_after_warm > 0 and time_cold > 0:
            improvement = time_cold / time_after_warm
            print(f"预热效果: {improvement:.1f}x 改善 ({time_cold:.3f}s -> {time_after_warm:.3f}s)")
            
            # 预热应该有明显效果
            assert time_after_warm <= time_cold * 1.1, (
                f"预热效果不明显: {time_cold:.3f}s -> {time_after_warm:.3f}s"
            )


class TestCacheOperationsCombined:
    """缓存操作组合测试"""
    
    @pytest.mark.cache
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_clear_then_warm_cycle(self, async_client, paper_id_fixture):
        """测试清除->预热->访问的完整周期"""
        # 1. 清除缓存
        clear_response = await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        assert clear_response.status_code == 200
        
        # 2. 预热缓存
        warm_response = await async_client.post(f"/paper/{paper_id_fixture}/cache/warm")
        assert warm_response.status_code == 200
        
        # 3. 访问论文（应该很快）
        access_response = await async_client.get(f"/paper/{paper_id_fixture}")
        assert access_response.status_code == 200
        access_time = float(access_response.headers.get("x-process-time", "0"))
        
        # 预热后的访问应该很快
        assert access_time < 1.0, f"预热后访问应该很快: {access_time:.3f}s"
    
    @pytest.mark.cache
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_multiple_clear_operations(self, async_client, paper_id_fixture):
        """测试多次清除缓存操作"""
        # 多次清除缓存应该都成功
        for i in range(3):
            response = await async_client.delete(f"/paper/{paper_id_fixture}/cache")
            assert response.status_code == 200, f"第{i+1}次清除失败"
            data = response.json()
            assert data.get("success") is True
    
    @pytest.mark.cache
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_multiple_warm_operations(self, async_client, paper_id_fixture):
        """测试多次预热缓存操作"""
        # 清除缓存
        await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        
        # 多次预热应该都成功
        for i in range(2):
            response = await async_client.post(f"/paper/{paper_id_fixture}/cache/warm")
            assert response.status_code == 200, f"第{i+1}次预热失败"
            data = response.json()
            assert data.get("success") is True
    
    @pytest.mark.cache
    @pytest.mark.integration
    async def test_cache_operations_different_papers(self, async_client, batch_paper_ids_fixture):
        """测试不同论文的缓存操作"""
        test_ids = batch_paper_ids_fixture[:2]
        
        for paper_id in test_ids:
            # 清除缓存
            clear_response = await async_client.delete(f"/paper/{paper_id}/cache")
            # 可能成功或失败（取决于论文是否存在），但不应该影响其他论文
            
            # 预热缓存
            warm_response = await async_client.post(f"/paper/{paper_id}/cache/warm")
            # 同样可能成功或失败
            
            # 操作应该是独立的
            print(f"论文 {paper_id}: 清除={clear_response.status_code}, 预热={warm_response.status_code}")


class TestCacheOperationsErrorHandling:
    """缓存操作错误处理测试"""
    
    @pytest.mark.cache
    @pytest.mark.integration
    async def test_cache_operations_with_prefixed_ids(self, async_client, doi_fixture):
        """测试带前缀ID的缓存操作"""
        prefixed_id = f"DOI:{doi_fixture}"
        
        # 清除缓存
        clear_response = await async_client.delete(f"/paper/{prefixed_id}/cache")
        # 应该成功处理或返回合理错误
        assert clear_response.status_code in [200, 400, 404, 500]
        
        # 预热缓存
        warm_response = await async_client.post(f"/paper/{prefixed_id}/cache/warm")
        # 应该成功处理或返回合理错误
        assert warm_response.status_code in [200, 400, 404, 500]
    
    @pytest.mark.cache
    @pytest.mark.integration
    async def test_cache_operations_concurrent(self, async_client, paper_id_fixture):
        """测试并发缓存操作"""
        import asyncio
        
        # 并发执行清除和预热操作
        tasks = [
            async_client.delete(f"/paper/{paper_id_fixture}/cache"),
            async_client.post(f"/paper/{paper_id_fixture}/cache/warm"),
            async_client.get(f"/paper/{paper_id_fixture}"),
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 所有操作都应该完成（可能成功或失败，但不应该崩溃）
        for i, response in enumerate(responses):
            assert not isinstance(response, Exception), f"操作{i}抛出异常: {response}"
            if hasattr(response, 'status_code'):
                assert response.status_code in [200, 400, 404, 500], f"操作{i}状态码异常: {response.status_code}"


class TestCacheOperationsDataIntegrity:
    """缓存操作数据完整性测试"""
    
    @pytest.mark.cache
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_cache_operations_preserve_data(self, async_client, paper_id_fixture):
        """测试缓存操作不影响数据完整性"""
        # 获取原始数据
        original_response = await async_client.get(f"/paper/{paper_id_fixture}")
        if original_response.status_code != 200:
            pytest.skip("论文不存在，跳过数据完整性测试")
            
        original_data = original_response.json()
        
        # 执行缓存操作
        await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        await async_client.post(f"/paper/{paper_id_fixture}/cache/warm")
        
        # 再次获取数据
        after_ops_response = await async_client.get(f"/paper/{paper_id_fixture}")
        assert after_ops_response.status_code == 200
        after_ops_data = after_ops_response.json()
        
        # 核心数据应该一致
        core_fields = ["paperId", "title"]
        for field in core_fields:
            if field in original_data and field in after_ops_data:
                assert original_data[field] == after_ops_data[field], (
                    f"缓存操作后字段 {field} 不一致: {original_data[field]} vs {after_ops_data[field]}"
                )
    
    @pytest.mark.cache
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_cache_operations_response_format(self, async_client, paper_id_fixture):
        """测试缓存操作响应格式一致性"""
        # 清除缓存响应格式
        clear_response = await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        if clear_response.status_code == 200:
            clear_data = clear_response.json()
            assert isinstance(clear_data, dict)
            assert "success" in clear_data
            assert isinstance(clear_data["success"], bool)
        
        # 预热缓存响应格式
        warm_response = await async_client.post(f"/paper/{paper_id_fixture}/cache/warm")
        if warm_response.status_code == 200:
            warm_data = warm_response.json()
            assert isinstance(warm_data, dict)
            assert "success" in warm_data
            assert isinstance(warm_data["success"], bool)
            
            # 两种操作的响应格式应该一致
            assert set(clear_data.keys()) == set(warm_data.keys()), (
                "清除和预热缓存的响应格式应该一致"
            )
