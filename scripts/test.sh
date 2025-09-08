#!/bin/bash

# Paper Parser 测试脚本

set -e

echo "🧪 运行 Paper Parser 测试..."

# 确保在项目根目录
cd "$(dirname "$0")/.."

# 检查服务是否运行
if ! curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "❌ API 服务未运行，请先启动服务"
    echo "运行: ./scripts/start.sh"
    exit 1
fi

echo "✅ API 服务运行正常"

# 测试基础端点
echo ""
echo "🔍 测试基础端点..."

echo "测试根路径..."
curl -s http://localhost:8000/ | jq '.success' || echo "❌ 根路径测试失败"

echo "测试健康检查..."
curl -s http://localhost:8000/api/v1/health | jq '.success' || echo "❌ 健康检查失败"

echo "测试详细健康检查..."
curl -s http://localhost:8000/api/v1/health/detailed | jq '.data.status' || echo "❌ 详细健康检查失败"

# 测试核心API（需要S2 API Key）
echo ""
echo "🔍 测试核心API..."

# 使用一个已知存在的论文ID
PAPER_ID="649def34f8be52c8b66281af98ae884c09aef38b"

echo "测试论文详情获取..."
response=$(curl -s -w "%{http_code}" http://localhost:8000/api/v1/paper/$PAPER_ID)
http_code="${response: -3}"
if [ "$http_code" = "200" ]; then
    echo "✅ 论文详情获取成功"
elif [ "$http_code" = "500" ]; then
    echo "⚠️  论文详情获取失败 (可能需要配置S2 API Key)"
else
    echo "❌ 论文详情获取失败，状态码: $http_code"
fi

echo "测试搜索功能..."
response=$(curl -s -w "%{http_code}" "http://localhost:8000/api/v1/paper/search?query=machine%20learning&limit=5")
http_code="${response: -3}"
if [ "$http_code" = "200" ]; then
    echo "✅ 搜索功能正常"
elif [ "$http_code" = "500" ]; then
    echo "⚠️  搜索功能失败 (可能需要配置S2 API Key)"
else
    echo "❌ 搜索功能失败，状态码: $http_code"
fi

# 测试批量API
echo "测试批量获取..."
response=$(curl -s -w "%{http_code}" -X POST http://localhost:8000/api/v1/paper/batch \
    -H "Content-Type: application/json" \
    -d "{\"ids\": [\"$PAPER_ID\"], \"fields\": \"paperId,title\"}")
http_code="${response: -3}"
if [ "$http_code" = "200" ]; then
    echo "✅ 批量获取正常"
elif [ "$http_code" = "500" ]; then
    echo "⚠️  批量获取失败 (可能需要配置S2 API Key)"
else
    echo "❌ 批量获取失败，状态码: $http_code"
fi

# 测试代理API
echo ""
echo "🔍 测试代理API..."

echo "测试作者信息获取..."
response=$(curl -s -w "%{http_code}" http://localhost:8000/api/v1/proxy/author/1741101)
http_code="${response: -3}"
if [ "$http_code" = "200" ]; then
    echo "✅ 代理API正常"
elif [ "$http_code" = "500" ]; then
    echo "⚠️  代理API失败 (可能需要配置S2 API Key)"
else
    echo "❌ 代理API失败，状态码: $http_code"
fi

# 运行单元测试
echo ""
echo "🧪 运行单元测试..."
if command -v pytest > /dev/null; then
    pytest tests/test_basic.py -v
else
    echo "⚠️  pytest 未安装，跳过单元测试"
fi

echo ""
echo "✅ 测试完成！"
echo ""
echo "💡 提示:"
echo "  • 如果看到 S2 API Key 相关错误，请在 .env 文件中配置 S2_API_KEY"
echo "  • 查看详细日志: docker-compose logs -f api-dev"
echo ""
