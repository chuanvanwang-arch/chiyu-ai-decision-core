# CRM 答 foundation 征询 —— 三大企业能力需求（CRM 分册回执）

> **回执方**：CRM-ai-native（消费方）
> **日期**：2026-10-13
> **答复对象**：《foundation 征询函 —— 三大企业能力需求收集（致 CRM / APS / enterprise）》（本函 §一 CRM 分册）
> **纪律**：全部源码锚点于 2026-10-13 **现场 grep 核验**（文件存在性 + 导出符号 + 行号逐条实取），可机检；来文点名 13 文件全部实存，无虚构。
> **优先级口径**：P0 = 必须进 foundation 1.0 稳定承诺；P1 = 强烈需要；P2 = 可选。

---

## 一、能力①：决策有效性与闭环追溯

### Q1.1 现状（有效性度量 + 闭环实现）

**有效性度量（4 问评分 + 聚合）**：
- `computeAudit4q`（`src/decision/auditability.js:34`）：对单决策做 4 问逐项 pass/warn/fail 判定（Q1 溯源材料充足性门控 `Q1_MIN_SUPPLIED_DIMS=5` 见 `auditability.js:18`；Q2 含**篡改检测**——`aggregateAuditability` 中 `r.questions.Q2.status === 'fail'` 计入 `tampered`，见 `auditability.js:190`）。
- `aggregateAuditability`（`auditability.js:164`）：窗口聚合出 `auditability_pct`（4 问均分百分比）、`full`（满分）、`with_conflict`（需人工复核）、`tampered`（Q2 fail）；空窗口降级返回 `pct=null` 不报错（`auditability.js:195`）；单决策超时/异常**跳过并诚实暴露未评，不掩盖为绿**（`auditability.js:182`）。
- **结局→置信度校准**：`outcomeToConfidence`（`src/decision/outcome.js:14`）把业务结局类型映射为置信度增量——这是「决策对不对」的定量回路。

**闭环（决策→执行→结局→复盘→喂回）**：
- **结局采集**：`writeOutcome`（`outcome.js:19`）+ `OUTCOME_TYPES = ['won','lost','paid','stalled','partial','other']`（`outcome.js:7`）；`listOutcomes`（`outcome.js:55`）。
- **闭环聚合**：`getDecisionClosure`（`src/decision/closure.js:109`）单决策三图聚合（K=事实 + M=关系 + J=判定/结局/校准），并输出**跨环映射 D1–D5**（`closure.js:100–104`）：D1 实体回写、D2 运行时边、D3 校准处方经第 0 闸写回、D4 结局反馈、D5 约束 SLA。
- **复盘**：`runDailyRetro`（`src/decision/decisionRetro.js:23`）每日复盘；`promoteLessonsFromRetro`（`src/decision/retroPromote.js:41`）把复盘结论按 `root_cause_class` 分类沉淀为 lesson **喂回**后续决策（`retroPromote.js:78` `kind:'lesson'`），跳过清单 `PROMOTE_SKIP_CLASSES = Set(['NEED_DIM_ORDER'])`（`retroPromote.js:16`）。
- **追溯**：`traceDecision` / `getImpact` / `getInsights`（`src/decision/decisionTrace.js:8/14/19`，上下游图追溯 maxDepth=3）。

### Q1.2 企业级痛点（P1）

客户/合规最常质疑的三件事，与 CRM 应对：
1. **「决策凭什么这么判」** → 4 问评分 + SHA-256 审计链（见能力②）。痛点在**各仓度量口径不一**：CRM 的 4 问、APS 的 SLA 升级、enterprise 的 strictness M1–M4 各自成体系，跨仓不可比。
2. **「错了怎么追责」** → 追责链要求「谁/何时/基于什么/做了什么」不可篡改且可复核。CRM 用 append-only + 墓碑擦除（`provenance.js:3`）实现，但这是**每个仓重复发明一遍**的轮子。
3. **「结果好不好怎么证明」** → 结局采集有（`outcome.js`），但**结局→决策质量的统计口径**（命中率/逆转率/校准曲线）无统一原语，CRM 的 `outcomeToConfidence` 是单点函数、缺成体系的度量管道。

### Q1.3 期望基座能力（P1）

**两者都要，但形态分级沉淀**：

