## Paper Parser 测试系统速览

本页快速说明测试分类、如何运行、常见问题与在线对齐测试的开启方式。适合日常开发“抄作业”。

### 测试分类
- **单元测试 (unit)**: 纯参数与校验逻辑等快速校验，独立于外部服务。
- **集成测试 (integration)**: 覆盖核心 API 端点形态与错误映射，使用本地客户端。
- **代理测试 (proxy)**: 覆盖 `/proxy/*` 直通端点的基本可用性与误差容忍。
- **性能测试 (perf)**: 冷/热缓存、批量 vs 单独、并发与字段过滤等延迟指标（依赖 `x-process-time` 响应头）。
- **在线对比 (live, parity)**: 需设置 `S2_API_KEY`，与 S2 直连或代理进行结果/结构对比。

对应 pytest 标记（`pytest.ini` 已注册）：
- 端点类: `paper_details`, `paper_citations`, `paper_references`, `paper_search`, `paper_batch`, `cache`, `proxy`, `paper_relations`
- 类型类: `unit`, `integration`, `perf`, `live`, `parity`, `e2e`, `slow`, `flaky`

### 如何运行
项目提供脚本 `scripts/test.sh`（推荐）：

```bash
# 全量（除 live）：unit + integration + proxy + perf
./scripts/test.sh all

# 仅单元
./scripts/test.sh unit

# 仅集成
./scripts/test.sh integration

# 仅代理
./scripts/test.sh proxy

# 仅性能（会打印性能信息）
./scripts/test.sh perf

# 在线对比（需 S2_API_KEY）
S2_API_KEY=your_key ./scripts/test.sh live

# 生成 HTML 报告（需 pytest-html）
./scripts/test.sh html

# 快速健康检查（unit + 基本集成）
./scripts/test.sh quick

# CI 模式（不跑 perf/live）
./scripts/test.sh ci
```

也可直接使用 pytest：
```bash
# 示例：只跑性能并打印输出
pytest tests/perf -v -s

# 只跑 live 对齐
S2_API_KEY=xxx pytest tests/live -v -s
```

### 在线对齐测试如何开启
在线对比位于 `tests/live/`，需提供环境变量 `S2_API_KEY`：
```bash
export S2_API_KEY=your_api_key
pytest tests/live -v -s
# 或
S2_API_KEY=your_api_key ./scripts/test.sh live
```
覆盖范围：
- 详情与搜索：核心 API vs S2 直连、核心 vs 代理
- 关系（引用/参考文献）：结构与 total 的合理偏差校验
- 错误处理与数据新鲜度：404/速率限制、引用计数差异提示

### 常见问题与排查
- **“光速全过”的单元测试是正常的吗？**
  - 单元测试集中于参数校验与解析，执行路径短、无外部 I/O，通常在数百毫秒内完成，是正常现象。

- **性能测试收集错误：`'xxx' not found in markers`**
  - 需在 `pytest.ini` 的 `markers` 段登记标记。例：缺少 `paper_relations` 时加入：
    ```ini
    paper_relations: Paper关系查询相关测试
    ```

- **如何跑 API 对齐测试？**
  - 设置 `S2_API_KEY` 后运行 `./scripts/test.sh live` 或 `pytest tests/live -v -s`。

- **HTML 报告生成失败**
  - 安装依赖：`pip install pytest-html`。

- **环境变量未生效**
  - 在同一 shell 导出或在命令前内联：`S2_API_KEY=xxx ./scripts/test.sh live`。

### 期望行为（核查点）
- 响应结构：详情对象；关系/搜索为 `{total, offset, data}`（搜索兼容 `papers` 键）。
- 性能：热缓存显著快于冷启动；批量优于或不劣于多次单独请求；字段过滤不应极端退化；并发时间差在合理范围。
- 错误映射：与 `core_paper_service` 的 `ErrorCodes` 一致（404/429/408/502/401/503）。

### 备注
- 运行 `perf`/`live` 可能访问外部网络或更耗时，建议本机网络稳定时执行。
- 若你新增了测试标记，请同步更新 `pytest.ini` 的 `markers` 段，避免收集错误。


