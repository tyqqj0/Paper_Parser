"""
论文批量获取接口集成测试
"""
import pytest
from tests.helpers.assertions import (
    assert_paper_basic_fields, assert_fields_filtering_works,
    assert_json_serializable, assert_error_response,
    assert_process_time_header
)


class TestPaperBatchBasic:
    """论文批量获取基础测试"""
    
    @pytest.mark.paper_batch
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_batch_basic_structure(self, async_client, batch_paper_ids_fixture):
        """测试批量获取基本响应结构"""
        payload = {"ids": batch_paper_ids_fixture[:2]}  # 只测试前2个
        
        response = await async_client.post("/paper/batch", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # 应该返回列表
        assert isinstance(data, list), "批量响应应该是列表"
        
        # 长度应该与请求一致
        assert len(data) == len(payload["ids"]), (
            f"响应长度 {len(data)} 与请求长度 {len(payload['ids'])} 不匹配"
        )
        
        # 检查处理时间头
        assert_process_time_header(response.headers, context="论文批量获取")
        
        # 检查JSON序列化
        assert_json_serializable(data, "批量获取响应")
    
    @pytest.mark.paper_batch
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_batch_with_fields(self, async_client, batch_paper_ids_fixture):
        """测试批量获取字段过滤"""
        fields = "title,year,authors"
        payload = {
            "ids": batch_paper_ids_fixture[:2],
            "fields": fields
        }
        
        response = await async_client.post("/paper/batch", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查每个结果的字段过滤
        for i, paper in enumerate(data):
            if paper:  # 跳过None值（不存在的论文）
                assert_fields_filtering_works(
                    paper, fields, f"批量获取第{i}个论文字段过滤"
                )
    
    @pytest.mark.paper_batch
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_batch_data_structure(self, async_client, batch_paper_ids_fixture):
        """测试批量获取数据结构"""
        payload = {"ids": batch_paper_ids_fixture[:2]}
        
        response = await async_client.post("/paper/batch", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查每个论文的基本结构
        for i, paper in enumerate(data):
            if paper:  # 跳过None值
                assert_paper_basic_fields(paper, f"批量获取第{i}个论文")
    
    @pytest.mark.paper_batch
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_batch_order_preservation(self, async_client, batch_paper_ids_fixture):
        """测试批量获取保持顺序"""
        # 使用特定顺序的ID
        ids_in_order = batch_paper_ids_fixture[:3]
        payload = {"ids": ids_in_order}
        
        response = await async_client.post("/paper/batch", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查返回顺序与请求顺序一致
        for i, (requested_id, paper) in enumerate(zip(ids_in_order, data)):
            if paper:  # 如果论文存在
                assert paper["paperId"] == requested_id, (
                    f"第{i}个位置：请求ID {requested_id}，返回ID {paper['paperId']}"
                )
            # 如果论文不存在（None），位置应该对应但值为None


class TestPaperBatchErrorHandling:
    """论文批量获取错误处理测试"""
    
    @pytest.mark.paper_batch
    @pytest.mark.integration
    async def test_batch_empty_ids(self, async_client):
        """测试空ID列表"""
        payload = {"ids": []}
        
        response = await async_client.post("/paper/batch", json=payload)
        
        # 空列表应该返回200和空列表，或者400错误
        if response.status_code == 200:
            data = response.json()
            assert data == [], "空ID列表应该返回空列表"
        else:
            assert response.status_code == 400
            data = response.json()
            assert_error_response(data, 400, context="空ID列表")
    
    @pytest.mark.paper_batch
    @pytest.mark.integration
    async def test_batch_too_many_ids(self, async_client):
        """测试过多ID（超过限制）"""
        # 创建超过500个ID的列表
        too_many_ids = [f"{'0' * 39}{i:01d}" for i in range(501)]
        payload = {"ids": too_many_ids}
        
        response = await async_client.post("/paper/batch", json=payload)
        
        # 应该返回400错误
        assert response.status_code == 400
        data = response.json()
        assert_error_response(data, 400, "500", "过多ID限制")
    
    @pytest.mark.paper_batch
    @pytest.mark.integration
    async def test_batch_invalid_ids(self, async_client):
        """测试包含无效ID的批量请求"""
        invalid_ids = ["invalid-id-1", "invalid-id-2", "123"]
        payload = {"ids": invalid_ids}
        
        response = await async_client.post("/paper/batch", json=payload)
        
        # 可能返回400（如果严格验证）或200（返回None值）
        if response.status_code == 400:
            data = response.json()
            assert_error_response(data, 400, context="无效ID批量")
        else:
            assert response.status_code == 200
            data = response.json()
            # 所有结果应该是None（因为ID无效）
            assert all(item is None for item in data), "无效ID应该返回None"
    
    @pytest.mark.paper_batch
    @pytest.mark.integration
    async def test_batch_mixed_valid_invalid_ids(self, async_client, paper_id_fixture):
        """测试混合有效和无效ID"""
        mixed_ids = [
            paper_id_fixture,  # 有效ID
            "invalid-id",      # 无效ID
            "0" * 40          # 可能不存在但格式有效的ID
        ]
        payload = {"ids": mixed_ids}
        
        response = await async_client.post("/paper/batch", json=payload)
        
        # 应该返回200，但部分结果为None
        if response.status_code == 200:
            data = response.json()
            assert len(data) == len(mixed_ids), "返回数量应该与请求一致"
            
            # 第一个应该有效（如果论文存在）
            if data[0]:
                assert data[0]["paperId"] == paper_id_fixture
            
            # 第二个应该无效（None或错误）
            # 第三个可能存在也可能不存在
        else:
            # 如果严格验证，可能返回400
            assert response.status_code == 400
    
    @pytest.mark.paper_batch
    @pytest.mark.integration
    async def test_batch_invalid_request_format(self, async_client):
        """测试无效的请求格式"""
        invalid_payloads = [
            {},  # 缺少ids字段
            {"ids": "not-a-list"},  # ids不是列表
            {"wrong_field": ["id1", "id2"]},  # 错误字段名
        ]
        
        for payload in invalid_payloads:
            response = await async_client.post("/paper/batch", json=payload)
            
            # 应该返回422验证错误
            assert response.status_code == 422, f"无效payload {payload} 应该被拒绝"
            data = response.json()
            assert_error_response(data, 422, context=f"无效格式 {payload}")


class TestPaperBatchPerformance:
    """论文批量获取性能测试"""
    
    @pytest.mark.paper_batch
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_batch_response_time(self, async_client, batch_paper_ids_fixture):
        """测试批量获取响应时间"""
        payload = {"ids": batch_paper_ids_fixture[:5]}  # 5个ID
        
        response = await async_client.post("/paper/batch", json=payload)
        
        assert response.status_code == 200
        
        # 检查响应时间
        process_time = float(response.headers.get("x-process-time", "0"))
        assert process_time < 10.0, f"批量获取响应时间过长: {process_time}s"
    
    @pytest.mark.paper_batch
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_batch_vs_individual_performance(self, async_client, batch_paper_ids_fixture):
        """测试批量获取vs单独获取的性能"""
        ids_to_test = batch_paper_ids_fixture[:3]
        
        # 批量获取
        batch_payload = {"ids": ids_to_test}
        batch_response = await async_client.post("/paper/batch", json=batch_payload)
        batch_time = float(batch_response.headers.get("x-process-time", "0"))
        
        # 单独获取（总时间）
        individual_times = []
        for paper_id in ids_to_test:
            individual_response = await async_client.get(f"/paper/{paper_id}")
            if individual_response.status_code == 200:
                individual_time = float(individual_response.headers.get("x-process-time", "0"))
                individual_times.append(individual_time)
        
        total_individual_time = sum(individual_times)
        
        # 批量获取应该比单独获取更高效（如果有足够的个别请求）
        if len(individual_times) >= 2 and total_individual_time > 0:
            efficiency_ratio = total_individual_time / batch_time if batch_time > 0 else 1
            print(f"批量效率: {efficiency_ratio:.1f}x (批量: {batch_time:.3f}s, 单独总计: {total_individual_time:.3f}s)")
            
            # 批量应该至少不比单独慢太多
            assert batch_time <= total_individual_time * 1.2, (
                f"批量获取效率不足: {batch_time:.3f}s vs {total_individual_time:.3f}s"
            )
    
    @pytest.mark.paper_batch
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_batch_size_scaling(self, async_client, batch_paper_ids_fixture):
        """测试批量大小对性能的影响"""
        # 测试不同大小的批量请求
        batch_sizes = [1, 3, 5, 10]
        times = []
        
        for size in batch_sizes:
            if size <= len(batch_paper_ids_fixture):
                payload = {"ids": batch_paper_ids_fixture[:size]}
                response = await async_client.post("/paper/batch", json=payload)
                
                if response.status_code == 200:
                    time = float(response.headers.get("x-process-time", "0"))
                    times.append(time)
                    print(f"批量大小 {size}: {time:.3f}s")
        
        # 时间应该随批量大小合理增长（但不是线性的，因为有缓存等优化）
        if len(times) >= 2:
            # 最大时间不应该超过最小时间的10倍（考虑到缓存和并发优化）
            max_time = max(times)
            min_time = min(times)
            if min_time > 0:
                scaling_factor = max_time / min_time
                assert scaling_factor <= 10, (
                    f"批量大小扩展性能差: {scaling_factor:.1f}x ({min_time:.3f}s -> {max_time:.3f}s)"
                )


class TestPaperBatchDataIntegrity:
    """论文批量获取数据完整性测试"""
    
    @pytest.mark.paper_batch
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_batch_null_handling(self, async_client, paper_id_fixture):
        """测试批量获取中的None值处理"""
        # 混合存在和不存在的ID
        mixed_ids = [
            paper_id_fixture,  # 应该存在
            "0000000000000000000000000000000000000000",  # 可能不存在
        ]
        payload = {"ids": mixed_ids}
        
        response = await async_client.post("/paper/batch", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # 长度应该匹配
        assert len(data) == len(mixed_ids)
        
        # 检查第一个结果（应该存在或为None）
        first_result = data[0]
        if first_result:
            assert first_result["paperId"] == paper_id_fixture
        
        # 检查第二个结果（可能为None）
        second_result = data[1]
        # 不管是否为None，位置应该对应
    
    @pytest.mark.paper_batch
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_batch_consistency_with_individual(self, async_client, batch_paper_ids_fixture):
        """测试批量获取与单独获取的一致性"""
        test_ids = batch_paper_ids_fixture[:2]
        
        # 批量获取
        batch_payload = {"ids": test_ids}
        batch_response = await async_client.post("/paper/batch", json=batch_payload)
        assert batch_response.status_code == 200
        batch_data = batch_response.json()
        
        # 单独获取并比较
        for i, paper_id in enumerate(test_ids):
            individual_response = await async_client.get(f"/paper/{paper_id}")
            
            batch_paper = batch_data[i]
            
            if individual_response.status_code == 200:
                individual_paper = individual_response.json()
                
                if batch_paper:
                    # 基本字段应该一致
                    assert batch_paper["paperId"] == individual_paper["paperId"]
                    assert batch_paper["title"] == individual_paper["title"]
                else:
                    # 如果批量返回None，单独获取也应该失败或返回相同结果
                    pass
            elif individual_response.status_code == 404:
                # 如果单独获取404，批量应该返回None
                assert batch_paper is None, (
                    f"单独获取404但批量返回了数据: {batch_paper}"
                )
    
    @pytest.mark.paper_batch
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_batch_duplicate_ids(self, async_client, paper_id_fixture):
        """测试批量获取中的重复ID"""
        # 包含重复ID的列表
        duplicate_ids = [paper_id_fixture, paper_id_fixture, paper_id_fixture]
        payload = {"ids": duplicate_ids}
        
        response = await async_client.post("/paper/batch", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # 长度应该与请求一致（包含重复）
        assert len(data) == len(duplicate_ids)
        
        # 所有结果应该相同（如果论文存在）
        if data[0]:
            for result in data:
                if result:
                    assert result["paperId"] == paper_id_fixture
                    assert result["title"] == data[0]["title"]
    
    @pytest.mark.paper_batch
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_batch_fields_consistency(self, async_client, batch_paper_ids_fixture):
        """测试批量获取字段过滤的一致性"""
        fields = "title,year,authors"
        payload = {
            "ids": batch_paper_ids_fixture[:2],
            "fields": fields
        }
        
        response = await async_client.post("/paper/batch", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查所有非None结果的字段一致性
        valid_papers = [p for p in data if p is not None]
        
        if valid_papers:
            # 所有论文应该有相同的字段集合（除了可能的None值）
            first_paper_fields = set(valid_papers[0].keys())
            
            for paper in valid_papers[1:]:
                paper_fields = set(paper.keys())
                # 字段集合应该基本一致（允许一些论文缺少某些可选字段）
                common_fields = first_paper_fields & paper_fields
                assert len(common_fields) >= 2, (  # 至少有paperId和title
                    f"论文间字段差异过大: {first_paper_fields} vs {paper_fields}"
                )
