"""
测试断言和比较工具
"""
from typing import Dict, List, Set, Any, Optional, Union
import json


def assert_subset_keys(actual: Dict[str, Any], required_keys: Set[str], context: str = ""):
    """断言字典包含必要的键"""
    actual_keys = set(actual.keys())
    missing_keys = required_keys - actual_keys
    
    assert not missing_keys, (
        f"{context}缺少必要字段: {missing_keys}. "
        f"实际字段: {actual_keys}, 期望字段: {required_keys}"
    )


def assert_subset_equal(
    actual: Dict[str, Any], 
    expected: Dict[str, Any], 
    fields: List[str],
    context: str = ""
):
    """比较两个字典在指定字段上的值"""
    for field in fields:
        actual_val = actual.get(field)
        expected_val = expected.get(field)
        
        assert actual_val == expected_val, (
            f"{context}字段 '{field}' 不匹配. "
            f"实际值: {actual_val}, 期望值: {expected_val}"
        )


def assert_latency_improves(
    t1: float, 
    t2: float, 
    *, 
    factor: float = 3.0, 
    absolute_ms: float = 300.0,
    context: str = ""
):
    """断言延迟有改善"""
    # 转换为毫秒
    t1_ms = t1 * 1000
    t2_ms = t2 * 1000
    
    # 检查绝对改善
    improvement = t1_ms - t2_ms
    assert improvement > 0, (
        f"{context}延迟没有改善. "
        f"第一次: {t1_ms:.1f}ms, 第二次: {t2_ms:.1f}ms"
    )
    
    # 检查相对改善
    ratio = t1_ms / t2_ms if t2_ms > 0 else float('inf')
    assert ratio >= factor, (
        f"{context}延迟改善不够显著. "
        f"期望改善 {factor}x, 实际改善 {ratio:.1f}x "
        f"({t1_ms:.1f}ms -> {t2_ms:.1f}ms)"
    )
    
    # 检查绝对阈值
    assert t2_ms <= absolute_ms, (
        f"{context}缓存后延迟仍然过高. "
        f"期望 <= {absolute_ms}ms, 实际 {t2_ms:.1f}ms"
    )


def assert_response_shape(
    response_data: Dict[str, Any],
    expected_shape: Dict[str, Any],
    context: str = ""
):
    """断言响应结构符合预期"""
    def check_shape(actual, expected, path=""):
        if isinstance(expected, dict):
            assert isinstance(actual, dict), (
                f"{context}路径 '{path}' 应该是字典, 实际是 {type(actual)}"
            )
            for key, expected_val in expected.items():
                current_path = f"{path}.{key}" if path else key
                assert key in actual, (
                    f"{context}缺少字段 '{current_path}'"
                )
                check_shape(actual[key], expected_val, current_path)
        elif isinstance(expected, list):
            assert isinstance(actual, list), (
                f"{context}路径 '{path}' 应该是列表, 实际是 {type(actual)}"
            )
            if expected and actual:  # 如果都不为空，检查第一个元素
                check_shape(actual[0], expected[0], f"{path}[0]")
        elif isinstance(expected, type):
            assert isinstance(actual, expected), (
                f"{context}路径 '{path}' 类型不匹配. "
                f"期望 {expected}, 实际 {type(actual)}"
            )


def assert_pagination_response(
    response_data: Dict[str, Any],
    expected_total: Optional[int] = None,
    expected_offset: Optional[int] = None,
    min_data_length: Optional[int] = None,
    max_data_length: Optional[int] = None,
    context: str = ""
):
    """断言分页响应格式正确"""
    # 检查基本结构
    required_fields = {"total", "offset", "data"}
    assert_subset_keys(response_data, required_fields, f"{context}分页响应")
    
    # 检查类型
    assert isinstance(response_data["total"], int), (
        f"{context}total 应该是整数"
    )
    assert isinstance(response_data["offset"], int), (
        f"{context}offset 应该是整数"
    )
    assert isinstance(response_data["data"], list), (
        f"{context}data 应该是列表"
    )
    
    # 检查值
    if expected_total is not None:
        assert response_data["total"] == expected_total, (
            f"{context}total 不匹配. 期望 {expected_total}, 实际 {response_data['total']}"
        )
    
    if expected_offset is not None:
        assert response_data["offset"] == expected_offset, (
            f"{context}offset 不匹配. 期望 {expected_offset}, 实际 {response_data['offset']}"
        )
    
    data_length = len(response_data["data"])
    if min_data_length is not None:
        assert data_length >= min_data_length, (
            f"{context}data 长度过短. 期望 >= {min_data_length}, 实际 {data_length}"
        )
    
    if max_data_length is not None:
        assert data_length <= max_data_length, (
            f"{context}data 长度过长. 期望 <= {max_data_length}, 实际 {data_length}"
        )


