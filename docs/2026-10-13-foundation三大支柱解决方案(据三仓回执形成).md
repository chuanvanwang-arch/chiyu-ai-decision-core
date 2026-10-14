# foundation 三大支柱解决方案 —— 据三仓回执形成

> **发出方**：foundation（AI 原生底座唯一事实源）
> **日期**：2026-10-13
> **依据**：三仓对《foundation 征询函 —— 三大企业能力需求收集》的回执
> - `2026-10-13-enterprise答foundation征询-三大企业能力需求.md`
> - `2026-10-13-CRM答foundation征询-三大企业能力需求.md`
> - `2026-10-13-APS答foundation征询-三大企业能力需求.md`
>
> **性质**：需求驱动的收敛方案（先本仓增强、后三仓改造）。本方案将三仓回执的**共识 P0** 沉淀为 foundation 1.0 稳定承诺的候选批次一；**共识 P1** 批次二；**域特有**明确不上收。所有引用锚点均为本仓源码核实，非转抄回执。

---

## 〇、三仓回执共识提炼

### 0.1 跨仓共识（全部 P0，foundation 据此优先排序）

| 能力 | 共识 | 三家共同诉求 | 三仓锚点 |
|---|---|---|---|
| **① 决策闭环** | **OutcomeRecord 结局采集契约**缺统一基座 | CRM `outcome.js` / APS `decisions.py:79` / enterprise `decision_memory_store.py` 各自造结局采集，口径漂移 | `CRM:src/decision/outcome.js:7/14/19`；`APS:src/aps/platform/decisions.py:13/79`；`enterprise:host/retro_backend.py:65` |
| **① 决策闭环** | **"结局→复盘候选"触发原语**缺管道 | 三仓均无"结局→自动复盘"自动化，靠人工/SLA 触发 | `APS:reflux.py:281-287` C2 反面先例；`CRM:decisionRetro.js:23` |
| **② 安全** | **HITL 审批原语上收，且闸必须基座结构保证**（非约定级） | 三仓共识：无 approve 不可生效是**基座不变式**，缺 approver 参数即抛错 | `CRM:approval/stateMachine.js:4/15/27`；`APS:security.py`；`enterprise:approval/state_machine.py:13-56` |
| **② 安全** | **三档模式（off/advisory/enforced）为基座默认** | APS 实证渐进收紧 + advisory 生产观测，防漂移断言升格基座不变量 | `APS:security.py:59/75/365/380` |
| **③ 进化** | **"草稿→回测→HITL→生效"毕业原语**，HITL 闸结构性不可绕过 | CRM `icpSelfEvolution` 与基座 evolution 语义逐字同构；APS `promote_gate` 判据可贡献 | `CRM:evolution/icpSelfEvolution.js:22/45/54`；`APS:promotion.py:135` |
| **耦合** | **三能力互为前提，收敛顺序 ②→①→③** | 安全/HITL 为底、决策闭环为主干、进化为消费端；进化不得先于 ①② 毕业 | CRM §四；APS Q4；enterprise Q4 |

### 0.2 关键分档共识（避免过度上收）

| 项 | enterprise | CRM | APS | foundation 裁定 |
|---|---|---|---|---|
| **IAM/RBAC 完整层** | P1 可贡献参考实现 | P2 观望 | P1 判定接口进基座 | **收"判定接口（Principal/SecurityDecision）+ 角色闸原语"，不收"具体角色矩阵"** |
| **有效性度量管道** | P1 canonical schema 毕业 | P1 可插拔评分器 | P1 跨仓统一口径 | **P1 批次二**，评分器维度可插拔 |
| **审计链** | P0 三段链毕业 | P1 统一（双实现同构） | P1 合一（同名异实） | **P1 批次二**：chain_hash 与各仓自有 SHA-256 链合一为单一事实源 |
| **K-M-D 四通道/K-M/J 三图** | — | ⛔ 不上收 | ⛔ 不上收 | **域特有，形态对齐、语义各异，留消费方** |
| **具体枚举值/评分尺子/红线规则/动作目录** | ⛔ | ⛔ | ⛔ | **域特有，基座只收"机制"不收"值"** |

---

## 一、能力① —— 决策有效性与闭环追溯

### 1.1 现状核实（foundation 侧）

- **已有**：`run_spine/resume_spine` + 九尺子评分 + 八要素判定 + 审批闸三态（`chiyu_kernel.approval`）+ 记忆网先例召回（`write_decision_memory_net` 唯一写、`recall_precedents` 读）+ `AUDIT_RECORD_KIND` 审计轨契约（`contract/decision.py:129`）。
- **缺口**（三仓一致 P0）：**OutcomeRecord 结局采集契约**本仓不存在——`contract/audit.py` 的 `AUDIT_REQUIRED_FIELDS` 覆盖决策动作改值（prescription/from_value/to_value/verdict），但**不覆盖结局**（成交/失败/迟交类别）。三仓各自拼结局采集，跨仓不可比。

