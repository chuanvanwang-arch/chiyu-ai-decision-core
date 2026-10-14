# foundation 三支柱收敛设计 —— 三平台重复能力上收方案

> 定位：本仓作为 **AI 原生底座唯一事实源**，需把三平台（CRM / APS / enterprise）在三大支柱上各自重复实现的能力**收敛上收**。
> 本设计为**收敛裁定稿**（P6·设计文档），供用户评审后转 writing-plans 分批实施。
> 来源证据：三仓源码逐文件盘点（2026-10-13 实测）+ foundation 既有层对照。

---

## 0. 三大支柱定义（用户口径）

| 支柱 | 企业诉求 | 对应 foundation 既有面 | 现状 |
|---|---|---|---|
| **① 决策有效性 + 闭环追溯** | 决策是否有效、能否从结局回溯到依据 | `run_spine`/`resume_spine` + `write_decision_memory_net` + `recall_precedents`/`build_memory_recaller` + `REFERENCED_PRECEDENT` | ✅ 基座已建成 K-M-D 记忆网 + 单源守卫；但三平台仍有**并行写者** |
| **② 安全可审计** | 谁在何时基于什么做了什么，不可篡改 | `audit/chain.py`（SHA-256 链）+ `ApprovalGate` 五符号 + `AUDIT_EVENT_*` + `AUDIT_RECORD_KIND` | ✅ 基座已建成；但三平台各建 audit 表/评分/枚举 |
| **③ 自我进化** | 系统从决策反馈中自我改进但保持人工可控 | `evolution/`（experimental：guard/knob/prescription/replay/readiness/skill_draft）+ 七闸认证 | ⚠️ **experimental**，未毕业；三平台各建 HITL 进化链 |

---

## 1. 三平台重复能力实证盘点（2026-10-13 逐文件）

### ① 决策有效性 + 闭环追溯 —— 重复的「记忆网写者」与「脊柱执行器」

| 平台 | 重复实现 | 文件（锚点） | 与基座关系 |
|---|---|---|---|
| **APS** | 自造 KMD 脊柱执行器 | `src/aps/platform/kmd.py`（S1→S5 执行器） | ⚠️ 已按契约收窄到基座 `run_spine` 组合（kmd.py:3-7 声明"初版判定作废"）；仍保留 S1 装配/S2 判分/域红线 | 域特有，**保留** |
| **CRM** | 自己的记忆写者链 | `src/memory/`（capture/precipitate/promote/distillScheduler/judge/note）+ `src/decision/edgeWrite.js`/`edgeMirrorToFoundation.js`/`edgeDimensionSpec.js` | ⚠️ `edgeMirrorToFoundation` 已回镜基座；但 `src/memory/` 仍自建记忆管道 | **上收写者**，CRM 改消费基座 `write_decision_memory_net` |
| **CRM** | 闭环/复盘自实现 | `src/decision/closure.js`/`closureLoop.js`/`retro.js`/`retroPromote.js`/`decisionRetro.js`/`retroTrigger.js` | 域复盘（决策结局→判定），基座无统一复盘形态 | 复盘形态候选收敛 |
| **enterprise** | 自己的决策记忆网读写 | `host/decision_memory_store.py` / `decision_memory_recall.py` | ⚠️ **与基座 `write_decision_memory_net`/`recall_precedents` 直接重复**（基座 single-writer 守卫已立） | **最优先上收**（双写者冲突） |
| **CRM** | 先例召回自实现 | `src/decision/scenarioAdvisors.js` | 基座 `recall_precedents` + `build_memory_recaller` 已有 | 上收召回 |

**结论①**：基座**已有完整 K-M-D 决策记忆网**（`write_decision_memory_net` 是 graph_edge 唯一写者、`PgNoteStore` 是 particle_attribute 唯一写者、`recall_precedents`/`build_memory_recaller` 是读路径）。收敛重点 = **消灭三平台并行写者**，统一走基座单源；保留各平台 S1 域装配与域判分（R134）。

### ② 安全可审计 —— 重复的「审计事件枚举」「审计落库」「可审计性评分」

