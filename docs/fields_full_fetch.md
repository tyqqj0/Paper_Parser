## 全量抓取与按需裁剪（fields）设计

本文档描述在获取论文数据时，默认进行“全量抓取 + 分段缓存 + 按需裁剪返回”的架构设计，并对高引用/参考文献的分页抓取与缓存合并进行增强，确保：
- 首次代价换后续低延迟：首次对某篇论文触发抓取时尽可能完整，一次性或分段获取全量数据；后续请求直接命中 Redis/Neo4j，fields 仅做返回层过滤。
- 可扩展的分页策略：对 citations/references 数量很大的论文，采用分页增量合并策略，避免超大 payload 与上游限流风险。
- 多级缓存一致：Redis 作为热缓存，Neo4j 作为持久化缓存；两者以“全量数据”为主，fields 仅用于“返回视图”裁剪，不影响存储内容。

### 1. 术语与目标
- 全量抓取（Full Fetch）：对于论文主体字段与适度规模的关系字段，尽可能获得完整数据。
- 分段缓存（Segmented Caching）：对 citations/references 这类可分页数据，分批抓取并在缓存层合并，提供“完整视图”。
- 按需裁剪（On-demand Projection）：用户传入 `fields` 仅影响最终返回的字段子集，不触发上游按字段过滤请求（除非明确设置退化模式）。

### 2. 数据流总览
1) API 层（`app/api/v1/paper.py`）
   - 接收 `paper_id` 与 `fields`（可选）。
   - 始终请求服务层“完整视图”（不依赖 `fields`）。
   - 将 `fields` 仅用于“响应裁剪”。

2) 服务层（`CorePaperService`）
   - 读取 Redis：优先命中 `paper:{paper_id}:full`（主体 + 已合并的关系段）。
   - 未命中 → 查询 Neo4j：若新鲜则回填 Redis。
   - 缺失或过期 → 触发上游抓取：
     - 主体：一次性抓取完整主体字段（CORE + EXTENDED + AUTHOR）。
     - 关系：按阈值分页抓取 `citations` 与 `references`，逐页合并到 Redis，并在完成或达到上限后异步持久化 Neo4j。
   - 最终在服务层形成“完整视图”，再交由 API 层根据 `fields` 裁剪返回。

3) 存储层
   - Redis：
     - 主体缓存键：`paper:{paper_id}:full:meta`（主体/扩展/作者等合并体）
     - 关系段缓存键：`paper:{paper_id}:citations:page:{n}`、`paper:{paper_id}:references:page:{n}`
     - 合并视图键：`paper:{paper_id}:full:relations`（已合并的 citations/references 列表 + total/next 等元信息）
   - Neo4j：
     - 存全量主体与关系（节点边），作为持久化来源；用于后续回填 Redis。

### 3. 分页增强策略
- 触发条件：当 `citationCount` 或 `referenceCount` 超过阈值（如 200）时，采用分页抓取。
- 抓取流程：
  1. 先抓主体（不包含大列表），确定计数与可分页信息。
  2. 以固定 `page_size`（如 100/200）逐页抓取 citations/references。
  3. 每页写入 Redis 分段键，并持续维护一个合并视图（按 `paperId` 去重）。
  4. 当达到期望页数或抓取完成时，生成完整关系列表视图，合并到 `paper:{paper_id}:full:relations`。
  5. 异步写入 Neo4j（节点与边）。
- 幂等与恢复：
  - 使用 `paper:{paper_id}:relations:progress` 记录已抓取进度，可断点续抓。
  - 定期校验 `total` 与已抓取数量差异，必要时补抓。

### 4. fields 的自动裁剪
- 约定：
  - 存储层（Redis/Neo4j）尽量保存全量字段；
  - `fields` 仅用于“返回层投影”，不改变缓存的完整性。
- 实现：
  - 在 `CorePaperService._format_response(data, fields)` 中扩展：
    - 支持嵌套字段（如 `authors.name`, `citations.title`），按路径裁剪。
    - 未请求的字段不包含在返回数据里。
- 好处：
  - 上游请求次数减少（一次抓全，后续裁剪），命中率高。
  - 避免多版本缓存键膨胀（不再为每种 fields 组合构建不同键）。

### 5. Redis/Neo4j 读写策略
- 读取顺序：`Redis(full)` → `Neo4j(full)` → `S2(full)`。
- 写入策略：
  - 主体：获取后立即写 `paper:{paper_id}:full:meta`。
  - 关系：分页逐步写 `page` 键，并维护合并视图；完成后将合并视图与主体合并为 `paper:{paper_id}:full`。
  - 持久化：主体获取成功即触发 Neo4j `merge_paper`；关系抓取每 N 页或完成时批量 merge。

### 6. 需要的代码改动点（概览）
1) `CorePaperService.get_paper`：
   - 改为只查/写 `paper:{paper_id}:full`（与 relations 合并后的完整视图）。
   - fields 只用于 `_format_response`。

2) `CorePaperService._fetch_from_s2`：
   - 拆分为：`_fetch_paper_body_full` 与 `_fetch_relations_segmented`。
   - 主体一次抓全（CORE+EXTENDED+AUTHOR）。
   - 关系按阈值分页抓取，合并去重，维护进度，最终合流。

3) `CorePaperService._format_response`：
   - 支持嵌套字段路径裁剪（authors.name / citations.title 等）。

4) Redis 客户端：
   - 新增分段写入/读取 API：`set_relation_page/get_relation_page/merge_relations_view`。
   - 新增进度键读写：`set_fetch_progress/get_fetch_progress`。

5) Neo4j 客户端：
   - 新增批量 merge 边接口，支持分页流式写入。

6) S2 客户端：
   - 新增按页获取 citations/references 的方法（若已有则复用），并支持速率限制与重试。

### 7. 伪代码（关键流程）
```python
async def get_paper(paper_id, fields=None):
    full_key = f"paper:{paper_id}:full"
    cached = await redis.get(full_key)
    if cached: return project(cached, fields)

    db = await neo4j.get_paper_full(paper_id)
    if db and is_fresh(db):
        await redis.set(full_key, db, ttl)
        return project(db, fields)

    body = await _fetch_paper_body_full(paper_id)
    await redis.set(f"{full_key}:meta", body, ttl)

    if large_relations(body):
        await _fetch_relations_segmented(paper_id)
    else:
        rels = await s2.get_relations_all(paper_id)
        await redis.set(f"{full_key}:relations", rels, ttl)

    full = merge(body, await redis.get(f"{full_key}:relations"))
    await redis.set(full_key, full, ttl)
    asyncio.create_task(neo4j.merge_paper(full))
    return project(full, fields)
```

### 8. 回退与兼容
- 若需要保留“按 fields 精准上游请求”的能力，可通过开关 `settings.fetch_mode = 'full' | 'by_fields'` 控制：
  - default 为 `full`；
  - `by_fields` 模式仅在特殊场景（带宽/速率极紧）启用。

### 9. 运维与观察性
- 为 `get_paper` 增加指标：
  - 命中类型（redis/neo4j/s2）、抓取页数、合并耗时、返回大小、投影复杂度。
- 关键日志：分页抓取开始/结束、进度、重试与回退。

---
以上设计兼顾吞吐、延迟、与上游配额的平衡：对单篇论文以“首抓尽量完整、后续按需裁剪”的模式运行，同时对超大关系数据采用分页增量合并，从而提升整体体验与稳定性。


