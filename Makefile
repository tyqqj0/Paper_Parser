# Paper Parser项目管理
.PHONY: help build up down start stop restart restart-api logs set-log-level clean clean-data clean-redis clean-neo4j status shell arq-logs backup-neo4j restore-neo4j backup-sqlite restore-sqlite

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
	@echo "  set-log-level - 修改日志等级（LEVEL=INFO/DEBUG/WARNING/ERROR）"
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
	@echo "  backup-neo4j   - 备份 Neo4j（冷备，生成 neo4j.dump 与带日期副本）"
	@echo "  restore-neo4j  - 恢复 Neo4j（可选 DUMP_FILE，缺省交互选择备份）"
	@echo "  backup-sqlite  - 备份 SQLite（冷备,fallback复制文件external_id_mapping.db）"
	@echo "  restore-sqlite - 恢复 SQLite（可选 DB_FILE，缺省交互选择备份）"

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
	docker compose restart api arq-worker

# 查看所有服务日志
logs:
	docker compose logs -f

# 修改 Compose 使用的日志等级（只写入 .env，不自动重启）
set-log-level:
	@[ -n "$(LEVEL)" ] || { echo "请提供 LEVEL=INFO/DEBUG/WARNING/ERROR"; exit 1; }
	@echo "设置日志等级为 $(LEVEL) 到 .env ..."
	@touch .env
	@grep -q '^LOG_LEVEL=' .env && sed -i 's/^LOG_LEVEL=.*/LOG_LEVEL=$(LEVEL)/' .env || echo "LOG_LEVEL=$(LEVEL)" >> .env
	@echo "完成。请手动重启：docker compose restart 或 make restart"

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

# 备份 Neo4j（冷备，短暂停机）
backup-neo4j:
	@echo "备份 Neo4j（冷备）..."
	@mkdir -p /home/zhihui/code/parser2/backups/neo4j
	@docker compose stop neo4j
	@docker run --rm \
		--volumes-from paper_parser_neo4j \
		-v /home/zhihui/code/parser2/backups/neo4j:/backups \
		neo4j:5 bash -lc "mkdir -p /backups && /var/lib/neo4j/bin/neo4j-admin database dump --to-path=/backups neo4j"
	@DATE=$$(date +%F_%H%M%S); cp -f /home/zhihui/code/parser2/backups/neo4j/neo4j.dump /home/zhihui/code/parser2/backups/neo4j/neo4j-$$DATE.dump
	@docker compose start neo4j
	@echo "Neo4j 冷备完成。"

# 恢复 Neo4j（从指定 dump 文件或交互选择）
restore-neo4j:
	@bash -lc 'set -euo pipefail; \
	BACKUP_DIR="/home/zhihui/code/parser2/backups/neo4j"; \
	SELECTED="$(DUMP_FILE)"; \
	if [ -z "$$SELECTED" ]; then \
		mapfile -t files < <(ls -1t "$$BACKUP_DIR"/*.dump 2>/dev/null || true); \
		if [ $${#files[@]} -eq 0 ]; then echo "未在 $$BACKUP_DIR 找到 *.dump 备份文件"; exit 1; fi; \
		echo "可用备份："; \
		for i in $${!files[@]}; do idx=$$((i+1)); printf "  %d) %s\n" "$$idx" "$${files[$$i]}"; done; \
		while :; do \
			read -p "输入序号 [1-$${#files[@]}] (默认1): " choice; \
			[ -z "$$choice" ] && choice=1; \
			if [[ "$$choice" =~ ^[0-9]+$$ ]] && [ "$$choice" -ge 1 ] && [ "$$choice" -le $${#files[@]} ]; then \
				SELECTED="$${files[$$((choice-1))]}"; break; \
			else echo "无效输入，请重试。"; fi; \
		done; \
	else \
		[ -f "$$SELECTED" ] || { echo "找不到文件 $$SELECTED"; exit 1; }; \
	fi; \
	echo "恢复 Neo4j 从 $$SELECTED..."; \
	mkdir -p "$$BACKUP_DIR"; \
	if [ "$$SELECTED" != "$$BACKUP_DIR/neo4j.dump" ]; then \
		cp -f "$$SELECTED" "$$BACKUP_DIR/neo4j.dump"; \
	else \
		echo "选择的文件已是目标路径，跳过复制。"; \
	fi; \
	docker compose stop neo4j; \
	docker run --rm --volumes-from paper_parser_neo4j -v "$$BACKUP_DIR":/backups \
		neo4j:5 bash -lc "mkdir -p /backups && rm -rf /data/databases/neo4j && /var/lib/neo4j/bin/neo4j-admin database load --from-path=/backups --overwrite-destination=true neo4j"; \
	docker compose start neo4j; \
	echo "Neo4j 恢复完成。"'