| 平台 | 重复实现 | 文件（锚点） | 与基座关系 |
|---|---|---|---|
| **enterprise** | 自建决策审计表 | `host/decision_audit_store.py`（自建 `decision_audit` 表，_DDL:26-42） | ⚠️ 基座 `AUDIT_RECORD_KIND="audit"` + `audit_persister`（RFE audit-first）已定形态；enterprise 表**字段漂移**风险 |
| **CRM** | 可审计性 4 问 / 审计钩子 | `src/decision/auditability.js`（Q1-Q4 评分）、`src/action/auditHook.js`、`src/decision/provenance.js` | 基座无「可审计性评分」原语，但有 `audit/chain.py` 链 | Q1-Q4 评分→候选收敛原语 |
| **APS** | 安全/违规审计 | `src/aps/platform/security.py` + `violation_store.py` + `capability_audit.py` + `audit.py` | 域安全（违规定义）留 APS；审计事件形态候选对接基座 | 分界：域安全留，事件形态上收 |
| **enterprise** | 审批状态机 | `approval/state_machine.py` | 基座 `ApprovalGate` 五符号 + `DecisionVerdictState` | 校验是否重复 gate |

**结论②**：基座**已有审计链（SHA-256）+ 审批闸 + 审计事件常量**。收敛重点 = ① 统一**审计事件枚举**（`AUDIT_EVENT_*` 闭集已定，三平台 match 只准引用常量——G4 铁律已在 T68 落地）；② 统一**审计轨落库形态**（`audit_persister` + `AUDIT_RECORD_KIND`，enterprise `decision_audit` 表须对齐或改消费基座）；③ CRM **Q1-Q4 可审计性评分**上升为基座原语（跨平台复用）。

### ③ 自我进化 —— 重复的「HITL 草稿→回测→生效」链

| 平台 | 重复实现 | 文件（锚点） | 与基座关系 |
|---|---|---|---|
| **CRM** | 自造 ICP 自进化 | `src/evolution/icpSelfEvolution.js`（draft→backtest→HITL approve，铁律与基座 evolution 语义**逐字同构**） | ⚠️ 高重复：基座 `evolution/readiness.py` 七闸 + `prescription.py::apply_atomic` + `skill_draft` 已定「草稿绝不自动生效」 |
| **APS** | 自造进化环 | `src/aps/platform/evolution_feed.py` + `outer_loop.py` + `weight_tuner.py` + `promotion.py` | ⚠️ 权重调参属域；但「草稿→回测→HITL→promote」形态与基座 `skill_draft` 重复 |
| **enterprise** | 已消费基座 SkillDraft | `evolution/bridge.py`（订阅决策事件→SkillDraft→validate→promote，标注 experimental） | ✅ **已走基座**（E1 守则），是正确范例 |

**结论③**：基座 `evolution/` **已具备完整原语**（guard/knob/prescription/replay/readiness/skill_draft + 七闸认证），但 **experimental 未毕业**。收敛重点 = ① 把「**HITL 草稿→回测→生效**」抽为基座**毕业候选**原语（CRM icpSelfEvolution 与之逐字同构是强信号）；② APS `promotion.py`/`outer_loop.py` 的 promote 形态并入 `skill_draft`；③ enterprise bridge 已是正确消费者，作为**毕业验收锚点**。

---

## 2. 收敛原则（C-B 等权铁律 / R134 边界重申）

> **基座只收「形态 / 原语 / 契约」，域特有留消费方可配置注入。**

| 收敛（基座收） | 不收敛（留消费方） |
|---|---|
| 契约常量、事件枚举、状态机 | 行业评分矩阵（enterprise strictness M1-M4 / CRM / APS 域评分） |
| 通用原语（记忆网单写、审计链、HITL 进化、可审计性评分、先例召回） | 域判分逻辑、域红线词表、域风险/违规定义、阈值数值 |
| 形态（S1-S5 时序、单源写、审计轨 vs 业务轨） | 表结构细节、租户/场景配置布局、行业命名 |
| 毕业路径（experimental→stable 判据） | — |

**⛔ 硬边界**：foundation 一律不反向依赖 decision/api 外的内部模块；三平台经 sanctioned 门面（`chiyu_kernel.api` / `chiyu_kernel.contract` / `chiyu_approval`）消费。本设计任何收敛项都不得突破 `tools/check_import_surface.py` 的 SANCTIONED 集合。

---

## 3. 应该本仓收敛的内容清单（按优先级）

### ③ 已由基座锁定、只待消费方切换（零基座改动，先做）

