# foundation 功能成熟度与消费侧接入指南

> 配套文档：`2026-10-12-foundation核心功能清单(全门面枚举).md`
> 日期：2026-10-13 ｜ 口径来源：源码级（`version.py` / `capability-matrix.md` / `plans/2026-10-09-foundation-maturity-blueprint.md` / `docs/release/v0.1.0-使用指南.md`）
> 仓边界：本仓为 AI 原生底座唯一事实源；消费方文档只读、不回写。

---

## 一、产品侧：功能成熟度评级

### 1.1 真相：成熟度**只在能力层（layer）登记，无逐符号评级**

- 状态枚举只有三级：`stable` / `experimental` / `deprecated` —— `version.py:62` `VALID_STATUSES`。
- 登记载体是 **29 个能力层**（`version.py:67` `CAPABILITIES`），**不是 478 个符号**。每个符号挂在某一层下；"除 `evolution` 外全 stable"是**层口径**，不是逐符号审计结论。
- 机器可查：
  - `capability_status(name)` → 单能力状态（`version.py:129`，未登记抛 `KeyError`，有界不静默）；
  - `capabilities()` → 只读全表；
  - `require_capabilities(...)` → 启动期 fail-closed 能力闸（三仓均已接，G5 范式）。
- 弃用机制：`DEPRECATIONS`（`version.py:103`，`TIER_*`→`VTIER_*` 别名），政策=**先 warn 一版再移除**，加法兼容不破。

> 结论：**有成熟期评级体系，但粒度为层、不是符号**。核心功能清单里的 478 符号目前没有各自的成熟度列；要做逐符号评级需另建映射表（见 §2.4 建议）。

### 1.2 各能力当前成熟度（29 层实况）

| 状态 | 层数 | 能力层 |
|---|---|---|
| **stable（1.0 兼容承诺，可写硬验收判据）** | 28 | `contract` `vector` `ontology` `context` `actions` `domain` `persist` `approval` `graph` `mcpserver` `canary` `orchestration` `events` `audit` `llm` `plugins` `session` `tools` `skills` `plan` `mcp` `hooks` `interaction` `workflow` `scenario` `store` `decision` `memory` |
| **experimental（禁写硬判据、禁对外宣称端到端跑通）** | 1 | `evolution` |
| **deprecated（告警待移除）** | 0（仅别名映射） | —（弃用别名见 `DEPRECATIONS`，非层状态） |

- `memory` 已于 **T44（2026-10-10）从 experimental 毕业为 stable**（判据面=真库 E2E `test_memory_e2e.py` + 单源裁定守卫 `tools/check_single_source_memory.py`，不是翻标志）。
- `evolution` 仍 experimental —— 对外口径必须标 experimental（`R-FE1`），毕业须走 RFE（先例 memory T44）。

### 1.3 成熟度的"收口门槛"（不是测试绿就算成熟）

每个能力层收口须过三件套（`maturity-blueprint.md §3`）：
1. **测试绿**（幂等写 / 维度约束 / 召回降级）；
2. **反假绿探针绿**（带可证伪探针 + **变异自证**：故意删判据分支→转红→还原）；
3. **零领域字面量 grep=0**（守内核零领域字面量铁律）。

---

## 二、产品侧：未来功能规划与计划

### 2.1 已落地路线（Phase 0–3，均 2026-10-09 收口）

| 阶段 | WS | 状态 | 关键交付 |
|---|---|---|---|
| Phase 0（就绪） | F-02 AGE 核实 / MEMORY 声明态 / APS R1-R2-R5 | ✅ | — |
| Phase 1 | WS5 场景注册表 · WS4 门面守卫 · WS1 能力矩阵 | ✅（420 测试绿） | 五门面 + lint 门禁 |
| Phase 2 | WS6 领域注入SDK · WS2 标准persister+记忆网 · WS3 注入式ApprovalGate | ✅（488 测试绿） | `inject_domain` / `PgVectorStorePersister` / `RedlinePriorityGate` |
| Phase 3 | WS8 GraphStore · WS7 MCP 服务骨架 | ✅（508 测试绿） | 只读派生图 / 两阶段零信任 MCP |
| Phase 3（尾部） | **WS9 参考消费层** | ⏳ **唯一未 ship** | 端到端样板 + 常驻 canary 探针 |

### 2.2 未来规划清单（待排期）

