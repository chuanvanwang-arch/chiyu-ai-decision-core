# foundation 征询函 —— 三大企业能力需求收集（致 CRM / APS / enterprise）

> **发出方**：foundation（AI 原生底座唯一事实源）
> **日期**：2026-10-13
> **致**：CRM-ai-native / APS-ai-native / chiyu-enterprise 三消费仓
> **性质**：需求征询函（非裁定稿）—— 站在**企业级 AI 项目落地需求**角度，**分别**收集三仓对三大能力的企业级需求，作为 foundation 收敛/增强的**需求输入**（先本仓、后三仓改造的前提是：先问清三仓究竟要什么）。
>
> **纪律**：总纲落本仓 `docs/`；三仓**分册**（§一/§二/§三）由各仓自行认领填写，回执投回本仓 `docs/`。回执须附源码锚点，可机检；缺锚点的申报不采纳。

---

## 〇、背景与目的

三仓各自已在企业级落地中**独立实现**了三大能力（决策闭环/审计/进化的局部方案），但存在重复与口径漂移。foundation 作为底座要收敛并提供**统一、稳定、全面**的能力出口，**必须先摸清三仓在企业级项目中的真实需求**——不是本仓单方拍板，而是**需求驱动收敛**。

本函围绕三大能力展开，请三仓基于各自企业级项目的**真实痛点**（合规要求、客户验收、规模/性能、审计追责、人机协作流程）回答。每项能力附**统一问题集**，三仓按分册逐条回答。

## 三大能力定义（企业价值口径）

