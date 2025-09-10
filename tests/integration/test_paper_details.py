"""
论文详情接口集成测试
"""
import pytest
from tests.helpers.assertions import (
    assert_subset_keys, assert_paper_basic_fields, 
    assert_fields_filtering_works, assert_json_serializable,
    assert_error_response, assert_process_time_header
)


class TestPaperDetailsBasic:
    """论文详情基础测试"""
    
    @pytest.mark.paper_details
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_paper_details_default_shape(self, async_client, paper_id_fixture):
        """测试默认响应结构"""
        response = await async_client.get(f"/paper/{paper_id_fixture}")
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查基本字段
        assert_paper_basic_fields(data, "论文详情默认响应")
        
        # 检查JSON序列化
        assert_json_serializable(data, "论文详情响应")
        
        # 检查处理时间头
        assert_process_time_header(response.headers, context="论文详情")
    
    @pytest.mark.paper_details
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_paper_details_with_fields(self, async_client, paper_id_fixture):
        """测试字段过滤"""
        fields = "title,abstract,year,authors,citationCount"
        response = await async_client.get(
            f"/paper/{paper_id_fixture}",
            params={"fields": fields}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查字段过滤是否生效
        assert_fields_filtering_works(data, fields, "字段过滤测试")
        
        # 检查特定字段类型
        if "year" in data:
            assert isinstance(data["year"], (int, type(None)))
        if "citationCount" in data:
            assert isinstance(data["citationCount"], (int, type(None)))
        if "authors" in data:
            assert isinstance(data["authors"], (list, type(None)))
    
    @pytest.mark.paper_details
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_paper_details_nested_fields(self, async_client, paper_id_fixture):
        """测试嵌套字段过滤"""
        fields = "title,authors.name,authors.authorId"
        response = await async_client.get(
            f"/paper/{paper_id_fixture}",
            params={"fields": fields}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 基本检查
        assert "title" in data
        assert "paperId" in data  # 总是包含
        
        # 如果有authors，检查嵌套字段
        if "authors" in data and data["authors"]:
            for author in data["authors"]:
                if isinstance(author, dict):
                    # 应该只包含请求的嵌套字段
                    expected_author_fields = {"name", "authorId"}
                    actual_author_fields = set(author.keys())
                    # 至少包含请求的字段
                    assert expected_author_fields.issubset(actual_author_fields) or not author


class TestPaperDetailsErrorHandling:
    """论文详情错误处理测试"""
    
    @pytest.mark.paper_details
    @pytest.mark.integration
    async def test_paper_not_found(self, async_client):
        """测试论文不存在的情况"""
        fake_id = "0000000000000000000000000000000000000000"
        response = await async_client.get(f"/paper/{fake_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, 404, "不存在", "论文不存在测试")
    
    @pytest.mark.paper_details
    @pytest.mark.integration
    async def test_invalid_paper_id_format(self, async_client):
        """测试无效的论文ID格式"""
        invalid_ids = [
            "invalid-id",
            "123",
            "10.1038/nature14539",  # DOI without prefix
            "1705.10311"  # ArXiv without prefix
        ]
        
        for invalid_id in invalid_ids:
            response = await async_client.get(f"/paper/{invalid_id}")
            assert response.status_code == 400
            data = response.json()
            assert_error_response(data, 400, context=f"无效ID测试 {invalid_id}")
    
    @pytest.mark.paper_details
    @pytest.mark.integration
    async def test_valid_prefixed_ids(self, async_client, doi_fixture, arxiv_fixture):
        """测试有效的带前缀ID"""
        test_cases = [
            f"DOI:{doi_fixture}",
            f"ARXIV:{arxiv_fixture}",
            # f"PMID:12345678",  # 可能不存在，先注释
        ]
        
        for prefixed_id in test_cases:
            response = await async_client.get(f"/paper/{prefixed_id}")
            # 应该返回200或404，不应该是400（格式错误）
            assert response.status_code in [200, 404], f"前缀ID {prefixed_id} 格式应该有效"
            
            if response.status_code == 200:
                data = response.json()
                assert_paper_basic_fields(data, f"前缀ID {prefixed_id}")


class TestPaperDetailsPerformance:
    """论文详情性能测试"""
    
    @pytest.mark.paper_details
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_response_time_reasonable(self, async_client, paper_id_fixture):
        """测试响应时间在合理范围内"""
        response = await async_client.get(f"/paper/{paper_id_fixture}")
        
        assert response.status_code == 200
        
        # 检查处理时间（应该在5秒内）
        process_time = float(response.headers.get("x-process-time", "0"))
        assert process_time < 5.0, f"响应时间过长: {process_time}s"
    
    @pytest.mark.paper_details
    @pytest.mark.perf
    @pytest.mark.integration
    async def test_minimal_fields_faster(self, async_client, paper_id_fixture):
        """测试最小字段请求更快"""
        # 清理缓存确保公平比较
        await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        
        # 请求最小字段
        response_minimal = await async_client.get(
            f"/paper/{paper_id_fixture}",
            params={"fields": "title"}
        )
        time_minimal = float(response_minimal.headers.get("x-process-time", "0"))
        
        # 清理缓存
        await async_client.delete(f"/paper/{paper_id_fixture}/cache")
        
        # 请求完整字段
        response_full = await async_client.get(
            f"/paper/{paper_id_fixture}",
            params={"fields": "title,abstract,authors,citations,references"}
        )
        time_full = float(response_full.headers.get("x-process-time", "0"))
        
        # 最小字段应该更快（或至少不慢很多）
        assert time_minimal <= time_full * 1.5, (
            f"最小字段请求应该更快: {time_minimal}s vs {time_full}s"
        )


class TestPaperDetailsDataIntegrity:
    """论文详情数据完整性测试"""
    
    @pytest.mark.paper_details
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_paper_id_consistency(self, async_client, paper_id_fixture):
        """测试返回的paperId与请求一致"""
        response = await async_client.get(f"/paper/{paper_id_fixture}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["paperId"] == paper_id_fixture
    
    @pytest.mark.paper_details
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_required_fields_present(self, async_client, paper_id_fixture):
        """测试必要字段总是存在"""
        response = await async_client.get(f"/paper/{paper_id_fixture}")
        
        assert response.status_code == 200
        data = response.json()
        
        # 这些字段应该总是存在
        required_fields = {"paperId", "title"}
        assert_subset_keys(data, required_fields, "必要字段检查")
        
        # 检查字段值不为空
        assert data["paperId"], "paperId不能为空"
        assert data["title"], "title不能为空"
    
    @pytest.mark.paper_details
    @pytest.mark.shape  
    @pytest.mark.integration
    async def test_optional_fields_types(self, async_client, paper_id_fixture):
        """测试可选字段的类型正确"""
        fields = "title,abstract,year,authors,citationCount,referenceCount,venue,url"
        response = await async_client.get(
            f"/paper/{paper_id_fixture}",
            params={"fields": fields}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 类型检查
        type_checks = {
            "title": str,
            "abstract": (str, type(None)),
            "year": (int, type(None)),
            "authors": (list, type(None)),
            "citationCount": (int, type(None)),
            "referenceCount": (int, type(None)),
            "venue": (str, type(None)),
            "url": (str, type(None))
        }
        
        for field, expected_type in type_checks.items():
            if field in data:
                assert isinstance(data[field], expected_type), (
                    f"字段 {field} 类型错误: 期望 {expected_type}, 实际 {type(data[field])}"
                )
    
    @pytest.mark.paper_details
    @pytest.mark.shape
    @pytest.mark.integration
    async def test_authors_structure(self, async_client, paper_id_fixture):
        """测试authors字段结构"""
        fields = "title,authors"
        response = await async_client.get(
            f"/paper/{paper_id_fixture}",
            params={"fields": fields}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if "authors" in data and data["authors"]:
            authors = data["authors"]
            assert isinstance(authors, list), "authors应该是列表"
            
            for author in authors:
                if author:  # 跳过None/空值
                    assert isinstance(author, dict), "每个author应该是字典"
                    # authorId和name是常见字段
                    if "authorId" in author:
                        assert isinstance(author["authorId"], str)
                    if "name" in author:
                        assert isinstance(author["name"], str)