| 项 | 类型 | 状态 | 说明 |
|---|---|---|---|
| **WS9 参考消费层** | 能力补全 | ⏳ 待做 | 端到端样板 + 反假绿探针常驻；蓝图 §7.7 明示为下一步 |
| **evolution 毕业** | 成熟度演进 | 📋 规划中 | RFE 模型（memory T44 先例）：具体工程落地 + 真库 E2E + 单源裁定守卫，非翻标志 |
| **E9** approval 族 contract 再导出 | 契约增强 | ✅ **已实施（T68=67c06c4）** | 纯再导出，零行为变更 |
| **X2+** `AUDIT_EVENT_*` 经 api 再导出 | 契约增强 | ✅ **已实施（T68）** | 同上 |
| **C1** 消费方 import 门禁 `--consumer-root` | 契约卫生 | 🟡 P1 接受候选 | 扩展 `tools/check_import_surface.py`，发布 CI 片段供三仓自检 |
| **C2** 契约机器可读导出（版本化 JSON/manifest） | 契约卫生 | 🟡 P1 接受候选 | 扩展 `tools/gen_capability_manifest.py`，消费方守卫吃稳定导出物替代源码字面量对拍 |
| **C3** 键名 alias / deprecation 机制 | 契约卫生 | 🟡 P1 接受候选 | contract 面提供 deprecated alias 表 + `deprecations()` 警告 |
| C4–C7 / X-C1 / X-C2 | 跨语言/月度回捐 | 📋 P2 排期触发 | sidecar 骨架 / 双轨审计样例 / graph 读回路径澄清 / force_pending 契约 / 契约变更影响面通知 |
| **portal（页面生成）** | 能力启用 | ⏳ 未启用 | 三仓零消费（F2 观察项）；CRM 到 P3 阶段才启 |

### 2.3 边界纪律（不再扩大范围）

`maturity-blueprint.md §5` 已定：**动词/机制归内核，名词/内容归消费方**。
- 纳入：领域无关底层机制（存储/向量/本体/记忆/决策脊柱/情境/Action/场景/事件/进化/审计/MCP/门户暴露面）；
- 不纳入：SKILL 交互流程本身（保持方法论）、领域内容（经 `TenantProfile` 注入）、应用组合层、具体场景决策逻辑。
- 杠杆在"**把已在树能力打包成稳定、有 SLA、零改内核即可用**"，不是新增子系统。

---

## 三、消费侧：必选 / 可选 + 开发顺序

### 3.1 强制纪律：sanctioned 五门面（唯一合法 import 通道）

```
chiyu_kernel.api  /  chiyu_kernel.contract（含子树）  /  chiyu_kernel.approval
chiyu_decision.api  /  chiyu_portal.api
```
- 门禁 `tools/check_import_surface.py` 接 `make lint`；**违反即失去兼容性保护**（使用指南 §8）。
- 撞名符号（`register_scenario` / `Particle` 等）建议全限定引用。

### 3.2 必选 vs 可选（按能力层 + 三仓消费现状）

| 能力层 | 必选性 | 三仓消费现状 | 判定依据 |
|---|---|---|---|
| `decision`（run_spine 脊柱 + 八要素/九尺子/红线/置信） | **必选（核心）** | 三仓全用 | 决策主链，无此不成 AI-native 决策 |
| `contract`（决策契约 / 审计双轨 / SEVEN_DIMS） | **必选** | 三仓全用 | 契约单一事实源 |
| `approval`（RedlinePriorityGate 等） | **必选** | APS/CRM/enterprise 均接 | 红线优先闸，硬约束先于置信度 |
| `persist`（PgVectorStorePersister + write_decision_memory_net） | **必选** | 三仓接（落库生产前提） | 单库多轨收口，event+particle+graph_edge 同源事务 |
| `store` / `vector` | **必选** | 三仓接 | PG + pgvector 单一事实源 |
| `domain`（TenantProfile + inject_domain） | **必选（关键石）** | 三仓接 | 领域注入唯一通道，消除重复劳动最高杠杆 |
| `graph`（只读派生视图） | **推荐** | APS/CRM 用 relation_view 等 | 审计溯源/关系视图，建议接 |
| `canary`（canary_probe 三判据） | **推荐** | APS/enterprise 接 | 周期巡检探针，建议接 |
| `mcpserver`（MCP 输出面） | **可选** | enterprise 接；CRM/APS 直连 import | 稳定输出面，按架构选 |
| `memory`（记忆网） | **可选增强** | 仅 enterprise 接；CRM/APS 未接 | stable 但非强制；enterprise 已接 |
| `evolution` | **禁止写硬判据** | 仅 enterprise bridge.py（标 experimental） | experimental，对外须标实验态 |
| `portal`（页面生成） | **可选/未启用** | 三仓零消费（F2，CRM P3 启用） | 当前无消费方使用 |
| `scenario`/`actions`/`orchestration`/`workflow`/`events`/`llm`/`plugins`/`session`/`tools`/`hooks`/`plan`/`interaction`/`context`/`ontology`/`audit` | **按需（组合层）** | 视消费方应用组合 | 原语层，由各仓组合期裁决 |

### 3.3 推荐开发顺序（消费方接入路径）