| 基座原语候选 | 形态 | 优先级 |
|---|---|---|
| **结局采集 schema + 结局→置信度校准原语** | 通用化 CRM `OUTCOME_TYPES`/`outcomeToConfidence`：结局枚举 + 枚举→置信度映射表 + 采集 API。**度量管道的地基** | **P0** |
| **有效性度量管道**（评分/置信/命中率聚合） | 通用化 `aggregateAuditability` 的「窗口聚合 + 诚实降级（未评不掩盖为绿）」形态，评分器维度可插拔（4 问/SLA/strictness 各仓注入） | P1 |
| **复盘→lesson 喂回循环骨架** | 通用化 `runDailyRetro` + `promoteLessonsFromRetro`（`root_cause_class` 分类 + 跳过清单 + 喂回），与能力③进化共用 | P1 |
| **闭环追溯管道**（复盘/结局/负面先例/处方） | 与上条合并为「闭环管道」，负面先例存储契约由基座统一（memory 网已有先例召回，补「负面」维度） | P1 |

**暂不建议上收**：`getDecisionClosure` 的 K/M/J 三图聚合与 D1–D5 跨环映射（`closure.js:100–104`）——D1–D5 的载体全部绑定 CRM 图模型（`decision.involved_entities → particles`、`decision_relation`、`calibration_patch`），是 CRM 图 schema 特有，上收会造成基座反向依赖消费方 schema。

### Q1.4 边界

- **基座原语**（可统一）：结局类型枚举与采集契约、结局→置信度校准、复盘→lesson 循环骨架、负面先例存储契约、窗口聚合度量形态。
- **CRM 域特有**（必须保留在消费方）：K/M/J 三图与 D1–D5 载体（图 schema 绑定）、业务结局语义（won/lost/paid 是销售管线语义，制造/医疗行业租户可自定义枚举值——**枚举值须可配置**，基座只收「枚举机制」不收「具体枚举值」）、`root_cause_class` 分类学（`PROMOTE_SKIP_CLASSES` 是 CRM 维度顺序的领域约束）。

---

## 二、能力②：企业安全 + 可审计可追溯（含 HITL）

### Q2.1 现状

**鉴权/角色闸（RBAC 局部）**：
- `canWriteTenantConfig`（`src/http/middleware/rbac.js:58`）：租户配置写权限**单一事实源**（canonical=`ten_admin`，别名归一）。
- 双层角色闸：`src/rbac.js:32` 经销商闸（`channel_manager`/`ten_admin` + 功能总闸 + 跨租户拒绝，`src/rbac.js:13–21` 三重拒绝原因）。
- 前端 guard 第三层：`guardNlInput`（`src/page/guardrails.js:15`）NL 输入护栏。

**HITL 人工审批（智能体决策后）**：
- 审批状态机：`INSTANCE_STATES = ['PENDING_SUBMIT','APPROVING','APPROVED','REJECTED','CANCELED']` + `OPERATIONS_BY_STATE`（`src/approval/stateMachine.js:4/15`），非法迁移 `assertTransition`（`:27`）。
- 审批引擎全操作面：`startInstance:157` / `advanceTask:216` / `withdrawInstance:255` / `addSignTask:275` / `transferTask:297` / `returnTask:326`（`src/approval/engine.js`）；顺序闸 `seqCheck:19`、审批人解析 `resolveApprovers:80`。
- 审批配置面：`DEFAULT_APPROVAL_CONFIG`（`src/approval/approvalConfig.js:16`，租户可配）。
- **配置写第 0 闸**：`produceConfigDecision`（`src/config/configDecision.js:10`）——配置类写操作必须先产出决策凭证。
- **MCP 写两阶段确认**：`src/mcp/confirmToken.js:1`（A9 契约等价件：确认令牌绑定三元组，真值来源符号级对齐 `chiyu_kernel/mcpserver` 的 `issue_confirm_token`/`verify_confirm_token`）。
- **自治分级放行 fail-closed**：`autonomyEngine.js:319` `escalated = forceException || tier === 'HIGH' || !sceneAllowsAuto || (conf < effectiveThreshold)`——HIGH 级一律升级（`:309`）、场景级 `autonomous_allowed !== true → 一律升级`（`:293`）。QUOTE_PRICING 等高危场景 `default_tier='HIGH'` 由种子钉死（`db/seed.sql:253,257`，见 `adviceCard.js:54` 注释）。

