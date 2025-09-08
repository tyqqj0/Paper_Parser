#!/bin/bash
# 快速测试脚本 - 用于快速验证系统基本功能

set -e

echo "🚀 开始快速测试..."

# 构建和启动
echo "📦 构建和启动服务..."
docker compose down --volumes --remove-orphans 2>/dev/null || true
docker compose build --parallel
docker compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 15

# 基本健康检查
echo "🔍 健康检查..."
curl -f http://localhost:8000/health || { echo "❌ 健康检查失败"; exit 1; }
echo "✅ 健康检查通过"

# 测试API文档
echo "📚 测试API文档..."
curl -f http://localhost:8000/docs > /dev/null || { echo "❌ API文档访问失败"; exit 1; }
echo "✅ API文档正常"

# 测试论文搜索
echo "🔍 测试论文搜索..."
curl -f "http://localhost:8000/api/v1/papers/search?query=machine%20learning&limit=3" > /dev/null || { echo "❌ 论文搜索失败"; exit 1; }
echo "✅ 论文搜索正常"

echo "🎉 快速测试完成！"
echo "💡 要运行完整测试，请执行: ./tests/e2e_test.sh"
echo "🌐 API文档地址: http://localhost:8000/docs"
