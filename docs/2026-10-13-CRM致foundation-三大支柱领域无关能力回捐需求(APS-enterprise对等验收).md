# CRM 致 foundation — 三大支柱「领域无关能力」回捐需求（APS / enterprise 对等验收标准）

> **来文性质**：CRM（第一个落地的消费方项目）对 foundation 三大支柱收敛度的**反向反馈**。
> **触发**：用户诊断——「从三大支柱在 APS 与 enterprise 的落地看，与 CRM 差异很大；CRM 反馈需求不认真、foundation 收敛不全面」。
> **核心主张**：foundation 此前仅收敛了**契约/词汇层**（D1 结局、D2 三档安全、D3 HITL、D5 度量、D6 审计契约、D7 IAM、D8 evolution 词汇）——这是「名词」，不是「引擎」。CRM 在三大支柱上已建成**领域无关的运转机制**（决策脊柱、写通道多闸编排、链式防篡改审计、闭环回流、校准自调、每日复盘智能体、审批流引擎、常驻授权凭证模型……），这些**应当回捐为 foundation 底座能力**，使 APS / enterprise / 未来项目无需重造。
> **验收标准（用户给定）**：APS 与 enterprise 在三大支柱方面，达到与 CRM **同等层级**的功能。

---

## 0. 总原则（回捐边界）

1. **机制回捐、触发留域**：foundation 只吸纳「机制原语 / 状态机 / 算法 / 编排范式」；业务触发条件（S1–S8 阶段、CRM_DEAL、商机三要素、owner_id 分组等）仍由各消费方按领域注入。与 foundation「内核零领域字面量」原则一致。
2. **契约先行、机制随后**：已在 `contract.*` 落地的词汇（D1/D2/D3/D5/D6/D7/D8）保留为单一事实源；本函要求在其上补「机制层」实现件。
3. **CRM 既有功能原则上迁移到 foundation**：凡被判定「领域无关」的，CRM 后续切换为消费方（与 A-evolution 立项同族），不再各项目重复实现。
4. **fail-closed 铁律**：所有安全/决策闸门默认拒绝；自动化自进化「无 HITL 绝不生效」「绝不自动 apply」。

---

## ① 决策有效性与闭环追溯（decision effectiveness & closed-loop traceability）

### 1.1 CRM 现状（源码实证，全部 file:line 已 grep 验证）

| 能力 | 语义 | 主文件:行 | 领域无关性 |
|---|---|---|---|
| 决策第 0 闸「无决策不写」 | 任何写操作必须携带 `decision_id`，否则 fail-closed 阻断 | `src/decision/autonomyEngine.js:151`（`requireDecision`） | 锚定机制可迁移 |
| 溯源链 PROV-O 链式校验和 | SHA-256 `previous_checksum` 串联；`verifyChain` 判 `TAMPERED/FORKED/BROKEN_HEAD`；`patrolChains` 巡逻 + 封印比对 | `src/decision/provenance.js:89/134/152/185/219` | 防篡改链机制领域无关 |
| AI 建议→决策回路 | `recordAdvice` 落 `crm.advice_record` 补「AI 曾建议」回路；对话原文零落库 | `src/decision/adviceRecord.js:82/111`、`adviceStore.js:21` | 回路模式领域无关 |
| 可审计性「4 问验证」评分 | `computeAudit4q`（Q1 维度供给 / Q2 溯源链 / Q3 冲突 / Q4 下游影响）+ `aggregateAuditability` 有界并发 + 3000ms 超时护栏 → `auditability_pct` | `src/decision/auditability.js:34/164/196` | 4 问框架 + 聚合护栏领域无关 |
| **决策深度监控（用户点名）** | `auditability_pct` 全量评分；`A9 auditabilityTrendMonitor`（`src/agent/agentLoop.js:36`）监控趋势，恶化 ≥15pt 发射 alert | `auditability.js:196`、`agentLoop.js:36` | 监控范式领域无关 |
| 闭环回流路由 + 复合效应 | `routeRetroChannels`（C1 事实 / C2 反面先例 / C3 处方 / C3′ 记忆影响）；`qSkillComposite`（90d 复合效应测「空转」）；`hindsightCheck` 证实性偏差校验 | `src/decision/closureLoop.js:58/290/349/391` | 回流 + 采样模式领域无关 |
| 决策复盘夜批智能体 | `runDailyRetro` / `buildRequirementRetro` / `summarizeDailyOps` 三源聚合；每日 02:00 定时（`timers.js:399-410`） | `src/decision/decisionRetro.js:23`、`dailyOps.js:28`、`scheduler/timers.js:399` | 复盘编排领域无关 |
| 决策冲突 5 策略仲裁 | `detectConflicts` + `resolveConflict`（timestamp / source_priority / confidence_weighted / merge / human_arbitration），仲裁须过第 0 闸 | `src/decision/conflict.js:41/86` | 冲突解决引擎领域无关 |
| 方法论置信度单一事实源 | `methodologyScore/evidenceCoverage/requiredMet/composeConfidence`，与影子重放共用同一评分核 | `src/decision/methodologyScoring.js:29/41/53/62` | 纯算法领域无关 |

