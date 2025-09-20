# Paper Parser项目管理
.PHONY: help build up down start stop restart restart-api logs clean clean-data clean-redis clean-neo4j status shell arq-logs

# 默认目标
help:
	@echo "Paper Parser 项目管理命令："
	@echo ""
	@echo "  build      - 构建所有Docker镜像"
	@echo "  up/start   - 启动完整服务（API + Redis + Neo4j + ARQ Worker）"
	@echo "  down/stop  - 停止所有服务"
	@echo "  restart    - 重启所有服务"
	@echo "  restart-api - 仅重启API服务"
	@echo "  infra      - 仅启动基础服务 (Redis + Neo4j)"
	@echo "  logs       - 查看所有服务日志"
	@echo "  arq-logs   - 查看ARQ Worker日志"
	@echo "  status     - 查看服务状态"
	@echo "  shell      - 进入API容器"
	@echo "  clean      - 清理未使用的镜像和容器"
	@echo "  clean-data - 清除Neo4j和Redis的持久化数据"
	@echo "  clean-redis - 仅清除Redis的持久化数据"
	@echo "  clean-neo4j - 仅清除Neo4j的持久化数据"
	@echo "  rebuild    - 强制重新构建镜像"
	@echo "  schema-migrate - 运行一次性Neo4j模式迁移（索引/约束）"
	@echo "  schema-check   - 检查Neo4j索引/约束是否到位"
	@echo "  pre-deploy     - 仅启动基础设施并执行Schema迁移"

# 构建镜像
build:
	@echo "构建Docker镜像..."
	docker compose build

# 强制重新构建
rebuild:
	@echo "强制重新构建Docker镜像..."
	docker compose build --no-cache

# 启动完整服务（包含ARQ Worker）
up start:
	@echo "启动完整服务（API + Redis + Neo4j + ARQ Worker）..."
	docker compose up -d

# 仅启动基础服务
infra:
	@echo "启动基础服务 (Redis + Neo4j)..."
	docker compose up -d redis neo4j

# 一次性运行：Neo4j Schema 迁移（索引/约束）
schema-migrate:
	@echo "执行 Neo4j Schema 迁移（索引/约束）..."
	@echo "如果Neo4j未就绪，此命令会自动重试连接。"
	docker compose run --rm api python -m migration_scripts.schema_migrate

# 检查：验证索引/约束是否存在，缺失将返回非零退出码
schema-check:
	@echo "检查 Neo4j 索引/约束..."
	docker compose run --rm api python -m migration_scripts.schema_check

# 预部署：仅启动基础设施并执行Schema迁移（不启动API/Worker）
pre-deploy: infra schema-migrate
	@echo "预部署完成：基础设施已就绪且Schema已迁移"

# 停止所有服务
down stop:
	@echo "停止所有服务..."
	docker compose down

# 重启服务
restart: down up

# 仅重启API服务
restart-api:
	@echo "重启API服务..."
	docker compose restart api

# 查看所有服务日志
logs:
	docker compose logs -f

# 查看ARQ Worker日志
arq-logs:
	docker compose logs -f arq-worker

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

# 清理Neo4j和Redis数据
clean-data:
	@echo "警告：此操作将永久删除Neo4j和Redis的所有数据！"
	@read -p "确认继续？(y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "停止所有服务..."
	docker compose down
	@echo "删除Neo4j和Redis数据卷..."
	docker volume rm paper_parser_redis_data paper_parser_neo4j_data paper_parser_neo4j_logs 2>/dev/null || true
	@echo "数据清理完成！"

# 仅清理Redis数据
clean-redis:
	@echo "警告：此操作将永久删除Redis的所有数据！"
	@read -p "确认继续？(y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "停止Redis服务..."
	docker compose stop redis
	@echo "删除Redis数据卷..."
	docker volume rm paper_parser_redis_data 2>/dev/null || true
	@echo "Redis数据清理完成！"

# 仅清理Neo4j数据
clean-neo4j:
	@echo "警告：此操作将永久删除Neo4j的所有数据！"
	@read -p "确认继续？(y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "停止Neo4j服务..."
	docker compose stop neo4j
	@echo "删除Neo4j数据卷..."
	docker volume rm paper_parser_neo4j_data paper_parser_neo4j_logs 2>/dev/null || true
	@echo "Neo4j数据清理完成！"

# 快速部署（构建并启动）
deploy: build up
	@echo "部署完成！"
	@echo "API服务: http://localhost:8000"
	@echo "Neo4j控制台: http://localhost:7474"
	@echo "查看所有日志: make logs"
	@echo "查看ARQ日志: make arq-logs"