**审计链（防篡改）**：
- **provenance SHA-256 链**：`shaChainEntry:66` / `shaChain:75`（`src/decision/provenance.js`，`HASH_VERSION=2` `:56`，链字段含墓碑 `HASH_FIELDS:57`）；append-only + `invalidated` 墓碑擦除不物理删除（`provenance.js:3,21`）。
- **动作审计钩子**：`recordAudit:38` / `verifyAuditChain:73`（`src/action/auditHook.js`，含价格变更专项审计 `recordPriceChangeAudit:60`）。

### Q2.2 企业级痛点（P0 性质）

企业项目对安全最苛刻的四条，CRM 全部实碰：
1. **多租户隔离**：所有审批/审计/决策表强制 tenant_id；跨租户即拒绝（`rbac.js` 闸三重原因）。痛点是**隔离是每张表每条 SQL 的纪律**，基座无原语则靠 review 人防。
2. **审计追责到个人**：actor 全链携带（`recordAudit` 的 `actor` 参数、审批 task 的 `approver`），且链不可篡改（SHA-256 + append-only）。
3. **人工审批留痕**：审批实例/任务全轨迹（谁提交/谁审批/意见/加签/转办/退回），这是客户验收的硬要求。
4. **智能体越权零容忍**：自治放行必须 fail-closed（`autonomyEngine.js:319`），高危场景永不自主。

### Q2.3 期望基座能力

| 候选 | 判断 | 优先级 |
|---|---|---|
| **HITL 审批原语**（决策后人工审批的通用状态机 + 两阶段确认） | **支持上收**。CRM 的 `confirmToken.js` 是 A9 契约**平行实现**（Node 侧重写 `issue/verify_confirm_token` 语义），基座提供原生实现可消除平行维护成本；审批状态机五态 + 全操作面语义通用（CRM 已被报价/配置/经销商三线复用）。**但毕业面必须走 `chiyu_kernel.api.__all__` 单一 sanctioned 通道**（对齐 C1 门禁纪律） | **P0** |
| **审计链原语**（SHA-256 + append-only + 墓碑） | **支持统一**。CRM `provenance.js` 与 foundation audit 链是双实现（同构），收敛为一份可减一套维护。墓碑擦除语义（GDPR 类需求 vs 禁 DELETE）须在基座层明确定义 | P1 |
| **IAM/RBAC 完整层** | **P2 观望**。CRM 的 RBAC 深度绑定业务角色语义（sales/ten_admin/channel_manager/经销商功能闸），上收收益有限；enterprise 的 governance 最完整，可先由 enterprise 供形、基座收「角色闸原语」（principal + scope + deny 理由结构化返回），具体角色矩阵留各仓 | P2 |
| **三档模式**（off/advisory/enforced 渐进收紧） | **认可为基座默认**（对 APS 形态的判断 CRM 从旁印证：CRM 自治分级/guardrails 实质是同构思想），P1 | P1 |

### Q2.4 边界（域特有、不可上收）

- **业务角色语义**：sales/ten_admin/channel_manager 等角色矩阵与租户功能闸（`feature:dealer-portal`）是 CRM 域概念。
- **报价红线审批**：BANT 未达禁报价、QUOTE_PRICING HIGH 恒升级（`db/seed.sql:253,257` + `autonomyEngine.js:319`）——红线规则是销售域知识。
- **审批规则解析**：`resolveApprovers`（`engine.js:80`）按 CRM 审批配置（部门/角色/金额阶梯）解析审批人，规则 DSL 留消费方。

---

## 三、能力③：自我进化

### Q3.1 现状

`src/evolution/icpSelfEvolution.js` 完整实现「草稿→回测→HITL 生效」三段：
- **草稿**：`proposeIcpRecalibration`（`:45`），`DRAFT_STATUS = ['draft','approved','rejected']`（`:13`）。
- **回测**：`backtestIcpDraft`（`:22`）——`passLine=0.6` + `minSample` 双闸，verdict ∈ `['threshold','count','noop']`（`:14`，分别对应：回测通过/样本不足/无操作）。样本闸**复用统一常量 `MIN_SAMPLE`**（`src/calibration/constants.js:5`，`icpSelfEvolution.js:10` import），禁自造数值（R5/R6 防过拟合噪声）。
- **HITL 生效**：`approveIcpRecalibration`（`:54`）须 approver 显式批准；全流程编排 `runIcpEvolutionPass`（`:63`，含 `dryRun`）。
- **另一条进化轨**：复盘 lesson 喂回（`retroPromote.js:41`，见能力①），同样人工可控（skip 清单 + 分类约束）。