def assert_paper_basic_fields(paper_data: Dict[str, Any], context: str = ""):
    """断言论文包含基本字段"""
    basic_fields = {"paperId", "title"}
    assert_subset_keys(paper_data, basic_fields, f"{context}论文基本字段")
    
    # 检查字段类型和基本约束
    assert isinstance(paper_data["paperId"], str), "paperId 应该是字符串"
    assert len(paper_data["paperId"]) > 0, "paperId 不能为空"
    
    assert isinstance(paper_data["title"], str), "title 应该是字符串"
    assert len(paper_data["title"]) > 0, "title 不能为空"


def assert_fields_filtering_works(
    response_data: Dict[str, Any],
    requested_fields: str,
    context: str = ""
):
    """断言字段过滤正确工作"""
    if not requested_fields:
        return
        
    # 解析请求的字段
    fields = [f.strip() for f in requested_fields.split(",")]
    
    # 基本字段总是存在
    expected_fields = set(fields)
    if "paperId" not in expected_fields:
        expected_fields.add("paperId")
    
    actual_fields = set(response_data.keys())
    
    # 检查请求的字段都存在
    missing_fields = expected_fields - actual_fields
    assert not missing_fields, (
        f"{context}请求的字段缺失: {missing_fields}"
    )


def assert_json_serializable(data: Any, context: str = ""):
    """断言数据可以序列化为JSON"""
    try:
        json.dumps(data, default=str)
    except (TypeError, ValueError) as e:
        assert False, f"{context}数据不能序列化为JSON: {e}"


def assert_s2_api_compatibility(
    our_response: Dict[str, Any],
    s2_response: Dict[str, Any],
    compare_fields: List[str],
    context: str = ""
):
    """断言我们的响应与S2 API兼容"""
    for field in compare_fields:
        our_val = our_response.get(field)
        s2_val = s2_response.get(field)
        
        # 允许一些字段为None/空
        if field in ["abstract", "venue"] and (our_val is None or s2_val is None):
            continue
            
        # 数值字段允许小幅差异
        if field in ["citationCount", "referenceCount"] and isinstance(our_val, int) and isinstance(s2_val, int):
            diff_ratio = abs(our_val - s2_val) / max(s2_val, 1)
            assert diff_ratio < 0.1, (  # 允许10%差异
                f"{context}字段 '{field}' 数值差异过大. "
                f"我们的值: {our_val}, S2值: {s2_val}, 差异比例: {diff_ratio:.2%}"
            )
            continue
        
        # 其他字段严格比较
        assert our_val == s2_val, (
            f"{context}字段 '{field}' 不匹配S2. "
            f"我们的值: {our_val}, S2值: {s2_val}"
        )


def assert_error_response(
    response_data: Dict[str, Any],
    expected_status: int,
    expected_error_pattern: Optional[str] = None,
    context: str = ""
):
    """断言错误响应格式正确"""
    # 检查是否有错误信息
    assert "detail" in response_data or "error" in response_data, (
        f"{context}错误响应缺少错误信息"
    )
    
    error_msg = response_data.get("detail") or response_data.get("error", "")
    
    if expected_error_pattern:
        assert expected_error_pattern.lower() in error_msg.lower(), (
            f"{context}错误信息不包含期望模式 '{expected_error_pattern}'. "
            f"实际错误: {error_msg}"
        )


def assert_process_time_header(headers: Dict[str, str], max_time: float = 5.0, context: str = ""):
    """断言处理时间头存在且合理"""
    assert "x-process-time" in headers, f"{context}缺少 X-Process-Time 头"
    
    process_time = float(headers["x-process-time"])
    assert 0 <= process_time <= max_time, (
        f"{context}处理时间异常: {process_time}s (期望 0-{max_time}s)"
    )
