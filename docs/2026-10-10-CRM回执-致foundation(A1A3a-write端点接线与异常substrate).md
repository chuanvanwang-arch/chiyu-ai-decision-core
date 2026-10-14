# 致 foundation：R9 方案 A 接续协商——核实确认 + MCP write 工具端点接线请求 + 异常 substrate 裁定请求

> 状态：**正式回执请求（决策位 C）**——非完成申报，是推动 A-1/A-3a 可联调的前置协商。等 foundation 接线 MCP write 端点 + 裁定异常 substrate 后，A-1 双写与 A-3a 落地方可联调。
> 日期：2026-10-10
> 致：chiyu-foundation
> 回应：foundation `docs/2026-10-10-答复-CRM-方案A实现稿交付与A1A3a解锁路径.md`（T48）
> 关联：CRM `docs/2026-10-10-crm-R9-A3a-vertex-substrate-design.md`（A-3a substrate 语义设计草案）；`docs/2026-10-10-crm-R9-A1-decision-relation-integration-design.md`（A-1 已裁定）
> 取证基线：CRM 2026-10-10 工作树；foundation T47 提交后工作树（trust-but-verify，回两仓源码核实，符号名引证不引行号）

---

## 0. 一句话

**T47 能力交付采信（源码核实为真），但 T48 §2.1 的"A-1 已解锁"当前不成立**——`write_controlled_edges` 只作为 Python 库函数导出、`McpServer` 是通用骨架、**生产代码里没有任何 `expose("write_controlled_edges", risk="write")` 的实际注册** ⇒ A-1 双写缺"已接线的 MCP write 工具端点"。**请求 foundation 把该工具经 `McpServer.expose(risk="write")` 接线交付**；同时**异常顶点 substrate 在 foundation `CORE_ROLES` 下无恰当落库载体，请求裁定**。CRM 侧 A-3a 的 substrate 语义设计已完成 `docs/2026-10-10-crm-R9-A3a-vertex-substrate-design.md`（待决策第 0 闸评审），不阻塞上述两请求。

---

## 1. 我方对 T47 的核实结论（确认交付，采信）

按 trust-but-verify（判据 #23：不采信转述，回源码核实；符号名引证不引行号），逐条核实 foundation：

| 论断 | 核实结果 | 证据 |
|---|---|---|
| `persist/graph_edges.py` 三判据 | ✅ 为真 | `_validate_closed_sets` 闭集 fail-fast（谓词∈profile.predicates M∪K、layer∈EDGE_LAYERS、edge_source∈EDGE_SOURCES，先全量校验一条不写）；悬空边拒绝（`SELECT particle_id FROM particle WHERE particle_id=ANY(...)`，strict 抛/非 strict skip，不隐式建顶点）；`upsert_graph_edge` 唯一落库点（ON CONFLICT (from,to,predicate) DO UPDATE 幂等） |
| 单源守卫收窄 | ✅ 为真 | `tools/check_single_source_memory.py` 白名单收窄到 `persist/graph_edges.py`；`persist/__init__.py` `_store_write_edge` 委托 `upsert_graph_edge` |
| 七边闭集 + EDGE_SOURCES 六值 | ✅ 为真 | `contract/particle.py` `MEMORY_PREDICATES`（7 边，layer=M）与 CRM `WRITABLE_EDGES` 逐字一致；`EDGE_SOURCES=("human","rule","ai","llm","engine","manual")` 无 "consumer"。CRM 跨仓守卫 `test/scripts/r9-edge-consistency.test.js`（已变异自证）持续对拍 |
| manifest 据实更新 | ✅ 为真 | graph 条目已按"受控边写提供；顶点写不提供；WritableGraph 1.0 后裁定"更新 |

**采信决议**：T47 的图写能力（受控边写 + 三判据）**真实交付**，作为 A-1 双写的写侧基座，我方接受。

---

## 2. 我方对 T48 §2.1 的核实结论（A-1 解锁通道当前是纸面）

T48 §2.1 声称"写经 foundation MCP 服务端暴露为 write 类工具（risk="write"，走 A9 契约两阶段确认）"。核实结果：

- `write_controlled_edges` **仅作为 Python 库函数导出**（`persist/__init__.py` / `api.py` 门面），被单元/真库测试**直接函数调用**。
- foundation `McpServer`（`mcpserver/__init__.py`）是**通用服务端骨架**——`expose` 注册 + 零信任 auth + 两阶段确认 + 传输无关派发，**没有**任何 `expose("write_controlled_edges", risk="write")` 的实际注册（既有 expose 全是示意工具 read_thing/write_thing）。
- 因此 **A-1 双写当前无可调用的 MCP write 端点**：不是缺写能力，是**缺已接线的端点**（判据 #16 暴露≠可调用；判据 #6 静态骨架≠可消费证据）。

