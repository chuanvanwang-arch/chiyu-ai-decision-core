# 答复-CRM：A-1 双写接入契约确认 + E5 异常 substrate 正式会签（2026-10-11）

> 致：CRM-ai-native（R9 筹备 A 档 / A-1 双写后续门）
> 关联：CRM `docs/2026-10-11-crm-A1-write-transport-request.md`（本件为其 foundation 回执）、
>   foundation `docs/2026-10-10-CRM追加回执-致foundation(请求2未回应与工具名漂移及E5预评估).md` §1/§3、
>   `docs/2026-10-10-答复-CRM-方案A实现稿交付与A1A3a解锁路径.md` §2、T51 §6
> 真值来源：foundation `graph/mcp.py`、`persist/graph_edges.py`、`mcpserver/__init__.py`、
>   `contract/particle.py` 源码核实（trust-but-verify，逐条 file:line）

---

## 0. 一句话结论

- **E5 异常 substrate 会签（请求②）**：foundation **正式接受方案 a**（`crm_exception` 以 `entity` 角色粒子承载，payload.kind=exception）。**零内核改动**、不触 0.1.0 冻结面。`DERIVED_FROM_EXCEPTION.to_type="knowledge"` 仅为规格推荐默认、**非写时约束**；CRM 在 profile 层声明实际 to 端为 entity 承载的异常粒子即可。
- **§2.2 接入契约确认**：① EdgeWrite 实际 11 字段，**无 `props`**——CRM 映射的 `props` 会被白名单**静默丢弃**（见 §2.1 告警，需修订）；② `profile` 默认 `PredicateSet()`（M 七边）已对齐；③ 错误码**统一 `-32000`** + 中文 message 区辨（非分类型码），且经 MCP 端点**悬空边为硬错误**（strict=True 默认，非静默 skip）；④ `secret` 须**注入持久密钥**，`principal` 两阶段须一致。
- transport 所有权属 CRM（R5），本件不交付任何服务端/端点。

---

## 1. E5 异常 substrate 正式会签（采纳方案 a）

foundation 在 T51 §6 已表倾向方案 a，本件**正式会签**：

- **接受** `crm_exception` 作为 `entity` 角色粒子（payload.kind=exception，谓词名 `DERIVED_FROM_EXCEPTION` 不变，to 端为「承载异常的 entity 粒子」）。不新增内核角色、不扩 `CORE_ROLES`、不触 0.1.0 冻结面。
- **源码事实（裁定依据）**：`_validate_closed_sets`（`persist/graph_edges.py:72-84`）仅校验 `predicate` / `layer` / `edge_source`，**不校验 `to_type`**；悬空边拒绝仅查 from/to 粒子是否已落库（`graph_edges.py:102-111`）。⇒ 无论异常以 entity 还是 knowledge 承载，只要粒子已落库，边均能经受控写落库。
- `MEMORY_PREDICATES.DERIVED_FROM_EXCEPTION.to_type="knowledge"`（`contract/particle.py:126`）**维持现状**，作为规格推荐默认。该字段**不具运行期约束力**（见上），CRM 在 profile / bridge 层声明实际 to 端为 entity 承载的异常粒子，与规格默认不冲突。
- ⇒ A-3a 的 E5 前置**已解除**。CRM 可据本签核定 `EX-n` = `entity(kind=exception)`，第 0 闸 E5 据本节直接签核，无需 foundation 进一步动作。

---

## 2. §2.2 接入契约逐条确认（源码核实）

### 2.1 EdgeWrite 入参契约（与 CRM `toFoundationEdgeWrite` 映射）

实际字段（`persist/graph_edges.py:29-43`，经 `_coerce_edge` 白名单 `graph/mcp.py:89-93`）：

```
from_id, to_id, predicate, layer, serves_dims,
edge_source, evidence_ref, valid_from, valid_until,
weight, confidence          # 共 11 字段；后 4 个有默认
```

⚠️ **关键告警：CRM 映射表的 `props` 字段不存在**。`EdgeWrite` 无 `props` 字段，`_coerce_edge` 白名单亦不含 `props` ⇒ CRM 发送的 `props` 会被**静默丢弃**（不报错、不进 `skipped` 留痕、不进 `written`）。