# 备份 SQLite（external_id_mapping.db）
backup-sqlite:
	@echo "备份 SQLite（external_id_mapping.db）..."
	@mkdir -p /home/zhihui/code/parser2/backups/sqlite
	@bash -lc 'set -euo pipefail; \
	docker compose stop api arq-worker; \
	BACKUP_DIR="/home/zhihui/code/parser2/backups/sqlite"; \
	SRC_DB="/home/zhihui/code/parser2/Paper_Parser/data/external_id_mapping.db"; \
	TS=$$(date +%F_%H%M%S); \
	if command -v sqlite3 >/dev/null 2>&1; then \
		sqlite3 "$$SRC_DB" ".backup '$$BACKUP_DIR/external_id_mapping-$$TS.db'"; \
	else \
		echo "未找到 sqlite3，直接复制数据库文件（请确保没有程序在写入该库）..."; \
		cp -f "$$SRC_DB" "$$BACKUP_DIR/external_id_mapping-$$TS.db"; \
	fi'
	docker compose start api arq-worker;
	@echo "SQLite 备份完成。"

# 恢复 SQLite（提供 DB_FILE 或交互选择）
restore-sqlite:
	@bash -lc 'set -euo pipefail; \
	docker compose stop api arq-worker; \
	BACKUP_DIR="/home/zhihui/code/parser2/backups/sqlite"; \
	TARGET_DB="/home/zhihui/code/parser2/Paper_Parser/data/external_id_mapping.db"; \
	SELECTED="$(DB_FILE)"; \
	if [ -z "$$SELECTED" ]; then \
		mapfile -t files < <(ls -1t "$$BACKUP_DIR"/external_id_mapping-*.db 2>/dev/null || ls -1t "$$BACKUP_DIR"/*.db 2>/dev/null || true); \
		if [ $${#files[@]} -eq 0 ]; then echo "未在 $$BACKUP_DIR 找到 *.db 备份文件"; exit 1; fi; \
		echo "可用备份："; \
		for i in $${!files[@]}; do idx=$$((i+1)); printf "  %d) %s\n" "$$idx" "$${files[$$i]}"; done; \
		while :; do \
			read -p "输入序号 [1-$${#files[@]}] (默认1): " choice; \
			[ -z "$$choice" ] && choice=1; \
			if [[ "$$choice" =~ ^[0-9]+$$ ]] && [ "$$choice" -ge 1 ] && [ "$$choice" -le $${#files[@]} ]; then \
				SELECTED="$${files[$$((choice-1))]}"; break; \
			else echo "无效输入，请重试。"; fi; \
		done; \
	else \
		[ -f "$$SELECTED" ] || { echo "找不到文件 $$SELECTED"; exit 1; }; \
	fi; \
	echo "恢复 SQLite 从 $$SELECTED..."; \
	cp -f "$$SELECTED" "$$TARGET_DB"; \
	docker compose start api arq-worker; \
	echo "SQLite 恢复完成。"'