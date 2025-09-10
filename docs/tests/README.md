# Paper Parser 测试系统

本文档描述 Paper Parser 项目的测试系统架构、运行方式和最佳实践。

## 📁 目录结构

```
tests/
├── conftest.py                 # 全局 fixtures 和配置
├── helpers/
│   ├── assertions.py           # 断言工具和比较器
│   └── s2.py                   # S2 直连工具（在线测试用）
├── data/
│   └── goldens/               # 黄金样本数据
├── unit/
│   └── test_validators.py     # ID校验和参数验证单元测试
├── integration/
│   ├── test_paper_details.py  # 论文详情集成测试
│   ├── test_paper_relations.py# 引用和参考文献测试
│   ├── test_paper_search.py   # 搜索功能测试
│   ├── test_paper_batch.py    # 批量获取测试
│   └── test_cache_ops.py      # 缓存操作测试
├── proxy/
│   └── test_proxy_passthrough.py # 代理端点测试
├── perf/
│   └── test_latency_and_cache.py # 性能和缓存测试
└── live/
    └── test_live_parity_vs_proxy.py # 在线对比测试
```

## 🎯 测试目标

### 1. 一致性（S2 Parity）
- 核心端点在字段与语义上与 Semantic Scholar API 对齐
- 代理端点透明透传，保持 S2 原始响应格式
- 错误处理与状态码映射正确

### 2. 性能与缓存
- 验证首访→热缓存→别名路径的延迟优化
- 关系数据切片命中测试
- 缓存预热和清除功能验证

### 3. 稳定回归
- 采用黄金样本/录制策略，控制与 S2 数据漂移的影响
- 可选在线对比，存在 `S2_API_KEY` 时进行 live 对比
- 确定性用例不依赖外部服务

## 🏷️ 测试标记（Markers）

### 端点类别
- `paper_details`: 论文详情相关测试
- `paper_citations`: 论文引用相关测试
- `paper_references`: 论文参考文献相关测试
- `paper_search`: 论文搜索相关测试
- `paper_batch`: 论文批量获取相关测试
- `cache`: 缓存操作相关测试
- `proxy`: 代理端点相关测试

### 测试类型
- `shape`: 响应结构和字段测试
- `parity`: 与S2 API对比测试
- `perf`: 性能和延迟测试
- `live`: 需要真实S2 API Key的在线测试
- `e2e`: 端到端集成测试
- `integration`: 集成测试
- `unit`: 单元测试

### 特殊标记
- `slow`: 运行时间较长的测试
- `flaky`: 可能不稳定的测试（通常是网络相关）

## 🚀 运行测试

### 使用测试脚本（推荐）

```bash
# 显示帮助
./scripts/test.sh help

# 运行所有测试（不包括在线测试）
./scripts/test.sh all

# 快速测试（单元测试 + 基本集成测试）
./scripts/test.sh quick

# 仅运行单元测试
./scripts/test.sh unit

# 仅运行集成测试
./scripts/test.sh integration

# 运行性能测试
./scripts/test.sh perf

# 运行在线对比测试（需要 S2_API_KEY）
export S2_API_KEY=your_api_key_here
./scripts/test.sh live

# 生成HTML报告
./scripts/test.sh html

# CI模式（适合持续集成）
./scripts/test.sh ci
```

### 使用 pytest 直接运行

```bash
# 安装依赖
pip install pytest pytest-asyncio httpx pytest-html

# 运行所有确定性测试
pytest -m "not live" -q --durations=20

# 按标记运行
pytest -m paper_search -v
pytest -m perf -v
pytest -m "shape and not live" -v

# 运行特定文件
pytest tests/integration/test_paper_details.py -v

# 生成HTML报告
pytest tests/ -m "not live" --html=report.html --self-contained-html

# 在线对比测试
export S2_API_KEY=your_api_key_here
pytest -m live -v
```

## 🔧 配置和环境

### 环境变量

- `S2_API_KEY`: Semantic Scholar API Key，在线测试必需
- `API_HOST`: API服务主机，默认 `0.0.0.0`
- `API_PORT`: API服务端口，默认 `8000`
- `REDIS_URL`: Redis连接URL，默认 `redis://localhost:6379/0`
- `NEO4J_URI`: Neo4j连接URI，默认 `bolt://localhost:7687`