### 1.2 foundation 当前缺口

- foundation **无决策脊柱**（已自承「内核零领域字面量 / 无决策脊柱」）。
- `contract.outcome`(D1) 仅定义 `OutcomeRecord` 字段；**无「无决策不写」闸门、无 PROV-O 链式校验和、无 4 问评分、无闭环回流、无冲突仲裁、无复盘夜批**。
- `contract.audit`(D6) 仅定义审计记录/验证接口，**链式防篡改机制未落地**。

### 1.3 回捐需求（机制层，按优先）

| 优先级 | 回捐件 | 对应 CRM 真值 | 验收（APS/enterprise 对等） |
|---|---|---|---|
| **P0** | `decision_gate`：写操作「无决策不写」fail-closed 锚定原语 | `autonomyEngine.js:151` | APS/enterprise 任意写通道默认拒绝无 `decision_id` 的写 |
| **P0** | `prov_chain`：SHA-256 `previous_checksum` 链式校验和 + `TAMPERED/FORKED/BROKEN_HEAD` 判定 + 巡逻 | `provenance.js:89-219` | 任意领域可挂不可篡改溯源链，篡改被常态探测 |
| **P1** | `audit_4q`：4 问可审计性评分框架 + 有界并发/超时聚合护栏 | `auditability.js:34/164/196` | 决策可审计率可量化、可趋势监控（恶化告警） |
| **P1** | `closure_loop`：事实/反面先例/处方/记忆影响 四类回流路由 + 复合效应（空转）检测 | `closureLoop.js:58/349` | 系统具备「建议→回流→校准」闭环，能识别空转 |
| **P2** | `conflict_resolver`：5 策略冲突仲裁（含 human_arbitration 兜底，须过决策闸） | `conflict.js:86` | 多源决策冲突可自动仲裁 |
| **P2** | `decision_retro_agent`：复盘夜批智能体编排（三源聚合 + 定时 + 失败不静默） | `decisionRetro.js` + `timers.js:399` | 每日自动复盘并落盘，无需各项目重造 |
| **P3** | `confidence_scorer`：方法论置信度单一事实源（供重放/线上共用） | `methodologyScoring.js:29` | 评分核统一，重放与线上永不漂移 |

---

## ② 企业安全 + 可审计可追溯（enterprise security + auditability/traceability）

### 2.0 「写操作八闸」官方定义（重要，用户点名，以产品 PPT 为准）

> **更正口径**：经核对公司《企业AI销售决策平台·北京青羽智行》官方参赛 PPT（**slide 4 / slide 5**），**「写操作八闸」是产品的官方安全模型名称**，并非源码里一个字面常量。PPT 将其定义为四大类（节选）：
> - **事前校验**：字段完整性、业务规则、依赖关系，不合规进不来；
> - **权限边界**：谁能改价、谁能看谁，角色化控制，越权即拦截；
> - **红线拦截**：BANT 未达标禁止报价、折扣超线强制进审批流；
> - **事后可溯**：每一步写操作留痕，谁在何时改了什么，一目了然。
>
> 源码 `src/action/executor.js` 的 `dispatch` **9 级串行闸门 + 两阶段确认令牌**，正是这一「八闸」模型的**代码级落地实现**（PPT slide 5 ③「写操作八闸：危险操作先拦截再放行，拦截原因写得明明白白」即对应）。二者一致：PPT 是产品规范，代码是其工程实现。foundation 应吸收的，是这套**以「事前校验 / 权限边界 / 红线拦截 / 事后可溯」为骨架的写操作安全范式**，而非仅 9 个闸标签。

