# 底座能力矩阵（稳定子集 / 实验态边界）

> 状态：生效中（与 `chiyu_kernel.api.MEMORY_EXPERIMENTAL = True` 同步）
> 日期：2026-10-08
> 目的：明确 foundation 对外承诺的**稳定子集**与**实验态边界**，供消费方（CRM / APS / enterprise）据此判断"哪些能力可写进硬验收判据、哪些不可"。
> 受众：三个消费方 + foundation 团队
> 仓边界：本文件只描述本仓（`chiyu-foundation`）能力；消费方文档只读、不回写。

---

## 0. 判定原则

- **稳定（Stable）**：已有测试守护、语义固定、可承诺 SLA 的能力。消费方可将其写入生产验收判据。
- **实验态（Experimental）**：状态登记为 `experimental` 的能力（当前仅 `evolution`）。**消费方不得把实验态能力写进硬验收判据，也不得在对客户/对外材料中宣称"已端到端跑通"**（见 §13 纪律与 `enterprise` 反馈 #4）。

> **memory 毕业更新（T44，2026-10-10）**：`memory` 已从 experimental 转 stable，`MEMORY_EXPERIMENTAL = False`。毕业依据是五件具体工程全部落地并有真库 E2E 守护（T40 双轨 PG 落库 / T41 召回接入 `run_spine` / T42 RRF 多源融合 / T43 真库 E2E 全链路 / T44 单源裁定守卫）——不是翻标志了事，而是"写了真被读"已有 `@pytest.mark.pg` 判据（`packages/chiyu-kernel/tests/test_memory_e2e.py`）。
>
> ⚠ **锚点漂移警示（R1 佐证）**：本文引用 `chiyu_kernel.api` 的行号锚点会随并发提交漂移（`MEMORY_EXPERIMENTAL` 2026-10-09 当日已从 `:419` 漂到 `:425`）。跨仓引用请用本文档+能力名，禁用 `file:line` 作契约（详见《CRM-建议逐项回顾.md》R1）。

---

## 1. 稳定子集（可承诺 SLA）

| 能力 | 模块 / 符号 | 说明 |
|---|---|---|
| 向量持久化 | `PgVectorStore` · `open_store` · `vec_to_pg` · `pad_to_dim` · `ddl_statements` · `vector_index_ddl` · `assert_no_free_jsonb` | PG + pgvector 单一事实源；`dim` 由 `TenantProfile.vector_dim` 注入（APS R2 已修） |
| 离线向量（零 torch） | `OnnxRunner` · `cosine` · `content_hash` · `compute_coverage` · `backfill_plan` | 本地 ONNX 推理 + 覆盖度回放 |
| 本体 / 粒子 | `OntologyGraph` · `Particle` · `normalize` · `ensure_embedding` · `ensure_tsvector` · `ontology_sync` · `BackfillChannel` | 写时三钩子 + 受控关系图 |
| 情境与降级召回 | `assemble` · `degraded_recall` · `check_supply_demand` · `build_knowledge_needs` | L1–L4 装配 + 三级降级语义 |
| 决策脊柱（L2） | `run_spine` · `SpineResult` · `score_rubric` · `evaluate_redline` · `RedlineVerdict` · `autonomous_release` · `aggregate_confidence` · `validate_spine_order` · `SPINE_ORDER` | S1→S5 顺序契约单一事实源；`aggregate_confidence` 已入门面（APS R1 已修） |
| 契约 / 配置载体 | `TenantProfile` · `RedlineSpec` · `MEMORY_PREDICATES` · `VECTOR_DIM` · `CORE_ROLES` | L0 零领域字面量；7 记忆谓词 schema 已定义（`source="engine"`） |
| 场景包 / 决策场景注册表 | `ScenarioPack` · `from_dict` · `register_scenario` · `require_scenario` · `set_key_format` · `key_format`（WS5） | 场景包双入口共用写闸；决策场景键单一事实源。⚠ 2026-10-09 双方核验更正：~~「根治 CRM 三态键分裂」~~ 作废——CRM 侧 `config_change` 与 `config-change` **语义不同必须共存**（`CRM-ai-native/docs` 及《CRM-建议逐项回顾.md》实证）；键格式闸**可插拨**（`kebab` 默认 / `none` 供跨语言消费方命名族），**禁止按字符串规范化判重** |
| 质量 / 契约守卫 | `test_api_facade_covers_all_layers` · `tools/check_facade_coverage.py` · `tools/check_zero_residue.py`（WS4） | 门面完整性 + §13 零残留 lint，已接入 `make lint` |

---

## 1b. 图算子支持矩阵（CRM R4 · 2026-10-09 增补）

> 依据 `chiyu_kernel/graph/__init__.py`（WS8 只读派生面）真值，一行不超过现有实现。