### 1.2 P0 新增 —— OutcomeRecord 结局采集契约（本仓增强核心）

新增 `contract/outcome.py`，定义结局采集最小契约，统一三仓口径。设计基于三仓回执共同最小面（CRM `OUTCOME_TYPES` / APS `decisions.py:79` outcome_signal / enterprise 复盘证据面缺口）：

```python
"""结局采集契约 —— 决策→执行→结局→复盘 闭环的第一环。"""

OUTCOME_KINDS: Tuple[str, ...] = (
    # 三仓共同最小面；具体枚举值可扩展，机制由基座统一
    "success",      # 成功/赢单/达标
    "failure",      # 失败/丢单
    "partial",      # 部分达成/局部
    "stalled",      # 停滞
    "other",        # 其他（域自定义入口）
)

OUTCOME_REQUIRED_FIELDS: Tuple[str, ...] = (
    "outcome_id",   # 结局记录 id
    "decision_id",  # 关联决策（闭环锚点，追溯链关键）
    "outcome_kind", # 结局类型（∈ OUTCOME_KINDS）
    "recorded_ts",  # 采集时间
    "recorded_by",  # 采集者（人工/系统，追责到个人）
    "evidence_ref", # 证据引用（回放依据）
)
```

**设计要点**：
1. **`decision_id` 强制关联** —— 使结局可挂回决策形成闭环追溯链；APS 所述"net"结局证据挂回 decision_id 是自拼"的缺口在基座补上契约。
2. **`recorded_by` 追责到个人** —— 对齐客户"错了怎么追责"痛点（enterprise Q1.2 / CRM Q1.2）。
3. **与审计链 hash 挂钩（防篡改）** —— 复用 `contract/audit.py` 链式哈希，结局记录经同一 SHA-256 链，杜绝结局被事后篡改掩盖"系统错了"。
4. **`outcome_kind` 枚举机制统一、值可扩展** —— 遵守 CRM Q1.4"基座只收枚举机制不收具体枚举值"（won/lost/paid 是销售语义，制造/医疗可自定义）。

**接入面**：`api.py.__all__` 登记 + `contract/__init__.py` + `manifest.json` 重生成（遵守新增子包四步闸：test LAYERS / version CAPABILITIES / 门面 `__all__` / Makefile lint `--layers`）。

### 1.3 "结局→复盘候选"触发原语（P0/P1）

- **P0**：`append_outcome` 采集 API + `list_outcomes(decision_id)` 读取（对齐 CRM `writeOutcome/listOutcomes`、APS `reflux_record_outcome` 边⑤形态）。
- **P1**：`build_retro_candidates` 复盘候选触发原语 —— 按 case/决策簇聚合结局，生成复盘候选，使"结局→自动复盘"从人工/SLA 触发升级为管道驱动（三仓均有此洞：APS"negative 结局不回流⇒同类错误重复"、CRM 复盘靠每日定时）。
- **明确不上收**（三仓共识）：K-M-D 四通道映射语义（APS）、K/M/J 三图与 D1-D5 载体（CRM，绑定图 schema）、复盘建议的业务判定逻辑（enterprise retro_toggle 域逻辑）。基座只收 **OutcomeRecord 契约 + 采集/聚合原语**。

### 1.4 有效性度量管道（P1 批次二）

- 通用化 CRM `aggregateAuditability` 的"窗口聚合 + 诚实降级（未评不掩盖为绿）"形态。
- 评分器维度**可插拔**：4 问（CRM）/SLA 升级（APS）/strictness M1-M4（enterprise）各仓注入，跨仓**统计口径统一**（命中率/逆转率对账最小面，APS P1-C）。
- 九尺子评分/八要素**语义与评分尺子实现留消费方**（enterprise `strictness.py:12` 业务判断定界）。

---

## 二、能力② —— 企业安全 + 可审计可追溯（含 HITL）

### 2.1 现状核实（foundation 侧）

- **已有**：审计链（`contract/audit.py` SHA-256 链式）、审批闸三态（`chiyu_kernel.approval`，B3）+ `AUDIT_EVENT_APPROVAL_*` 事件族（`contract/decision.py:114-116`）+ `interaction.ApprovalGate`（工具执行前 HITL）。
- **缺口**（三仓一致 P0）：**无 IAM/auth/rbac 安全层**；无三档模式；`AUDIT_EVENT_APPROVAL_RESUMED` 事件存在但 **resume 侧证据 payload 无契约锚**（APS P0-B 实名指出）；审计链与各仓自有链**同名异实**（APS P1-D）。

