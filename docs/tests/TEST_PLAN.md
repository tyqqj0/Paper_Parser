### Paper Parser 测试系统设计（v1）

本文件定义测试目标、范围、结构、用例矩阵与落地方案，指导当前与下一阶段（缓存/别名/搜索优化、可观测性增强）的演进。

---

## 1. 总体目标
- **一致性（S2 parity）**：核心端点在字段与语义上与 S2 对齐；代理端点透明透传。
- **性能与缓存**：验证首访→热缓存→别名路径的延迟优化；关系数据切片命中。
- **稳定回归**：采用黄金样本/录制策略，控制与 S2 数据漂移的影响。
- **可选在线对比**：存在 `S2_API_KEY` 时进行 live 对比；否则仅跑确定性用例。
- **清晰报告**：命令行摘要 + HTML 报告，关键数据（差异、时延）可追溯。

---

## 2. 端点与行为范围

前缀：`settings.api_prefix`，默认 `\/api\/v1`。

- **核心 Paper API（`/paper`）**
  - `GET /paper/{paper_id:path}`：详情；`fields` 支持嵌套路径裁剪；严格 ID 策略（除 40 位 S2ID 以外均需前缀）。
  - `GET /paper/{paper_id:path}/citations`：顶层 `{total, offset, data}`；支持 `offset/limit` 与嵌套 `fields`。
  - `GET /paper/{paper_id:path}/references`：同上。
  - `POST /paper/batch`：请求体 `{ids, fields?}`；保序、<=500 条、缺失为 null。
  - `GET /paper/search`：`query, offset, limit, fields, year, venue, fields_of_study, match_title, prefer_local, fallback_to_s2`；返回 `{total, offset, papers}` 并兼容 `data`。
  - 缓存管理：`DELETE /paper/{id}/cache`，`POST /paper/{id}/cache/warm`。

- **代理 API（`/proxy`）**
  - `GET /paper/autocomplete`
  - `GET /paper/search`、`GET /paper/search/match`、`POST /paper/search/bulk`
  - `GET /author/{author_id}`、`GET /author/{author_id}/papers`
  - 行为：透传 S2 的 JSON（不包装），错误采用统一 `{ "error": "..." }` 格式（由全局异常处理）。

备注：`GET /paper/search` 已实现，且由 `core_paper_service.search_papers` 提供缓存与回退策略；代理端点为直通。

---

## 3. 测试维度与矩阵

- **形态与默认值（Shape & Defaults）**
  - 详情：无 `fields` 至少含 `paperId,title`；有 `fields` 时精确裁剪（含嵌套）。
  - 关系：`citations|references` 均返回 `{total, offset, data}`，并遵循 `offset/limit`；嵌套 `fields` 生效。
  - 搜索：返回 `{total, offset, papers}` 且包含兼容键 `data`；过滤项可用；空 `query` 400。
  - 批量：尊重 `fields`；<=500；结果与请求顺序一一对应；缺失为 `null`。
  - 代理：响应体与 S2 等价（字段级对比或形态断言）。

- **校验与错误映射（Validation & Errors）**
  - 严格 ID：非 40hex 必须显式前缀（`DOI:`, `ARXIV:` 等），否则 400。
  - 上游错误映射：404/429/408/502/401/503 等对齐。

- **性能与缓存（Perf & Caching）**
  - 首次 vs 二次：`X-Process-Time` 二次显著降低（如 <300ms 或 3x 改善）。
  - 别名路径：通过 `paperId` 首次获取后，`DOI:...`/`ARXIV:...` 命中更快。
  - 关系切片：full 视图已缓存时，`citations`/`references` 二次切片更快。
  - 缓存操作：`warm` 可降低首次访问延迟；`clear` 恢复冷启动特征。

- **在线对比（可选 Live Parity）**
  - 在 `S2_API_KEY` 存在时，对比核心端点与 `/proxy`（或直连 S2）的选定稳定字段。

- **边界与鲁棒性（Edge Cases）**
  - 复杂 `fields`：如 `citations.title,citations.authors.name`。
  - 大 `limit` 情况依旧保持形态正确与分页切片。
  - 响应体大小控制：测试用例避免请求巨大数据集（通过 `fields` 控制）。

---

## 4. 目录结构建议

```
tests/
  conftest.py                 # 全局 fixtures（app、client、开关、比较器等）
  helpers/
    assertions.py             # 形态/子集对比、延迟断言
    s2.py                     # 可选直连 S2 的小工具（仅 live 测试使用）
  data/
    goldens/                  # 黄金样本或录制
  unit/
    test_validators.py        # ID 校验与字段裁剪的小单元
  integration/
    test_paper_details.py
    test_paper_relations.py
    test_paper_search.py
    test_paper_batch.py
    test_cache_ops.py
  proxy/
    test_proxy_passthrough.py
  perf/
    test_latency_and_cache.py # 使用 X-Process-Time 做对比
  live/                       # 依赖 S2_API_KEY，默认 skip
    test_live_parity_vs_proxy.py
```