**影响**：CRM 侧要按 T48 §2.2 把 `ageGraph` 镜像写改造为"MCP 调用 write_controlled_edges"，**前提是 foundation 先把该工具 expose(risk="write") 接线并部署**。这一步尚未发生，故 T48 所述"CRM 只需接 sanctioned 面"的承诺**在当前基线不成立**。

---

## 3. 请求①：把 `write_controlled_edges` 接线为 MCP write 工具端点

**请求 foundation**：在 foundation MCP 服务端内新增实际注册：

```
McpServer.expose("write_controlled_edges",
    handler=...,        # 委托 persist.write_controlled_edges
    risk="write",       # 走 A9 契约：confirmation_required → confirm_token 两阶段
    ...)
```

同时提供**可观测证据**（对齐我方判据 #16/#6，不满足即视为未接线）：
1. 该端点被 `ExposedTools`/`lifecycle` 枚举为**已注册**（非 `reserved`）；
2. 有**真库 E2E**：经 MCP 调用 `write_controlled_edges` → `graph_edge` 落库 → CteGraphStore 读回命中；
3. 两阶段确认生效：`confirmation_required` 返回 → confirm_token 变更 → 重新确认（A9 契约 §3 变异）；
4. deployment/compose 中 MCP 服务实际暴露该工具。

**我方配合**：端点就绪后，CRM 侧即按 T48 §2.2 实施 A-1 C1 第一步（迁移期双写经此端点）+ 四判据对拍（镜像写成功/降级不阻塞/闭集对拍/两阶段确认）。

---

## 4. 请求②：异常顶点 substrate 裁定

foundation T48 §3 把 A-3a 的"decision/entity/exception 顶点用哪个 particle type"划为 CRM 定。**决策与实体的语义我方已定**（见 `docs/2026-10-10-crm-R9-A3a-vertex-substrate-design.md` §4）：决策→`decision` 核心角色；实体→`entity` 角色 + 业务名小写化细分；七边 from 恒 `decision`；edge_source 建议 `rule`/`manual`（禁 `consumer`）。

**但异常存在 foundation 侧硬约束冲突，单凭 CRM 无法定**：

- CRM `DERIVED_FROM_EXCEPTION` 的 to 端是**异常**（`EX-1` 等裸字符串），语义是**告警/事件触发**（`autonomyEngine` disposition=EXCEPTION），非知识。
- foundation `CORE_ROLES = (unstructured_asset, entity, decision, memory, knowledge)` **无"异常/事件"角色**；且 `MEMORY_PREDICATES` 把 `DERIVED_FROM_EXCEPTION.to_type` 硬编码为 `knowledge`。
- 若 CRM 强行落成 `knowledge` 粒子→语义错位；若不落库→**受控写悬空边拒绝全量拦 DERIVED_FROM_EXCEPTION 镜像**。

**请 foundation 三选一裁定**（涉及 0.1.0 冻结面，须 foundation 评估后回复，我方会签）：
- **方案 a**：允许 CRM 以 `entity` 角色承载异常（payload 标记 kind=exception）——最小改动，不碰内核枚举；
- **方案 b**：foundation 新增 `exception`/`event` 核心角色 + `ParticleTypeSet` 扩展——需评估 0.1.0 冻结面与 CORE_ROLES 准入标准（是否跨域恒定）；
- **方案 c**：维持 `to_type=knowledge`，语义上接受异常以知识粒子形态落库——需我方确认营销上可接受语义妥协。

（此请求与请求①同批投递；A-3a 其余部分不阻塞。）

---

## 5. 我方状态与边界声明

- **已定（CRM 自主）**：A-3a substrate 语义设计草案 `docs/2026-10-10-crm-R9-A3a-vertex-substrate-design.md` 已产出，待决策第 0 闸评审（E1–E5 待决，其中 E5 异常 substrate 即本回执请求②）。
- **阻塞于 foundation（非 CRM 可自主）**：A-1 双写落地、A-3a 实体化落地、顶点落库——均依赖请求①（MCP write 端点接线）与请求②（异常 substrate 裁定）。
- **不因本回执触发 P1/正式回执**：P1 硬前置（staging 流量 ≥2 周 + 周度 §8 出口闸 + HITL 翻开关 + 生产发布）与 A-1 完成后给 foundation 的正式回执（四项触发条件）**均不因本次协商而满足**；本回执属**接续协商**，非完成申报。
- **0.1.0 冻结尊重**：请求①的 expose 接线是 foundation 服务端**加法**（不 deprecate 既有 API）；请求②b 若触内核枚举扩展，请 foundation 明确冻结面判据，我方不在冻结期内强推。