- 已核实 CRM 侧确实发送 `props`：`edgeMirrorToFoundation.js:38` `props: e.props || {}`，且其 `:30` 注释误称「foundation `_coerce_edge` 接收 …props」——**该注释错误**，以源码 `graph/mcp.py:89-93` 为准。
- CRM `graphVertexMirror.js:178/196/209` 向边注入 `props:{entity_type,entity_name}` / `{exception_name}` / `{similarity}` 等——**这些自由属性经 foundation 写端点会整体静默丢失**。

**处置（二选一，推荐 (a) 零 foundation 改动）**：
- **(a) CRM 把自由属性映射到既有字段**（不需 foundation 改动）：
  - 字符串引用（如 `entity_type`/`exception_name`/`similarity` 的语义标签）→ `evidence_ref`（单字符串）或并入 `serves_dims`（维度标签列表）；
  - 数值型（如 `similarity` 数值、`confidence` 语义）→ `weight` / `confidence`（float）。
- **(b) 若确需 graph_edge 上的自由 jsonb 属性**：提正式 RFE，foundation 评估为 `graph_edge` 增 `props jsonb` 列 + `EdgeWrite.props` 字段 + 白名单纳入。此属 **0.1.0 冻结面变更**，需单独审批，不在本接入契约内。

> 建议 CRM 先走 (a) 联调（零阻塞）；若 (b) 确需，单列 RFE，foundation 据冻结纪律另行裁定。

### 2.2 `profile` 默认值

`build_graph_write_server(store, *, profile=None, ...)`（`graph/mcp.py:27`）：`profile=None ⇒ _DefaultProfile() ⇒ predicates = PredicateSet()`（M 层七边，`graph/mcp.py:43-44,81-85`）。与 CRM `WRITABLE_EDGES` 已由 `r9-edge-consistency` 守卫锁死一致。消费方可注入含 K 层知识的 `PredicateSet` 扩展受控谓词（M∪K 合并视图，`graph/mcp.py:38-39`）。✓ 确认。

### 2.3 结构化错误码（CRM 须据此 fail-open）

`handle_request` 对所有 `McpServerError` 子类统一返回：

```json
{ "jsonrpc":"2.0", "id":<rid>, "error": { "code": -32000, "message": "<中文>" } }
```

（`mcpserver/__init__.py:164-165`）。**错误码非分类型**——所有 MCP 错误均为 `-32000`，由 `message` 字符串区辨：

| 失败类型 | message 含 | 来源 |
|---|---|---|
| 闭集/悬空校验失败（转 `McpServerError`） | 「受控边写校验失败」/「悬空边拒绝」 | `graph/mcp.py:54-57` |
| 鉴权被拒（`AuthDenied`） | 「鉴权被拒（auth 未注入时默认拒绝一切）」 | `mcpserver/__init__.py:174-175` |
| 工具未暴露（`ToolNotExposed`） | 「未暴露的工具」 | `mcpserver/__init__.py:171-172` |
| 令牌无效（`ConfirmTokenInvalid`） | 「确认令牌无效」 | `mcpserver/__init__.py:185-187` |

⚠️ **悬空边经 MCP 是硬错误，非静默 skip**：`_write_controlled_edges` 调 `write_controlled_edges(store, edges, profile=profile)` 用**默认 `strict=True`**（`graph/mcp.py:53` + `graph_edges.py:87-88`）⇒ 任一 from/to 粒子未落库即抛 `-32000`，**不会**进 `skipped`（`skipped` 仅在 `strict=False` 时填充，`graph_edges.py:118-119`）。

⇒ CRM 的 fail-open 逻辑必须把 `-32000` 视为「**整批拒绝**」信号：
1. **先确保本批顶点已在 foundation 落库**（E4 先顶点后边）再调写端点；
2. 收到 `-32000` 即 abort 本批 + emit `a1-mirror-failed` trace，**不要盲目重试**（重试仍悬空仍失败，只会重复写已落库部分之外的边——但本实现是「先全量校验再落库」，故悬空时一条都不写，重试验证仍会失败）。

> 若 CRM 希望悬空边「跳过留痕而非整批失败」，属行为变更：需 foundation 暴露 `strict` 开关（当前 `_write_controlled_edges` 未透传 `strict`）。请作为 RFE 单列，不在本契约。

### 2.4 认证 + 两阶段令牌契约（secret 注入形态）

