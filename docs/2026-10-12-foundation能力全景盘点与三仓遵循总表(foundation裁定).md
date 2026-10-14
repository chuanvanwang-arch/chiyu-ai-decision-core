# foundation 能力全景盘点与三仓遵循总表（foundation 裁定）

- 日期：2026-10-12
- 性质：foundation 对全能力面 × 三消费方（CRM / APS / enterprise）的盘点裁定总册
- 证据基线：本轮会话多轮 trust-but-verify 实跑（四件套三路取证、N1–N7 整改复核、回捐四模式 M1–M4 机检复核、K-M-D 闭环实查、sanctioned import 面全量扫描）
- 权威能力清单来源：`packages/chiyu-kernel/src/chiyu_kernel/version.py::CAPABILITIES`（29 项）

---

## 一、foundation 能力全景（CAPABILITIES 29 项，分五组）

| 组 | 能力 | 状态 | 契约/门面出口 |
|---|---|---|---|
| **决策族** | decision（脊柱/八要素/九尺子/审计双轨） | stable | `chiyu_decision.api`：run_spine / resume_spine / score_rubric / aggregate_confidence / audit_persister(T58) |
| | contract（EIGHT_ELEMENTS·RUBRIC_KEYS·SPINE_ORDER·AUDIT_RECORD_KIND·SEVEN_DIMS·DecisionIOField） | stable | `chiyu_kernel.contract`（含再导出完备性守卫，T61） |
| | approval（RedlinePriorityGate / DecisionVerdictState） | stable | `chiyu_kernel.approval` |
| | memory（决策记忆网：PgNoteStore / write_decision_memory_net / build_memory_recaller） | stable（T44 毕业，1.0 承诺） | `chiyu_kernel.api` |
| **数据族** | persist / store（PgVectorStore / open_graph_write_store / chain_hash·verify_chain） | stable | `chiyu_kernel.api` |
| | graph（受控边写：write_controlled_edges 两阶段） | stable | MCP + stdio 工厂 |
| | vector / ontology / context / domain | stable | contract + api |
| **运行族** | actions（ActionRegistry/ACTION_MAX）/ events（EventBus）/ workflow / scenario / plan / session / interaction | stable | api |
| | mcpserver / mcp（McpBridge·McpTransport·normalize_mcp_name）/ plugins / tools / skills / hooks / llm（LlmProvider）/ canary | stable | api |
| | audit（审计链/事件） | stable | contract + kernel |
| | **evolution（SkillDraft/promote/validate_draft）** | **experimental**（排除出 1.0 承诺） | api（bridge） |
| | portal（页面生成） | stable | `chiyu_portal.api` |

 sanctioned import 面（唯一合法通道）：`chiyu_kernel.api` / `chiyu_kernel.contract`（含子树）/ `chiyu_kernel.approval` / `chiyu_decision.api` / `chiyu_portal.api`；门禁 `tools/check_import_surface.py`。

## 二、三仓采用矩阵（源码级，本轮实证）

| 能力 | CRM（Node 桥接式） | APS（Python 契约直连+编排自持） | enterprise（Python 全门面） |
|---|---|---|---|
| decision 脊柱 | ✅ run_spine 经 sidecar/shadow（QUOTE_PRICING 1/27，P1 试点） | ⚠️ 机制采纳自持（KmdSpine），run_spine 仅 spike；双轨接线 10-20 | ✅ run_spine/resume_spine 六阶段直连 |
| 八要素/九尺子 | ⚠️ N1 映射层已交付未接线；RUBRIC_KEYS 已改 import（N2 闭环） | ✅ 直连+is 同一性断言 | ✅ 直连原生，0 重实现 |
| 四评分矩阵 | 不适用（enterprise 消费面） | 不适用（基座未下发） | ✅ 全链路+复盘闭环 |
| audit 双轨 | ✅ 消费 run_spine 内建 | ✅ 双轨 E2E 4 passed（M2） | ✅ persister/approval 闸全接 |
| approval | ✅ RedlinePriorityGate 复用 | ✅ RedlinePriorityGate | ✅ DecisionApprovalVerdict |
| memory 决策记忆网 | ❌ 未接（可选，自有 decisionRepo） | ❌ 未接（可选，自持轨道） | ✅ build_memory_recaller + store（C3a） |
| graph 受控边写 | ✅ write_controlled_edges 两阶段（kill-switch 默认休眠） | ❌ psycopg3 同纪律重实现（R1 允许） | ✅ PgVectorStore 多 store |
| canary / 能力闸 | ✅ require_capabilities({graph,mcpserver}) | ✅ 能力闸（foundation.py） | ✅ lifespan 六键 stable fail-closed |
| events / actions / scenario | ❌ 自有 action 体系（合规） | ❌ 自有 ActionDef（M1 守卫已落） | ✅ ActionRegistry/EventBus/register_scenario/DecisionIOField |
| llm / mcpserver | ✅（自有 LLM 通道，桥接 MCP） | ⚠️ R7 真 transport 排期 10-23/11-06 | ✅ LlmProvider/McpBridge |
| **evolution** | ❌ | ❌ | ⚠️ **bridge.py 在用（experimental）** |
| portal | ❌ | ❌ | ❌（观察项） |

## 三、总裁定

1. **enterprise**：全门面深度消费，四件套全合规、R-E 全闭环、四模式机检化——由"整改模式"转入**维持+月度回捐模式**。
2. **APS**：机制合规、三硬判据有实测、C-B 零违规；核心欠账是**生产实证破零与接线执行**（10-20/10-27/11-06 三节点）——**排期盯办模式**。
3. **CRM**：脊柱消费合规、R-C/N1/N2 全闭环；核心欠账是**覆盖广度**（1/27 场景）与 N6 概念残留——**扩面迁移模式**。

## 四、foundation 侧自欠账（不在三仓，登记在此）

| # | 项 | 级别 |
|---|---|---|
| F1 | 平台级 EBUSY 汇总上报文档（enterprise 两次留证+CRM 根因修正已收，APS 未报；foundation spawnSync 假红排查待做） | P1 |
| F2 | portal 门面三仓零消费——观察项：判定为内部能力或补消费引导 | P2 |
| F3 | evolution 被 enterprise 在用但属 experimental——对外口径须防"1.0 承诺"误读（本册 §五 enterprise 要求①） | P2 |

## 五、差异化要求（分册已投三仓 docs/，本册为总表）

- **CRM 分册**：P2 扩面（M2 同面证据门禁+N1 映射层接线）、N6 注释残留清理、七维概念对拍锚定、sidecar 版本握手回传。
- **APS 分册**：三节点盯办（接线/破零/回执）、E5 重放、N6 清理、R7 transport 排期、⛔ 禁一步换 spine。
- **enterprise 分册**：evolution experimental 口径纪律、月度回捐、M3/M4 例行、U2/ELEMENT_PRIORITY 字面量同步点。

（各分册均含验收判据与回信通道；复核窗口随既有节点。）