**9 级串行 fail-closed 写通道闸门**（`src/action/executor.js`，逐行验证）：

| 闸级 | 标签 | 语义 | 行 |
|---|---|---|---|
| 第 0 闸 | `decision_required` | 无 `decision_id` 不写（无决策不写） | `:61` |
| 第 1 闸 | `scope_violation` | 数据范围越界 | `:87` |
| 第 1.5 闸 | `permission_denied` | 角色 RBAC 硬闸 | `:102` |
| 第 1.7 闸 | `plan_entitlement` | 套餐功能门槛（缺 tenantId 即 fail-closed） | `:127` |
| 第 2.5 闸 | `field_permission` | 字段级 RBAC | `:141` |
| 第 2 闸 | `needs_force` / `write_whitelist` | force 双闸 + 对话式写白名单 | `:149/156` |
| 第 3 闸 | `approval_required` | HITL 审批流 | `:163` |
| 第 3.5 闸 | `sales_prereq` | 阶段推进前置（STAGE_GATES 纯函数） | `:180` |
| 第 3.6 闸 | `sales_deal_prereq` | 商机三要素闸 | `:198` |

叠加层：**两阶段确认令牌**（对外 MCP 通道）— `CONFIRM_TTL_MS=10min`（`src/mcp/gateway.js:18`）、`resolveSession` 验签 + 过期 + 防重放（`:135`）、`consumedNonces` 一次性消费（`:297`）；等价件 `confirmToken.js:53/61`（HMAC-SHA256 自含 payload 持久令牌，A9 契约回捐件）。

**「八闸」四大类 → 代码闸门 → 回捐件 映射**（证明模型可被 foundation 通用化，不绑定 CRM 业务字面量）：

| 八闸大类（PPT 官方） | 代码闸门（executor.js，已逐行验证） | 回捐件（§2.3） |
|---|---|---|
| 事前校验（字段完整 / 业务规则 / 依赖关系） | `decision_required`(:61) + `scope_violation`(:87) + `sales_prereq`(:180) + `sales_deal_prereq`(:198) | `gate_chain` |
| 权限边界（角色化控制 / 越权即拦截） | `permission_denied`(:102) + `field_permission`(:141) + `plan_entitlement`(:127) | `gate_chain` + `rbac_core` |
| 红线拦截（BANT 未达标禁报价 / 折扣超线进审批） | `needs_force`(:149) + `write_whitelist`(:156) + `approval_required`(:163) | `gate_chain` + `two_phase_token` |
| 事后可溯（每步留痕 / 谁何时改什么） | `auditHook.js` 链式审计 + `provenance.js` PROV-O 链 | `prov_chain`（①/② 同源） |

### 2.1 CRM 现状（其余安全能力，源码实证）

| 能力 | 语义 | 主文件:行 | 领域无关性 |
|---|---|---|---|
| 链式校验和审计（单一事实源） | append-only + SHA-256 `previous_checksum` 链式（`recordAudit`/`verifyAuditChain`） | `src/action/auditHook.js:38/73` | 与 ① 同源，可统一下沉 |
| RBAC 判定核 | `hasRbacGate/rbacAllows/rbacGateVerdict` 纯函数 | `src/action/roleGate.js:17/25/32` | 纯函数领域无关 |
| 对话式写白名单 + 爆炸半径 | `WRITE_WHITELIST`（4 个 autonomous 动作）、`writeBlastRadius` | `src/action/whitelist.js:15/22/27` | 白名单 + 半径模式可迁移 |
| CRUD 爆炸护栏 | `detectCrudExplosion` 反「把对话当 CRUD 用」 | `src/action/registry.js:63` | 模式领域无关 |
| 渠道审批闸 | `createChannelReviewGate`（`hasApproval` fail-closed） | `src/channels/reviewGate.js:22` | 渠道闸可迁移 |
| Token 配额闸 | `enforceTokenQuota` 超额强制 block/bill + 安全上限 | `src/billing/quotaGate.js:9` | 配额闸领域无关 |
| 配置写第 0 闸铸造器 | `produceConfigDecision` 配置写必经第 0 闸 | `src/config/configDecision.js:10` | 铸造器模式可迁移 |
| **常驻授权凭证模型** | `T3_ACTIONS`（T3 动作永不常驻授权）、`consultStandingGate`（含 `require_export_healthy` 运行时顺序闸）、执行仍 mint 决策过第 0 闸 | `src/authorization/standingAuthorization.js:29/65/88` | 凭证模型领域无关 |
| 授权凭证存储/扫荡 | `grantCovers`（纯函数）、`recordExecution`（用量自增 + 熔断 paused）、`sweepOnce`（过期 + 连续否决暂停） | `src/authorization/grantStore.js:13/73/88`、`grantSweeper.js:12` | 凭证生命周期领域无关 |
| 审批流引擎 | `seqCheck`（顺序闸）、`resolveApprovers`（AUTO_PASS 不再架空节点审批人）、`startInstance`（fail-closed 要求覆盖全节点）、`advanceTask`（ANY/ALL/SEQUENTIAL） | `src/approval/engine.js:19/80/157/216` | 审批模式领域无关 |
| 审批补偿/快照 | `snapshotFor`（写前快照）、`rollbackIfNeeded` | `src/approval/compensation.js:11/25` | 补偿模式领域无关 |
| 审批配置单一事实源 | `DEFAULT_APPROVAL_CONFIG`（R1-R4 / 金额档位 / 审批链） | `src/approval/approvalConfig.js:16/45/59` | 配置聚合领域无关 |