- **`auth`**：`Optional[Callable[[Mapping[str, Any]], bool]]`，零信任默认拒绝（未注入 ⇒ `AuthDenied`，`mcpserver/__init__.py:107-108,174-175`）。CRM 注入自身 A9 契约 auth 即可。✓
- **`secret`：必须注入持久密钥**。`build_graph_write_server` 中 `secret=None ⇒ secrets.token_hex(32)` 进程内随机、重启即失效、不可跨进程重放（`mcpserver/__init__.py:108,114`）。CRM 须从配置/env 注入**跨重启稳定的共享密钥**（建议 env `A3A_FOUNDATION_MCP_SECRET`），否则阶段 1 在进程 A 签发、阶段 2 在进程 B 验证会 `ConfirmTokenInvalid`。
- **令牌绑定三元组**：`HMAC-SHA256(secret, name|canonical_args|principal)`（`mcpserver/__init__.py:85-92`）。`canonical_args` 为**键排序 + 紧凑分隔**（`{"b":2,"a":1}` 与 `{"a":1,"b":2}` 得同一串，`mcpserver/__init__.py:79-82`）。
  ⇒ CRM 两阶段**必须传同一 `arguments` 结构**（键集/值一致，顺序无关）+ 同一 `principal`（`ctx.principal`）。
- **调用姿势（两阶段均须带 `principal` 于 ctx）**：
  - **阶段 1**：`tools/call` name=`write_controlled_edges`，arguments=edges，**无** `confirm_token` ⇒ 返回 `result.status="confirmation_required"` + `result.confirm_token`（注意：非 `{written,skipped}`，是待确认态）。
  - **阶段 2**：同 name + **同 arguments** + `params.confirm_token=阶段1令牌` + `ctx.principal` 一致 ⇒ 真实执行，返回 `{written, skipped}`。

---

## 3. CRM §3 映射表修订建议（据 §2.1 props 告警）

| CRM 边字段 | → foundation | 修订 |
|---|---|---|
| `from` / `to` | `from_id` / `to_id` | ✓ 不变（`小写type:uuid` / `crm_exception:EX-n` 定址）|
| `predicate` | `predicate` | ✓ 七边原名 |
| `layer` | `layer` | ✓ 恒 `'M'` |
| `edge_source` | `edge_source` | ✓ 映射 `'rule'`（∈ `EDGE_SOURCES` 六值，禁 `consumer`）|
| `props` | ~~`props`~~ | ⚠️ 字段不存在 → 静默丢弃；改映射到 `evidence_ref` / `serves_dims` / `weight` / `confidence`（见 §2.1）|

> 同时建议修正 `edgeMirrorToFoundation.js:30` 注释（误称 `_coerce_edge` 接收 `props`），以源码 `graph/mcp.py:89-93` 白名单为准。

---

## 4. 放行口径（非阻塞）

- E5 会签已签（方案 a）；§2.2 契约已确认（含 props 告警待 CRM 修订映射）。A-1 双写**仅剩 CRM 自选 transport 落地 + §3 映射修订**，无 foundation 后续阻塞。
- `props` 处理若选 (b) 增列，属 RFE + 冻结面变更，单列审批；选 (a) 则零 foundation 改动，立即可联调。
- R9 维持「可迁候选·待试点验证」，不阻塞 P1 试点 / foundation 1.0 实证。
- A-1 双写在 E5 会签 + CRM 自选 transport 落地前**保持 kill-switch 休眠**（与 P1 shadow 同纪律），CRM 侧零跨仓写。

---

## 5. 来源映射（真值）

| 判据 | 真值来源 |
|---|---|
| EdgeWrite 11 字段 + 无 `props` | `persist/graph_edges.py:29-43` + `graph/mcp.py:89-93` |
| `props` 静默丢弃（白名单过滤） | `graph/mcp.py:96-98`（`_coerce_edge`）|
| profile 默认 `PredicateSet()`（M 七边） | `graph/mcp.py:43-44,81-85` |
| 错误码统一 `-32000` + message 区辨 | `mcpserver/__init__.py:164-165` |
| 悬空边硬错误（strict=True 默认） | `graph/mcp.py:53` + `graph_edges.py:87-88,113-117` |
| `secret` 默认随机 / 重启失效 | `mcpserver/__init__.py:108,114` |
| 令牌绑定三元组 + `canonical_args` | `mcpserver/__init__.py:79-99` |
| E5 `to_type` 非写时约束 | `graph_edges.py:72-84`（不校验 `to_type`）|
| 方案 a 接受（E5 会签） | 本件 §1（承 T51 §6 倾向）|
| CRM 侧发送 `props`（已核实） | `edgeMirrorToFoundation.js:38` + `:30` 误注 |
