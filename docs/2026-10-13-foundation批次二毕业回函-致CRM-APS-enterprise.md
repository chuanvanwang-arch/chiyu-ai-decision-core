# foundation 批次二（P1）毕业回函 —— 致 CRM / APS / enterprise

> **发出方**：foundation（AI 原生底座唯一事实源）
> **日期**：2026-10-13
> **上级链**：T74 方案（1231caf）→ T75 详细设计（ccebca0）→ T76 批次一毕业（6ed82ae）→ **本函（批次二落地）**
> **回执对象**：CRM《评审 T75 三大支柱详细设计》（e1840c7，9 项发现）
> **性质**：批次二（P1）契约级实现完成宣告 + D8 evolution 毕业排期 + CRM 修订采纳回执。**零三仓改造**；接线均为消费方新增适配层。

---

## 一、批次二落地清单（本函宣告毕业）

| 设计项 | 落点 | 符号 | 状态 |
|---|---|---|---|
| **D5 有效性度量** | `contract/metrics.py` | `SCORECARD_FIELDS` / `METRIC_SUMMARY_FIELDS` / `AGGREGATE_METRIC_KEYS` / `HONEST_DEGRADATION_INVARIANTS` / `ScoreCard` / `MetricSummary` | ✅ 毕业进 contract 面 |
| **D6 审计链合一** | `contract/audit.py` 扩展 | `AUDIT_CANONICAL_SCHEMA`（= 必填字段 + record_kind/rubric_scores/elements 三毕业键）/ `AUDIT_CHAIN_RULE` / `AUDIT_TOMBSTONE_FIELD` / `AUDIT_TOMBSTONE_REASON_FIELD` / `AUDIT_TOMBSTONE_INVARIANTS`（墓碑≠物理删/链连续/必带依据） | ✅ |
| **D7 IAM/RBAC 判定接口** | `contract/iam.py` | `Principal` / `SecurityDecision` / `RoleGate(Protocol)` + `PRINCIPAL_FIELDS` / `SECURITY_DECISION_FIELDS` | ✅ **收接口不收角色矩阵**（三仓共识） |
| **D3 HITL 断言实现** | `approval/hitl.py`（经 approval sanctioned 面 + contract/api 再导出） | `assert_hitl_evidence` / `missing_hitl_evidence_fields`（advisory 观测面）/ `assert_approval_transition`（出门面带前缀，见 §三.1）/ `HITLEvidenceError` / `ApprovalTransitionError` | ✅ 「无 approve 不可生效」= **结构保证** |
| **D8 evolution 毕业** | 未翻 CAPABILITIES | 见 §四排期 | ⏳ 按前置条件排期 |

诚实降级与防漂移均做成 **`__post_init__` 结构保证**（非文档纪律）：
- `MetricSummary`：无样本 ⇒ 强制 degraded 且禁携带汇总值（不伪造）；degraded ⇒ 必带 reason；非 degraded 禁携带 reason（状态互斥）。
- `SecurityDecision`：mode ∈ SECURITY_MODES 闭集（禁裸字符串）；enforced 下 `would_deny == (not allowed)`（D2 防漂移单对象投影）；off 恒放行（存量零破坏）。
- `Principal`：id 必填（匿名主体不可判定）。

---

## 二、CRM 评审 T75 修订采纳回执（2 项设计期修订全部落地）

### 2.1 修订①（迁移闭集域扩展）→ ✅ 采纳，机制同构 D1

CRM 指出：审批引擎含加签/转办/退回/撤回回流，五态迁移边多于基座三边，压扁即违背合一初衷。

**落地**：`assert_transition(from_state, to_state, extra=())` —— 与 `validate_outcome_kind(kind, extra)` 完全同构：基座收核态最小面（`APPROVAL_TRANSITIONS` 三边闭集），消费方**显式传 extra 迁移边**；`extra` 每条须为非空 `(str, str)` 二元组，形状非法即抛错（**禁裸字符串**）。契约面新增 `APPROVAL_TRANSITION_EXTENSION_RULE` 常量锚（`contract/security.py`）。

### 2.2 修订②（resume ↔ HITL 别名映射）→ ✅ 采纳，机检断言锚

CRM 指出：resume 三键与 HITL 三件套同语义异名，不钉死映射 ⇒ 双副本字段名漂移、审计链对拍恒 null。

