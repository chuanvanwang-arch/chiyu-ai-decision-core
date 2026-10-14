"""企业安全契约 —— 三档安全模式 + HITL 证据 + resume 证据（L0 单一事实源）。

⛔ L0 纪律：零第三方依赖、零 IO、零领域字面量。

设计来源（三仓回执一致 P0，详见 docs/plans/2026-10-13-foundation三大支柱详细设计.md D2-D4）：
  - D2 三档模式（off/advisory/enforced）：APS security.py 实证形态升格基座默认范式。
    渐进收紧是企业上线刚需：默认 off 零破坏 → advisory 生产观测（would_deny 命中率）
    → enforced 收口。
  - D3 HITL 证据三件套：CRM Q3.4「无 approve 不可生效做成基座不变式而非文档纪律」/
    APS Q3.3「生效入口只认带 HITL 证据链的 payload」。
  - D4 resume 证据契约：APS P0-B 实名缺口 —— AUDIT_EVENT_APPROVAL_RESUMED 事件
    存在但 resume 的 principal/依据 payload 无契约锚。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Mapping, Tuple

# ══ D2 三档安全模式 ═══════════════════════════════════════════════════
SECURITY_MODES: Tuple[str, ...] = ("off", "advisory", "enforced")

# ⛔ 缺省模式：off（对存量系统零破坏；企业显式收紧才升档）
SECURITY_MODE_DEFAULT = "off"

# 不变量键（升格自 APS security.py:380 防漂移断言）：
#   advisory.would_deny == (not enforced.allowed)
# 结构保证两档判定一致性，杜绝「advisory 观测绿、enforced 才现红」的回归。
# 实现期由内核判定执行器断言（变异自证：删断言→构造不一致判定→须红）。
SECURITY_MODE_INVARIANTS: Tuple[str, ...] = (
    "advisory_would_deny_eq_not_enforced_allowed",
)

# ══ D3 HITL 证据三件套 ════════════════════════════════════════════════
# 任何「PENDING 决策放行 / 进化生效 / 高危险动作放行」入口只认带 HITL 证据链
# 的 payload：三件套缺任何一项 ⇒ 入口抛错（结构保证，非文档纪律）。
# 实现期由内核 assert_hitl_evidence(payload) 强制（批次二实现计划落地）。
HITL_EVIDENCE_FIELDS: Tuple[str, ...] = (
    "approver_id",    # 谁批准（追责到个人；禁止匿名/系统代签）
    "approved_at",    # 何时批准（ISO-8601）
    "evidence_ref",   # 基于什么（审批单 id / 证据引用，回放依据）
)

# ── 审批核态（闭集；域可扩展但不得删除这四态）────────────────────────
# 收敛三仓既有状态机（CRM 五态 / enterprise INSTANCE_STATES / 基座 B3 三态）
# 为基座核态；域扩展态由消费方追加，核态语义不动。
APPROVAL_CORE_STATES: Tuple[str, ...] = (
    "pending", "approved", "rejected", "canceled",
)

# 合法迁移闭集（不可重排、不可旁路）：非法迁移由内核 assert_transition 拒绝。
APPROVAL_TRANSITIONS: Tuple[Tuple[str, str], ...] = (
    ("pending", "approved"),
    ("pending", "rejected"),
    ("pending", "canceled"),
)
# 【D1 裁定登记·2026-10-14，CRM 为源仓】三条口径：
# ① intra-pending 边（如 CRM PENDING_SUBMIT→APPROVING 的 submit）属 pending 核态内
#    子相位推进，不入基座三边闭集——消费方经 extra 显式声明（APPROVAL_TRANSITION_EXTENSION_RULE）；
# ② 命名大小写：CRM 大写（PENDING_SUBMIT）/ 基座小写（pending）——两侧都不回改
#    （禁为对齐改存量），对拍由消费方 parity 守卫带大小写映射表承载；
# ③ 任务级保态操作（加签/退回/转办等保态不改态）**不是迁移边**，不进 transitions
#    闭集——它们是操作面语义，与状态迁移面分离。

# ══ D4 resume 证据契约 ════════════════════════════════════════════════
# PENDING 批准后续跑（G3 resume_spine）的证据 payload 契约锚（APS P0-B）。
# 与 HITL_EVIDENCE_FIELDS 同语义族但字段名专门化：basis 承载「基于什么」。
# 不变量：resume_spine 入口校验三件套齐备，缺则拒续跑并落
# AUDIT_EVENT_APPROVAL_RESUMED 审计失败态 —— PENDING 放行与决策审计同链可追。
RESUME_EVIDENCE_FIELDS: Tuple[str, ...] = (
    "resume_principal",  # 谁批准（追责到个人）
    "resumed_at",        # 何时批准（ISO-8601）
    "basis",             # 基于什么（决策 id / 证据 ref，回放依据）
)

# ── CRM 评审修订②（T75 回执）：resume 三键 ↔ HITL 三件套别名映射 ─────────
# 同一证据语义两套字段名（同语义异名），不钉死映射 ⇒ 双副本字段名漂移、
# 审计链对拍恒 null。此映射是**机检断言锚**：内核 assert_hitl_evidence 的
# aliases 参数只认本映射的键集合（禁裸字符串扩展）。
HITL_RESUME_FIELD_ALIASES: Mapping[str, str] = {
    # resume 字段 → HITL 同语义字段
    "resume_principal": "approver_id",
    "resumed_at": "approved_at",
    "basis": "evidence_ref",
}

# ── CRM 评审修订①（T75 回执）：迁移闭集支持域扩展（extra_transitions）─────
# CRM 审批引擎含加签/转办/退回/撤回回流，五态迁移边多于基座三边；压扁即违背
# 「合一」初衷。机制（与 validate_outcome_kind(kind, extra) 同构）：
# 基座收核态最小面 + 消费方显式传 extra 迁移边（内核 assert_transition 的
# extra 参数），禁裸字符串、禁基座闭集被静默改写。
APPROVAL_TRANSITION_EXTENSION_RULE = (
    "assert_transition(from_state, to_state, extra=()) — "
    "(from,to) ∈ APPROVAL_TRANSITIONS ∪ extra 方放行；extra 须显式传二元组闭包"
)

# ══ Batch-1b-2 approval_engine（聚合裁决核；对拍 CRM approve_all/approve_any/SEQ 链）══
# 聚合模式闭集：all=会签（全过才过）/ any=或签（一过即过）/ seq=链签（按序推进，
# 首个非 pending 裁决即定）。CRM OPERATIONS_BY_STATE 的 approve_all/approve_any
# 与 tierChains 有序链在基座收敛为同一聚合核。
APPROVAL_AGGREGATION_MODES: Tuple[str, ...] = ("all", "any", "seq")

# 审批档位闭集（tier 名通用；**阈值与币种口径留消费方**——基座禁带 ¥ 金额默认值，
# CRM resolveTier 的 5_000_000/1_000_000 回落值属域值）。
APPROVAL_TIERS: Tuple[str, ...] = ("T1", "T2", "T3")

APPROVAL_ENGINE_INVARIANTS: Tuple[str, ...] = (
    "empty_approver_chain_fails_closed",  # 空审批链 ⇒ 拒（无人审批=自动通过是假绿）
    "unknown_rule_or_tier_raises",        # 未知规则/档位 ⇒ 抛错（禁静默回落默认链）
    "thresholds_fully_injected",          # 档位阈值全量注入（缺键即抛，禁基座带币种默认值）
    "aggregation_over_core_states",       # 聚合输入输出只认 APPROVAL_CORE_STATES 裁决词汇
    "empty_verdict_set_fails_closed",     # 空裁决集 ⇒ 抛错（all 的空真陷阱禁入）
)


class ApprovalEngineError(KernelError):
    code = "CONTRACT_VIOLATION"
    """审批引擎配置/输入非法（未知规则、空审批链、缺阈值、非法聚合输入）。"""


__all__ = [
    # D2
    "SECURITY_MODES", "SECURITY_MODE_DEFAULT", "SECURITY_MODE_INVARIANTS",
    # D3
    "HITL_EVIDENCE_FIELDS", "APPROVAL_CORE_STATES", "APPROVAL_TRANSITIONS",
    # D4
    "RESUME_EVIDENCE_FIELDS",
    # CRM 评审修订（T75 回执 2 项设计期修订）
    "HITL_RESUME_FIELD_ALIASES", "APPROVAL_TRANSITION_EXTENSION_RULE",
    # Batch-1b-2 approval_engine
    "APPROVAL_AGGREGATION_MODES", "APPROVAL_TIERS",
    "APPROVAL_ENGINE_INVARIANTS", "ApprovalEngineError",
]
