# CRM 补充／更正 —— 对《三大支柱收敛完整性审计-CRM域无关能力上收计划》的修订建议

> 来文：`docs/2026-10-13-三大支柱收敛完整性审计-CRM域无关能力上收计划.md`（foundation 只读审计 CRM 后撰写）
> 立场：CRM 作为被审计方 + 参照实现提供方，就**锚点真实性、口径校正、缺口补全、Batch 排序、验收基线**给出补充与更正。
> 方法：trust-but-verify——本文每一项 `file:line` 均经 CRM 源码 Grep 实证；foundation 声称已存在的符号亦已反向核验。

---

## 〇、总体评价

**方向完全赞同**，但两处口径须校正：

1. **「CRM 反馈不认真」的归因不成立**（foundation §〇 已部分承认）。客观事实：CRM 此前已交付 `27ed3c5` 全门面对照、`e1840c7` T75 九项评审、Q1–Q4 征询回执、`2a3834d` T79 整盘值级核收——反馈链路完整且可机检。真实根因是 foundation 吸收了**契约层（D1–D8）却未收割 CRM 的运行时参考实现**。建议把用户「CRM 反馈不认真」这一措辞在正式对外件中改为「CRM 已详实反馈，但 foundation 此前聚焦契约设计、未收割运行时实现」，以免误导后续协作。

2. **「foundation 收敛不全面」成立**，但应精确表述为：**契约/词汇层收敛完整（D1–D8 + evolution stable），运行时机制层（execution/scheduler/monitor/approval-engine/authorization）几乎为零**。本文档与 foundation 审计的目标一致——补运行时层。

---

## 一、锚点核实结论（trust-but-verify）

| foundation 引用 | 实证结果 |
|---|---|
| `src/action/executor.js` 八闸串行 | ✅ 命中：第0闸 `decision_required`(:61) → `scope_violation`(:87) → `permission_denied`(:102) → `plan_entitlement`(:127) → `field_permission`(:141) → `needs_force`(:149) → `write_whitelist`(:156) → `approval_required`(:163) → `sales_prereq`(:180) → `sales_deal_prereq`(:198)。**实为 10 个 gate 标识（含 9 级串行 + 第0闸），非字面「8」** |
| `src/decision/auditability.js` computeAudit4q | ✅ 命中 `:34`（4 问评分真源，被物化/趋势闭环共用，评分口径单一事实源） |
| `src/decision/provenance.js` shaChain | ✅ 此前已核（PROV-O 链 + TAMPERED/FORKED/BROKEN_HEAD + 巡逻） |
| `src/monitor/*` 根因七态/信号/失败/诊断 | ✅ 目录真实：`monitorStore.js`/`attribution.js`/`diagnosis.js`/`signalMetrics.js`/`enrichmentMetrics.js`/`syncMetrics.js`/`dimCoverage.js`/`monitorSubscriber.js` |
| `src/calibration/*` 影子重放/处方 | ✅ 14 文件：`replay.js`/`store.js`/`patchAssembler.js`/`autoSuggest.js`/`paramInspector.js` + `knobs/*`(base/weight/threshold/sevenDimConfigStrategy/configStoreStrategy/routingStrategy/requiredDims/index) |
| `src/approval/engine.js`/`stateMachine.js` | ✅ 存在 |
| `src/authorization/standingAuthorization.js`/`grantSweeper.js` | ✅ 存在（常驻授权 + 扫荡回收，foundation 确无） |
| `src/sevenDimensions/engine.js` / `src/decision/interception.js` | ✅ 存在 |
| `src/memory/promote.js` / `src/decision/retroPromote.js` | ✅ 存在 |
| `src/billing/metering.js` / `src/config/configStore.js` | ✅ 存在 |
| `src/mcp/gateway.js` 两阶段令牌 | ✅ 此前已核（`CONFIRM_TTL_MS`、`resolveSession` 验签/过期/防重放、`consumedNonces`） |
| foundation 已有 `DecisionApprovalGate`/`DecisionVerdictState`/`RedlinePriorityGate`/`DecisionPassThroughGate` | ✅ 真实存在于 `packages/chiyu-kernel/src/chiyu_kernel/approval/__init__.py:24/61/72/91`（经 `api.py:491/699` 再导出，facade-clean） |

**结论**：foundation 审计的锚点**全部属实**，无漂移；其声称已存在的符号亦真实。可放心以该审计为实施基线。

---

## 二、关键更正（必须修正后再实施）

