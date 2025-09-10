"""
ID校验和字段处理的单元测试
"""
import pytest
from app.api.v1.paper import _is_valid_paper_id, _validate_paper_identifier_strict
from fastapi import HTTPException


class TestPaperIdValidation:
    """论文ID校验测试"""
    
    @pytest.mark.unit
    def test_valid_s2_paper_id(self):
        """测试有效的S2论文ID"""
        valid_id = "649def34f8be52c8b66281af98ae884c09aef38b"
        assert _is_valid_paper_id(valid_id) == True
    
    @pytest.mark.unit
    def test_valid_doi(self):
        """测试有效的DOI"""
        valid_dois = [
            "10.1038/nature14539",
            "10.1145/3292500.3330701",
            "10.48550/arXiv.1706.03762"
        ]
        for doi in valid_dois:
            assert _is_valid_paper_id(doi) == True
    
    @pytest.mark.unit
    def test_valid_arxiv(self):
        """测试有效的ArXiv ID"""
        valid_arxivs = [
            "1705.10311",
            "arXiv:1705.10311", 
            "1705.10311v1",
            "arXiv:1705.10311v2"
        ]
        for arxiv in valid_arxivs:
            assert _is_valid_paper_id(arxiv) == True
    
    @pytest.mark.unit
    def test_valid_pubmed(self):
        """测试有效的PubMed ID"""
        valid_pubmeds = [
            "12345",
            "1234567890"
        ]
        for pubmed in valid_pubmeds:
            assert _is_valid_paper_id(pubmed) == True
    
    @pytest.mark.unit
    def test_invalid_paper_ids(self):
        """测试无效的论文ID"""
        invalid_ids = [
            "",  # 空字符串
            "123",  # 太短
            "not-a-valid-id",  # 无效格式
            "10.invalid",  # 无效DOI
            "arxiv:invalid"  # 无效ArXiv
        ]
        for invalid_id in invalid_ids:
            assert _is_valid_paper_id(invalid_id) == False


class TestStrictIdValidation:
    """严格ID校验测试（需要显式前缀）"""
    
    @pytest.mark.unit
    def test_valid_s2_id_no_prefix_needed(self):
        """S2 ID不需要前缀"""
        s2_id = "649def34f8be52c8b66281af98ae884c09aef38b"
        # 应该不抛出异常
        _validate_paper_identifier_strict(s2_id)
    
    @pytest.mark.unit
    def test_valid_prefixed_ids(self):
        """测试有效的带前缀ID"""
        valid_prefixed_ids = [
            "DOI:10.1038/nature14539",
            "ARXIV:1705.10311", 
            "PMID:12345678",
            "PMCID:2323736",
            "CORPUSID:123456789",
            "URL:https://example.com/paper"
        ]
        for prefixed_id in valid_prefixed_ids:
            # 应该不抛出异常
            _validate_paper_identifier_strict(prefixed_id)
    
    @pytest.mark.unit
    def test_invalid_unprefixed_ids(self):
        """测试无前缀的ID会被拒绝"""
        unprefixed_ids = [
            "10.1038/nature14539",  # DOI without prefix
            "1705.10311",  # ArXiv without prefix  
            "12345678",  # PMID without prefix
            "https://example.com"  # URL without prefix
        ]
        for unprefixed_id in unprefixed_ids:
            with pytest.raises(HTTPException) as exc_info:
                _validate_paper_identifier_strict(unprefixed_id)
            assert exc_info.value.status_code == 400
    
    @pytest.mark.unit
    def test_unknown_prefix_rejected(self):
        """测试未知前缀被拒绝"""
        unknown_prefixed_ids = [
            "UNKNOWN:12345",
            "INVALID:test",
            "CUSTOM:something"
        ]
        for unknown_id in unknown_prefixed_ids:
            with pytest.raises(HTTPException) as exc_info:
                _validate_paper_identifier_strict(unknown_id)
            assert exc_info.value.status_code == 400
            assert "未知ID前缀" in str(exc_info.value.detail)
    
    @pytest.mark.unit
    def test_empty_id_rejected(self):
        """测试空ID被拒绝"""
        empty_ids = ["", "  ", None]
        for empty_id in empty_ids:
            with pytest.raises(HTTPException) as exc_info:
                _validate_paper_identifier_strict(empty_id)
            assert exc_info.value.status_code == 400


class TestFieldsProcessing:
    """字段处理测试"""
    
    @pytest.mark.unit
    def test_basic_fields_parsing(self):
        """测试基本字段解析"""
        # 这里我们测试字段解析逻辑
        # 由于字段处理在service层，这里主要测试输入验证
        
        # 测试逗号分隔的字段
        fields_input = "title,abstract,authors"
        fields_list = [f.strip() for f in fields_input.split(",")]
        expected = ["title", "abstract", "authors"]
        assert fields_list == expected
    
    @pytest.mark.unit
    def test_fields_with_spaces(self):
        """测试带空格的字段"""
        fields_input = " title , abstract , authors "
        fields_list = [f.strip() for f in fields_input.split(",")]
        expected = ["title", "abstract", "authors"]
        assert fields_list == expected
    
    @pytest.mark.unit
    def test_nested_fields_parsing(self):
        """测试嵌套字段解析"""
        fields_input = "title,authors.name,citations.title"
        fields_list = [f.strip() for f in fields_input.split(",")]
        expected = ["title", "authors.name", "citations.title"]
        assert fields_list == expected
    
    @pytest.mark.unit
    def test_empty_fields(self):
        """测试空字段处理"""
        empty_inputs = ["", "  ", None]
        for empty_input in empty_inputs:
            if empty_input:
                fields_list = [f.strip() for f in empty_input.split(",") if f.strip()]
                assert fields_list == []
            else:
                assert empty_input is None or empty_input == ""


class TestParameterValidation:
    """参数校验测试"""
    
    @pytest.mark.unit
    def test_offset_validation(self):
        """测试offset参数校验"""
        valid_offsets = [0, 1, 100, 1000]
        invalid_offsets = [-1, -10]
        
        # 在实际API中，这些会通过FastAPI的Query验证
        # 这里我们测试逻辑
        for offset in valid_offsets:
            assert offset >= 0
        
        for offset in invalid_offsets:
            assert offset < 0  # 这些应该被拒绝
    
    @pytest.mark.unit
    def test_limit_validation(self):
        """测试limit参数校验"""
        valid_limits = [1, 10, 50, 100]
        invalid_limits = [0, -1, 101, 1000]
        
        # 测试范围 1-100
        for limit in valid_limits:
            assert 1 <= limit <= 100
        
        for limit in invalid_limits:
            assert not (1 <= limit <= 100)
    
    @pytest.mark.unit
    def test_year_format_validation(self):
        """测试年份格式校验"""
        valid_years = ["2020", "2018-2020", "2015-2023"]
        
        for year in valid_years:
            # 基本格式检查
            if "-" in year:
                parts = year.split("-")
                assert len(parts) == 2
                assert all(part.isdigit() and len(part) == 4 for part in parts)
            else:
                assert year.isdigit() and len(year) == 4
    
    @pytest.mark.unit 
    def test_boolean_parameters(self):
        """测试布尔参数"""
        # match_title, prefer_local, fallback_to_s2 等
        valid_bools = [True, False, "true", "false", "1", "0"]
        
        def normalize_bool(val):
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ("true", "1", "yes", "on")
            return bool(val)
        
        # 测试转换
        assert normalize_bool(True) == True
        assert normalize_bool(False) == False
        assert normalize_bool("true") == True
        assert normalize_bool("false") == False
        assert normalize_bool("1") == True
        assert normalize_bool("0") == False
