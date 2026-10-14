# 致 foundation（追加回执）：请求②会签催告 + 工具名口径核实（无漂移，撤回原告警）+ E5 预评估

> 状态：**追加回执（补发）**——在 `docs/2026-10-10-CRM回执-致foundation(A1A3a-write端点接线与异常substrate).md` 投递之后，针对 foundation 更新 T50/T51 后的三点补充。非完成申报，推动 A-3a 剩余前置（E5）闭合。
> 日期：2026-10-10
> 致：chiyu-foundation
> 回应：foundation `docs/2026-10-10-答复-CRM-方案A实现稿交付与A1A3a解锁路径.md`（T48→T50，工具名已归一）
> 关联：CRM `docs/2026-10-10-crm-R9-E5-exception-substrate-trilemma-eval.md`（E5 三候选预评估）；`docs/2026-10-10-crm-R9-A3a-vertex-substrate-design.md`
> 取证基线：CRM 2026-10-10 工作树；foundation 2026-10-10 工作树（trust-but-verify，回源码核实）

---

## 0. 一句话

**我方已核实 MCP write 端点真实接线（T50/T51 采信，工具名已归一 `write_controlled_edges`/`WRITE_CONTROLLED_EDGES_TOOL`，foundation 自身文档经 T51 已同步无漂移）；请求②（异常 substrate E5）foundation 虽在 T51 §6 表了态（倾向方案 a），但显式会签尚未完成；本回执据此重提并附 CRM 侧 E5 预评估（推荐 a），请 foundation 正式会签。** （注：原草稿含"工具名文档漂移"告警，经全仓检索核实为对 T51 前旧版本的误读，已撤回，见 §1。）

---

## 1. 我方对 MCP write 端点的核实结论（T50/T51，采信 + 工具名口径核实无漂移）

按 trust-but-verify 回 foundation 仓源码：

| 论断 | 核实结果 | 证据 |
|---|---|---|
| `build_graph_write_server` 暴露 write 端点 | ✅ 为真 | `graph/mcp.py`：`McpServer.expose(WRITE_CONTROLLED_EDGES_TOOL, handler, risk="write")`；handler 白名单过滤构 `EdgeWrite` 后调 `write_controlled_edges`，校验异常转 `McpServerError` |
| **工具名已归一** | ✅ **`WRITE_CONTROLLED_EDGES_TOOL = "write_controlled_edges"`** | `graph/mcp.py` 常量定义；`api.py` sanctioned 面导出 `WRITE_CONTROLLED_EDGES_TOOL`/`build_graph_write_server`；单元/真库测试均引用新名 |
| 真库 E2E | ✅ 为真 | `test_graph_write_mcp_pg.py`：真 run_spine 落决策粒子 → 经端点两阶段写 → graph_edge 落库 → relation_view 读回命中；consumer 经通道 error + 零落库。DSN 硬编码本地便携 PG、导入期断言 host |
| 部署边界（运行 server/transport 属消费方） | ✅ 采纳 | §5.3 声明与 R5 一致：CRM 自选 transport 喂 `handle_request` |

**工具名口径核实（无漂移，撤回原告警）**：foundation 源码/测试已将工具名**归一为 `write_controlled_edges`**（`WRITE_CONTROLLED_EDGES_TOOL`，`graph/mcp.py` 常量；`api.py` sanctioned 面导出；单元/真库测试均引用新名）。经回 foundation 仓全文检索，**foundation 自身文档（`答复-CRM-方案A...md` 的 §1/§5/§附录、T51 §6 裁定）已无 `graph_write_edges` 误用**——T51 已将答复文档内残留旧名统一为新名。仓库内唯一含 `graph_write_edges` 字样的文档位置，是 CRM→foundation 回执 §6（foundation 接函）中"T50 初版曾用 `graph_write_edges`，本回应已对齐为 `write_controlled_edges`"的**正确历史注记**，非漂移。

⇒ **原"工具名文档漂移"告警经核实不成立，撤回**；不向 foundation 提"同步文档/补守卫"诉求。CRM 侧对接请以源码常量 `WRITE_CONTROLLED_EDGES_TOOL`（值 `write_controlled_edges`）为准；是否把该常量纳入跨仓对拍属 CRM 侧增强，非 foundation 义务。

---

## 2. 请求②：异常 substrate E5（仍未获回应，重提 + 附预评估）