| 算子 | `GraphStore` 协议 | `InMemoryGraphStore`（:131） | `PgCteGraphStore`（:194） | 限制 / 语义 |
|---|---|---|---|---|
| `controlled()` 受控谓词集 | 抽象 | ✅ | ✅ | 谓词来自 `profile.predicates` 注入；请求未受控谓词 ⇒ **抛**（不静默返空） |
| `out_edges(node, predicates?)` | 抽象 | ✅ | ✅ | 一跳出边，按谓词过滤 |
| `in_edges(node, predicates?)` | 抽象 | ✅ | ✅ | 一跳入边，按谓词过滤 |
| `traverse(start, predicates?, hops?, ...)` | 抽象 | ✅ | ✅ | 多跳遍历；**深度上限 `MAX_TRAVERSAL_HOPS=3`**（:44），环检测，触及上限置 `truncated=True`（:84，不谎称全量） |
| `relation_view(store, root, ...)` | ✅（派生函数 :306） | ✅ | ✅ | 关系图谱视图（一/二跳邻域 + 路径） |
| `timeline_view(...)` | ✅（派生函数 :329） | ✅ | ✅ | 四源只读聚合、按决策时间基准排序 |
| `decision_backlinks(store, decision_id, ...)` | ✅（派生函数 :367） | ✅ | ✅ | 决策回链（审计：被谁引用 / 覆盖谁 / 源自哪条例外） |
| **写方法**（建点和边） | ❌ **协议不暴露**（:13） | ❌ | ❌ | 写边一律走 `persist.write_decision_memory_net` / `ontology.OntologyGraph`；否则单源退化为双写 |
| 最短路径 / 社区发现 / 图算法 | ❌ | ❌ | ❌ | 未实现、未承诺（CRM 评估 AGE→CTE 边界时按此判断） |

**结论**：该面覆盖「受控边多跳遍历 / 邻域 / 路径 / 回链」；**不具备通用图算法**。跨仓引用请用
`capability_id=graph`（manifest 已收录）。

---

## 1c. 失败语义默认（CRM R6 · 2026-10-09 增补成文）

> 统一纪律：**输入非法 ⇒ fail-closed；依赖不可用 ⇒ fail-open 但必须留痕；结果受限 ⇒ 显式受限标记**。

| 场景 | 默认语义 | 依据（现有实现） |
|---|---|---|
| 键非法 / 重复登记 / I/O 契约非法（注册表） | **fail-closed**：抛 `ScenarioRegistryError` | `scenario/registry.py` 六道注册闸 |
| 未注册键首调 | **fail-closed**：抛 `ValueError` | `registry.py:226 require_scenario` |
| 请求未受控图谓词 | **fail-closed**：抛（有界谓词） | `graph/__init__.py:19` |
| 遍历触及深度上限 | **fail-open + 受限标记**：返回 `truncated=True`，禁用"已全量"表述 | `TraversalResult.truncated`（:84） |
| 决策 I/O 缺供给 | **fail-open 降级**：`DecisionIOField.required=False` ⇒ 允许降级路径 | `registry.py:62` |
| 情境召回降级 | **fail-open + 留痕**：三级降级语义 | `assemble` / `degraded_recall`（L1–L4） |
| 向量维度不符 | **必须显式报错 + trace 留痕**（禁静默 NULL / 禁用 L1） | CRM 侧 A3 对齐目标；底座侧以 `pad_to_dim` / `assert_no_free_jsonb` 为写闸参考，消费方禁止静默写 NULL |

---

## 2. 实验态与近期毕业对照（更新于 T44，2026-10-10）

| 能力 | 状态 | 备注 |
|---|---|---|
| memory 内核运行时 | **已毕业转 stable（T40–T44）** | 运行时在树内：`persist/memory_tracks.py`（双轨）+ `persist/pg_memory_stores.py`（PG 落库）+ `context/recall_memory.py`（召回）+ `context/fuse.py`（RRF）；真库 E2E 守护 |
| 决策↔记忆↔知识谓词物化闭环 | **已接线（T40–T43）** | 7 谓词经 `write_decision_memory_net` 落真 PG，`test_memory_e2e.py` 验证写了真被读 |
| 决策持久化标准 persister | 已 ship | `PgVectorStorePersister`（`persist` 层）；原"计划中"条目已过时，随本表更新 |
| 注入式 ApprovalGate | 已 ship（S4 钩子形态） | `run_spine(redline_callback=...)`（T10）；三态语义见 decision 层 |
| evolution | 仍 experimental | 未验收，不得写硬判据 |

---

## 3. 对外表述纪律（§13）

- 提及"决策记忆网 / 双轨记忆闭环"时：T44（2026-10-10）起 memory 为 **stable**，可写进生产验收判据；仍须如实注明其判据面（真库 E2E `test_memory_e2e.py` + 单源裁定守卫），不得虚构超出判据面的能力（如分层召回调优、跨会话记忆迁移等未实现项）。
- `grep` 全仓不得出现词表 `tools/zero_residue.tokens` 中所列的"…已落地"类越权表述（命中即非零残留；由 `tools/check_zero_residue.py` 在 `docs ppt` 展示页层拦截；词表条目见该文件，此处不转录以免自触发）。

---

## 4. 收口路线（与 `2026-10-08-foundation-consumability-design.md` 对齐）

- Phase 1（已启动）：WS5 决策场景注册表 · WS4 门面守卫模板 + §13 lint · 本文档（WS1）。
- Phase 2：WS2 标准 persister + 记忆网 writer · WS3 注入式 ApprovalGate · WS6 领域注入 SDK。
- Phase 3：WS8 图存储抽象 · WS7 MCP 服务骨架 · WS9 参考消费层。
- 上述 Phase 2/3 能力在各自收口并补测试前，**不在稳定子集内**。
