# Paper Parser Makefile

.PHONY: help dev-up dev-down dev-logs install test lint format clean

# 默认目标
help:
	@echo "Paper Parser 开发命令:"
	@echo "  dev-up      - 启动开发环境 (API + Redis + Neo4j)"
	@echo "  dev-full    - 启动完整开发环境 (包含Celery)"
	@echo "  dev-down    - 停止开发环境"
	@echo "  dev-logs    - 查看服务日志"
	@echo "  install     - 安装Python依赖"
	@echo "  test        - 运行测试"
	@echo "  lint        - 代码检查"
	@echo "  format      - 代码格式化"
	@echo "  clean       - 清理缓存和临时文件"

# 启动基础开发环境
dev-up:
	docker-compose --profile dev up -d

# 启动完整开发环境
dev-full:
	docker-compose --profile dev --profile celery --profile monitoring up -d

# 停止开发环境
dev-down:
	docker-compose down

# 查看日志
dev-logs:
	docker-compose logs -f

# 安装依赖
install:
	pip install -r requirements.txt

# 运行测试
test:
	pytest tests/ -v

# 代码检查
lint:
	mypy app/
	isort --check-only app/
	black --check app/

# 代码格式化
format:
	isort app/
	black app/

# 清理
clean:
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	docker system prune -f

# 重置数据库
reset-db:
	docker-compose down -v
	docker-compose --profile dev up -d

# 查看服务状态
status:
	docker-compose ps
