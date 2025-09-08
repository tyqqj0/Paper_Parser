#!/bin/bash

# Paper Parser 启动脚本

set -e

echo "🚀 启动 Paper Parser..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

# 检查是否存在.env文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，从示例文件创建..."
    cp env.example .env
    echo "✅ 已创建 .env 文件，请编辑配置后重新运行"
    exit 1
fi

# 构建镜像（如果需要）
echo "🔨 构建开发镜像..."
docker-compose build api-dev

# 启动基础服务
echo "🏃 启动基础服务 (Redis + Neo4j)..."
docker-compose up -d redis neo4j

# 等待服务启动
echo "⏳ 等待数据库服务启动..."
sleep 10

# 检查Redis连接
echo "🔍 检查 Redis 连接..."
docker-compose exec redis redis-cli ping || {
    echo "❌ Redis 连接失败"
    exit 1
}

# 检查Neo4j连接
echo "🔍 检查 Neo4j 连接..."
timeout=30
while [ $timeout -gt 0 ]; do
    if docker-compose exec neo4j cypher-shell -u neo4j -p password "RETURN 1" > /dev/null 2>&1; then
        break
    fi
    echo "等待 Neo4j 启动... ($timeout)"
    sleep 2
    timeout=$((timeout-2))
done

if [ $timeout -le 0 ]; then
    echo "❌ Neo4j 启动超时"
    exit 1
fi

# 启动API服务
echo "🚀 启动 API 服务..."
docker-compose --profile dev up -d api-dev

# 等待API服务启动
echo "⏳ 等待 API 服务启动..."
sleep 5

# 健康检查
echo "🔍 执行健康检查..."
timeout=30
while [ $timeout -gt 0 ]; do
    if curl -s http://localhost:8000/api/v1/health > /dev/null; then
        break
    fi
    echo "等待 API 服务启动... ($timeout)"
    sleep 2
    timeout=$((timeout-2))
done

if [ $timeout -le 0 ]; then
    echo "❌ API 服务启动超时"
    docker-compose logs api-dev
    exit 1
fi

echo ""
echo "✅ Paper Parser 启动成功！"
echo ""
echo "📋 服务地址:"
echo "  • API 文档:     http://localhost:8000/docs"
echo "  • 健康检查:     http://localhost:8000/api/v1/health"
echo "  • Neo4j 控制台: http://localhost:7474 (neo4j/password)"
echo ""
echo "🔧 管理命令:"
echo "  • 查看日志:     docker-compose logs -f"
echo "  • 停止服务:     docker-compose down"
echo "  • 重启服务:     docker-compose restart"
echo ""
echo "🧪 测试 API:"
echo "  curl http://localhost:8000/api/v1/health"
echo ""