### 2.2 foundation 当前缺口

- `contract.security`(D2/D3) 仅定义 `SECURITY_MODES` / `HITL_EVIDENCE_FIELDS` / `APPROVAL_TRANSITIONS` / `assert_hitl_evidence` / `assert_approval_transition` —— **无多闸串行编排、无 RBAC 判定核、无字段权限、无审批流引擎、无常驻授权凭证模型、无配额闸**。
- `contract.iam`(D7) 仅定义 `Principal` / `SecurityDecision` / `RoleGate(Protocol)` 接口 —— **无凭证生命周期（熔断/扫荡/运行时顺序闸）机制**。
- `contract.audit`(D6) 仅契约 —— **链式防篡改机制未落地**（同 ①）。

### 2.3 回捐需求（机制层，按优先）

| 优先级 | 回捐件 | 对应 CRM 真值 | 验收（APS/enterprise 对等） |
|---|---|---|---|
| **P0** | `gate_chain`：可插拔多闸串行编排范式（决策锚定→范围→RBAC→字段权限→force/白名单→HITL→业务前置，全 fail-closed） | `executor.js:48-200` | APS/enterprise 写通道具备 ≥ 同层级的串行闸链，各闸可插拔 |
| **P0** | `two_phase_token`：危险操作二次确认原语（HMAC + TTL + 一次性 nonce 防重放），固化进安全内核 | `gateway.js:135/297`、`confirmToken.js:53/61` | 所有 MCP/外部危险写须两阶段确认，防重放/过期 |
| **P1** | `rbac_core`：RBAC 判定纯函数核 + 字段级权限 | `roleGate.js:17/32` | 角色 + 字段级授权可复用 |
| **P1** | `standing_credential`：常驻授权凭证模型（T3 永不常驻 + 运行时顺序闸 + 熔断 paused + 扫荡 sweep） | `standingAuthorization.js:29/65/88`、`grantStore.js`、`grantSweeper.js` | 长期凭证可回收、可熔断、可审计 |
| **P1** | `approval_engine`：ANY/ALL/SEQUENTIAL 三模式 + AUTO_PASS 不架空 + 写前快照补偿 + fail-closed 全覆盖 | `engine.js:19/80/157/216`、`compensation.js` | 审批流引擎通用，零项目重复实现 |
| **P2** | `quota_gate`：Token/资源配额闸（超额 block/bill + 安全上限） | `quotaGate.js:9` | 多租户配额护栏可复用 |
| **P2** | `write_guard`：对话式写白名单 + 爆炸半径 + CRUD 爆炸护栏 | `whitelist.js`、`registry.js:63` | 防「对话即 CRUD」护栏组合可复用 |

---

## ③ 自我进化（self-evolution，含每日复盘智能体的自动化运行与调整）

### 3.0 用户点名：「每日复盘智能体的自动化运行与调整」