### Q3.2 企业级痛点（风险）

CRM 最担心的三项与已有对策：
1. **失控**（未经验证的阈值写入影响全租户决策）→ 三重闸：回测 passLine + 最小样本 + HITL 显式 approve（`icpSelfEvolution.js:22/45/54`）。
2. **过拟合**（小样本回测假阳性）→ `minSample` 门控 + verdict 三态（样本不足显式返回 `count` 而非静默通过，`:14`）。
3. **无人工闸的自动生效** → `dryRun` 参数（`:63`）支持空跑预演；生效必须走 approve。

**核心风险判断：进化的危险性不在算法，在闸。某仓忘闸即失控。**

### Q3.3 期望基座能力

- **支持将「HITL 草稿→回测→生效」沉淀为基座毕业原语**（来文指出 `icpSelfEvolution` 与 foundation evolution 原语语义逐字同构——CRM 侧确认：草稿态枚举/回测双闸/显式 approve 逐项对得上）。优先级 **P1**。
- 毕业前置条件（CRM 立场）：
  1. evolution 目前标注 experimental（`evolution/guard/knob/prescription/replay/readiness/skill_draft` 未毕业）——**毕业须先过 readiness 评审 + 版本稳定承诺 + 走 `api.__all__` 单一通道**；
  2. 基座原语收**形态**（状态机 + 回测闸接口 + HITL 钩子），不收**域参数**（passLine/minSample 的具体值属消费方配置）；
  3. 进化的生效动作必须**强制经过能力②的 HITL 原语 + 留能力①的 provenance 审计痕**（见 Q4 耦合）。

### Q3.4 边界

- **「人工可控」的闸必须基座保证**（P0 性质）——理由：若 HITL 闸由消费方自担，则三仓各自实现、各自可能遗漏；进化原语的 graduated 版本应把「无 approve 不可生效」做成**基座不变式**（原语层面缺 approver 参数即抛错），而非文档纪律。
- **域特有留消费方**：ICP 阈值语义（`icp_draft` 的业务字段）、`root_cause_class` 分类学、回测样本的业务查询。

---

## 四、Q4：三能力耦合（CRM 判断）

**三者互为前提，非独立能力**。CRM 代码里的实际依赖方向：

```
② 安全/HITL（底座轨）
   ├─ 为 ① 提供追溯轨：provenance SHA-256 链挂 decision_id（provenance.js:21）
   └─ 为 ③ 提供人工闸：进化生效走 approval/confirm 原语
① 决策闭环（主干）
   ├─ 产出 ③ 的输入：runDailyRetro → promoteLessonsFromRetro（decisionRetro.js:23 → retroPromote.js:41）
   └─ 产出 ② 的审计对象：每条决策即审计链节点
③ 进化（消费端）
   └─ 消费 ① 的复盘输出 + 必须经 ② 的闸生效后反哺 ①
```

**对 foundation 的建议**：基座分层实现顺序 **② → ① → ③**（安全/HITL 为底、决策闭环为主干、进化为消费端）；进化原语毕业**必须**以 ② 的 HITL 原语与 ① 的 provenance 原语先毕业为前提，否则进化会在无闸/无痕状态下放开。

---

## 五、锚点机检总表（本回执全部源码引用）

