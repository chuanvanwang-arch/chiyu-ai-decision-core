# enterprise 对 T75 设计落地核查报告 + 三仓通知的确认与对齐回执

> **发出方**：enterprise ｜ **日期**：2026-10-13 ｜ **对应来文**：`docs/2026-10-13-T75设计落地核查报告-兼致三仓通知.md`（T79）
> **方法**：本仓逐符号实测（解释器）+ 源码锚点核对 + 既有判据复跑，非凭记忆。

---

## 一、T75 核查报告结论确认

**D1–D8 全部落地、验收全绿**，我方逐符号实测复核，结论与报告一致：

| 设计项 | 我方实测核对 | 判定 |
|---|---|---|
| D1 OutcomeRecord | `OUTCOME_KINDS` 5 值闭集 / `OUTCOME_REQUIRED_FIELDS` 6 字段 / `validate_outcome_kind(kind, extra=())` 签名一致（实测：闭集外 `won` 判 False、`extra=('won','lost')` 后判 True、大小写 `Succeeded` 不静默） | ✅ |
| D2 三档安全模式 | `SECURITY_MODES=("off","advisory","enforced")` / `SECURITY_MODE_DEFAULT="off"` 逐字一致；本仓零消费点 ⇒ 默认零破坏成立 | ✅ |
| D3 HITL 原语 | `HITL_EVIDENCE_FIELDS` 三必填、`APPROVAL_CORE_STATES` 四核态、`APPROVAL_TRANSITIONS` 三迁移闭集、`assert_hitl_evidence`/`assert_transition` 实存；并吸收 CRM §2.1/§2.2 修订（extra 通道 + `HITL_RESUME_FIELD_ALIASES`） | ✅ |
| D4 resume 证据 | `RESUME_EVIDENCE_FIELDS` 三键 + 别名通道与 HITL 三件套逐键映射（实核：键集相等守卫） | ✅ |
| D5 有效性度量（契约级） | `SCORECARD_FIELDS`/`METRIC_SUMMARY_FIELDS`/`AGGREGATE_METRIC_KEYS`/`HONEST_DEGRADATION_INVARIANTS` 字段数一致 | ✅（契约级） |
| D6 审计链合一 | `AUDIT_CANONICAL_SCHEMA` 13 键（必填 10 + 三毕业键 `record_kind`/`rubric_scores`/`elements`）实测到位——**本仓 E5 接线正对齐此三毕业键**（见第三节 B） | ✅ |
| D7 IAM/RBAC 接口 | `Principal`/`SecurityDecision`/`RoleGate(Protocol)` 签名一致，`RoleGate` `_is_protocol=True` | ✅ |
| D8 evolution 毕业 | `capability_status("evolution")="stable"`、`EVOLUTION_EXPERIMENTAL=False` 实测到位（**本仓据此落实口径升级，见第三节 A**） | ✅ |

批次验收计数（T76/T77/T78 = 849/870/876 passed）我方不独立复跑（属基座仓自证），但 D6/D8 两个与本仓强相关的对账面已实机核对，结论可信。

---

## 二、4 处差异申报确认（均认可，无争议）

| # | 差异 | 我方意见 |
|---|---|---|
| 1 | D3.4 统一 `ApprovalStateMachine` 类未新建，收敛为「契约闭集 + `assert_transition` + 既有 Gate」 | ✅ 认可。与我方此前批次二核验回执所述「本仓 `INSTANCE_STATES` 大写五态（含 `APPROVING` 会签中间态）与基座核态小写四态不同名不同构」一致——收敛为契约闭集 + 断言，**避免第二份状态机实现**，正合「不新增第二份判据表」纪律。我方映射层方案（`state→core_state` 纯函数，域五态保留保会签语义）仍有效，待批次二 D6/D7 兼容约定吸收 |
| 2 | D1.5 `append_outcome`/`list_outcomes` 未落（设计原文明示属后续实现计划） | ✅ 认可。**这正是我方征询回执 Q1.1 申报的「结局采集管道未闭环」缺口的解药**——D1 契约已就绪，企业侧接线排期随 P-1 基座实现 |
| 3 | D5 `aggregate_metrics` 未落（批次二定位契约级） | ✅ 认可。schema 常量 + dataclass + 诚实降级结构保证已落，实现 P-2 |
| 4 | D4 `resume_spine` 入口断言接线未落（属 decision 层，kernel/api 无该符号） | ✅ 认可。契约 + 断言已就绪；入口接线属三仓后续项。企业侧 `persist_resume` 当前自建 audit 记录、不经脊柱审计轨，是否改接 `resume_spine`+`assert_hitl_evidence` 待评估（建议保留域复算逻辑、仅补等价 HITL 证据断言，防基线漂移） |

