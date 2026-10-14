# enterprise 核验确认 —— foundation 三大支柱批次一毕业

> **发出方**：chiyu-enterprise（消费仓）
> **日期**：2026-10-13
> **复函对象**：`docs/plans/2026-10-13-foundation三大支柱回函-批次一毕业(致三仓).md`
> **性质**：消费方核验回执（trust-but-verify 实测）＋ 接线对齐意见（批次二输入）。

---

## 一、核验结论：批次一交付属实 ✅

enterprise 侧独立实测（本仓 venv 直连 foundation 源码，非转抄回函）：

| 检查项 | 结果 |
|---|---|
| `contract/outcome.py` + `contract/security.py` 存在 | ✅ 两文件在位 |
| 11 新符号 contract `__all__` 登记 | ✅ `contract/__init__.py:89-97`（import）+ `:144-149`（`__all__`） |
| api 门面再导出 8 符号可达 | ✅ `OUTCOME_KINDS/OUTCOME_REQUIRED_FIELDS/SECURITY_MODES/APPROVAL_CORE_STATES/APPROVAL_TRANSITIONS/HITL_EVIDENCE_FIELDS/RESUME_EVIDENCE_FIELDS/validate_outcome_kind` 全 `True`（X2/E9 模式沿用——enterprise 征询回执的 api 再导出建议已被采纳为范式） |
| 判定器行为冒烟 | ✅ 5 断言全过：闭集内 True / 域值未经 `extra` 判 False / `extra=("won","lost","paid")` 扩展 True / 大小写变体 `Succeeded` 判 False（拼错不静默） |
| 实测符号值 | `OUTCOME_REQUIRED_FIELDS=6 字段`；`APPROVAL_TRANSITIONS=3 条闭集（pending→approved/rejected/canceled）`；`SECURITY_MODE_DEFAULT="off"`——与回函口径逐字一致 |

诚实申报：840 passed 全量回归为 foundation 自验面，enterprise 未复跑（不属本仓义务）；本仓核验覆盖契约存在性、可达性、判定器行为三点。

---

## 二、接线对齐实态与意见（批次二输入）

### 2.1 D1 结局采集（OUTCOME_REQUIRED_FIELDS）—— 缺口再实锤，接线面已明确

`host/retro_backend.py` / `host/decision_memory_store.py` grep `outcome|won|lost` **零命中**——enterprise 征询回执 Q1.1 申报的「结局采集缺口」经基座符号面二次实锤。接线候选：新增结局采集动作（消费 `OUTCOME_REQUIRED_FIELDS` 6 字段，`decision_id` 强关联 spine 决策）→ `retro_backend` 证据面反查 `collect_strictness_evidence` 增结局信号源。属批次二可选工作，排期随征询回执 P0 项 1。

### 2.2 D3 核态对齐（APPROVAL_CORE_STATES）—— ⛔ 需修正「域态扩展」表述，建议映射层方案

回函口径「核态不动、域态扩展」对本仓**不完全成立**：本仓 `approval/state_machine.py:13` 的 `INSTANCE_STATES` 是**大写五态** `PENDING_SUBMIT / APPROVING / APPROVED / REJECTED / CANCELED`，与基座核态小写四态**不同名不同构**——不是核态超集，是平行词汇。两点关键差异：
1. `PENDING_SUBMIT`（待提交）≠ `pending`（待审批）——本仓区分「未提交」与「审批中」；
2. `APPROVING` 态挂 8 个会签操作（`approve_all/approve_any/reject/cancel/add_sign/return/transfer/withdraw`，`:17-26`）——会签工作流语义，基座核态无对应位。

**建议方案：核态映射纯函数**（不做替换式收敛）：`state → core_state`（PENDING_SUBMIT/APPROVING→pending，APPROVED→approved，REJECTED→rejected，CANCELED→canceled），域五态原样保留（会签语义不可丢），映射函数断言进判据。若强行让本仓五态改词汇，会破坏存量审批实例与会签流程——请 foundation 批次二将「映射层」纳入 IAM-RBAC/审计合一设计（D6/D7）的兼容约定。

### 2.3 D4 resume 证据（RESUME_EVIDENCE_FIELDS）—— 对齐属批次二

本仓 resume 路径自建审计记录（`decision/orchestrator.py` `persist_resume`，不经脊柱审计轨，本轮 E5 已实证其独立性）。接 `RESUME_EVIDENCE_FIELDS` 三件套属批次二接线，无阻碍。

### 2.4 D2 三档安全模式（SECURITY_MODES）—— 暂无消费点，off 默认零破坏成立

本仓安全层为 enforced 语义直落（写闸 G0-G1.6 无 off/advisory 中间档），暂不接三档；`SECURITY_MODE_DEFAULT="off"` 对存量零破坏的口径实测成立（本仓零改动即合规）。

---

## 三、批次二期待项确认

与 enterprise 征询回执 P0/P1 汇总对齐：有效性度量 canonical schema 毕业／审计链合一（D6，本仓三段 `_AUDIT_PHASES` 形态贡献）／IAM-RBAC 判定接口（Principal/SecurityDecision/RoleGate，本仓五档+effective_roles 参考实现可上收）／evolution 毕业按 RFE。本仓保持「先问清、后改造」节奏，接线窗口随批次二设计稿定。

*enterprise 核验回执 · 2026-10-13 · 锚点实测于两仓源码；副本留本仓 `docs/`。*
