# foundation 整体架构图（三支柱 × 完整能力面）

- 日期：2026-10-13
- 性质：本仓整体架构说明（等待三大能力需求征询回执期间产出）
- 内容：**三大支柱**（企业价值口径）横贯 **五层运行栈 + 决策族 + portal**，以**五个 sanctioned 门面**为消费方唯一出口；权威来源 = `docs/2026-10-12-foundation核心功能清单(全门面枚举).md` + 源码实测

---

## 一、三大支柱（企业价值口径，2026-10-13 用户定稿）

| # | 支柱 | 映射能力族 | 支撑符号（锚点） | 现状 |
|---|---|---|---|---|
| **① 决策有效性与闭环追溯** | 决策有效（有据可依/可判对错/质量可度量）+ 闭环（决策→执行→结局→复盘→喂回） | 决策族 · 数据层 · 语义层 | `run_spine`/`resume_spine`、`score_rubric`、`aggregate_confidence`、`write_decision_memory_net`、`recall_precedents`、`DecisionApprovalGate` | ✅ 基座大部分已有；**缺结局采集/复盘/有效性度量管道**（三仓有，待征询） |
| **② 企业安全 + 可审计可追溯** | 完整企业安全方案（IAM/RBAC/鉴权/越权防护 + 人机协作/**智能体决策后人工审批 HITL**) + 可审计可追溯（追得回/不可篡改） | 决策族审批 · 数据层 audit · 集成层两阶段 confirm | `RedlinePriorityGate`、`chain_hash`/`verify_chain`、`issue_confirm_token`/`verify_confirm_token`、`SandboxedFs`/`FORBIDDEN_HOSTS` | ⚠️ 基座已有审批闸+审计链+两阶段 confirm；**缺 IAM/auth/rbac 安全层**（enterprise/APS 有，待征询） |
| **③ 自我进化** | 从决策反馈自改进（阈值/技能/规则/知识）且**人工可控** | 进化层 | `SkillDraft`/`promote`/`validate_draft`、`Prescription`/`KnobTable`/`begin_replay`、`readiness_report`（七闸） | ⚠️ **experimental 未毕业**（exclude 1.0 承诺），待 RFE 毕业 |

## 二、五层运行栈（完整能力面）

| 层 | 能力族（目录/符号） | 稳定位 |
|---|---|---|
| **L0 契约层** | `chiyu_kernel.contract` · decision契约 · memory契约 · profile · particle · audit事件 · evolution契约 · `manifest.json` 守卫 | stable |
| **数据层** | store/persist/vector/pg · graph(受控写) · audit链 · `PgVectorStore`/`NoteStore`/`PgVectorStorePersister` | stable |
| **语义层** | ontology/context分层/domain · canary金丝雀 · audit规范 · `OntologyGraph`/`assemble`/`canary_probe` | stable |
| **运行层** | actions/events/workflow · orchestration/plan/scenario · session · `ActionRegistry`/`EventBus`/`WorkflowRunner`/`AgentRegistry`/`DecisionScenarioProfile` | stable |
| **集成层** | llm/mcp(client+server)/tools/plugins/hooks · 两阶段confirm · 沙箱 · `McpBridge`/`SandboxedFs`/`HookBus` | stable |
| **进化层** | skill_draft/promote · prescription/knob/replay · readiness七闸 | ⚠️ experimental |
| **portal 页层** | NL→schema/render · PageStore/onboarding | stable（三仓零消费，观察项） |

## 三、决策族（三支柱交汇核心）

- **决策脊柱**：`run_spine`/`resume_spine` · S1→S5 · 置信度 ratio(铁律 C-B) · 红线(链末) · 审批三态闸(APPROVED/REJECTED/PENDING)
- **评分体系**：九尺子(RUBRIC_KEYS 等权 0-4) · 八要素(EIGHT_ELEMENTS) · 封顶(ELEMENT_RUBRIC_CAPS)
- **契约**：SPINE_ORDER · CONFIDENCE_SOURCE_KEY · AUDIT_EVENT_* · GATE_KINDS/IO_KINDS
- **记忆网（闭环追溯）**：write_decision_memory_net(单写) · recall_precedents · build_memory_recaller · degrade_recall/RRF

## 四、对外出口 · 五个 sanctioned 门面

```
chiyu_kernel.api · chiyu_kernel.contract(含子树) · chiyu_kernel.approval
chiyu_decision.api · chiyu_portal.api
≈478 符号(listed) / 499 唯一 · 门禁 tools/check_import_surface.py
```

## 五、版本出口与稳定性护栏

- **版本出口**：`API_VERSION`(1.0.0) · `CONTRACT_VERSION`(1.0.0) · `__version__` · `capabilities()`/`capability_status`/`deprecations()` · `require_capabilities`(消费方 fail-closed 能力闸)
- **能力登记**：`version.py::CAPABILITIES` 29 层 = 28 stable + evolution experimental
- **门禁组合**：`check_import_surface.py`(合法面) · `check_facade_coverage.py`(门面覆盖) · `check_zero_residue.py`(零残留) · `check_single_source_memory.py`(记忆单源) · 全量回归 make test(test-all 含根 tests)

## 六、收敛待决（接三仓征询回执后）

本架构标注的 ⚠️ 缺口（企业安全层 / 决策闭环管道 / evolution 毕业）正是「三大能力需求征询函」(T72) 待三仓回执后按 P0-P2 排收敛批次的对象。**先本仓增强、后三仓对齐**。

---

*foundation 整体架构图 · 2026-10-13 · 本仓留档；随征询回执更新。*