---

## 附：回执 ↔ 来源映射

| 论断 | 真值来源 |
|---|---|
| T47 三判据/单源收窄/七边闭集/EDGE_SOURCES 六值 | foundation `persist/graph_edges.py`；`persist/__init__.py`；`tools/check_single_source_memory.py`；`contract/particle.py`（symbol 级，不引行号） |
| McpServer 通用骨架无 write_controlled_edges 注册 | foundation `mcpserver/__init__.py`（`expose` 既有注册均为示意工具） |
| 七边一致跨仓守卫（变异自证） | CRM `test/scripts/r9-edge-consistency.test.js` |
| A-1 裁定 C1 graph_edge 权威分两步 + D4→A-3a | CRM `docs/2026-10-10-crm-R9-A1-decision-relation-integration-design.md` §4 |
| A-3a substrate 语义（决策/实体/七边/edge_source/异常开放） | CRM `docs/2026-10-10-crm-R9-A3a-vertex-substrate-design.md` |
| 异常=告警/事件语义（disposition=EXCEPTION） | CRM `src/decision/autonomyEngine.js`；`src/decision/decisionRepo.js`（`addParticleVertex('EXCEPTION', ...)`） |
| 顶点落库归宿（run_spine persist / MCP 决策落库工具） | foundation T48 §2.2 自述 |
| A9 两阶段确认契约 | foundation `docs/2026-10-10-MCP服务端授权接入契约-A9.md` §3 |

---

## 6 foundation 侧接函与裁定（决策位：foundation 回应；2026-10-10 晚）

> 状态：**请求①已交付、请求②已裁定**。本回执起草时 T48 §2.1 为纸面；但本回执投递前 foundation 已先行以 **T50** 闭合该缺口（承办于 2026-10-10 晚，commit 7976b37）。本 §6 对两请求逐条回应，并据实校正贵方回执中的时点偏差。

### 6.1 请求①：MCP write 端点接线 —— **已交付（T50），工具名已对齐 `write_controlled_edges`**

贵方回执 §2 所述"全仓无任何 `expose("write_controlled_edges", risk="write")` 实际注册"——**该 gap 已于 T50 真实闭合**（在贵方起草本回执之后、投递之前）。为避免贵方按旧时点重复判定，逐条回应该回执 §3 的四判据证据：

| 判据（贵方 §3） | foundation 现状（T50 已交付，可信源） |
|---|---|
| ① 端点被枚举为已注册（非 reserved） | ✅ `chiyu_kernel.graph.mcp.build_graph_write_server` 经 `McpServer.expose("write_controlled_edges", handler, risk="write")` 注册；`list_tools` 可枚举且 `risk="write"`。`test_graph_write_mcp_e2e.py` 断言覆盖（`assert tools[WRITE_CONTROLLED_EDGES_TOOL].risk == "write"`）。**工具名即贵方点名的 `write_controlled_edges`**（T50 初版曾用 `graph_write_edges`，本回应已将注册名与常量 `GRAPH_WRITE_TOOL` 一并对齐为 `write_controlled_edges`，消除贵方 `list_tools` 找名不匹配的二次误判） |
| ② 真库 E2E：经端点 → graph_edge 落库 → 只读视图读回 | ✅ `test_graph_write_mcp_pg.py` 本地 PG **实测跑通**：两阶段确认 → `graph_edge` 真实落库 → `PgCteGraphStore` 只读派生读回（写读同表闭环）；闭集 `edge_source="consumer"` 经通道零落库 |
| ③ 两阶段确认生效 | ✅ `McpServer` 内置 `confirmation_required` → `confirm_token` → 重确认（与 A9 契约 §3 同构）；校验异常（`ValueError` 闭集/悬空）转 `McpServerError` 结构化错误（不把未处理异常抛消费方，T50 补的真实可用性洞） |
| ④ deployment/compose 暴露该工具 | ⚠️ **属消费方职责**（R5：http/stdio transport 由消费方自实现）。foundation 提供 `build_graph_write_server` + 注入 `auth`；CRM 实例化 server、选 transport、把请求喂 `McpServer.handle_request` 即闭合 A-1 通道。此条不归 foundation 仓库"部署"动作，但**通道已就绪、无 foundation 遗留** |

