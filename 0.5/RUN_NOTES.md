## 最近一次测试运行记录与结论

### 现象与结论
- perf 套件收集报错：`'paper_relations' not found in markers`。
  - 已修复：在 `pytest.ini` 增补 `paper_relations` 标记后，perf 能正常收集。

- 再次运行 perf：开始执行，但受上游 S2 速率限制/网络波动影响出现 429 等情况；此外，`test_paper_details_cold_vs_warm` 的阈值在本机网络下过于严格（缓存后 1.245s > 500ms 且改善倍率不足）。
  - 已做软化处理：对关键 perf 用例增加“若非 200 则跳过”的分支，避免因偶发 429/503 导致整套失败；阈值仍保持严格，仅在上游不可用时跳过。
  - 建议：配置 `S2_API_KEY` 可显著降低 429；或在低网速/高延迟环境下适当放宽 `assert_latency_improves` 的阈值（仅限本地非回归场景）。

- all（单元测试）“光速通过”：属正常。
  - 单元测试主要覆盖参数校验、字段解析等纯 CPU 逻辑，无外部 I/O，整体耗时极短是合理的。

### 如何启动 API 对齐（parity）测试
- 路径：`tests/live/test_live_parity_vs_proxy.py`
- 运行前设置环境变量：
```bash
export S2_API_KEY=your_key
pytest tests/live -v -s
# 或
S2_API_KEY=your_key ./scripts/test.sh live
```
- 覆盖：详情/搜索与 S2 直连、核心 vs 代理、关系（引用/参考文献）total 合理偏差、错误处理与新鲜度。

### 已做的测试系统修复/优化
- 在 `pytest.ini` 增补 `paper_relations` 标记，修复 perf 收集错误。
- 对 perf 用例追加上游不可用/被限流时的 `skip` 处理，使本地网络不稳定时不至于误报失败。

### 建议的后续改进
- 在 CI 环境默认跳过 perf（已在脚本中体现），本地需要时再跑。
- 若长期在无 `S2_API_KEY` 的环境下运行 perf，可进一步将阈值参数化（如通过环境变量）以适配不同网络。


