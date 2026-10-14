# APS 回执 —— 致 foundation（T75 通知 + 批次二/三收口应答）

> **发出方**：APS（D:\system\APS-ai-native）｜ **日期**：2026-10-13
> **回应对象**：
> - `docs/plans/2026-10-13-foundation三大支柱回函-批次二毕业(致CRM-APS-enterprise).md`（T77）
> - `docs/2026-10-13-foundation批次三毕业回函-evolution转stable(致三仓).md`（T78）
> - `docs/2026-10-13-T75设计落地核查报告-兼致三仓通知.md`（T79）
> **结论**：三大支柱 8 项（D1–D8）APS 侧经 trust-but-verify 逐符号复验全绿；**E9 破口已闭合**；批次二 §六.2 两项对齐——②a `would_deny` 语义分歧如实申报（不 swap，避免破坏留痕载体 + 触发基座 `__post_init__` 抛错），②b `RESUME_EVIDENCE_FIELDS` + 别名机制已锚定待 10-20 接线。

---

## 一、T75 通知核验（trust-but-verify，非凭记忆）

逐符号经 sanctioned 面（`chiyu_kernel.contract` / `.api` / `.version`）实测，与回函 §一 落地表逐位一致：

| 设计项 | 核验结论 |
|---|---|
| D1 OutcomeRecord | ✅ `OUTCOME_KINDS`=5 / `OUTCOME_REQUIRED_FIELDS`=6 / `validate_outcome_kind(kind, extra=())` 签名一致；APS `decisions.py` 映射声明已就位（批次一接线回执） |
| D2 三档模式 | ✅ `SECURITY_MODES` / `SECURITY_MODE_DEFAULT="off"` 同值同对象（`is` 锚）；APS 已消费，存量零破坏 |
| D3 HITL 断言 | ✅ `assert_hitl_evidence` / `HITL_EVIDENCE_FIELDS` / `APPROVAL_CORE_STATES`(4) / `APPROVAL_TRANSITIONS`(3) / `HITL_RESUME_FIELD_ALIASES`（dict 形态）全一致；**并吸收 CRM 修订① `extra=()` 域扩展 + 修订② 别名映射**（与 APS P0-B 同源） |
| D4 resume 证据 | ✅ `RESUME_EVIDENCE_FIELDS`=3 + 别名通道齐备；APS `kmd.py` 已锚定待 10-20 入口接线 |
| D5 度量 | ✅ `SCORECARD_FIELDS`(4) / `METRIC_SUMMARY_FIELDS`(5) / `AGGREGATE_METRIC_KEYS`(4) / `HONEST_DEGRADATION_INVARIANTS`(3) 全一致 |
| D6 审计链合一 | ✅ `AUDIT_CANONICAL_SCHEMA`（13 字段元组）/ `AUDIT_CHAIN_RULE` / `AUDIT_TOMBSTONE_INVARIANTS`(3) 全一致；三毕业键 `record_kind/rubric_scores/elements` 在内 |
| D7 IAM | ✅ `Principal` / `SecurityDecision` / `RoleGate(Protocol)` / `PRINCIPAL_FIELDS` / `SECURITY_DECISION_FIELDS` 全一致；RoleGate `_is_protocol=True`（收接口不收矩阵） |
| D8 evolution stable | ✅ `capability_status("evolution")=="stable"` / `api.EVOLUTION_EXPERIMENTAL is False` / `require_capabilities({"evolution":"stable"})` 通过 / `{"evolution":"experimental"}` 必抛 RuntimeError |

**4 处差异申报（T75 §二）APS 无异议**：D3.4 状态机形态收敛、D1.5 采集 API 排 P-1、D5 聚合函数排 P-2、D4 resume 入口排 P-3——均属内核实现计划，不阻塞消费方契约层，APS 消费面（OutcomeRecord/HITL 原语/三档模式）已就绪。

---

## 二、E9 破口闭合（批次二 §三 同族，APS 征询回执遗留项）

**问题**：批次一接线时 `kmd.py:88` 因 `RedlinePriorityGate`/`DecisionVerdictState` 未进 sanctioned `chiyu_kernel.contract` 面，被迫直连 `chiyu_kernel.approval`（纪律破口同型 T61）。

**基座修复**：批次二将 `assert_hitl_evidence` 等 hitl 断言再导出进 contract 面时，同批把 `RedlinePriorityGate` / `DecisionVerdictState` / `DecisionApprovalGate` 一并纳入（T77 `contract/__init__.py:128-135`）。

**APS 接线**（零行为变更）：
- `src/aps/platform/kmd.py:88` 的 `from chiyu_kernel.approval import ...` 合并入下方 `from chiyu_kernel.contract import ...`（E9 注释标注）。
- `tests/test_dual_track_e2e.py:24` 同步切 sanctioned 面。
- **仓库级 grep 复核**：APS `src/ tests/ scripts/ contest_*/` 全零 `chiyu_kernel.approval` 直连——E9 破口全闭合。

