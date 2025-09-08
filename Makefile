# Paper Parser项目管理
.PHONY: help build up down start stop restart logs clean status shell

# 默认目标
help:
	@echo "Paper Parser 项目管理命令："
	@echo ""
	@echo "  build      - 构建所有Docker镜像"
	@echo "  up/start   - 启动完整服务（API + Redis + Neo4j + Celery）"
	@echo "  down/stop  - 停止所有服务"
	@echo "  restart    - 重启所有服务"
	@echo "  infra      - 仅启动基础服务 (Redis + Neo4j)"
	@echo "  logs       - 查看服务日志"
	@echo "  status     - 查看服务状态"
	@echo "  shell      - 进入API容器"
	@echo "  clean      - 清理未使用的镜像和容器"
	@echo "  rebuild    - 强制重新构建镜像"

# 构建镜像
build:
	@echo "构建Docker镜像..."
	docker compose build

# 强制重新构建
rebuild:
	@echo "强制重新构建Docker镜像..."
	docker compose build --no-cache

# 启动完整服务
up start:
	@echo "启动完整服务..."
	docker compose up -d

# 仅启动基础服务
infra:
	@echo "启动基础服务 (Redis + Neo4j)..."
	docker compose up -d redis neo4j

# 停止所有服务
down stop:
	@echo "停止所有服务..."
	docker compose down

# 重启服务
restart: down up

# 查看日志
logs:
	docker compose logs -f

# 查看服务状态
status:
	@echo "服务状态："
	docker compose ps

# 进入API容器
shell:
	docker exec -it paper_parser_api /bin/bash

# 清理系统
clean:
	@echo "清理未使用的镜像和容器..."
	docker system prune -f
	docker image prune -f

# 快速部署（构建并启动）
deploy: build up
	@echo "部署完成！"
	@echo "API服务: http://localhost:8000"
	@echo "查看日志: make logs"