**落地**：`contract/security.py` 新增 `HITL_RESUME_FIELD_ALIASES`（resume_principal→approver_id / resumed_at→approved_at / basis→evidence_ref，**值集合与 `HITL_EVIDENCE_FIELDS` 逐项相等，守卫机检**）。内核 `assert_hitl_evidence(payload, aliases=...)` / `missing_hitl_evidence_fields` 的别名通道**只认本映射键集合**，未登记别名即抛错（禁裸字符串扩展）。resume 场景显式传 `aliases=("resume_principal","resumed_at","basis")` ⇒ 判据等价切换，字段名不分裂。

### 2.3 CRM 四项接线点登记（确认收到，均不阻塞）

多结局并存语义（latest-wins 默认可覆盖）／`writeOutcome` 六字段适配（映射层）／advisory 观测面（影子基建复用 approval_shadow_log）／影子台账 resume 三键补列——均按 CRM 回执登记为接线适配项，随批次一/二符号接线时对齐。

---

## 三、命名纪律说明（实现期发现，已按仓规处置）

1. **`assert_transition` 撞名**：api 门面既有 spine 状态机同名 API。按 `DecisionApprovalGate` 前缀先例，批次二断言**出门面带前缀**：`assert_approval_transition`（import 别名实现，定义点 `approval/hitl.py` 保持 `assert_transition`，域内无歧义）。contract 与 api 两门面同名同对象。
2. 守卫组（`tests/test_batch2_contracts.py`，19 用例）G1 门面同对象断言直接抓出该撞名（identity 检查）——**守卫先行生效的实证**。

---

## 四、D8 evolution 毕业排期（按 RFE 流程，不翻 CAPABILITIES 于本批）

**前置条件核验**（T75 设计 D8 三项）：

| # | 前置 | 状态 |
|---|---|---|
| 1 | 能力②（HITL 原语）先毕业 —— 进化闸复用「无 approve 不可生效」 | ✅ 本批 `assert_hitl_evidence` 结构保证落地 |
| 2 | 能力①（OutcomeRecord/复盘）先毕业 —— 进化消费复盘输出 | ✅ T76 批次一落地 |
| 3 | readiness_report（`evolution/readiness.py`）+ 版本稳定承诺 + `api.__all__` 纳入 + manifest 重生成 + RFE 流程 | ⏳ **排批次三** |

**排期**：批次三（下一窗口）执行 D8 —— `version.py CAPABILITIES` 中 `("evolution","experimental") → ("evolution","stable")`，跑 readiness 评审 + 27 个 evolution 符号逐个过 `api.__all__` 通道 + 变异自证；**禁伪稳定包装**（CRM Q3.3 / enterprise Q3.3 一致要求）。生效动作强制经 `assert_hitl_evidence` + 落 D6 audit 痕。

---

## 五、验收（junitxml 权威）

- 守卫组 6 文件（批次二守卫 + 批次一守卫 + 门面覆盖/import_vs_all/contract_only/manifest）：**43 passed / 0 failed**（RC=0）。
- **变异自证 ×2**：①删 `MetricSummary` degraded_requires_reason 分支 → `test_g2_degraded_requires_reason` 红；②删 `assert_hitl_evidence` 缺失拦截 → G4 组 3 红；均还原后复绿（43 passed）。
- import 面门禁 lint：`OK: 跨分发 import 全部落在 sanctioned 面内`（RC=0）。
- 全量组合回归（kernel+decision+portal+examples+cli+tools）：后台运行，junitxml 权威计数见提交信息（**验收只认组合命令**）。

## 六、请三仓动作（可选、不强制时限）

1. **CRM**：接线点 4 项按 §2.3 对齐；`outcome.js`/`provenance.js` 与基座 `AUDIT_CANONICAL_SCHEMA`/墓碑语义对拍（P1 审计链合一的消费侧动作）。
2. **APS**：`security.py:380` 防漂移断言可改为消费 `contract` 的 `SecurityDecision` 结构保证（advisory/enforced 同判定器共享已由 `missing_hitl_evidence_fields`/`assert_hitl_evidence` 分层提供）；reflux resume 通道接 `RESUME_EVIDENCE_FIELDS` 别名机制。
3. **enterprise**：IAM 五档参考实现可对照 `Principal`/`RoleGate`/`SecurityDecision` 收敛判定面；`decision_audit_store` 可对拍 `AUDIT_CANONICAL_SCHEMA`。

---

*foundation 批次二毕业回函 · 2026-10-13 · 本仓增强零三仓改造；符号面以 contract/api `__all__` 为唯一事实源。*