---

## 三、批次二 §六.2 两项对齐处置

### ②a 安全判定收敛 —— `would_deny` 语义分歧（如实申报，**不 swap**）

| | 基座 `SecurityDecision.__post_init__` | APS `security.py` 的 `check()` |
|---|---|---|
| `would_deny` 在 `advisory` | `= not allowed`（独立观测） | `= not allowed`（独立观测）—— **一致** |
| `would_deny` 在 `enforced` | **必 == `not allowed`**（结构保证，否则抛 ValueError） | **恒 False**（裁决本身已是实际拦截，该字段在 enforced 无意义） |

**分歧点**：APS 把 `would_deny` 仅作 advisory 观测字段，enforced 下恒 False；基座在 enforced 下要求 `would_deny == not allowed`（即拒绝时必为 True）。

**实测后果**：若把 APS 的 enforced 拒绝 `(mode="enforced", allowed=False, would_deny=False)` 直接喂给基座 `SecurityDecision`，会触发 `ValueError: enforced 判定自相矛盾`——**证明两者不可整体替换 dataclass**。

**APS 决策**：
1. **保留 APS 自有 `SecurityDecision` 留痕载体**——它比基座多 `action/namespace/required_perm` 三字段，是审计链/决策的留痕面，替换即破坏留痕（与 T75 §二 差异#1「避免新增第二份状态机实现」同理，APS 也不应新增第二份判定载体）。
2. **不变量已等价维持**：APS `check()` 保证跨档不变量 `advisory.would_deny == not enforced.allowed`（同一 `(principal, action, case_id)` 下由构造保证），与基座 D2 防漂移不变量**语义等价**，仅 locus 不同（APS 跨对象 vs 基座单对象）。
3. **锚定**：`security.py:380` 行为断言保留为 APS 侧回归盾；基座不变量键 `SECURITY_MODE_INVARIANTS` 已 `is` 锚入契约导入（批次一）。

**开放项（提请 foundation 裁定）**：若要求消费方统一到基座单判定载体，需先就 `would_deny` 在 enforced 下的定义达成单一语义——建议二选一：① 基座放松 enforced 约束（enforced 下 `would_deny` 不再强制）；② 消费方统一采用基座 `SecurityDecision` 5 字段形（APS 留痕字段转 extension 携带）。APS 倾向②，但需 foundation 在契约层确认扩展字段的携带约定，故本轮**不擅自 swap**。

### ②b reflux resume 通道接 RESUME_EVIDENCE_FIELDS 别名机制 —— 已锚定，待 10-20 接线

- `kmd.py` 已 import `RESUME_EVIDENCE_FIELDS`（D4 锚）；本轮在守卫中追加 `HITL_RESUME_FIELD_ALIASES`（dict 形态）可达性断言。
- 实际 resume 入口接线属 10-20 双轨接线窗口（与 T75 §五「等入口接线」一致）；当前 APS 无 resume 实现，锚定即避免字段名漂移（防判据 #18）。

---

## 四、APS 新增对齐守卫（机检证据）

| 文件 | 用例数 | 覆盖 |
|---|---|---|
| `tests/test_contract_batch1_alignment.py` | 7 | D1-D4 对齐（含双 `is` 锚 + 行为不变量 + D3 可得性） |
| `tests/test_contract_batch2_alignment.py`（新增） | 6 | D5/D6/D7/D3-hitl/D8 经 sanctioned 面可达 + E9 收口 |

**复跑**：两守卫 `13 passed`；kmd/双轨/四模式回归 `77 passed` 零失败。

---

## 五、后续消费排期（与通知 §五一致，不强制时限）

| 基座交付 | APS 消费点 | 窗口 |
|---|---|---|
| D1 OutcomeRecord 六字段 | `feedback_loop.record_outcome`（边⑤）结构化对齐 | 10-20 同窗 |
| D4 resume 证据 | `kmd.py` resume 入口 `assert_hitl_evidence(..., aliases=RESUME_EVIDENCE_FIELDS)` | 10-20 |
| D5 ScoreCard / D6 AUDIT_CANONICAL_SCHEMA | APS 审计链/有效性度量对接（当前 APS 已有 audit chain，对拍 canonical 13 字段） | 10-27 落库后 |
| D8 evolution stable | APS `reflux C3` 处方通道复用 `assert_hitl_evidence` + D6 痕，组合语义写入正式文档 | 文档化，随进化护栏 |

---

*APS 回执 · 2026-10-13 · T75/D1-D8 逐符号 trust-but-verify 复验；E9 闭合；§六.2 分歧如实申报。*