> 这正是 CRM 的 **`calibration`（校准）子系统 + `nightlyReport`（夜批三段报告）+ `scheduler/timers`（多定时器编排）** 的合体——一个**每天自动运行、自动出处方、但绝不自动生效**的自进化智能体。其机制完全领域无关。

### 3.1 CRM 现状（源码实证）

| 能力 | 语义 | 主文件:行 | 领域无关性 |
|---|---|---|---|
| **校准处方状态机** | `createPatch/savePatches`（PENDING）→ `approvePatch`（事务内写配置 + APPLIED）→ `rollbackPatch`（绝不自动 apply）；`scanEscalations`（SLA 超时升级） | `src/calibration/store.js:174/198/250/282/308` | 处方状态机领域无关 |
| 第 0 闸铸造器（校准写） | `produceDecision` 配置写必经第 0 闸 | `src/calibration/store.js:94` | 铸造器可迁移 |
| **参数体检（26 项）** | `PARAM_ITEMS`（26 项算法参数）、`inspectAll`、`judge/suggest`、冷却护栏 `cooldown`、`DEFAULT_KNOB_MAP` | `src/calibration/paramInspector.js:28/99/119/200` | 确定性巡检领域无关 |
| **影子重放** | `replayConfidence`（用历史决策精确重算置信度）、`wouldEscalate`、`replayScenario`，与 autonomyEngine 共用 `methodologyScoring` 单一事实源 | `src/calibration/replay.js:17/53/67` | 重放机制领域无关 |
| 归因规则引擎（R1-R17） | `RULES`（R1-R17），守卫 R5/R6 优先级高于出方规则 | `src/calibration/rules.js:9/149/154` | 规则引擎领域无关 |
| 自动出方订阅 | `deriveDeviationMetrics`、`suggestForScenario`、`registerAutoSuggest`（实时订阅 decision 事件推浮卡） | `src/calibration/autoSuggest.js:17/69/98` | 事件订阅出方可迁移 |
| 处方装配（影子重放预期影响） | `enrichPatchesAndSave`（影子重放预期影响 + 幂等 savePatches + 第 0 闸） | `src/calibration/patchAssembler.js:14` | 装配模式可迁移 |
| 校准度量 | `computeMetrics`（自主/升级口径 decider_type） | `src/calibration/metrics.js:20` | 度量口径领域无关 |
| 重放常量守卫 | `REPLAY_K=5`、`MIN_SAMPLE=20`（样本不足守卫）、`FATIGUE_HOURS=24`（冷却） | `src/calibration/constants.js` | 守卫常量可迁移 |
| ICP 自进化（回测→HITL） | `backtestIcpDraft`（noop/count/threshold 三态）、`proposeIcpRecalibration`（`needsApproval` 恒真）、`approveIcpRecalibration`（无 approver 即抛）、`runIcpEvolutionPass` | `src/evolution/icpSelfEvolution.js:22/45/54/63` | 回测-HITL 范式领域无关（A-evolution 立项已覆盖切换面） |
| 路由自进化（A/B 收口） | `judgeArms`（prefer_on/off/insufficient，样本不足明确 insufficient 不硬凑）、`routingReview`（出 PENDING 处方） | `src/decision/routingReview.js:44/142` | A/B 判据领域无关 |
| **夜批三段报告 + 多定时器编排** | `saveNightlyReport` / `renderNightlyMarkdown`（三段：决策复盘 + 参数体检 + 路由收口）；`timers`：`nightly-distill`(24h `:352`)、`crm-risk-scan`(30min `:361`)、`decision-retro`(02:00 `:408`)、`auditability-sla-snapshot`(`:527`)、`calibration-sla-scan`(30min `:683`)，**失败 `emit trace + recordFailure` 绝不静默** | `src/report/nightlyReport.js:80/150`、`src/scheduler/timers.js:352/361/408/527/683` | 自进化调度骨架领域无关 |

### 3.2 foundation 当前缺口