**结论**：请求①已满足，A-1 双写"已接线的调用端点"缺口闭合。贵方回执 §0/§2 的"纸面"论断，对 T48 初版成立、对 T50 基线不成立——请据此更新贵方内部基线，避免重复催办。

### 6.2 请求②：异常顶点 substrate 裁定 —— **选 a（entity + kind=exception），拒 b、拒 c**

经源码核实与内核纪律评估，裁定如下：

- **拒 b（新增 exception/event 核心角色）**：`CORE_ROLES` 准入标准 = 该角色在**任意**业务领域都成立（`contract/particle.py:17-19`，黑名单 `config/domain-literal-denylist.json` 强制）。"异常/事件"是 CRM `autonomyEngine` disposition=EXCEPTION 的**域语义**，非跨域恒定；0.1.0 冻结期内**不扩展内核枚举**。若 1.0 后出现跨域真实需求，须走正式 CORE_ROLES 准入提案（附多消费方证据），不在本回执范围。
- **拒 c（妥协为 knowledge）**：把告警/事件妥协成 knowledge 会污染知识图谱，破坏 T41 `recall_precedents` / T42 `rrf_fuse` 的记忆召回质量（alert 被当知识召回），得不偿失；且语义错位（贵方回执已自陈"告警/事件触发非知识"），故否决。
- **选 a（entity 角色 + payload `kind=exception`）**：异常/告警作为 `entity` 角色粒子、`payload.kind=exception` 承载。依据：
  1. `entity` = "任意域都有参与主体"（`contract/particle.py:53`）——异常是决策因果上下文中的参与主体，符合 CORE_ROLES 准入，**内核零改动、零冻结面破坏**；
  2. **运行期可行（已核实）**：`write_controlled_edges` 闭集校验（`persist/graph_edges.py:72-84` `_validate_closed_sets`）**只校验 `predicate`/`layer`/`edge_source`，不校验 `to_type`**；`MEMORY_PREDICATES.DERIVED_FROM_EXCEPTION.to_type="knowledge"`（`contract/particle.py:126`）是**规格推荐默认（advisory），非写时硬约束**；
  3. 故 CRM 以 `entity(kind=exception)` 为 `to` 端写 `DERIVED_FROM_EXCEPTION` 边：`predicate∈M 七边`、`edge_source∈六值`（建议 `rule`/`manual`，**禁 `consumer`**）、`to` 粒子先经粒子写落库（不触发悬空边拒绝）即闭集通过。

**对贵方的下一步**：在 `docs/2026-10-10-crm-R9-A3a-vertex-substrate-design.md` 中把 `EX-n` 节点定为 `entity(kind=exception)`；E5（异常 substrate）裁定已闭合，第 0 闸 E5 项可据此签核。**foundation 侧无遗留动作**。

### 6.3 状态与边界（对贵方 §5 的回应）

- 请求①已交付、请求②裁定为 a，foundation 侧**均无遗留动作**；A-1 双写与 A-3a 实体化落地的联调前提现已齐备，贵方按 T48 §2.2 / 本 §6.2 实施即可。
- **P1 硬前置（staging 真实流量 ≥2 周 + 周度 §8 出口闸 + HITL 翻开关 + 生产发布）与 A-1 完成后给 foundation 的正式回执（四触发条件）均不因本接函而满足**——本接函属**接续协商的闭合**，非完成申报，与贵方 §5 边界声明一致。
- 0.1.0 冻结尊重：本裁定全程零内核枚举扩展、零 API deprecation。

| 论断 | 真值来源（foundation 侧） |
|---|---|
| T50 端点已注册 `write_controlled_edges` risk="write" | `graph/mcp.py` `build_graph_write_server`；`test_graph_write_mcp_e2e.py` |
| 真库 E2E 写读同表闭环 | `test_graph_write_mcp_pg.py`（本地 PG 实测） |
| 闭集校验不强制 to_type | `persist/graph_edges.py:72-84` `_validate_closed_sets` |
| `DERIVED_FROM_EXCEPTION.to_type="knowledge"` 为规格默认非硬约束 | `contract/particle.py:126`（PredicateSpec 形态声明） |
| CORE_ROLES 准入 = 任意域成立、禁域字面量 | `contract/particle.py:17-19` + `tests/test_contract_no_domain_literals.py` |
