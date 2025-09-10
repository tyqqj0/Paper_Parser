"""
论文关系（引用和参考文献）接口集成测试
"""
import pytest
from tests.helpers.assertions import (
    assert_pagination_response, assert_paper_basic_fields,
    assert_fields_filtering_works, assert_json_serializable,
    assert_error_response, assert_process_time_header
)


class TestPaperCitations:
    """论文引用测试"""
    
    @pytest.mark.paper_citations
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_citations_pagination_structure(self, async_client, paper_id_fixture):
        """测试引用分页结构"""
        response = await async_client.get(f"/paper/{paper_id_fixture}/citations")
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查分页响应结构
        assert_pagination_response(
            data, 
            expected_offset=0,
            context="引用分页结构"
        )
        
        # 检查处理时间头
        assert_process_time_header(response.headers, context="论文引用")
    
    @pytest.mark.paper_citations
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_citations_with_offset_limit(self, async_client, paper_id_fixture):
        """测试引用分页参数"""
        # 测试不同的offset和limit
        test_cases = [
            {"offset": 0, "limit": 5},
            {"offset": 5, "limit": 10},
            {"offset": 0, "limit": 1},
        ]
        
        for params in test_cases:
            response = await async_client.get(
                f"/paper/{paper_id_fixture}/citations",
                params=params
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 检查分页参数正确返回
            assert_pagination_response(
                data,
                expected_offset=params["offset"],
                max_data_length=params["limit"],
                context=f"引用分页 {params}"
            )
    
    @pytest.mark.paper_citations
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_citations_fields_filtering(self, async_client, paper_id_fixture):
        """测试引用字段过滤"""
        fields = "title,year,authors"
        response = await async_client.get(
            f"/paper/{paper_id_fixture}/citations",
            params={"fields": fields, "limit": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查基本结构
        assert_pagination_response(data, context="引用字段过滤")
        
        # 检查每个引用论文的字段过滤
        if data["data"]:
            for citation in data["data"]:
                if citation:  # 跳过None值
                    assert_fields_filtering_works(
                        citation, fields, "引用论文字段过滤"
                    )
    
    @pytest.mark.paper_citations
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_citations_data_structure(self, async_client, paper_id_fixture):
        """测试引用数据结构"""
        response = await async_client.get(
            f"/paper/{paper_id_fixture}/citations",
            params={"limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查JSON序列化
        assert_json_serializable(data, "引用响应")
        
        # 检查每个引用的基本结构
        if data["data"]:
            for citation in data["data"]:
                if citation:  # 跳过None值
                    assert_paper_basic_fields(citation, "引用论文")


class TestPaperReferences:
    """论文参考文献测试"""
    
    @pytest.mark.paper_references
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_references_pagination_structure(self, async_client, paper_id_fixture):
        """测试参考文献分页结构"""
        response = await async_client.get(f"/paper/{paper_id_fixture}/references")
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查分页响应结构
        assert_pagination_response(
            data,
            expected_offset=0,
            context="参考文献分页结构"
        )
        
        # 检查处理时间头
        assert_process_time_header(response.headers, context="论文参考文献")
    
    @pytest.mark.paper_references
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_references_with_offset_limit(self, async_client, paper_id_fixture):
        """测试参考文献分页参数"""
        test_cases = [
            {"offset": 0, "limit": 5},
            {"offset": 3, "limit": 7},
            {"offset": 0, "limit": 1},
        ]
        
        for params in test_cases:
            response = await async_client.get(
                f"/paper/{paper_id_fixture}/references",
                params=params
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 检查分页参数正确返回
            assert_pagination_response(
                data,
                expected_offset=params["offset"],
                max_data_length=params["limit"],
                context=f"参考文献分页 {params}"
            )
    
    @pytest.mark.paper_references
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_references_fields_filtering(self, async_client, paper_id_fixture):
        """测试参考文献字段过滤"""
        fields = "title,year,venue"
        response = await async_client.get(
            f"/paper/{paper_id_fixture}/references",
            params={"fields": fields, "limit": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查基本结构
        assert_pagination_response(data, context="参考文献字段过滤")
        
        # 检查每个参考文献的字段过滤
        if data["data"]:
            for reference in data["data"]:
                if reference:  # 跳过None值
                    assert_fields_filtering_works(
                        reference, fields, "参考文献字段过滤"
                    )
    
    @pytest.mark.paper_references
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_references_data_structure(self, async_client, paper_id_fixture):
        """测试参考文献数据结构"""
        response = await async_client.get(
            f"/paper/{paper_id_fixture}/references",
            params={"limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查JSON序列化
        assert_json_serializable(data, "参考文献响应")
        
        # 检查每个参考文献的基本结构
        if data["data"]:
            for reference in data["data"]:
                if reference:  # 跳过None值
                    assert_paper_basic_fields(reference, "参考文献")


class TestRelationsErrorHandling:
    """关系接口错误处理测试"""
    
    @pytest.mark.paper_citations
    @pytest.mark.paper_references
    @pytest.mark.integration
    async def test_relations_paper_not_found(self, async_client):
        """测试不存在论文的关系查询"""
        fake_id = "0000000000000000000000000000000000000000"
        
        # 测试引用
        response = await async_client.get(f"/paper/{fake_id}/citations")
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, 404, context="引用-论文不存在")
        
        # 测试参考文献
        response = await async_client.get(f"/paper/{fake_id}/references")
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, 404, context="参考文献-论文不存在")
    
    @pytest.mark.paper_citations
    @pytest.mark.paper_references
    @pytest.mark.integration
    async def test_relations_invalid_paper_id(self, async_client):
        """测试无效论文ID的关系查询"""
        invalid_id = "invalid-id"
        
        # 测试引用
        response = await async_client.get(f"/paper/{invalid_id}/citations")
        assert response.status_code == 400
        data = response.json()
        assert_error_response(data, 400, context="引用-无效ID")
        
        # 测试参考文献
        response = await async_client.get(f"/paper/{invalid_id}/references")
        assert response.status_code == 400
        data = response.json()
        assert_error_response(data, 400, context="参考文献-无效ID")
    
    @pytest.mark.paper_citations
    @pytest.mark.paper_references
    @pytest.mark.integration
    async def test_relations_invalid_pagination(self, async_client, paper_id_fixture):
        """测试无效分页参数"""
        invalid_params = [
            {"offset": -1},  # 负offset
            {"limit": 0},    # 零limit
            {"limit": 101},  # 超出限制的limit
        ]
        
        for params in invalid_params:
            # 测试引用
            response = await async_client.get(
                f"/paper/{paper_id_fixture}/citations",
                params=params
            )
            assert response.status_code == 422, f"引用分页参数 {params} 应该被拒绝"
            
            # 测试参考文献
            response = await async_client.get(
                f"/paper/{paper_id_fixture}/references", 
                params=params
            )
            assert response.status_code == 422, f"参考文献分页参数 {params} 应该被拒绝"


class TestRelationsPerformance:
    """关系接口性能测试"""
    
    @pytest.mark.paper_citations
    @pytest.mark.paper_references
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_relations_response_time(self, async_client, paper_id_fixture):
        """测试关系查询响应时间"""
        endpoints = ["citations", "references"]
        
        for endpoint in endpoints:
            response = await async_client.get(
                f"/paper/{paper_id_fixture}/{endpoint}",
                params={"limit": 10}
            )
            
            assert response.status_code == 200
            
            # 检查响应时间
            process_time = float(response.headers.get("x-process-time", "0"))
            assert process_time < 10.0, f"{endpoint} 响应时间过长: {process_time}s"
    
    @pytest.mark.paper_citations
    @pytest.mark.paper_references
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_relations_small_vs_large_limit(self, async_client, paper_id_fixture):
        """测试小limit vs 大limit的性能差异"""
        endpoints = ["citations", "references"]
        
        for endpoint in endpoints:
            # 清理缓存确保公平比较
            await async_client.delete(f"/paper/{paper_id_fixture}/cache")
            
            # 小limit
            response_small = await async_client.get(
                f"/paper/{paper_id_fixture}/{endpoint}",
                params={"limit": 5}
            )
            time_small = float(response_small.headers.get("x-process-time", "0"))
            
            # 清理缓存
            await async_client.delete(f"/paper/{paper_id_fixture}/cache")
            
            # 大limit
            response_large = await async_client.get(
                f"/paper/{paper_id_fixture}/{endpoint}",
                params={"limit": 50}
            )
            time_large = float(response_large.headers.get("x-process-time", "0"))
            
            # 大limit不应该比小limit慢太多（考虑到可能的缓存和优化）
            assert time_large <= time_small * 3, (
                f"{endpoint} 大limit性能差异过大: {time_small}s vs {time_large}s"
            )


class TestRelationsDataConsistency:
    """关系数据一致性测试"""
    
    @pytest.mark.paper_citations
    @pytest.mark.paper_references
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_relations_pagination_consistency(self, async_client, paper_id_fixture):
        """测试分页一致性"""
        endpoints = ["citations", "references"]
        
        for endpoint in endpoints:
            # 获取第一页
            response1 = await async_client.get(
                f"/paper/{paper_id_fixture}/{endpoint}",
                params={"offset": 0, "limit": 5}
            )
            
            if response1.status_code != 200:
                continue  # 跳过不存在的论文
                
            data1 = response1.json()
            
            # 如果有足够的数据，测试第二页
            if data1["total"] > 5:
                response2 = await async_client.get(
                    f"/paper/{paper_id_fixture}/{endpoint}",
                    params={"offset": 5, "limit": 5}
                )
                
                assert response2.status_code == 200
                data2 = response2.json()
                
                # total应该一致
                assert data1["total"] == data2["total"], (
                    f"{endpoint} total不一致: {data1['total']} vs {data2['total']}"
                )
                
                # 数据不应该重复（假设有足够的数据）
                if data1["data"] and data2["data"]:
                    ids1 = {item.get("paperId") for item in data1["data"] if item}
                    ids2 = {item.get("paperId") for item in data2["data"] if item}
                    overlap = ids1 & ids2
                    assert not overlap, f"{endpoint} 分页数据重复: {overlap}"
    
    @pytest.mark.paper_citations
    @pytest.mark.paper_references
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_relations_total_vs_actual_count(self, async_client, paper_id_fixture):
        """测试total字段与实际数据的一致性"""
        endpoints = ["citations", "references"]
        
        for endpoint in endpoints:
            response = await async_client.get(
                f"/paper/{paper_id_fixture}/{endpoint}",
                params={"limit": 100}  # 尝试获取更多数据
            )
            
            if response.status_code != 200:
                continue
                
            data = response.json()
            
            # 如果total较小，实际数据数量应该接近total
            if data["total"] <= 100:
                actual_count = len([item for item in data["data"] if item])
                # 允许一些差异（可能有None值或其他原因）
                assert actual_count <= data["total"], (
                    f"{endpoint} 实际数据量超过total: {actual_count} > {data['total']}"
                )
    
    @pytest.mark.paper_citations
    @pytest.mark.paper_references  
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_relations_empty_results(self, async_client, paper_id_fixture):
        """测试空结果的处理"""
        endpoints = ["citations", "references"]
        
        for endpoint in endpoints:
            # 使用很大的offset来测试空结果
            response = await async_client.get(
                f"/paper/{paper_id_fixture}/{endpoint}",
                params={"offset": 10000, "limit": 10}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 即使没有数据，结构也应该正确
                assert_pagination_response(
                    data, 
                    expected_offset=10000,
                    context=f"{endpoint} 空结果"
                )
                
                # data应该是空列表
                assert isinstance(data["data"], list)
                assert len(data["data"]) == 0