- `contract.evolution`(D8) 仅定义词汇/状态机（`PRESCRIPTION_STATES`/`RISK_TIERS`/`DIRECTIONS`/`VERDICTS`/`PRESCRIPTION_TRANSITIONS`/`PRESCRIPTION_AUDIT_FIELDS`）。
- `evolution` **引擎层**（`Prescription`/`SkillDraft`/`shadow_replay`/`readiness_report`）面向「平台自改技能/旋钮处方」——**与 CRM 校准（租户配置值重标定）语义错配**，且 CRM 已立项仅切 `contract.evolution` 词汇面（A-evolution 设计书 `docs/2026-10-13-crm-A-evolution-design.md`）。
- **foundation 缺**：参数体检、影子重放（领域无关版）、归因规则引擎、夜批三段报告 + 多定时器编排、路由 A/B 收口、校准处方状态机（绝不自动 apply）这些**通用自进化运转机制**。

### 3.3 回捐需求（机制层，按优先）

| 优先级 | 回捐件 | 对应 CRM 真值 | 验收（APS/enterprise 对等） |
|---|---|---|---|
| **P0** | `patch_state_machine`：处方状态机（PENDING→APPROVED→APPLIED→ROLLED_BACK，绝不自动 apply，HITL 硬约束） | `store.js:174/250/282` | 任何自进化出方须过 HITL 才生效、可回滚 |
| **P1** | `shadow_replay`（领域无关版）：用历史决策精确重算 + 单一事实源防漂移 | `replay.js:17` + `methodologyScoring.js:29` | 自进化调整前必做离线回测，重放与线上同核 |
| **P1** | `param_health_check`：确定性参数体检（样本不足不误报 + 冷却期不频调） | `paramInspector.js:28/99/119` + `constants.js` | 算法参数定期健康巡检可复用 |
| **P1** | `nightly_self_evo_agent`：夜批三段报告 + 多定时器编排（失败不静默） | `nightlyReport.js` + `timers.js:352/361/408/527/683` | 每日自动复盘 + 落盘 + 多 SLA 扫描，零项目重造 |
| **P2** | `attribution_rules`：归因规则引擎（守卫优先于出方规则） | `rules.js:9/149/154` | 决策归因可配置、可复用 |
| **P2** | `ab_experiment_close`：路由 A/B 实验收口（样本不足不硬凑结论） | `routingReview.js:44/142` | 在线实验自动判臂 + 反噪声 |
| **P3** | `auto_patch_subscribe`：事件订阅自动出方（实时推浮卡） | `autoSuggest.js:17/69/98` | 实时偏差侦测可复用 |

---

## ④ 回捐优先序总表（跨三大支柱）

| 优先 | 回捐件 | 归属支柱 | 补 foundation 缺口 |
|---|---|---|---|
| **P0** | 决策第 0 闸「无决策不写」 | ① | 补「无决策脊柱」缺口 |
| **P0** | PROV-O 链式校验和防篡改审计（`prov_chain`） | ①/② | 强化 `contract.audit`(D6) 机制层 |
| **P0** | 多闸串行 fail-closed 写通道编排（`gate_chain`） | ② | 安全写骨架，下沉为通用编排 |
| **P0** | 两阶段确认令牌（`two_phase_token`） | ② | 固化危险操作二次确认原语 |
| **P0** | 校准处方状态机（绝不自动 apply） | ③ | 强化 `contract.evolution`(D8) 机制层 |
| **P1** | 4 问可审计性评分 + 有界并发聚合 | ① | 强化 `contract.metrics`(D5) |
| **P1** | 闭环回流路由 + 复合效应（空转）检测 | ① | 通用决策闭环范式 |
| **P1** | RBAC 判定核 + 字段权限 | ② | 补 `contract.iam`(D7) 机制层 |
| **P1** | 常驻授权凭证模型（熔断/扫荡/顺序闸） | ② | 补 `contract.iam`(D7) 机制层 |
| **P1** | 审批流引擎（SEQUENTIAL/AUTO_PASS 不架空/fail-closed） | ② | 通用工作流原语 |
| **P1** | 影子重放（领域无关版） | ③ | 自进化回测引擎 |
| **P1** | 参数体检（冷却/样本守卫） | ③ | 模型体检范式 |
| **P1** | 夜批三段报告 + 多定时器编排 | ③ | 自进化调度骨架 |
| **P2** | 决策冲突 5 策略仲裁 | ① | 冲突解决引擎 |
| **P2** | 决策复盘夜批智能体编排 | ① | 复盘自动化 |
| **P2** | Token 配额闸 | ② | 多租户护栏 |
| **P2** | 写白名单 + 爆炸半径 + CRUD 爆炸护栏 | ② | 防对话即 CRUD |
| **P2** | 归因规则引擎 | ③ | 决策归因内核 |
| **P2** | 路由 A/B 实验收口 | ③ | 在线实验收口器 |
| **P3** | 方法论置信度单一事实源 | ① | 评分核统一 |
| **P3** | 事件订阅自动出方 | ③ | 实时偏差侦测 |

