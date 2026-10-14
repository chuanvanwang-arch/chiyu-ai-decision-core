# foundation 三大支柱 —— 详细设计文档

> **发出方**：foundation（AI 原生底座唯一事实源）
> **日期**：2026-10-13
> **上级方案**：`docs/2026-10-13-foundation三大支柱解决方案(据三仓回执形成).md`（T74=1231caf）
> **三仓回执**：enterprise / CRM / APS 答《foundation 征询函——三大企业能力需求》
> **设计范围（用户拍板）**：**批次一设计到可直接实现；批次二设计到接口契约级（可机检判定）**。
> **性质**：设计稿（P6）。**⛔ 未获批准不进入实现**（brainstorming HARD-GATE）。批准后按批次排实现计划。
> **纪律**：本仓 = AI 原生底座唯一事实源。设计全部为本仓**新增 L0 契约**与**原语沉淀**，**零三仓改造**；收敛顺序 **②→①→③**；HITL 闸为**基座结构保证**（非约定级）。所有锚点为本仓源码实测。

---

## 目录

- [第一部分 · 设计与原则](#第一部分--设计与原则)
- [第二部分 · 批次一设计（P0，进 1.0 稳定承诺）](#第二部分--批次一设计p0进-10-稳定承诺)
  - [D1 OutcomeRecord 结局采集契约](#d1-outcomerecord-结局采集契约)
  - [D2 三档安全模式（off/advisory/enforced）](#d2-三档安全模式offadvisoryenforced)
  - [D3 HITL 审批原语 + 不可绕过不变式](#d3-hitl-审批原语--不可绕过不变式)
  - [D4 resume 侧证据契约](#d4-resume-侧证据契约)
- [第三部分 · 批次二设计（P1，接口契约级）](#第三部分--批次二设计p1接口契约级)
  - [D5 有效性度量管道](#d5-有效性度量管道)
  - [D6 审计链合一 + canonical schema](#d6-审计链合一--canonical-schema)
  - [D7 IAM/RBAC 判定接口](#d7-iamrbac-判定接口)
  - [D8 evolution 毕业（按 RFE 流程）](#d8-evolution-毕业按-rfe-流程)
- [第四部分 · 落地接缝与测试闸](#第四部分--落地接缝与测试闸)
- [第五部分 · 双轨生命契约（机器块 + 散文）](#第五部分--双轨生命契约机器块--散文)
- [第六部分 · P7 规格自检](#第六部分--p7-规格自检)
- [附录 A · 与三仓回执的逐项对齐](#附录-a--与三仓回执的逐项对齐)

---

## 第一部分 · 设计与原则

### 1.1 L0 契约纪律（对 D1/D4/D6 硬约束）

新增契约符号必须遵守既有 `contract/__init__.py` 的 L0 纪律：

1. **零第三方依赖**（除 dataclasses）、零 IO、零领域字面量；
2. 消费方**只许** import `chiyu_kernel.api` 与 `chiyu_kernel.contract`，import 内部实现即违约（守卫 `tests/test_app_imports_contract_only.py`）；
3. 契约常量取值或形状变化 → 升 `CONTRACT_VERSION`（`version.py:59`，现 1.0.0）。
4. **进 1.0 稳定承诺** ⇒ 状态 `stable`，此后 BREAKING 须走完整 deprecation 周期（`docs/versioning-and-deprecation.md`）。批次一 P0 设计即按 stable 交付，须过 readiness 评审。

### 1.2 门面登记四步闸（D1/D2/D4 落地必经）

新增符号进 `chiyu_kernel.api.__all__` 的**四步闸**（违反则测试判红，来源自记忆与实测）：

| # | 闸 | 落点 | 说明 |
|---|---|---|---|
| 1 | **新增子包/文件登记** | `tests/test_api_facade_covers_all_layers.py` 的 `LAYERS`（或 `EXEMPT_LAYERS` 登记豁免） | 磁盘枚举机械守卫，新增子包忘登记会**静默放行**，故硬编码清单必须手动同步 |
| 2 | **能力层登记** | `version.py` 的 `CAPABILITIES` | 新增能力层未登记 → `test_version_and_capabilities.py` 判红 |
| 3 | **门面 `__all__`** | `api.py` + `contract/__init__.py` | 门面 import 了却未进 `__all__` → `test_facade_import_vs_all.py` 判红 |
| 4 | **Makefile lint `--layers`** | `tools/check_import_surface.py` | 新增层未同步 `--layers` → lint 失败 |

### 1.3 批次划分

- **批次一（P0）**：D1 OutcomeRecord 契约 / D2 三档安全模式 / D3 HITL 审批原语 / D4 resume 证据契约。**进 1.0 稳定承诺**，设计到可实现。
- **批次二（P1）**：D5 有效性度量管道 / D6 审计链合一+canonical schema / D7 IAM-RBAC 判定接口 / D8 evolution 毕业。**接口契约级**，不写实现细节。

---

## 第二部分 · 批次一设计（P0，进 1.0 稳定承诺）

---

### D1 OutcomeRecord 结局采集契约

#### D1.1 现状（核实）

- `contract/audit.py` 的 `AUDIT_REQUIRED_FIELDS` 覆盖决策动作改值（prescription_id/from_value/to_value/verdict），**不覆盖结局**（success/failure 类别）。
- 三仓各自造结局采集：CRM `OUTCOME_TYPES=["won","lost","paid","stalled","partial","other"]` + `writeOutcome`；APS `decisions.py:79` `outcome_signal` 默认 `"pending"`；enterprise 复盘证据面缺口（结局信号源缺失）。
- 跨仓口径漂移 ⇒ 命中率/逆转率等统计跨仓不可比。

#### D1.2 落点

**新建** `contract/outcome.py`（L0 契约，零依赖），并在 `contract/__init__.py` re-export + `api.py.__all__` 登记。

#### D1.3 契约定义

```python
"""结局采集契约 —— 决策→执行→结局→复盘 闭环的第一环。

⛔ L0 单事实源：结局是"决策做完了事后证明它对错"的定量事实，必须与决策
   （decision_id）强关联、可追责（recorded_by）、防篡改（链式挂钩审计）。
   本契约只收"枚举机制"，不收"具体枚举值"（won/lost/paid 是销售语义，
   制造/医疗租户可扩展 OUTCOME_KINDS，见 CRM Q1.4 边界）。
"""
from __future__ import annotations

from typing import Mapping, Tuple

# ── 结局枚举机制（值可扩展，机制由本契约统一）────────────────────────
# 三仓共同最小面；消费方可在其域内追加合法 kind（构造期校验用 validate_outcome_kind）
OUTCOME_KINDS: Tuple[str, ...] = (
    "success",    # 成功 / 赢单 / 达标
    "failure",    # 失败 / 丢单
    "partial",    # 部分达成 / 局部
    "stalled",    # 停滞
    "other",      # 其他（域自定义入口）
)

# ── 结局记录的必填字段（顺序参与 canonical 序列化，不可重排；与 AUDIT_REQUIRED_FIELDS 同规）
OUTCOME_REQUIRED_FIELDS: Tuple[str, ...] = (
    "outcome_id",    # 结局记录 id
    "decision_id",   # 关联决策（闭环锚点，追溯链关键）
    "outcome_kind",  # 结局类型（∈ OUTCOME_KINDS）
    "recorded_ts",   # 采集时间（ISO-8601）
    "recorded_by",   # 采集者（人工 user_id / 系统 principal，追责到个人）
    "evidence_ref",  # 证据引用（回放依据：订单 id / 结算单 id 等）
)

# ── 结局→置信度校准方向映射（P0 提供机制；具体映射表由消费方 domain 注入？—— 见 D1.4 边界）
OUTCOME_CONFIDENCE_DIRECTION: Mapping[str, str] = {
    # 结局对"当时决策置信度"的校准方向：up（正向印证决策） / down（质疑） / neutral（无信息）
    "success": "up",
    "failure": "down",
    "partial": "down",       # 部分达成：弱质疑（保守单边）
    "stalled": "neutral",    # 停滞：无对错信息，不校准
    "other":   "neutral",
}


def validate_outcome_kind(kind: str, extra: Tuple[str, ...] = ()) -> bool:
    """构造期校验：kind ∈ OUTCOME_KINDS ∪ 域扩展值。域扩展值须显式传 extra，
       避免拼错进闭集却静默通过（对齐 G4 禁裸字符串纪律）。"""
    return kind in OUTCOME_KINDS or kind in extra


__all__ = [
    "OUTCOME_KINDS", "OUTCOME_REQUIRED_FIELDS",
    "OUTCOME_CONFIDENCE_DIRECTION", "validate_outcome_kind",
]
```

#### D1.4 边界（三仓共识）

- **基座收**：`OUTCOME_KINDS` 枚举机制 + `OUTCOME_REQUIRED_FIELDS` + `OUTCOME_CONFIDENCE_DIRECTION`（校准**方向**机制）+ `validate_outcome_kind`。
- **域特有留消费方**：具体枚举值扩展（won/lost/paid）、`OUTCOME_CONFIDENCE_DIRECTION` 的量值（基座只定方向语义，量值/映射表由各仓 domain 注入）、结局证据的域语义（排产 tardy/makespan、销售订单号）。⛔ 不违反 C-B 铁律：**结局校准不得污染 `S3_aggregate` 的 `ratio` 唯一置信度源**——校准是闭环反馈轨，不是 S3 的输入源。

#### D1.5 P0 采集/读取原语（接口形态）

批次一落契约；`append_outcome` / `list_outcomes(decision_id)` 采集 API 由**后续实现计划**完成（属 foundation 内核，非 L0 契约层）。设计只定契约与接口签名契约：

```python
# 接口契约（实现计划阶段落地，内核层）
# def append_outcome(outcome: Mapping[str, object]) -> str:      # 返回 outcome_id，落审计链
# def list_outcomes(decision_id: str) -> Tuple[Mapping[str, object], ...]:
#     """按 decision_id 读结局；空返回 ()（诚实降级，不造假）"""
```

---

### D2 三档安全模式（off / advisory / enforced）

#### D2.1 现状（核实）

- foundation **无** `SECURITY_MODE`/`advisory`/`enforced` 符号（Grep 实证：仅 `store/conn.py` 的无关命中）。
- APS `security.py:59/75/365/380` 已实现三档：off 恒放行但 reason 显式「未启用」、advisory 真判恒放行 + `would_deny`、enforced 真拦；`:380` 断言 `advisory.would_deny == not enforced.allowed` 防两档漂移。
- CRM 自治分级/guardrails 与三档同构思想（从旁印证）。

#### D2.2 落点

**新建** `contract/security.py`（L0 契约）或并入现有 `contract/audit.py`。建议**独立 `security.py`**（安全≠审计，职责分离，避免 security 符号混入审计字面量）。

#### D2.3 契约定义

```python
"""企业安全契约 —— 三档安全模式（off/advisory/enforced）默认范式。

来源：APS security.py 实证形态，升格为基座默认范式（三仓一致 P0，enterprise Q2.3/APS Q2.3）。
渐进收紧价值：企业上线不可能一步 enforced —— 默认 off 零破坏 → advisory 生产观测
 `would_deny` 命中率 → enforced 收口。对存量系统零破坏。
"""
from __future__ import annotations

from typing import Tuple

SECURITY_MODES: Tuple[str, ...] = ("off", "advisory", "enforced")

# ⛔ 缺省模式：off（对存量系统零破坏；企业显式收紧才升档）
SECURITY_MODE_DEFAULT = "off"

# 不变量（升格自 APS security.py:380 防漂移断言）：
#   advisory.would_deny == (not enforced.allowed)
# 结构保证两档判定一致性，杜绝「advisory 观测绿、enforced 才现红」的回归。
SECURITY_MODE_INVARIANTS: Tuple[str, ...] = (
    "advisory_would_deny_eq_not_enforced_allowed",  # 契约键；实现期由内核断言保证
)

__all__ = [
    "SECURITY_MODES", "SECURITY_MODE_DEFAULT", "SECURITY_MODE_INVARIANTS",
]
```

#### D2.4 判定结果形态（接口契约，批次二 D7 细化）

```python
@dataclass(frozen=True)
class SecurityDecision:
    mode: str          # ∈ SECURITY_MODES
    allowed: bool      # 是否放行
    would_deny: bool   # advisory 下若 enforced 是否会拒（生产观测面；enforced 下 = not allowed）
    reason: str        # 结构化拒因（off 时显式「未启用」，杜绝静默放行）
```
（`SecurityDecision` 的 dataclass 实现在**批次二 D7** 与 `Principal` 一并收（判定接口），本 D2 只定 `SECURITY_MODES` 常量契约。）

#### D2.5 边界

基座收**模式枚举 + 不变量键 + 判定结果形态**；权限矩阵、角色-动作映射、红线规则业务语义、principal 身份源对接留消费方（不违反三仓共识「收判定接口不收角色矩阵」）。

---

### D3 HITL 审批原语 + 不可绕过不变式

#### D3.1 现状（核实）

- foundation 已有两层审批闸：
  - **决策落库前**：`chiyu_kernel.approval` 的 `DecisionApprovalGate`（B3 三态 APPROVED/REJECTED/PENDING，已经 `contract/__init__.py` re-export，`approval/__init__.py:121-124`）。`RedlinePriorityGate` 裁定顺序：红线→REJECTED；判据缺失→PENDING；autonomous→APPROVED。
  - **工具执行前**：`interaction.ApprovalGate`（同步 HITL：`request/approve/deny` 三态 + `guard()` 拦截，`interaction/__init__.py:25-69`）。
- **缺口**：两层之间**无统一 HITL 证据契约**；`approve`/`deny` 无 `approver_id/approved_at/evidence_ref` 必填溯源；"无 approve 不可生效"是**文档纪律而非结构保证**（三仓一致 P0 痛点）。

#### D3.2 HITL 不变式（结构保证，非约定）

**不变量 `HITL_EVIDENCE_INVARIANT`**：任何「PENDING 决释放 / 进化生效 / 高危险动作放行」入口**只认带 HITL 证据链的 payload**：

```python
# 证据必填三件套（缺任何一项 ⇒ 入口抛 HITLEvidenceError，不是跳过、不是文档提示）
HITL_EVIDENCE_FIELDS: Tuple[str, ...] = ("approver_id", "approved_at", "evidence_ref")
```

实现期由**内核生效 API** 强制（`assert_hitl_evidence(payload)`，缺字段即抛错），而非消费方"记得调用"。

#### D3.3 落点

- `contract/security.py`（与 D2 合并，因 HITL 闸与三档模式同属「企业安全」契约域）新增 `HITL_EVIDENCE_FIELDS` 等常量。
- 内核层（实现计划阶段）提供 `assert_hitl_evidence` + 统一 `ApprovalStateMachine`（三态+防护），对齐三仓既有状态机形态。

#### D3.4 统一状态机形态（接口契约）

三仓既有状态机（CRM 五态 `PENDING_SUBMIT/APPROVING/APPROVED/REJECTED/CANCELED` + `OPERATIONS_BY_STATE`；enterprise `INSTANCE_STATES`；基座 B3 三态）收敛为基座核态 + 域扩展：

```python
# 基座核态（闭集；域可扩展但不得删除这四态）
APPROVAL_CORE_STATES: Tuple[str, ...] = ("pending", "approved", "rejected", "canceled")
APPROVAL_TRANSITIONS: Tuple[Tuple[str, str], ...] = (
    ("pending", "approved"), ("pending", "rejected"), ("pending", "canceled"),
)
# 非法迁移防护：assert_transition(from, to) —— 不在 APPROVAL_TRANSITIONS ⇒ 抛错
```

**实现纪律**：基座管**协议与格式**（状态机 + HITL 证据 + 不可绕过断言），消费方管**动作语义与存储**（enterprise Q2.4；CRM Q2.3「毕业面走 api.__all__ 单一通道」；APS Q3.3「生效入口只认带 HITL 证据链的 payload」）。

---

### D4 resume 侧证据契约

#### D4.1 现状（核实）

- `AUDIT_EVENT_APPROVAL_RESUMED = "approval_resumed"`（`contract/decision.py:116`）事件存在，但 **resume 的 principal/依据 payload 无契约锚**（APS P0-B 实名指出）——PENDING 批准后续跑落库（`resume_spine`）的证据结构缺失。

#### D4.2 契约定义

在 `contract/decision.py`（或 `contract/security.py`）新增 resume 证据字段契约：

```python
# PENDING 批准后续跑（G3 resume_spine）的证据 payload 契约锚（APS P0-B）
RESUME_EVIDENCE_FIELDS: Tuple[str, ...] = (
    "resume_principal",  # 谁批准（追责到个人）
    "resumed_at",        # 何时批准（ISO-8601）
    "basis",             # 基于什么（决策 id / 证据 ref，回放依据）
)
```

**不变量**：`resume_spine` 入口校验 `RESUME_EVIDENCE_FIELDS` 三件套齐备，缺则拒续跑并落 `approval_resumed` 审计失败态——使 PENDING 放行的证据结构与决策审计**同链可追**（enterprise Q2.4 / CRM「审批留痕」痛点）。⚠ 复用 D3 的 `HITL_EVIDENCE_FIELDS` 语义，但 resume 有专门字段名（`basis` 承载"基于什么"）。

---

## 第三部分 · 批次二设计（P1，接口契约级）

> 本批设计到**接口契约级**：只定符号签名、schema、不变量键，不写实现细节。批准后单独排期。

---

### D5 有效性度量管道

**目标**：跨仓**统计口径统一**（命中率/逆转率/校准曲线的对账最小面），评分器维度**可插拔**。

**接口契约**：

```python
class ScoreCard:          # 单决策度量卡（可插拔评分器各自的输出收敛为一张卡）
    decision_id: str
    rubric_scores: Mapping[str, float]     # 九尺子（基座）
    elements: Mapping[str, bool]           # 八要素声明（基座契约）
    metrics: Mapping[str, object]          # 域评分器注入（4问/SLA/strictness），键为域命名空间

def aggregate_metrics(cards, window) -> MetricSummary:
    """窗口聚合：auditability_pct / full / hit_rate / reversal_rate。
    ⛔ 诚实降级：无样本/未评 ⇒ 返回空而不掩盖为绿（对齐 CRM aggregateAuditability「未评不掩盖」）。"""
```

- **基座收**：聚合窗口形态 + 诚实降级语义 + `ScoreCard`/`MetricSummary` schema（canonical，enterprise Q1.3 P1「record_kind+rubric_scores+elements 三键毕业」）。
- **域特有留消费方**：各仓评分器实现、域 KPI（排产 makespan/tardy、销售命中率语义）。

---

### D6 审计链合一 + canonical schema

**目标**：消除 `chain_hash`（foundation）与 APS `audit.py`/CRM `provenance.js` 自有 SHA-256 链的**同名异实**（APS P1-D/CRM P1）。

**接口契约**：

```python
# 审计 canonical schema（enterprise Q1.3 P1「record_kind+rubric_scores+elements」毕业）
AUDIT_CANONICAL_SCHEMA: Tuple[str, ...] = ("record_kind", "rubric_scores", "elements", ...)
# 链式哈希单一事实源：chain_hash = sha256(prev_hash + canonical(record))
# 墓碑擦除语义（GDPR vs 禁 DELETE）在基座层定义：软删标记，不物理删（对齐 CRM append-only 墓碑）
```

- **基座收**：canonical schema + 链式哈希统一实现 + 墓碑语义。
- **域特有留消费方**：各仓动作域字段的 canonical 组装（消费方只余接线）。

---

### D7 IAM/RBAC 判定接口

**目标**（三仓交集：收判定接口不收角色矩阵）：enterprise P1 / APS P1-C / CRM P2 观望。

**接口契约**：

```python
class Principal:          # 判定主体（身份最小面，不绑定具体 IdP）
    id: str
    scopes: Tuple[str, ...]       # 作用域（tenant / case）

class SecurityDecision:   # 判定结果（D2.4 已在批次一定型，此处补 scope）
    mode: str
    allowed: bool
    would_deny: bool
    reason: str
    scope: str

class RoleGate(Protocol): # 角色闸原语：principal + scope + deny 理由结构化
    def check(self, principal: Principal, resource: str, action: str) -> SecurityDecision: ...
```

- **基座收**：`Principal`/`SecurityDecision`/`RoleGate` 接口 + 三档判定执行器（复用 D2 不变量）。
- **域特有留消费方**：角色矩阵（sales/ten_admin/channel_manager/actions 目录 rbac_roles）、身份源映射（IdP 对接）。enterprise 贡献参考实现（IAM 五档+token 验签/过期/吊销+双层 effective_roles）。

---

### D8 evolution 毕业（按 RFE 流程）

**目标**：`evolution/` 从 experimental 毕业为 stable（三仓一致 P0），"草稿→回测→HITL→生效"为通用原语。

**毕业前置（三仓一致）**：
1. 能力②（D3 HITL 原语）先毕业——进化闸复用其「无 approve 不可生效」不变式；
2. 能力①（D1 OutcomeRecord/复盘）先毕业——进化消费复盘输出，倒序则进化消费不存在的复盘出口（APS Q4）；
3. 过 `readiness_report`（`evolution/readiness.py`）+ 版本稳定承诺 + `api.__all__` 纳入 + manifest 重生成 + **RFE 流程**（禁伪稳定包装，CRM Q3.3/enterprise Q3.3）；
4. `version.py CAPABILITIES` 中 `("evolution", "experimental")` → `("evolution", "stable")`。

**接口契约（毕业面）**：
- 基座收**形态**：状态机 + 回测闸接口 + HITL 钩子，不收 passLine/minSample 具体值（域配置）。
- 生效动作**强制**经 D3 HITL 原语 + 留 D6 audit 痕（CRM Q3.3-3 / APS promote_gate 判据形态可贡献）。

---

## 第四部分 · 落地接缝与测试闸

### 4.1 批次一落地文件映射

| 设计项 | 变更文件 | 四步闸动作 |
|---|---|---|
| D1 | **新增** `contract/outcome.py` | ① LAYERS 登记 ② CAPABILITIES ③ contract/__init__.py + api.py `__all__` ④ Makefile lint `--layers`；随后运行 `contract/_gen_manifest.py` 重生成 manifest.json |
| D2+D3+D4 | **新增** `contract/security.py`（复用 D2 落点） | 同上四步闸 |
| D3 | 内核层 `assert_hitl_evidence` + `ApprovalStateMachine` | 落地实现计划（非 L0 契约） |

### 4.2 变异自证要求（每个守门测试必须）

⛔ 本仓纪律：每个闸门必须**变异自证**——删判据分支→转红→还原；退出码判据禁止经管道。D1/D2 的 `validate_outcome_kind`/`SECURITY_MODE_INVARIANTS` 校验器须配变异测试，证明"漏校验会红"。

### 4.3 组合命令验收

全量回归（Makefile `test` = kernel+tools+decision+portal+examples）**只跑组合命令**，单跑绿曾掩盖组合全塌（记忆纪律）。新增后须 `make test` 全绿 + `test-all`。

---

## 第五部分 · 双轨生命契约（机器块 + 散文）

每个设计任务携带一个 `contract-yaml` 机器块 + 一行散文复述，供执行智能体在运行期被可机检验证。

```contract-yaml
- task: "批次一落地：新建 contract/outcome.py OutcomeRecord 契约 + 门面登记 + manifest 重生成"
  contract_task_id: ct-foundation-pillar1-outcome
  agent: foundation
  skills: [brainstorming, write-implementation-plan]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L0, L1], max_hops: 2 }
  success: "OUTCOME_KINDS/OUTCOME_REQUIRED_FIELDS 入 contract.__all__ 且四步闸全绿(make test 组合命令 passed)"
```
**契约说明**：批次一 OutcomeRecord 契约由 foundation 承接（键 `ct-foundation-pillar1-outcome`），须调用 `brainstorming`+`write-implementation-plan` SKILL、读取本仓记忆（L0/L1，≤2 跳）；成功标准为契约符号入 `contract.__all__` 且四步闸组合命令全绿。

```contract-yaml
- task: "批次一落地：新建 contract/security.py 三档安全模式 + HITL 证据不变式 + resume 证据契约 + 门面登记"
  contract_task_id: ct-foundation-pillar1-security
  agent: foundation
  skills: [brainstorming, write-implementation-plan]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L0, L1], max_hops: 2 }
  success: "SECURITY_MODES/HITL_EVIDENCE_FIELDS/RESUME_EVIDENCE_FIELDS 入 contract.__all__ 且不变量变异自证绿"
```
**契约说明**：批次一安全契约由 foundation 承接（键 `ct-foundation-pillar1-security`），须调用 `brainstorming`+`write-implementation-plan` SKILL、读取本仓记忆（L0/L1，≤2 跳）；成功标准为三组常量入 `contract.__all__` 且不变量变异自证绿。

```contract-yaml
- task: "批次二：向三仓回函宣布批次一毕业（OutcomeRecord/三档模式/HITL原语），请三仓接线对齐"
  contract_task_id: ct-foundation-pillar1-declarerelease
  agent: foundation
  skills: [brainstorming]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L0], max_hops: 1 }
  success: "docs/ 落《批次一毕业回函-致CRM-APS-enterprise》声明契约符号与接线约定"
```
**契约说明**：批次一毕业回函由 foundation 承接（键 `ct-foundation-pillar1-declarerelease`），须调用 `brainstorming`、读取本仓记忆（L0，≤1 跳）；成功标准为在 `docs/` 落回函声明契约毕业与接线约定。

> **覆盖性**：本设计为 foundation 单仓文档，只覆盖 foundation 承接任务（上述 3 个）——不覆盖任一注册 agent 全编队；若后续文档跨 ≥2 注册 agent，则必须补齐全部 agent 契约块（§A 双向覆盖断言）。

---

## 第六部分 · P7 规格自检

| # | 自检项 | 结果 |
|---|---|---|
| 1 | 每个任务含 `contract_task_id + agent + skills + memory + success` | ✅ 见第五部分 |
| 2 | `contract_task_id` 唯一且与 agent 登记键一致 | ✅ foundation 三键唯一 |
| 3 | skill ⊆ agent.skillCalls / memory ∈ agent.memory.read | 见运行 `validate-contract.mjs --registry`（若 registry 存在） |
| 4 | 覆盖性：单 agent 文档不必全编队覆盖 | ✅ 本设计只覆盖 foundation |
| 5 | 所有 L0 契约锚点为本仓实测（无虚构符号） | ✅ D1/D2/D3/D4 均写「现状（核实）」段 |
| 6 | HITL 闸为基座结构保证（非约定） | ✅ D3.2 不变量字段必填即抛错 |
| 7 | 收敛顺序 ②→①→③；批次一设计到可实现、批次二到契约级 | ✅ 已按用户拍板范围 |

**验证命令**（实现计划阶段）：
```bash
node scripts/validate-contract.mjs docs/plans/2026-10-13-foundation三大支柱详细设计.md [--registry src/agent/agentSpec.js]
```
（如本仓无 agentSpec registry，则仅结构自检；有则交叉校验 skill/memory/layer 隶属。）

---

## 附录 A · 与三仓回执的逐项对齐

| 设计方案 | 回执来源 | 对齐点 |
|---|---|---|
| D1 OutcomeRecord | APS #1 P0 / CRM Q1.3 P0 / enterprise Q1.3 P0 | 结局采集契约缺统一基座（三家各自造口径漂移） |
| D1.4 枚举机制不收值 | CRM Q1.4 | 基座只收枚举机制不收具体枚举值 |
| D2 三档模式 | APS #2 P0 / CRM P1 / enterprise 认可 | APS security.py 形态升格基座默认 |
| D3 HITL 审批原语 | CRM Q2.3 P0 / enterprise #3 P0 / APS #4 P0 | 闸基座结构保证，走 api.__all__ 单一通道 |
| D4 resume 证据契约 | APS #3 P0 | AUDIT_EVENT_APPROVAL_RESUMED payload 无契约锚 |
| D5 有效性度量管道 | enterprise Q1.3 P1 / CRM Q1.3 P1 / APS #5 P1 | 跨仓统计口径统一 + 诚实降级 |
| D6 审计链合一 | APS #6 P1 / CRM P1 | chain_hash 与各仓自有链同名异实 |
| D7 IAM/RBAC 判定接口 | enterprise #5 P1 / APS #6 P1 / CRM P2 | 收判定接口不收角色矩阵 |
| D8 evolution 毕业 | enterprise #7 / CRM Q3.3 / APS #4 | 按 RFE 流程，以 ②① 毕业为前提 |
| 收敛顺序 ②→①→③ | 三家 Q4 一致 | 安全/HITL 为底、决策闭环为主干、进化为消费端 |
| 不上收清单 | 三共识 | K-M-D/K-MJ 语义、评分尺子、红线规则、动作目录、角色矩阵 |

---

*foundation 三大支柱详细设计 · 2026-10-13 · 据解决方案（T74=1231caf）与三仓回执；P6 设计稿，批准后方进实现。*