### 2.1 「八闸」口径：产品模型 ≠ 代码闸数

foundation 审计 §一#1 写「受控写八闸框架（写动作串行安全闸链…）」并引 `executor.js(八闸串行)`，**混淆了两个不同概念**：

- **产品官方「八闸」模型**（来自我司参赛 PPT《企业AI销售决策平台·北京青羽智行》slide 4/5）= **四大类安全范式**：① 事前校验（字段完整性/业务规则/依赖关系）② 权限边界（角色化、越权即拦）③ 红线拦截（BANT 未达标禁报价、折扣超线转审批）④ 事后可溯（每步写操作留痕）。**这是范式，不是 8 个固定闸**。
- **代码落地**（`executor.js`）= **10 个 gate 标识的串行 fail-closed 链 + 第0闸 requireDecision + 两阶段令牌**。闸数随业务增长（当前 10，非 8）。

**harvest 要求**：上收到 foundation 的应是**「可配置 N 级 fail-closed 闸链框架 + 四分类（校验/权限/红线/可溯）注册模型」**，**闸名本身不硬编码**。CRM 域特定闸名（`sales_prereq`/`sales_deal_prereq`/`plan_entitlement`）必须留在 CRM 消费方，以回调/配置注入 foundation 框架。否则 foundation 内核会污染 CRM 领域字面量，违背其「内核零领域字面量」铁律。

### 2.2 监控根因分类含领域字面量 —— harvest 必须「模式收割」而非「字面搬运」

`src/decision/rootCauseClassifier.js` 的 `ROOT_CAUSES` 含**强领域标记**：
- `layer: '粒子库'` / `'粒子库/K'` / `'M/seven-dim'` / `'M/edge_bindings'` / `'M/K'` / `'K'`
- `knob: 'META_ATTR_MAP'` / `'PARTICLE_ATTR_ADD'` / `'SOURCE_REFRESH'` / `'REQUIRED_DIMS'` / `'EDGE_BINDING'` / `'DIM_ORDER'` / `'PRECEDENT_DISTILL'`
- `persistRootCause()` 硬编码 `UPDATE crm.decision ...`（DB 写回，内核零 IO 纪律冲突）

**harvest 要求（硬性）**：
1. foundation 只收**分类算法骨架**（R0–R3 决策树：usable/major_deviation → 命中即止 → UNKNOWN 进人工队列），**根因目录（code/layer/knob/name）必须由消费方注入为配置**。
2. `persistRootCause` 这类 DB 写回**留在消费方**，kernel 零 IO。
3. `monitor/*` 当前 `import ROOT_CAUSES from '../decision/rootCauseClassifier.js'` —— monitor 不自洽、耦合决策脊柱。harvest 时须解耦，让 monitor 接收注入的根因目录。

**这是「内核零领域字面量」铁律在 harvest 场景下的第一道验收闸**，建议写入每批 harvest 的 acceptance gate。

### 2.3 第0闸 requireDecision 依赖决策脊柱 —— B1-② 的前置架构决策

CRM 第0闸 `executor.js:61` 调用 `requireDecision()`（`autonomyEngine.js`），后者运行完整决策脊柱（S1–S5 + 情境装配）。**foundation 明确「无决策脊柱」**（本仓记忆与 foundation 自述一致）。

→ 若直接 harvest「受控写执行框架」而内核无脊柱，第0闸将悬空。两种解法（须用户拍板其一）：
- **(a) 轻量决策凭证契约**：foundation 只定义「决策凭证（decision_id + 有效期 + 签发方 + 校验和）」的校验契约（消费方签发、内核只验不产），第0闸退化为「写操作须持有效决策凭证」。不引入脊柱，保持内核轻量。
- **(b) foundation 同步引入最小决策脊柱**：成本高、与「内核零领域字面量」张力大，不推荐作为 Batch-1 范围。

**建议选 (a)**：与 D1 OutcomeRecord / D3 HITL 证据同源（消费方签发、内核只验），保持 foundation 不产决策。

---

## 三、审计遗漏的缺口（建议补入清单）

foundation 清单 #1–#10 基本覆盖，但遗漏/弱化以下：