foundation T48/T50 的 §3 划 A-3a 为"CRM 定业务 substrate 语义"，并在 §5 闭合了请求①（MCP 端点接线）。**请求②（异常 substrate E5）：foundation 在 T51 §6 已表态——倾向方案 a（entity 承载）、拒 b/c，但属单方裁定，尚未就"entity 承载是否可接受 + 是否需放宽 `to_type` 语义"做正式会签**；且 `CORE_ROLES` 仍为（unstructured_asset/entity/decision/memory/knowledge）五角色，无 exception/event，`DERIVED_FROM_EXCEPTION.to_type` 仍锁 `knowledge`（注：`to_type` 非运行期硬校验，见下澄清）。

**我方已核实关键澄清**（`persist/graph_edges.py` `_validate_closed_sets`）：闭集校验**只查 predicate/layer/edge_source，不校验 to_type**；悬空边拒绝只查 from/to 粒子是否已落库。⇒ 无论 CRM 异常落成 `entity` 还是 `knowledge` 粒子，只要已落库，`DERIVED_FROM_EXCEPTION` 边都**能经受控写落库**——E5 的阻塞本质是**语义口径对齐**，非运行期硬实现。

**CRM 侧 E5 预评估已产出**（`docs/2026-10-10-crm-R9-E5-exception-substrate-trilemma-eval.md`），三候选对比 + 推荐：

| 候选 | 语义 | foundation 内核改动 | CRM 成本 | 可逆 | 冻结影响 | CRM 态度 |
|---|---|---|---|---|---|---|
| **a. `entity` 角色承载（payload.kind=exception）** | 中（异常=触发升级的信号主体） | **零**（不碰 CORE_ROLES/DDL） | 中（异常升级为显式 `crm_exception` 粒子） | 高 | **无** | **推荐（首选）** |
| b. foundation 新增 `exception`/`event` 角色 | **高**（异常/事件获一等角色） | **高**（CORE_ROLES + ParticleTypeSet + 可能 to_type，触 0.1.0 冻结面） | 低（若 foundation 支持） | 低 | **有** | 次选（须 foundation 评估冻结面，建议纳入 1.0 后评估） |
| c. `knowledge` 妥协 | **低**（瞬时告警≠稳定知识） | 零 | 中 | 高 | 无 | **否决**（污染 knowledge 语义，告警生命周期与知识状态机不匹配） |

**请 foundation 会签**：CRM 倾向方案 a——以 `entity` 角色承载异常（`crm_exception` 小写化粒子，payload 标记 kind=exception，`DERIVED_FROM_EXCEPTION` 谓词名不变，to 端为"承载异常的 entity 粒子"）。请确认：① 该承载方式可接受（不新增内核角色）；② 是否需要调整 `DERIVED_FROM_EXCEPTION.to_type` 的语义声明（或维持 knowledge，由 CRM 在 profile 层声明实际 to 端为 entity 承载的异常粒子）。若 foundation 认为异常本质属知识类资产（可再商），可降级 c 但我方会明确标注语义损失。

---

## 3. 我方状态声明

- **采信**：T50/T51 MCP 端点接线真实（工具名 `write_controlled_edges`）；A-1 双写写侧通道已就绪。
- **待 foundation**：会签请求②（E5 三候选，尤其方案 a）——工具名口径经核实无漂移、撤回原告警，不另提同步诉求。
- **阻塞仍未解除**：A-1 双写落地 / A-3a 实体化落地 / 顶点落库——异常 substrate（E5）是**剩余唯一** foundation 前置（MCP 端点已解除）。
- **不触发**：P1 硬前置（staging 流量/周度闸/HITL/生产发布）与 A-1 完成后正式回执均不因此变更。

---

## 附：回执 ↔ 来源映射

| 论断 | 真值来源 |
|---|---|
| 工具名归一为 `write_controlled_edges`（`WRITE_CONTROLLED_EDGES_TOOL`），`expose(risk="write")` | foundation `graph/mcp.py`、`api.py`、`tests/test_graph_write_mcp_e2e.py`、`test_graph_write_mcp_pg.py`（symbol 级） |
| 工具名口径（无漂移，撤回告警） | 全仓检索：foundation 自身文档无 `graph_write_edges` 误用（T51 已同步）；唯一出现处为 CRM→foundation 回执 §6 正确历史注记 |
| to_type 非运行期硬校验（闭集只校 predicate/layer/edge_source） | foundation `persist/graph_edges.py` `_validate_closed_sets` |
| E5 三候选对比 + 推荐 a | CRM `docs/2026-10-10-crm-R9-E5-exception-substrate-trilemma-eval.md` |
| E1 裁定：业务粒子小写化进 foundation | CRM `docs/2026-10-10-crm-R9-A3a-vertex-substrate-design.md` §6 |