---

## 三、本仓对齐动作（来文第五节 enterprise 要求）

### A. SkillDraft/evolution 消费面同步 `EVOLUTION_EXPERIMENTAL=False` —— ✅ 已落实

来文要求企业侧同步 evolution 毕业后事实。我方原 `bridge.py` 口径块（2026-10-12 R-FE1 立）标注 evolution "属 experimental、排除在 1.0 之外"——**与基座已毕业事实直接矛盾**。已重写口径块（`packages/enterprise/src/enterprise/evolution/bridge.py:15-26`）：

- 第 1 条：evolution 已毕业 stable，**不再标注 experimental**，对外可据实表述稳定状态；
- 第 2 条：**零断言依赖纪律保留**（verify_evolution_* 两判据仍不直触草稿 API）+ 落实 `require_capabilities({"evolution":"stable"})` 机检守门（见 C）；
- 第 3 条：未来若基座再调级别，以 `require_capabilities` 实机探测为准，**不叠加伪稳定/伪实验包装**（R-FE1.3 精神保留）。

### B. `AUDIT_CANONICAL_SCHEMA` 为 record 毕业对账面（Q1.3）—— ✅ 已对齐

来文称该 schema 是 Q1.3 提的三毕业键对账面。我方 E5 接线（`orchestrator.py` `_audit_persister` + `_write_audit`）实测：

- `rubric_scores`（九尺子全数值）+ `elements`（要素声明快照）**进 `to_value` canonical**，复盘可据以复算「当时九尺子几分、声明了哪些要素」；
- `record_kind` 在 `_audit_persister` 作**轨身份硬断言**（`record_kind == AUDIT_RECORD_KIND` 不符即 RuntimeError fail-loud，R79 防串轨）；
- 运行态 E2E（`scripts/verify_u2_e2e_spine_audit.py`，host 重启后实跑 RC=0）已实证 REJECTED/PENDING 双路径 canonical 含上述双 inputs。

**结论**：三毕业键全部对齐，对账面成立。

### C. 新符号双面可达 + `require_capabilities` 机检 —— ✅ 已落实

来文称全部新符号经 `chiyu_kernel.contract` 与 `chiyu_kernel.api` 双面同对象可达，且 `require_capabilities` 可机检各层状态。我方实测：

- `EVOLUTION_EXPERIMENTAL`(api=T/contract=F)、`AUDIT_CANONICAL_SCHEMA`(双 T)、`AUDIT_RECORD_KIND`(双 T)、`require_capabilities`(api=T)、`capability_status`(api=T)——均按报告口径可达；
- **机检守门已落实**：`scripts/verify_u2_spine_route.py` 新增 **U19** 前置守卫 `require_capabilities({"evolution":"stable"})`（R134：声明=执行，防基座回退到 experimental 时静默沿用旧消费面）。复跑真值态 **101/0**（含 U19），机检生效、无回归。

---

## 四、后续排期表态（对应来文第四节 P-1/P-2/P-3）

| 项 | 企业侧态度 | 备注 |
|---|---|---|
| P-1 结局采集 API（`append_outcome`/`list_outcomes`） | **待基座实现后接**。当前 `retro_backend`/`decision_memory_store` 零 outcome 消费点（此前 Q1.1 缺口二次实锤），接 `append_outcome`（落审计链）+ 把 won/lost 结局事件接入复盘触发 | 企业侧接线排期待 P-1 基座就绪 |
| P-2 聚合函数 | 契约级已满足，企业侧按需调用，无阻塞 | — |
| P-3 resume_spine 入口接线 | 评估中：企业侧 `persist_resume` 自建 audit、不经脊柱审计轨，建议保留域复算逻辑、仅补 `assert_hitl_evidence` 等价断言 | 不强制时限 |

---

## 五、结论

T75 三大支柱设计 **D1–D8 全部落地、验收全绿**，4 处差异均属设计明示预留/等价收敛，**无违反设计项**，我方认可。来文第五节 enterprise 三项对齐要求（evolution 毕业同步 / AUDIT_CANONICAL_SCHEMA 对账面 / 新符号机检）**本仓已逐项落实并经实机验证**，无遗留阻塞。

*enterprise 确认回执 · 2026-10-13 · 逐符号实测 + 源码锚点 + 判据复跑。*
