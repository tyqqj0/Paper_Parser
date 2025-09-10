#!/bin/bash

# Paper Parser 测试运行脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数定义
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# 检查依赖
check_dependencies() {
    print_header "检查依赖"
    
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python 未安装"
        exit 1
    fi
    
    # 检测Python命令
    PYTHON_CMD="python3"
    if ! command -v python3 &> /dev/null; then
        PYTHON_CMD="python"
    fi
    
    if ! $PYTHON_CMD -m pytest --version &> /dev/null; then
        print_error "pytest 未安装，请运行: pip install pytest pytest-asyncio httpx"
        exit 1
    fi
    
    print_success "依赖检查通过"
}

# 运行单元测试
run_unit_tests() {
    print_header "运行单元测试"
    $PYTHON_CMD -m pytest tests/unit/ -v --tb=short
    print_success "单元测试完成"
}

# 运行集成测试
run_integration_tests() {
    print_header "运行集成测试"
    $PYTHON_CMD -m pytest tests/integration/ -v --tb=short -x
    print_success "集成测试完成"
}

# 运行代理测试
run_proxy_tests() {
    print_header "运行代理测试"
    $PYTHON_CMD -m pytest tests/proxy/ -v --tb=short
    print_success "代理测试完成"
}

# 运行性能测试
run_performance_tests() {
    print_header "运行性能测试"
    $PYTHON_CMD -m pytest tests/perf/ -v --tb=short -s
    print_success "性能测试完成"
}

# 运行在线对比测试
run_live_tests() {
    print_header "运行在线对比测试"
    
    if [ -z "$S2_API_KEY" ]; then
        print_warning "S2_API_KEY 未设置，跳过在线对比测试"
        print_warning "设置方法: export S2_API_KEY=your_api_key"
        return 0
    fi
    
    print_success "检测到 S2_API_KEY，运行在线对比测试"
    $PYTHON_CMD -m pytest tests/live/ -v --tb=short -s
    print_success "在线对比测试完成"
}

# 生成HTML报告
generate_html_report() {
    print_header "生成HTML测试报告"
    
    if $PYTHON_CMD -c "import pytest_html" &> /dev/null; then
        $PYTHON_CMD -m pytest tests/ -m "not live" --html=test_report.html --self-contained-html --tb=short
        print_success "HTML报告已生成: test_report.html"
    else
        print_warning "pytest-html 未安装，跳过HTML报告生成"
        print_warning "安装方法: pip install pytest-html"
    fi
}

# 显示使用帮助
show_help() {
    echo "Paper Parser 测试脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  all           运行所有测试（不包括在线测试）"
    echo "  unit          仅运行单元测试"
    echo "  integration   仅运行集成测试"
    echo "  proxy         仅运行代理测试"
    echo "  perf          仅运行性能测试"
    echo "  live          仅运行在线对比测试（需要S2_API_KEY）"
    echo "  html          生成HTML测试报告"
    echo "  quick         快速测试（单元+基本集成）"
    echo "  ci            CI模式（所有测试除了在线测试）"
    echo "  help          显示此帮助信息"
    echo ""
    echo "环境变量:"
    echo "  S2_API_KEY    Semantic Scholar API Key（在线测试需要）"
    echo ""
    echo "示例:"
    echo "  $0 all                    # 运行所有测试"
    echo "  $0 quick                  # 快速测试"
    echo "  S2_API_KEY=xxx $0 live    # 运行在线测试"
}

# 快速测试
run_quick_tests() {
    print_header "快速测试模式"
    run_unit_tests
    $PYTHON_CMD -m pytest tests/integration/test_paper_details.py -v --tb=short
    print_success "快速测试完成"
}

# CI模式
run_ci_tests() {
    print_header "CI测试模式"
    check_dependencies
    run_unit_tests
    run_integration_tests
    run_proxy_tests
    # 跳过性能测试和在线测试（CI环境可能不稳定）
    print_success "CI测试完成"
}

# 主逻辑
main() {
    case "${1:-help}" in
        "all")
            check_dependencies
            run_unit_tests
            run_integration_tests
            run_proxy_tests
            run_performance_tests
            ;;
        "unit")
            check_dependencies
            run_unit_tests
            ;;
        "integration")
            check_dependencies
            run_integration_tests
            ;;
        "proxy")
            check_dependencies
            run_proxy_tests
            ;;
        "perf")
            check_dependencies
            run_performance_tests
            ;;
        "live")
            check_dependencies
            run_live_tests
            ;;
        "html")
            check_dependencies
            generate_html_report
            ;;
        "quick")
            check_dependencies
            run_quick_tests
            ;;
        "ci")
            run_ci_tests
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# 运行主函数
main "$@"