| 序 | 步骤 | 对应能力 | 是否必选 | 锚点 |
|---|---|---|---|---|
| 0 | 启动自检：`require_capabilities` 断言 | `version` | 必选 | 使用指南 §1 |
| 1 | 领域注入 SDK（TenantProfile + inject_domain） | `domain` | **关键石** | maturity-blueprint §1（I3 最高杠杆） |
| 2 | 决策脊柱主链（run_spine + RedlinePriorityGate + 八要素/九尺子注入） | `decision`+`approval`+`contract` | 必选 | 使用指南 §2 |
| 3 | 标准落库（PgVectorStorePersister + write_decision_memory_net） | `persist`+`store` | 必选 | 使用指南 §4 |
| 4 | 审批续跑（resume_spine PENDING 收口） | `decision` | 必选 | 使用指南 §3 |
| 5 | 只读派生视图（relation_view / timeline_view / decision_backlinks） | `graph` | 推荐 | capability-matrix §1b |
| 6 | 巡检探针（canary_probe 三判据） | `canary` | 推荐 | 使用指南 §6 |
| 7 | 输出面 MCP（mcpserver + 两阶段 confirm） | `mcpserver` | 可选 | 使用指南 §7 |
| 8 | 记忆网（memory，可选增强） | `memory` | 可选 | T44 毕业 stable |
| 9 | 门户页面（portal，CRM P3 启用） | `portal` | 可选/未启 | F2 观察项 |

> 顺序原则：**先入口胶水（domain）→ 核心决策闭环（decision/approval/contract）→ 落库（persist）→ 人工闸收口（resume）→ 派生视图/巡检 → 输出面 → 可选增强（memory/portal）**。与蓝图 §4 "WS6→WS2→WS3→WS8→WS7→WS9" 一致。

### 3.4 完整使用手册现状与建议

**已存在（✅）：**
- `docs/release/v0.1.0-使用指南.md` —— 最短可用路径（安装→决策→三态→落库→视图→canary→MCP→纪律→FAQ）；
- `docs/release/v0.1.0-接口参考.md` —— 机器生成全接口全集；
- `docs/capability-matrix.md` —— 稳定子集 / 实验态边界 + 图算子支持矩阵 + 失败语义默认；
- `docs/plans/2026-10-09-foundation-maturity-blueprint.md` —— 路线图 + WS 收口标准 + 横切成熟度闸；
- `docs/release/v1.0-发布判据.md` / `v0.1.0-SLA与支持承诺.md` —— 发布与 SLA 承诺。

**缺失（❌）：**
- 逐符号 / 逐能力 cookbook（478 符号无逐条用法，接口参考是机械枚举非教程）；
- **分消费方接入手册**（CRM / APS / enterprise 各自的"必选清单 + 接入步骤 + 变异自证"尚未成册；R-FC/R-FA/R-FE 三份分册是裁定稿，非手册）；
- 反假绿探针范例库（各 WS 变异自证散落测试，未抽成可复用手册）。

**建议（落地动作）：**
1. 由 R-FC1-4 / R-FA1-4 / R-FE1-4 三份分册提炼**三份《消费方接入手册》**（必选能力 + 步骤 + 自检命令）；
2. 建**逐 WS cookbook**（WS6/WS2/WS3/WS8/WS7 各一份最小可运行样例 + 变异自证）；
3. **逐符号成熟度映射表**（把 478 符号映射到 29 层状态，补 §1.1 缺口）；
4. 接口参考已机器生成，保持与 `__all__` 版本联动。

---

## 四、结论

1. **成熟度有体系、粒度为层**：三级状态（stable/experimental/deprecated）覆盖 29 能力层（28 stable + 1 experimental=evolution）；可机器查询（`capability_status` / `require_capabilities`）；但**核心功能清单的 478 符号尚无逐符号评级**，需另建映射表。
2. **未来规划明确**：Phase 0–3 主体已 ship（至 508 测试绿），剩余 **WS9 参考消费层** + **evolution 毕业** + **契约卫生 RFE（C1/C2/C3，P1）**；本轮已实施 E9+X2（T68）。边界不扩大，杠杆在"暴露稳定子集"。
3. **消费侧必选/可选清晰**：`decision`/`contract`/`approval`/`persist`/`store`/`vector`/`domain` 为必选核心；`graph`/`canary` 推荐；`mcpserver`/`memory`/`portal` 可选；`evolution` 禁写硬判据。开发顺序以 domain 关键石为起点，先闭环决策再落库再派生。
4. **使用手册不完整**：最短指南 + 接口参考 + 能力矩阵 + 路线图已存在，但缺**逐符号 cookbook** 与**分消费方接入手册**；建议按 §3.4 四项补齐。

— foundation（chiyu-foundation 仓），2026-10-13