| # | 遗漏能力 | CRM 真源 | 说明 |
|---|---|---|---|
| 11 | **事件订阅 / 出方（订阅-回调解耦）** | `src/monitor/monitorSubscriber.js` + `src/scheduler/*` 事件钩子 | 监控/夜批的「事件驱动」骨架，harvest 调度器（B1-③）时须一并收，否则 scheduler 无触发源 |
| 12 | **信号链路 metrics（sync/enrichment 双维度）** | `src/monitor/signalMetrics.js`/`syncMetrics.js`/`enrichmentMetrics.js` | 深度监控的「信号级可观测」不止根因计数，还含同步/富化两路信号健康度；建议 B1-① 明确收这三件 |
| 13 | **维度覆盖率监控** | `src/monitor/dimCoverage.js` | 七维覆盖率的运行时度量，是「决策有效性」的可观测子集，建议并入 B1-① |
| 14 | **配置中心 id36 禁改 不变量** | CRM 铁律（config_center id36 禁改）+ `src/config/configStore.js` | B3-②「配置中心」必须显式携带此不变量 + tenant 隔离 + 阈值 100% 配置化，否则 harvest 出的配置中心会丢失 CRM 最关键的安全约束 |
| 15 | **升格引擎 vs 升格评分的拆分** | `src/memory/promote.js`/`retroPromote.js` | foundation §一#9 称「升格机制已有」——但 CRM 升格含**领域评分**（经验→先例/知识的打分）。harvest 只收**升格流水线（阶段迁移/去重/优先级）**，**评分留消费方** |

---

## 四、Batch 排序建议（修订 foundation §三）

**新增 Batch-0（验收基线，最高优先）**：先审计 APS / enterprise 当前三大支柱实现，建立**对等基线（parity baseline）**。理由：
- 用户验收标准「APS/enterprise 达 CRM 同等层级」**无基线不可测**；
- 避免 harvest 出 APS/enterprise 已有的机制造成重复（如 enterprise 大概率已有审批/授权）；
- Batch-0 不写 foundation 代码，纯只读审计，与本次 CRM 审计同法。

**Batch-1 内部重排**：
- B1-① 深度监控（最领域无关、最低风险）✅ 优先
- B1-③ 复盘调度 + 事件订阅（领域无关、低风险）✅ 紧随
- B1-② 八闸执行框架 ⚠️ **后置**，卡在 §2.3 第0闸架构决策（选 (a) 轻量凭证契约）后启动

**Batch-2/3 补充**：B3-② 配置中心必须带 id36 禁改不变量（#14）；B3-③ calibration 必须保留 CRM「绝不自动 apply + 无 HITL 不生效」双铁律。

---

## 五、跨仓一致性守卫（防「收敛变分叉」）

每 harvest 一项机制，CRM 须保留/新建**契约平行实现 + 源码对拍守卫**（与 A-evolution 立项 `docs/2026-10-13-crm-A-evolution-design.md` 同族，E9/A9 范式）：
- 例：`test/scripts/icp-evolution-contract-parity.test.js`（已设计）；
- 建议对八闸框架、监控根因分类、审批流引擎各建 `*parity.test.js`，含**变异自证**（改 foundation 符号或 CRM 镜像常量一方，守卫必须变红）。

否则「上收 foundation」会变成「fork 一份到内核」，背离收敛初衷。

---

## 六、对 foundation §五「待用户拍板」三问的 CRM 立场

1. **Batch 顺序**：赞同 Batch-1→3 主干，但**强烈建议插入 Batch-0（APS/enterprise 基线审计）**，且 Batch-1 内 B1-② 后置（卡 §2.3 决策）。
2. **Batch-1 三项是否现在启动**：B1-①/B1-③ 可立即启动（低风险、领域无关）；B1-② 须先拍板 §2.3 的 (a)/(b) 决策。
3. **APS/enterprise 是否本轮审计**：**必须审计**（即 Batch-0）。以 CRM 为唯一参照、下游各自接入，会导致「达同等层级」无客观度量且易重复建设。

---

## 七、验收闸（建议写入每批 acceptance）

除 foundation 已列的「变异自证 + 组合全量回归」外，新增两条硬闸：
- **G-域无关**：harvest 出的每个内核符号，grep 不得含 CRM 领域字面量（`crm-*`/`粒子`/`七维`/`sales_*`/`icp`/具体表名）；根因目录/闸名/评分须为消费方注入。
- **G-零IO**：内核 harvest 件不得含 DB 写回；持久化一律留消费方（对齐 kernel 零 IO 纪律）。
- **G-对等可测**：APS/enterprise 接入后，须有可机检的 parity 清单（决策 6 / 安全 6 / 自进化 6，见 CRM 回捐函 `71fab50` §5），而非主观评价。