---

## ⑤ 验收标准：APS 与 enterprise 达到 CRM 同等层级

> 判定口径：下列每一条，**APS 与 enterprise 均应「开箱即用消费 foundation 底座」达成，而非各自重造**。CRM 在回捐完成后亦切换为消费方（与 A-evolution 同族），三仓对齐同一底座。

### ⑤.1 支柱① 决策（对等清单）
- [ ] 写操作默认 fail-closed「无决策不写」（第 0 闸底座）
- [ ] 任意决策可挂 PROV-O 链式防篡改溯源，篡改被常态探测（非人工导出）
- [ ] 决策可审计率（4 问）可量化、可趋势监控、恶化告警
- [ ] 具备「事实/反面先例/处方/记忆影响」四类回流 + 复合效应（空转）检测
- [ ] 多源决策冲突可自动仲裁（含 human 兜底）
- [ ] 每日决策复盘夜批智能体自动运行并落盘

### ⑤.2 支柱② 安全（对等清单）
- [ ] 写通道具备 ≥ 同层级的串行 fail-closed 多闸（决策锚定→范围→RBAC→字段→force/白名单→HITL→业务前置）
- [ ] 所有外部/MCP 危险写须两阶段确认令牌（防重放/过期）
- [ ] 角色 + 字段级 RBAC 可复用
- [ ] 常驻授权凭证可回收、可熔断(paused)、可扫荡、带运行时顺序闸
- [ ] 审批流引擎通用（ANY/ALL/SEQUENTIAL，AUTO_PASS 不架空，fail-closed 全覆盖，写前快照补偿）
- [ ] 链式校验和审计与决策溯源同源、不可篡改

### ⑤.3 支柱③ 自进化（对等清单）
- [ ] 自进化出方须过 HITL 状态机（PENDING→APPROVED→APPLIED→ROLLED_BACK），**绝不自动 apply**
- [ ] 调整前必做影子重放（与线上同评分核，防漂移）
- [ ] 算法参数定期健康体检（样本不足不误报、冷却期不频调）
- [ ] 每日夜批三段报告（决策复盘 + 参数体检 + 路由收口）+ 多 SLA 定时器编排，失败不静默
- [ ] 归因规则引擎（守卫优先于出方）
- [ ] 路由 A/B 实验自动收口（样本不足不硬凑结论）

---

## ⑥ 治理与落地建议

1. **分阶段（contract 已就绪 → 机制层回捐）**：D1–D8 契约不需重做；本函全部为「机制层」新增件，按 P0→P3 分批落地，每批带**源码对拍守卫**（仿 E9/A9 同族），防横性漂移。
2. **CRM 切换为消费方**：回捐件 stable 后，CRM 对应模块（executor 闸链、provenance、auditability、calibration、approval engine、standingAuthorization…）切换为消费 foundation，逐步收敛「CRM 主体仍 Node 自建」的排除面（见 CRM 迁移计划）。
3. **横性要求**：foundation 每批回捐落地后，须向 CRM/APS/enterprise 三仓发函；CRM 核收（仿 T79 整盘核收的值级核验纪律）。
4. **本函与既有函件关系**：本函是 `27ed3c5`（CRM 消费对照·foundation→CRM 未用归因）的**反向补全**——彼函盘点「foundation 有、CRM 未用」，本函盘点「CRM 有、foundation 应吸收」。两函合观，方得三大支柱全貌。

---

> **证据纪律声明**：本函全部 `file:line` 锚点均经 CRM 源码 Grep 实证（含用户点名的「写操作八闸」已逐行核验为 9 级闸链 + 两阶段令牌）。「八闸」作为**产品官方安全模型**的权威定义源自公司《企业AI销售决策平台·北京青羽智行》参赛 PPT（slide 4 / slide 5），其代码落地即 executor.js 闸链；二者一致，不存在以讹传讹。foundation 当前缺口以 T79 整盘核收（`EVOLUTION_EXPERIMENTAL=False`、D1–D8 仅契约层）为权威基线。