配置与运行：
- `pytest.ini`：定义 markers：`paper_details, paper_citations, paper_references, paper_search, paper_batch, cache, proxy, shape, parity, perf, live, e2e, integration, unit`。
- 可选 `pytest-html` 输出：`--html=report.html --self-contained-html`。

---

## 5. Fixtures 设计（关键）

- `event_loop`：`pytest-asyncio` 下的默认事件环。
- `app`：FastAPI 应用（加载 lifespan，真实中间件，真实路由）。
- `async_client`：基于 `httpx.AsyncClient`，`base_url` 指向 `settings.api_prefix`。
- `settings_overrides`：在测试中短 TTL、关闭强制关系抓取等；必要时通过 env 或 monkeypatch 设置。
- `s2_api_key`：读取环境，若不存在则给出 `pytest.skip` 的机制（仅 `live` 用例依赖）。
- `paper_id_fixture`：提供稳定的 S2 论文 id（如 `649def34f8be52c8b66281af98ae884c09aef38b`）。
- 可选替身：
  - `fakeredis`/stub：用于确定性缓存测试（集成层）；
  - stubbed `neo4j_client`/`s2_client`：在不连接真实服务时回放黄金样本。

---

## 6. 断言与比较器

- `assert_subset_keys(actual: dict, keys: set)`：判断包含必要键。
- `assert_subset_equal(actual: dict, expected: dict, fields: list[str])`：仅比对若干字段。
- `assert_latency_improves(t1: float, t2: float, *, factor: float = 3.0, absolute_ms: float = 300)`：校验时延优化。
- JSON 近似比较：对于顺序不保证的集合，改比大小与元素子集（或排序规则后再比对）。

---

## 7. 示例用例（节选）

形态：
```python
@pytest.mark.paper_details
@pytest.mark.shape
async def test_paper_details_default_shape(async_client, paper_id_fixture):
    r = await async_client.get(f"/api/v1/paper/{paper_id_fixture}")
    assert r.status_code == 200
    body = r.json()
    assert {"paperId", "title"} <= set(body.keys())
```

性能：
```python
@pytest.mark.paper_details
@pytest.mark.perf
async def test_first_vs_second_latency(async_client, paper_id_fixture):
    await async_client.delete(f"/api/v1/paper/{paper_id_fixture}/cache")
    r1 = await async_client.get(f"/api/v1/paper/{paper_id_fixture}")
    r2 = await async_client.get(f"/api/v1/paper/{paper_id_fixture}")
    t1 = float(r1.headers.get("X-Process-Time", "1"))
    t2 = float(r2.headers.get("X-Process-Time", "1"))
    assert t2 < t1 and t2 <= 0.3
```

在线对比（可选）：
```python
@pytest.mark.live
@pytest.mark.parity
async def test_details_live_parity_vs_proxy(async_client, paper_id_fixture, s2_api_key):
    fields = "title,url,year,authors"
    a = (await async_client.get(f"/api/v1/paper/{paper_id_fixture}", params={"fields": fields})).json()
    b = (await async_client.get(f"/api/v1/proxy/paper/{paper_id_fixture}", params={"fields": fields})).json()
    assert a.get("paperId") == b.get("paperId")
    for k in ["title", "url", "year", "authors"]:
        assert k in a and k in b
```

---

## 8. 运行方式

- 仅确定性用例：
  - `pytest -m "not live" -q --durations=20`
- 单独模块：
  - `pytest -m paper_search -q`
- 性能用例：
  - `pytest -m perf -q`
- 在线对比：
  - `export S2_API_KEY=... && pytest -m live -q`
- HTML 报告：
  - `pytest -m "not live" --html=report.html --self-contained-html`

---

## 9. 后续演进（为优化设计提供牵引）

- 完善“局部字段裁剪”的一致性测试（深层嵌套、关系字段缺失时返回空列表）。
- 引入缓存命中率与 Neo4j 落库延迟的观测采样（测试读取指标接口或日志采集）。
- 为超大被引量创建 ingest 计划后的后台任务测试桩与断言（状态节点存在、分页参数正确）。
- 扩展黄金样本覆盖不同 ID 形态（S2ID、DOI、ARXIV、PMID、URL）。
- 使用 VCR/录制避免 live 漂移，或对选择性字段进行快照比对。

---

## 10. 代码组织建议（避免“大文件”）

- 各端点/话题拆分到 `tests/integration/` 的多文件；
- 代理相关独立在 `tests/proxy/`；
- 性能关注点集中在 `tests/perf/`；
- 工具与比较器置于 `tests/helpers/`，避免重复代码；
- 黄金样本与数据在 `tests/data/`，保持测试代码精简；
- `conftest.py` 仅放通用 fixtures，不堆积逻辑；
- 标记（markers）驱动选择性执行，避免一次性跑全部。