### 2.2 P0 新增 —— 三档安全模式（off/advisory/enforced）

以 APS `security.py:59/75/365/380` 形态为基础，升格为基座默认范式：

```python
SECURITY_MODES: Tuple[str, ...] = ("off", "advisory", "enforced")

class SecurityDecision:      # 判定结果（可序列化）
    mode: str                # 当前模式
    allowed: bool            # 是否放行
    would_deny: bool         # advisory 下若 enforced 是否会拒（生产观测面）
    reason: str              # 结构化拒因（含"未启用"显式状态）
```

**不变量（升格自 APS `security.py:380` 防漂移断言）**：
`advisory.would_deny == (not enforced.allowed)` —— 两档判定一致性**结构保证**，杜绝"advisory 观测绿、enforced 才现红"的回归。

**价值**：渐进收紧是企业上线刚需（APS "企业不可能一步 enforced：默认 off 零破坏 → advisory 生产观测 → enforced 收口"）。对存量系统零破坏。CRM 从旁印证（自治分级/guardrails 同构思想），三仓均认可。

### 2.3 P0 新增 —— HITL 审批原语 + 不可绕过不变式

基于已有 `DecisionApprovalGate` 三态 + `interaction.ApprovalGate`，沉淀统一原语：

1. **审批状态机原语**：统一三仓审批状态机形态（CRM `stateMachine.js` 五态 / enterprise `state_machine.py` INSTANCE_STATES / 基座 B3 三态），提供 `assert_transition` 非法迁移防护（对齐 CRM `:27`、enterprise `:13-56`）。
2. **HITL 不可绕过不变式（基座结构保证，非约定）**：
   - 生效/放行 API 入口**只认带 HITL 证据链的 payload**（approver_id/approved_at/evidence_ref 必填），缺 approver 参数即抛错（CRM Q3.4："无 approve 不可生效做成基座不变式而非文档纪律"；APS Q3.3："生效入口只认带 HITL 证据链的 payload 而非约定"）。
   - 该不变量是**进化闸的共同底座**（见能力③），三仓一致要求 P0。
3. **resume 侧证据契约（APS P0-B）**：补 `AUDIT_EVENT_APPROVAL_RESUMED` 的 payload 契约锚 —— `resume_principal/resumed_at/basis`（谁批准、何时、基于什么），使 PENDING 放行的证据结构与决策审计同链可追。enterprise Q2.4"基座管协议与格式，消费方管动作语义"。

### 2.4 P1 批次二 —— 审计链合一 + IAM/RBAC 判定接口

- **审计链合一（APS P1-D / CRM P1）**：foundation `chain_hash` 与 APS `audit.py`/CRM `provenance.js` 自有 SHA-256 链收敛为**单一事实源**，消费方只余接线。审计 canonical schema（`record_kind`+`rubric_scores`+`elements`，enterprise Q1.3 P1）毕业为 schema 契约。墓碑擦除语义（GDPR vs 禁 DELETE）在基座层定义。
- **IAM/RBAC 判定接口（enterprise P1 / APS P1-C / CRM P2 观望共识）**：收 `Principal`/`SecurityDecision`/角色闸原语（principal+scope+deny 理由结构化），**不收具体角色矩阵**（sales/ten_admin/channel_manager 等属各仓域语义）。enterprise 贡献参考实现（IAM 五档+token 验签/过期/吊销+双层 effective_roles），foundation 出接口契约。

### 2.5 明确不上收（三仓共识）

动作目录与 `rbac_roles` 声明（enterprise `platform_catalog.py`）、权限矩阵具体映射（APS `PERMISSION_MATRIX`）、角色语义与租户功能闸（CRM `rbac.js`）、红线规则业务语义（APS mutex_top/sensitive 判定内容）、principal↔MES/ERP 身份源映射（企业 IdP 属部署侧）。

---

## 三、能力③ —— 自我进化

### 3.1 现状核实（foundation 侧）

foundation **已有完整进化原语族**（`evolution/` 目录）：`guard`（G2/G3+只读不可豁免）+ `knob`（参数白名单+风险分档+G1 放宽永不自动）+ `prescription`（处方状态机：事务原子+挂起+一键回滚）+ `replay`（影子重放+无样本即拒）+ `readiness`（准备度评审）+ `skill_draft`（方法论草稿闸）。这正是三仓期望的"HITL 草稿→回测→生效"形态。**但标注 experimental 未毕业**。

### 3.2 三仓共识（全部 P0）

