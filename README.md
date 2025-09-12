# Paper Parser

基于 Semantic Scholar API 的学术论文缓存和代理服务。

## 🎯 项目概述

Paper Parser 采用"核心缓存 + 其他转发"的策略，对热门 API 进行深度优化，其他 API 直接代理转发。系统实现三级缓存架构，提供毫秒级响应速度。

### ✨ 主要特性

- **高性能**：三级缓存架构 (Redis + Neo4j + S2 API)
- **高可用**：异步处理，不阻塞用户请求  
- **完全兼容**：对外 API 完全兼容 Semantic Scholar
- **渐进式**：核心功能先行，逐步扩展

## 🏗️ 架构设计

```
┌─────────────────────────────────────────┐
│             API Gateway Layer            │
│         (FastAPI Router)                │
├─────────────────────────────────────────┤
│             Service Layer                │
│   CorePaperService | ProxyService       │
├─────────────────────────────────────────┤
│           Data Access Layer             │
│   Redis | Neo4j | S2 API Client        │
└─────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Docker & Docker Compose
- Make (可选)

### 1. 克隆项目

```bash
git clone <repository-url>
cd Paper_Parser
```

### 2. 配置环境

```bash
# 复制环境配置文件
cp env.example .env

# 编辑配置文件，设置你的 Semantic Scholar API Key
vim .env
```

### 3. 启动服务

使用 Make（推荐）：

```bash
# 启动基础开发环境
make dev-up

# 或启动完整环境（包含 Celery）
make dev-full
```

或使用 Docker Compose：

```bash
# 启动基础环境
docker-compose --profile dev up -d

# 启动完整环境（包含 Celery）
docker-compose --profile dev --profile celery up -d

# 启动 ARQ 轻量队列（可选，与 Celery 并行或替代）
docker-compose --profile arq up -d arq-worker
```

### 4. 验证服务

访问以下地址验证服务：

- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/v1/health
- **Neo4j 控制台**: http://localhost:7474 (neo4j/password)
- **Celery 监控**: http://localhost:5555 (如果启用)
- **ARQ Worker**: 使用 `docker-compose --profile arq up -d arq-worker` 启动

## 📚 API 使用示例

### 核心 API（缓存优化）

```bash
# 获取论文详情
curl "http://localhost:8000/api/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b"

# 搜索论文
curl "http://localhost:8000/api/v1/paper/search?query=machine learning&limit=10"

# 获取引用文献
curl "http://localhost:8000/api/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations"

# 批量获取论文
curl -X POST "http://localhost:8000/api/v1/paper/batch" \
  -H "Content-Type: application/json" \
  -d '{"ids": ["649def34f8be52c8b66281af98ae884c09aef38b", "another-paper-id"]}'
```

### 代理 API（直接转发）

```bash
# 获取作者信息
curl "http://localhost:8000/api/v1/proxy/author/1741101"

# 论文自动补全
curl "http://localhost:8000/api/v1/proxy/paper/autocomplete?query=neural network"
```

## 🛠️ 开发命令

```bash
# 查看所有可用命令
make help

# 启动开发环境
make dev-up

# 查看日志
make dev-logs

# 停止服务
make dev-down

# 运行测试
make test

# 代码格式化
make format

# 代码检查
make lint

# 重置数据库
make reset-db
```

## 📊 性能指标

### 响应时间目标

- **缓存命中 (Redis)**: < 10ms
- **持久化命中 (Neo4j)**: < 50ms  
- **S2 API调用**: < 3000ms
- **批量查询 (10篇)**: < 500ms
- **搜索查询**: < 200ms

### 缓存命中率目标

- **热门论文**: > 95%
- **一般论文**: > 70%
- **搜索结果**: > 60%

## 🔧 配置说明

主要配置项（在 `.env` 文件中）：

```env
# Semantic Scholar API
S2_API_KEY=your-api-key-here
S2_RATE_LIMIT=100

# Redis 缓存
REDIS_URL=redis://localhost:6379/0
REDIS_DEFAULT_TTL=3600

# Neo4j 数据库
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# 应用配置
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# 搜索后台入库（命中缓存时后台刷新Top N条）
ENABLE_SEARCH_BACKGROUND_INGEST=true
SEARCH_BACKGROUND_INGEST_TOP_N=3
```

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_core_service.py -v

# 生成覆盖率报告
pytest --cov=app tests/
```

## 📝 项目结构

```
Paper_Parser/
├── app/
│   ├── api/v1/          # API 路由
│   ├── clients/         # 外部客户端
│   ├── core/            # 核心配置
│   ├── models/          # 数据模型
│   ├── services/        # 业务逻辑
│   ├── tasks/           # 异步任务
│   └── main.py          # 应用入口
├── docs/                # 文档
├── tests/               # 测试
├── docker-compose.yml   # Docker 配置
├── requirements.txt     # Python 依赖
└── Makefile            # 开发命令
```

## 🚦 部署

### 生产环境部署

1. 构建生产镜像：
```bash
docker build -f Dockerfile.prod -t paper-parser:latest .
```

2. 使用生产配置启动：
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 环境变量

生产环境需要设置的关键环境变量：

```env
DEBUG=false
S2_API_KEY=your-production-api-key
REDIS_URL=redis://your-redis-host:6379/0
NEO4J_URI=bolt://your-neo4j-host:7687
```

## 🤝 贡献

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

- **文档**: [Architecture.md](docs/architecture.md)
- **问题报告**: [GitHub Issues](https://github.com/your-org/paper-parser/issues)
- **讨论**: [GitHub Discussions](https://github.com/your-org/paper-parser/discussions)

---

**Paper Parser** - 让学术研究更高效 🚀
