#!/bin/bash
# Paper Parser 健康检查脚本
# 用于快速验证服务是否正常运行

set -e

# 配置
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TIMEOUT="${TIMEOUT:-10}"
VERBOSE="${VERBOSE:-false}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查函数
check_endpoint() {
    local endpoint="$1"
    local description="$2"
    local expected_status="${3:-200}"
    
    if [ "$VERBOSE" = "true" ]; then
        log_info "检查 $description: $BASE_URL$endpoint"
    fi
    
    local response=$(curl -s -o /tmp/health_response.json -w "%{http_code}" --connect-timeout $TIMEOUT "$BASE_URL$endpoint" || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        log_success "$description: HTTP $response"
        return 0
    else
        log_error "$description: HTTP $response (期望: $expected_status)"
        if [ "$VERBOSE" = "true" ] && [ -f /tmp/health_response.json ]; then
            echo "响应内容:"
            cat /tmp/health_response.json | head -c 500
            echo
        fi
        return 1
    fi
}

check_json_response() {
    local endpoint="$1"
    local description="$2"
    local success_field="$3"
    
    if [ "$VERBOSE" = "true" ]; then
        log_info "检查 $description JSON响应: $BASE_URL$endpoint"
    fi
    
    local http_code=$(curl -s -o /tmp/health_json.json -w "%{http_code}" --connect-timeout $TIMEOUT "$BASE_URL$endpoint" || echo "000")
    
    if [ "$http_code" != "200" ]; then
        log_error "$description: HTTP $http_code"
        return 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_warning "jq未安装，跳过JSON验证"
        log_success "$description: HTTP $http_code (JSON未验证)"
        return 0
    fi
    
    local success_value=$(jq -r ".$success_field" /tmp/health_json.json 2>/dev/null || echo "null")
    
    if [ "$success_value" = "true" ]; then
        log_success "$description: HTTP $http_code, $success_field=true"
        return 0
    else
        log_error "$description: HTTP $http_code, $success_field=$success_value"
        if [ "$VERBOSE" = "true" ]; then
            echo "响应内容:"
            cat /tmp/health_json.json | jq . 2>/dev/null || cat /tmp/health_json.json
        fi
        return 1
    fi
}

# 主检查流程
main() {
    echo "🏥 Paper Parser 健康检查"
    echo "目标服务: $BASE_URL"
    echo "超时设置: ${TIMEOUT}秒"
    echo "=" * 50
    
    local failed_checks=0
    local total_checks=0
    
    # 1. 根路径检查
    total_checks=$((total_checks + 1))
    if ! check_json_response "/" "根路径" "success"; then
        failed_checks=$((failed_checks + 1))
    fi
    
    # 2. 基础健康检查
    total_checks=$((total_checks + 1))
    if ! check_endpoint "/api/v1/health" "基础健康检查"; then
        failed_checks=$((failed_checks + 1))
    fi
    
    # 3. 详细健康检查
    total_checks=$((total_checks + 1))
    if ! check_json_response "/api/v1/health/detailed" "详细健康检查" "success"; then
        failed_checks=$((failed_checks + 1))
    fi
    
    # 4. API功能快速测试
    total_checks=$((total_checks + 1))
    if ! check_json_response "/api/v1/paper/search?query=test&limit=1" "搜索API" "success"; then
        failed_checks=$((failed_checks + 1))
    fi
    
    echo "=" * 50
    
    # 生成报告
    local success_checks=$((total_checks - failed_checks))
    local success_rate=$((success_checks * 100 / total_checks))
    
    echo "📊 健康检查结果:"
    echo "   总检查项: $total_checks"
    echo "   ✅ 通过: $success_checks"
    echo "   ❌ 失败: $failed_checks"
    echo "   🎯 成功率: $success_rate%"
    
    if [ $failed_checks -eq 0 ]; then
        log_success "所有健康检查通过！服务运行正常。"
        echo "🎉 系统状态: 健康"
        return 0
    elif [ $success_rate -ge 75 ]; then
        log_warning "大部分检查通过，但存在一些问题。"
        echo "⚠️  系统状态: 部分异常"
        return 1
    else
        log_error "多项检查失败，服务可能存在严重问题。"
        echo "❌ 系统状态: 异常"
        return 2
    fi
}

# 清理临时文件
cleanup() {
    rm -f /tmp/health_response.json /tmp/health_json.json
}

# 设置清理陷阱
trap cleanup EXIT

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            BASE_URL="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo "选项:"
            echo "  -u, --url URL        服务地址 (默认: http://127.0.0.1:8000)"
            echo "  -t, --timeout SEC    超时时间 (默认: 10秒)"
            echo "  -v, --verbose        详细输出"
            echo "  -h, --help           显示帮助"
            echo ""
            echo "环境变量:"
            echo "  BASE_URL             服务地址"
            echo "  TIMEOUT              超时时间"
            echo "  VERBOSE              详细输出 (true/false)"
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            echo "使用 $0 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 运行主检查
main