1. **"草稿→回测→HITL→生效"是期望通用形态**：CRM `icpSelfEvolution` 与 foundation evolution 语义逐字同构（草稿态枚举/回测双闸/显式 approve 逐项对得上）；APS `promote_gate` 判据形态可贡献。
2. **HITL 闸必须基座结构保证**：生效入口只认带 HITL 证据链的 payload（复用能力②的 HITL 原语）。
3. **毕业前置**（CRM Q3.3、enterprise Q3.3，均坚持）：毕业须过 readiness 评审 + 版本稳定承诺 + 走 `api.__all__` 单一 sanctioned 通道 + RFE 流程（⛔ 禁伪稳定包装）。
4. **收形态不收域参数**：基座收状态机/回测闸接口/HITL 钩子，不收 passLine/minSample 具体值（域配置）。

### 3.3 P0 —— evolution 毕业（按 RFE 流程）

- **批次前提**：能力② HITL 原语先毕业（进化闸的"无 approve 不可生效"复用其不变式）；能力① OutcomeRecord/复盘先毕业（进化消费复盘输出，倒序则进化消费不存在的复盘出口 —— APS Q4）。
- **毕业路径**：`evolution/` 原语族过 `readiness_report` + 版本稳定承诺 + `api.__all__` 纳入 + manifest 重生成；`MEMORY_EXPERIMENTAL` 类标志位按成熟度逐个翻转为稳定。
- **P1**：进化的生效动作强制经能力② HITL 原语 + 留能力① provenance 审计痕（CRM Q3.3-3）；先例衰减/复核原语（APS P1：负面先例累积防过度保守）。

### 3.4 明确不上收

ICP 阈值语义（业务字段）、`root_cause_class` 分类学、回测判据函数（排产重放对比 KPI / ICP 双闸具体值）。基座提供回测框架位（`replay` 已有雏形）。

---

## 四、Q4 耦合 —— 统一设计原则

三仓一致：**三能力互为前提，非独立能力**。按"决策→审计→复盘→进化"事件链统一设计原语族，而非三个独立模块：

```
② 安全/HITL（底座轨）
   ├─ 为 ① 提供追溯轨：审计链 + 审批状态机贯穿（record_kind 分轨）
   └─ 为 ③ 提供人工闸：进化生效必须经 HITL 原语（不可绕过不变式）
① 决策闭环（主干）
   ├─ 产出 ③ 的输入：结局采集 → 复盘输出 → 进化候选
   └─ 产出 ② 的审计对象：每条决策即审计链节点
③ 进化（消费端）
   └─ 消费 ① 的复盘输出 + 必须经 ② 的闸生效后反哺 ①
```

**收敛批次顺序**（三仓一致，1.0 稳定承诺优先序）：
- **批次一（P0，进 1.0 稳定承诺）**：① OutcomeRecord 契约 + 结局采集原语；② 三档安全模式 + HITL 审批原语（含 resume 证据契约）；③ evolution 毕业（以 ②① 毕业为前提）。
- **批次二（P1）**：有效性度量管道 + 审计 canonical schema 毕业 + 审计链合一 + IAM/RBAC 判定接口 + 复盘候选触发。
- **不上收**：K-M-D/K/M-J 语义、具体枚举值/评分尺子/红线规则/动作目录/角色矩阵（域特有）。

---

## 五、方案落地检查（trust-but-verify）

| 检查项 | 状态 |
|---|---|
| 本仓现状锚点核实（approval 五符号 / AUDIT_EVENT_* / evolution 原语族 / audit.py 字段集） | ✅ 本方案撰写时已源码核实 |
| OutcomeRecord 契约是否本仓缺失 | ✅ 确认 `contract/audit.py` 无结局字段 |
| 三仓回执是否充分阅读 | ✅ enterprise/CRM/APS 三份全读 |
| 收敛顺序是否符合"先本仓增强、后三仓改造" | ✅ 本方案全部是本仓新增/毕业，无任何三仓改造动作 |
| HITL 闸是否为基座结构保证（非约定） | ✅ 不变式明确 |
| 是否过度上收（域特有误收） | ✅ 每能力均列"不上收"清单 |

---

## 六、后续动作
1. 批次一落地：新增 `contract/outcome.py` + `contract/audit.py` 补结局/三档模式符号（若需）+ 门面登记 + manifest 重生成。
2. 批次一落地后向三仓回函：宣布 OutcomeRecord 契约 + 三档模式 + HITL 原语毕业，请三仓接线对齐。
3. 批次二按 RFE 流程逐步毕业。

---

*foundation 三大支柱解决方案 · 2026-10-13 · 依据三仓回执形成，本仓留档。*