### 测试数据

测试使用以下稳定的数据：

- **测试论文ID**: `649def34f8be52c8b66281af98ae884c09aef38b` (Attention Is All You Need)
- **测试DOI**: `10.1038/nature14539`
- **测试ArXiv**: `1705.10311`
- **搜索查询**: `"attention is all you need"`

## 📊 断言工具

### 基本断言
- `assert_subset_keys()`: 检查字典包含必要键
- `assert_paper_basic_fields()`: 验证论文基本字段
- `assert_pagination_response()`: 验证分页响应格式

### 性能断言
- `assert_latency_improves()`: 验证延迟改善
- `assert_process_time_header()`: 检查处理时间头

### 兼容性断言
- `assert_s2_api_compatibility()`: S2 API兼容性检查
- `assert_fields_filtering_works()`: 字段过滤功能验证

## 🎭 测试场景

### 形态测试（Shape Tests）
- 响应结构正确性
- 字段类型和约束
- 分页格式一致性
- 错误响应格式

### 性能测试（Performance Tests）
- 冷启动 vs 热缓存延迟对比
- 别名路径性能
- 并发请求处理
- 批量 vs 单独请求效率

### 在线对比测试（Live Parity Tests）
- 核心API vs S2直连对比
- 核心API vs 代理API对比
- 数据新鲜度验证
- 错误处理一致性

### 缓存测试（Cache Tests）
- 缓存命中率验证
- 预热和清除功能
- 缓存一致性检查
- 别名缓存路径

## 📈 测试报告

### 命令行输出
- 简洁的成功/失败摘要
- 性能改善比例显示
- 关键数据差异报告

### HTML报告
```bash
pytest tests/ --html=report.html --self-contained-html
```
包含：
- 详细的测试结果
- 失败用例堆栈跟踪
- 执行时间统计
- 覆盖率信息（如果启用）

## 🔍 调试和故障排除

### 常见问题

1. **Redis连接失败**
   ```bash
   # 启动Redis
   docker run -d -p 6379:6379 redis:alpine
   ```

2. **Neo4j连接失败**
   ```bash
   # 启动Neo4j
   docker run -d -p 7687:7687 -p 7474:7474 \
     -e NEO4J_AUTH=neo4j/password neo4j:latest
   ```

3. **在线测试失败**
   - 检查 `S2_API_KEY` 是否设置
   - 验证网络连接
   - 检查API配额限制

### 调试技巧

```bash
# 详细输出
pytest tests/integration/test_paper_details.py -v -s

# 只运行失败的测试
pytest --lf

# 在第一个失败时停止
pytest -x

# 显示最慢的10个测试
pytest --durations=10

# 显示警告
pytest -v --tb=short --disable-warnings
```

## 🔄 持续集成

### GitHub Actions 示例

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:alpine
        ports:
          - 6379:6379
      neo4j:
        image: neo4j:latest
        env:
          NEO4J_AUTH: neo4j/password
        ports:
          - 7687:7687
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx pytest-html
      - name: Run tests
        run: ./scripts/test.sh ci
      - name: Upload test report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-report
          path: test_report.html
```

## 📝 最佳实践

### 编写测试
1. **使用描述性的测试名称**
2. **保持测试独立性**，不依赖其他测试的状态
3. **使用适当的标记**，便于分类执行
4. **添加有意义的断言消息**
5. **处理异步操作**，正确使用 `pytest-asyncio`

### 维护测试
1. **定期更新黄金样本**
2. **监控性能回归**
3. **保持测试数据的稳定性**
4. **及时修复flaky测试**

### 性能考虑
1. **使用缓存清理**确保性能测试公平
2. **避免在单个测试中请求大量数据**
3. **合理设置超时时间**
4. **监控测试执行时间趋势**

## 🤝 贡献指南

添加新测试时：

1. **选择合适的目录**（unit/integration/proxy/perf/live）
2. **添加适当的标记**
3. **更新相关文档**
4. **确保测试稳定性**
5. **考虑性能影响**

修改现有测试时：

1. **保持向后兼容性**
2. **更新相关断言**
3. **验证所有相关测试通过**
4. **更新文档说明**