| # | 能力 | 企业价值 | foundation 现状 |
|---|---|---|---|
| **① 企业 AI 决策的有效性与闭环追溯** | 决策**有效**（有据可依、可判对错、质量可度量）+ **闭环**（决策→执行→结局→复盘→喂回下一决策可追溯） | run_spine/resume_spine + 九尺子/八要素 + 记忆网先例召回；但**缺结局采集/复盘/有效性度量管道** |
| **② 企业安全的解决方案 + 可审计可追溯的解决方案** | 完整企业安全（IAM/鉴权/RBAC/越权防护/**人机协作、智能体决策后的人工审批 HITL**）+ 可审计可追溯（谁/何时/基于什么/做了什么，追得回、不可篡改） | audit 链(SHA-256)+审批闸(DecisionApprovalGate/interaction.ApprovalGate)；但**缺 IAM/auth/rbac 安全层** |
| **③ 自我进化能力** | 系统从决策反馈中自我改进（阈值/技能/规则/知识）且**人工可控** | evolution/（experimental：guard/knob/prescription/replay/readiness/skill_draft）未毕业 |

---

## ★ 统一问题集（三仓共同回答）

针对每项能力，请从**企业级项目角度**回答以下问题（每项给 1–5 档优先级，P0=必须进 1.0 稳定承诺；P1=强烈需要；P2=可选）：

### 能力① 决策有效性与闭环追溯
- **Q1.1 现状**：你仓当前如何实现"决策有效性"度量？如何实现"决策→结局→复盘"闭环？（附源码锚点）
- **Q1.2 企业级痛点**：上线企业项目时，客户/合规最常质疑什么？（决策凭什么这么判？错了怎么追责？）
- **Q1.3 期望基座能力**：你希望 foundation 提供什么**统一形态**？是"有效性度量管道（评分/置信/命中率）"还是"闭环追溯管道（复盘/结局采集/负面先例）"还是"两者"？
- **Q1.4 边界**：哪些必须是基座原语？哪些是你仓域特有（必须保留在消费方）？

### 能力② 企业安全 + 可审计可追溯
- **Q2.1 现状**：你仓当前如何实现"企业安全"（IAM/RBAC/鉴权/越权防护）？如何实现"人机协作、智能体决策后的人工审批 HITL"？（附源码锚点）
- **Q2.2 企业级痛点**：企业项目对"安全"最苛刻的要求是什么？（多租户隔离？最小权限？审计追责到个人？人工审批留痕？）
- **Q2.3 期望基座能力**：你希望 foundation 提供什么**企业安全统一层**？哪些（如 IAM/RBAC/鉴权/审计链/HITL 审批）必须进基座？
- **Q2.4 边界**：哪些安全能力是你仓域特有、不可上收？

### 能力③ 自我进化
- **Q3.1 现状**：你仓当前如何实现"自我进化"？（阈值/规则/技能/知识自改进，人工可控吗？）（附源码锚点）
- **Q3.2 企业级痛点**：企业项目对"自我进化"最担心的风险是什么？（失控？过拟合？无人工闸？）
- **Q3.3 期望基座能力**：你希望 foundation 提供什么**进化原语**？"HITL 草稿→回测→生效"是否是你仓期望的通用形态？
- **Q3.4 边界**："人工可控"的闸（HITL）必须基座保证还是消费方自担？

### 跨能力
- **Q4**：三能力间的耦合——你认为这三者是独立能力，还是互为前提（如：安全审计是决策闭环的追溯轨，进化消费决策闭环的复盘输出）？

---

## 一、CRM 分册（现状盘点 · 请逐条回答）

### ① 决策有效性与闭环追溯
你仓是闭环最完整的：`src/decision/closure.js`（K/M/J 三图聚合 + crossLoopMap D1-D5）、`outcome.js`（won/lost/paid 结局采集）、`decisionRetro.js`/`retroPromote.js`（复盘/推进）、`decisionTrace.js`/`auditability.js`（4 问可审计性）、`provenance.js`。
- **企业级观察**：你仓"有效性度量"（4 问评分/逆转率）与"闭环追溯"（复盘/结局）已自成体系。
- **对本函的需求视角**：请回答 Q1.1–Q1.4 —— 你希望 foundation 把"闭环追溯管道（复盘+结局+负面先例+处方）"沉淀为基座原语，还是保留在 CRM 域？

### ② 企业安全 + 可审计可追溯（含 HITL）
你仓有 `src/page/guardrails.js`、`src/approval/`（approvalConfig/stateMachine）、`src/action/auditHook.js`、`src/decision/provenance.js`、`src/config/configDecision.js`。
- **企业级观察**：你仓以"业务护栏 + 审批流 + 审计钩子"局部覆盖，未见完整 IAM/RBAC 层。
- **请回答 Q2.1–Q2.4**：企业级落地中，你是否需要 foundation 提供统一的**企业安全层（IAM/RBAC/鉴权/越权防护）**与**HITL 人工审批原语**？

### ③ 自我进化
你仓 `src/evolution/icpSelfEvolution.js`（ICP 草稿→回测→HITL approve）+ `retroPromote.js`。
- **请回答 Q3.1–Q3.4**：`icpSelfEvolution` 与 foundation evolution 原语语义逐字同构，是否支持将该形态沉淀为基座毕业原语？

---

## 二、APS 分册（现状盘点 · 请逐条回答）

### ① 决策有效性与闭环追溯
你仓 `src/aps/platform/kmd.py`（S1-S5 域执行器）+ `reflux.py`（K-M-D 单回流管道四通道：C1 事实/C2 反面先例/C3 处方 PENDING/C3′ 记忆影响）+ `feedback_loop.py`/`outer_loop.py`/`projection.py`/`sla_escalation.py`。
- **企业级观察**：你仓已按专利 F 收敛四条回流链为一条管道 + 四通道，形态与 CRM `closureLoop.js` 对齐。
- **请回答 Q1.1–Q1.4**：你希望 foundation 沉淀"K-M-D 回流管道"为基座原语吗？还是 APS 域管线保留？

### ② 企业安全 + 可审计可追溯（含 HITL）
你仓 `src/aps/platform/security.py`（RBAC + 权限矩阵 + 三档 off/advisory/enforced + principal 作用域）+ `audit.py`/`violation_store.py`/`capability_audit.py` + `store.scoped_identity()`。
- **企业级观察**：你仓是最早自主实现 RBAC 安全层的，三档模式（off/advisory/enforced）是有价值的渐进收紧范式。
- **请回答 Q2.1–Q2.4**：你愿意把安全层形态贡献给 foundation 统一吗？三档模式是否应成为基座默认？

### ③ 自我进化
你仓 `evolution_feed.py`/`outer_loop.py`/`weight_tuner.py`/`promotion.py`。
- **请回答 Q3.1–Q3.4**：权重调参属域特有权重，但"草稿→回测→HITL→promote"形态是否应沉淀基座？

---

## 三、enterprise 分册（现状盘点 · 请逐条回答）

### ① 决策有效性与闭环追溯
你仓 `decision/strictness.py`（M1-M4 矩阵）+ `host/decision_memory_store.py`/`recall.py`（记忆网读写）+ `decision_audit_store.py` + `retro_backend.py`（复盘调度落库）。
- **企业级观察**：你仓已深度消费基座（run_spine/PgVectorStorePersister/degraded_recall）。
- **请回答 Q1.1–Q1.4**：复盘（retro）与记忆网你希望由基座统一，还是 enterprise 域管？

### ② 企业安全 + 可审计可追溯（含 HITL）
你仓 **安全方案最完整**：`host/governance.py`（IAM 五档角色 + token 验签/过期/吊销 + 两阶段 confirm + 写闸 G0-G1.6 + **三段审计链 requested/executed/failed**）+ `iam_backend.py`（IAM 存储）+ `tenant/rbac.py`（双层角色 effective_roles）+ `host/approval_backend.py` + `approval/state_machine.py`。
- **企业级观察**：你仓已是一套**完整的企业安全解决方案**，且"人机协作（confirm 两阶段）+ 智能体决策后人工审批（approval）"俱备，正是本函②的定义。
- **请回答 Q2.1–Q2.4**：这是**最该上收/沉淀进基座**的候选。你是否愿意把 governance/iam/rbac/approval 形态贡献为 foundation 统一企业安全层（供 CRM/APS 复用）？

### ③ 自我进化
你仓 `evolution/bridge.py`（订阅决策事件→SkillDraft→validate→promote，标注 experimental，已走基座）。
- **请回答 Q3.1–Q3.4**：你已是基座 evolution 的正确消费者，是否支持 evolution 毕业 + 三仓进化原语统一？

---

## 四、回执要求

1. **回执投递**：三仓各自在 `docs/` 落 `2026-10-13-<仓>答foundation征询-三大企业能力需求.md`（或合并回答本函 §一/§二/§三）。
2. **可机检**：每题须附源码锚点（仓内文件+行号/符号名），缺锚点申报不采纳。
3. **优先级**：每题标注 P0/P1/P2；P0 = 必须进 foundation 1.0 稳定承诺，foundation 据此排收敛批次。
4. **回执期限**：建议 2026-10-16 前回投，foundation 据三仓回执汇总收敛清单（先本仓增强、后三仓对齐）。

---

*foundation 征询函 · 2026-10-13 · 本仓留档；分册由三仓各自认领。*
