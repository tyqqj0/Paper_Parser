#!/bin/bash
# 端到端测试脚本
# 测试Paper Parser系统的完整功能

set -e  # 遇到错误立即退出

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

# 配置
API_BASE_URL="http://localhost:8000"
TEST_TIMEOUT=60
COMPOSE_FILE="docker-compose.yml"

# 清理函数
cleanup() {
    log_info "清理测试环境..."
    docker compose down --volumes --remove-orphans 2>/dev/null || true
    docker system prune -f 2>/dev/null || true
}

# 错误处理
handle_error() {
    log_error "测试失败，开始清理..."
    cleanup
    exit 1
}

# 设置错误处理
trap handle_error ERR

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log_error "curl未安装"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_warning "jq未安装，JSON响应将不会格式化"
    fi
    
    log_success "依赖检查完成"
}

# 构建和启动服务
start_services() {
    log_info "构建和启动服务..."
    
    # 清理旧容器
    cleanup
    
    # 构建镜像
    log_info "构建Docker镜像..."
    docker compose build --no-cache
    
    # 启动服务
    log_info "启动服务..."
    docker compose up -d
    
    log_success "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_info "尝试连接API服务 (${attempt}/${max_attempts})"
        
        if curl -s --connect-timeout 5 "${API_BASE_URL}/health" >/dev/null 2>&1; then
            log_success "API服务已就绪"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "API服务启动超时"
            docker compose logs api
            exit 1
        fi
        
        sleep 2
        ((attempt++))
    done
    
    # 等待数据库服务
    log_info "等待数据库服务就绪..."
    sleep 10
    
    log_success "所有服务已就绪"
}

# API测试函数
test_api() {
    local endpoint=$1
    local method=${2:-GET}
    local data=${3:-}
    local expected_status=${4:-200}
    
    log_info "测试 ${method} ${endpoint}"
    
    local curl_cmd="curl -s -w '%{http_code}' -X ${method}"
    
    if [ -n "$data" ]; then
        curl_cmd="${curl_cmd} -H 'Content-Type: application/json' -d '${data}'"
    fi
    
    local response=$(eval "${curl_cmd} ${API_BASE_URL}${endpoint}")
    local status_code=${response: -3}
    local body=${response%???}
    
    if [ "$status_code" != "$expected_status" ]; then
        log_error "API测试失败: ${endpoint} 返回状态码 ${status_code}，期望 ${expected_status}"
        echo "响应体: $body"
        return 1
    fi
    
    log_success "API测试通过: ${endpoint}"
    
    # 如果安装了jq，格式化JSON响应
    if command -v jq &> /dev/null && [ -n "$body" ]; then
        echo "$body" | jq . 2>/dev/null || echo "$body"
    else
        echo "$body"
    fi
    
    return 0
}

# 运行API测试
run_api_tests() {
    log_info "开始API测试..."
    
    # 健康检查
    test_api "/health"
    
    # 根路径
    test_api "/"
    
    # API文档
    test_api "/docs" "GET" "" "200"
    
    # OpenAPI规范
    test_api "/openapi.json"
    
    # 论文搜索测试
    log_info "测试论文搜索功能..."
    test_api "/api/v1/papers/search?query=machine%20learning&limit=5"
    
    # 论文详情测试（使用一个常见的论文ID）
    log_info "测试论文详情功能..."
    test_api "/api/v1/papers/649def34f8be52c8b66281af98df2819f6e85b4f"
    
    # 相关论文推荐测试
    log_info "测试相关论文推荐..."
    test_api "/api/v1/papers/649def34f8be52c8b66281af98df2819f6e85b4f/related?limit=3"
    
    # 统计信息测试
    log_info "测试统计信息..."
    test_api "/api/v1/stats"
    
    log_success "API测试完成"
}

# 数据库连接测试
test_database_connections() {
    log_info "测试数据库连接..."
    
    # 检查Neo4j连接
    log_info "检查Neo4j连接..."
    docker compose exec -T neo4j cypher-shell -u neo4j -p password "RETURN 'Neo4j connection OK' as status;" || {
        log_warning "Neo4j连接测试失败，可能需要更多时间启动"
    }
    
    # 检查Redis连接
    log_info "检查Redis连接..."
    docker compose exec -T redis redis-cli ping || {
        log_warning "Redis连接测试失败"
    }
    
    log_success "数据库连接测试完成"
}

# 性能测试
run_performance_tests() {
    log_info "运行性能测试..."
    
    # 并发请求测试
    log_info "测试并发请求性能..."
    
    local concurrent_requests=10
    local pids=()
    
    for i in $(seq 1 $concurrent_requests); do
        curl -s "${API_BASE_URL}/health" >/dev/null &
        pids+=($!)
    done
    
    # 等待所有请求完成
    for pid in "${pids[@]}"; do
        wait $pid
    done
    
    log_success "并发请求测试完成"
}

# 容器健康检查
check_container_health() {
    log_info "检查容器健康状态..."
    
    # 获取所有服务状态
    local services=$(docker compose ps --services)
    
    for service in $services; do
        local status=$(docker compose ps $service --format "{{.State}}")
        if [ "$status" != "running" ]; then
            log_warning "服务 $service 状态异常: $status"
            docker compose logs --tail=20 $service
        else
            log_success "服务 $service 运行正常"
        fi
    done
}

# 日志检查
check_logs() {
    log_info "检查应用日志..."
    
    # 检查API服务日志中的错误
    local error_count=$(docker compose logs api 2>/dev/null | grep -i error | wc -l)
    
    if [ $error_count -gt 0 ]; then
        log_warning "发现 $error_count 个错误日志"
        docker compose logs api | grep -i error | tail -5
    else
        log_success "未发现错误日志"
    fi
}

# 生成测试报告
generate_report() {
    log_info "生成测试报告..."
    
    local report_file="e2e_test_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "Paper Parser 端到端测试报告"
        echo "================================"
        echo "测试时间: $(date)"
        echo "测试环境: Docker Compose"
        echo ""
        echo "服务状态:"
        docker compose ps
        echo ""
        echo "容器资源使用:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
        echo ""
        echo "最近日志:"
        docker compose logs --tail=20 api
    } > "$report_file"
    
    log_success "测试报告已生成: $report_file"
}

# 主函数
main() {
    log_info "开始Paper Parser端到端测试"
    echo "========================================"
    
    # 检查依赖
    check_dependencies
    
    # 启动服务
    start_services
    
    # 等待服务就绪
    wait_for_services
    
    # 检查容器健康
    check_container_health
    
    # 测试数据库连接
    test_database_connections
    
    # 运行API测试
    run_api_tests
    
    # 运行性能测试
    run_performance_tests
    
    # 检查日志
    check_logs
    
    # 生成报告
    generate_report
    
    log_success "所有测试完成！"
    echo "========================================"
    
    # 询问是否保持服务运行
    echo ""
    read -p "是否保持服务运行以便手动测试？(y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        cleanup
        log_info "服务已停止"
    else
        log_info "服务继续运行，可通过以下地址访问："
        log_info "API文档: ${API_BASE_URL}/docs"
        log_info "健康检查: ${API_BASE_URL}/health"
        log_info "要停止服务，请运行: docker compose down"
    fi
}

# 如果脚本被直接执行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