| 文件 | 行/符号 | 用途 |
|---|---|---|
| `src/decision/auditability.js` | `:18` `Q1_MIN_SUPPLIED_DIMS`、`:34` `computeAudit4q`、`:164` `aggregateAuditability`、`:182` 未评不掩盖、`:190` tampered | 4 问度量 |
| `src/calibration/constants.js` | `:5` `MIN_SAMPLE`（被 `icpSelfEvolution.js:10` 复用） | 回测样本闸统一常量 |
| `src/decision/outcome.js` | `:7` `OUTCOME_TYPES`、`:14` `outcomeToConfidence`、`:19` `writeOutcome`、`:55` `listOutcomes` | 结局采集/校准 |
| `src/decision/closure.js` | `:100–104` D1–D5、`:109` `getDecisionClosure` | 三图闭环聚合 |
| `src/decision/decisionRetro.js` | `:23` `runDailyRetro` | 复盘 |
| `src/decision/retroPromote.js` | `:16` `PROMOTE_SKIP_CLASSES`、`:41` `promoteLessonsFromRetro`、`:78` lesson 喂回 | 复盘→喂回 |
| `src/decision/decisionTrace.js` | `:8/:14/:19` | 图追溯 |
| `src/decision/provenance.js` | `:3` append-only 墓碑、`:21` 墓碑列、`:56–57` `HASH_VERSION=2`/`HASH_FIELDS`、`:66/:75` sha 链 | 审计链 |
| `src/action/auditHook.js` | `:38` `recordAudit`、`:60` `recordPriceChangeAudit`、`:73` `verifyAuditChain` | 动作审计 |
| `src/http/middleware/rbac.js` | `:58` `canWriteTenantConfig` | 角色闸单一事实源 |
| `src/rbac.js` | `:13–21/:32` 经销商闸三重原因 | 双层闸 |
| `src/page/guardrails.js` | `:15` `guardNlInput` | 前端护栏 |
| `src/approval/stateMachine.js` | `:4` 五态、`:15` `OPERATIONS_BY_STATE`、`:27` `assertTransition` | 审批状态机 |
| `src/approval/engine.js` | `:19` `seqCheck`、`:80` `resolveApprovers`、`:157/:216/:255/:275/:297/:326` 全操作面 | 审批引擎 |
| `src/approval/approvalConfig.js` | `:16` `DEFAULT_APPROVAL_CONFIG` | 审批配置 |
| `src/config/configDecision.js` | `:10` `produceConfigDecision` | 配置写第 0 闸 |
| `src/mcp/confirmToken.js` | `:1` A9 两阶段确认（issue/verify_confirm_token 符号级对齐） | MCP 写闸 |
| `src/decision/autonomyEngine.js` | `:293` autonomous_allowed fail-closed、`:309/:319` HIGH 恒升级 | 自治放行 |
| `db/seed.sql` | `:253,257`（见 `adviceCard.js:54` 注释）QUOTE_PRICING HIGH | 高危场景钉死 |
| `src/evolution/icpSelfEvolution.js` | `:12–14` 键/状态/verdict、`:22` `backtestIcpDraft`、`:45/:54/:63` 草稿/生效/编排 | 进化三段 |

---

## 六、与既有函件关系（去重声明）

- 本回执只回答本征询函问题集；**不重复** 10-12《CRM 消费对照》（C1–C7/X-C1–X-C4，foundation `27ed3c5`）的门禁/契约类需求，二者互补：那份管「消费面卫生」，本份管「三大能力收敛」。
- HITL 审批原语上收（Q2.3 P0）与 C7（恒人工审批一等契约表达）**同源不同层**：C7 是契约表达问题（spine 场景级表达），本份 P0 是**原语实现层**（状态机+两阶段）——二者可合并裁定。
- F-A 需求输入件（`docs/2026-10-13-fa-requirement-input.md`，`c7830d1`）管 import 门禁，与本份无关。

---

## 七、优先级汇总表（供 foundation 排收敛批次）

| 能力 | 原语 | 优先级 |
|---|---|---|
| ① | 结局采集 schema + 结局→置信度校准 | **P0** |
| ① | 有效性度量管道（可插拔评分器 + 诚实降级聚合） | P1 |
| ① | 复盘→lesson 喂回循环骨架 / 负面先例契约 | P1 |
| ② | HITL 审批原语（状态机 + 两阶段确认，走 api.__all__） | **P0** |
| ② | 审计链原语（SHA-256 + append-only + 墓碑）统一 | P1 |
| ② | 三档模式（off/advisory/enforced）为基座默认 | P1 |
| ② | IAM/RBAC 层 | P2（先由 enterprise 供形，收「角色闸原语」不收角色矩阵） |
| ③ | 「草稿→回测→HITL 生效」毕业原语（无 approve 不可生效为基座不变式） | P1（毕业前置：readiness + 版本承诺 + api 通道） |
| 耦合 | 分层实现顺序 ②→①→③；进化毕业以 ②① 先毕业为前提 | 建议 |

---

*CRM-ai-native 分册回执 · 2026-10-13 · 全锚点现场核验；随函投回 foundation 仓 docs/ 存档。*
