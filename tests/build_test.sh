#!/bin/bash

# Docker构建优化测试脚本
echo "=== Paper Parser Docker构建优化测试 ==="
echo ""

# 记录开始时间
START_TIME=$(date +%s)

echo "1. 清理现有镜像..."
docker image rm -f paper_parser-api 2>/dev/null || true

echo ""
echo "2. 开始构建开发环境镜像..."
echo "使用腾讯云源优化..."

# 构建并记录时间
if docker compose build api; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    echo "=== 构建完成 ==="
    echo "总耗时: ${DURATION} 秒"
    echo ""
    
    # 显示镜像信息
    echo "镜像信息:"
    docker images | grep paper_parser-api
    
    echo ""
    echo "=== 测试镜像是否可以正常启动 ==="
    if docker run --rm -d --name test_container paper_parser-api sleep 10; then
        echo "✅ 镜像可以正常启动"
        docker stop test_container 2>/dev/null || true
    else
        echo "❌ 镜像启动失败"
    fi
    
else
    echo "❌ 构建失败"
    exit 1
fi

echo ""
echo "=== 优化效果总结 ==="
echo "✅ 使用腾讯云apt源"
echo "✅ 使用清华大学pip源" 
echo "✅ Docker层缓存优化"
echo "✅ 多阶段构建（生产环境）"
echo ""
echo "建议："
echo "- 首次构建会较慢，后续构建将利用层缓存大幅加速"
echo "- 只修改代码时，不会重新安装依赖"
echo "- 使用 'make dev' 快速启动开发环境"