| # | 收敛项 | 基座既有 | 消费方动作 |
|---|---|---|---|
| C1 | **记忆网单写收敛** | `write_decision_memory_net`（graph_edge 单写）+ `PgNoteStore`（particle_attribute 单写） | **enterprise** 删 `decision_memory_store/recall` 自实现，改消费基座；**CRM** `edgeWrite` 走 `edgeMirrorToFoundation` 单写路径（`src/memory/` 蒸馏可留，落库统一基座） |
| C2 | **审计事件枚举统一** | `AUDIT_EVENT_*` + `AUDIT_APPROVAL_EVENTS` 闭集（T68 已 re-export 至 api） | 三平台 match 只准引用常量（G4），禁裸字符串；enterprise `decision_audit.verdict` 值域对齐 `DecisionVerdictState` |
| C3 | **审计轨落库形态统一** | `run_spine(audit_persister=...)` + `AUDIT_RECORD_KIND` | **enterprise** 使其 `decision_audit_store` 消费基座 audit_persister，或字段对齐基座载荷（decision_id/verdict/requisite/rubric_scores/elements） |

**C1-C3 是"已经建好、只待接通"**：基座零改动，消费方对齐。这正是仓库当前最需要的收敛——消除双写者/双形态。

### ② 基座新增原语（有跨平台复用价值，需新增稳定面）

| # | 收敛项 | 理由 | 建议落点 |
|---|---|---|---|
| C4 | **可审计性评分原语**（CRM Q1-Q4） | APS 审计 + enterprise 审计均需「这决策可不可审计」的同一口径；CRM `auditability.js` 已成熟、单源 | 基座新增 `chiyu_kernel.audit.auditability4q`（纯函数：追溯+冲突+快照维度→N/4 health），re-export 至 api |
| C5 | **先例召回 + 记忆召回装配** | 基座 `recall_precedents`/`build_memory_recaller` 已有读路径，但 CRM `scenarioAdvisors`、enterprise `decision_memory_recall` 各写召回 | 统一消费基座召回 + `REFERENCED_PRECEDENT` 出边，形成「写了能读」闭环（T41 已立接缝） |

### ③ 自我进化（experimental，须先毕业）

| # | 收敛项 | 理由 | 前置 |
|---|---|---|---|
| C6 | **HITL 草稿→回测→生效 原语毕业** | CRM `icpSelfEvolution` 与基座 `evolution/` 语义逐字同构 = 强证明「草稿绝不自动生效」是通用规律；抽为毕业候选原语 | **evolution 毕业**：走 RFE（比照 memory T44 先例），由 readiness 七闸 → stable |
| C7 | **skill_draft 沉淀统一** | enterprise `bridge` 已消费；APS `promotion.py` 的「草稿→promote」形态并入 | 随 C6 毕业 |

**⛔ 纪律**：C6/C7 落 experimental 面之前，对外口径必须标注 experimental，不得表述为稳定承诺（R-FE1，bridge.py:17-24 已有此纪律文本）。

---

## 4. 建议实施顺序（writing-plans 分批）

| 阶段 | 内容 | 基座改动 | 风险 |
|---|---|---|---|
| **P1（本周）** | C1-C3 消费方切换（enterprise 记忆网单写、审计事件/落库对齐；CRM edgeWrite 单写） | **零**（纯消费方） | 低——基座已全绿，只动消费方接线 |
| **P2（次周）** | C4 可审计性评分原语 + C5 先例召回装配 | 新增 `audit/auditability4q` + re-export | 中——新符号需登记 version.py CAPABILITIES + 单源守卫 |
| **P3（规划）** | C6/C7 evolution 毕业 + 进化原语上收 | evolution 毕业 RFE + 原语抽提 | **高**——experimental→stable 需 readiness 七闸验收 + 全量回归 |

**验收口径**：每收敛项 = 消费方删自实现 + 改消费基座单写 + 变异自证（删基座判据→转红→还原）。
**⛔ 边界**：本仓只做基座侧收敛（C4-C7 的新增原语/毕业）；C1-C3 属消费方接线，**落消费方仓**，本仓只出裁定+校验。

---

## 5. 待用户拍板

1. **C1 优先落地**：enterprise `decision_memory_store/recall` 与基座 `write_decision_memory_net` 双写者冲突最直接，是否授权推进 enterprise 切换（属消费方仓，base 出裁定）？
2. **C4 可审计性评分原语**：是否同意把 CRM Q1-Q4 上升为基座原语（新符号需登记 CAPABILITIES）？
3. **C6 evolution 毕业**：是否开启 evolution 毕业 RFE（比照 memory T44 先例）？毕业是 C6/C7 前置，风险最高。

---

*本设计基于 2026-10-13 三仓源码逐文件盘点；基座符号与守卫以 `chiyu_kernel.api`/`contract`/`approval` sanctioned 门面为唯一事实源。*
