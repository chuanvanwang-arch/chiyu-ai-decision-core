"""HITL 证据与审批状态机断言 —— 「无 approve 不可生效」的基座结构保证（批次二）。

⛔ 设计来源（docs/plans/2026-10-13-foundation三大支柱详细设计.md D3.2/D3.4）：
  - 三仓一致 P0：「无 approve 不可生效」必须是**基座结构保证**而非文档纪律。
    本模块把保证做成**入口断言**：证据缺字段即抛错（不是跳过、不是提示）。
  - CRM 评审 T75 回执修订①：迁移闭集须支持 extra_transitions 域扩展
    （CRM 加签/转办/退回/撤回回流五态迁移边多于基座三边；压扁即违背合一初衷）。

⛔ 落点纪律：本模块在 `chiyu_kernel.approval`（sanctioned 面，消费方可合法 import）；
   常量全部来自 `chiyu_kernel.contract`（L0 单一事实源），本模块零自有契约常量。

⛔ advisory 观测面：`missing_hitl_evidence_fields` 纯判定器（返回缺失字段元组）
   供 advisory 档生产观测（would_deny 形态）；`assert_hitl_evidence` 为 enforced
   入口断言。两档共享同一判定器 ⇒ 结构保证 advisory.would_deny 与 enforced
   拦截一致（升格自 APS security.py:380 防漂移不变量）。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Iterable, Mapping, Tuple

from chiyu_kernel.contract.security import (
    APPROVAL_TRANSITIONS,
    HITL_EVIDENCE_FIELDS,
    HITL_RESUME_FIELD_ALIASES,
)

__all__ = [
    "HITLEvidenceError",
    "ApprovalTransitionError",
    "missing_hitl_evidence_fields",
    "assert_hitl_evidence",
    "assert_transition",
]


class HITLEvidenceError(KernelError):
    code = "CONTRACT_VIOLATION"
    """HITL 证据链缺失（enforced 入口断言失败：缺字段即拒，无豁免路径）。"""


class ApprovalTransitionError(KernelError):
    code = "CONTRACT_VIOLATION"
    """非法审批状态迁移（不在 APPROVAL_TRANSITIONS ∪ 显式 extra 闭包内）。"""


def _effective_fields(aliases: Iterable[str]) -> Tuple[str, ...]:
    """解析显式别名通道：只认 HITL_RESUME_FIELD_ALIASES 的键（禁裸字符串扩展）。

    ⛔ 修复（T81）：必填 = 未被别名的 HITL 字段 + 显式声明的别名键（消费方实际
    使用的字段名）。原实现只返回「未被别名覆盖的 HITL 字段」，当 aliases 覆盖
    全部 HITL 字段（如 RESUME_EVIDENCE_FIELDS）时 required 为空 ⇒
    ``assert_hitl_evidence(aliases=RESUME_EVIDENCE_FIELDS)`` 恒放行（no-op），
    违背「判据等价切换为 RESUME_EVIDENCE_FIELDS 语义」的文档约定
    （test_g4_resume_alias_channel_explicit_only 只验 happy-path 掩盖了该 bug）。
    """
    known = tuple(HITL_RESUME_FIELD_ALIASES.keys())
    unknown = [a for a in aliases if a not in known]
    if unknown:
        raise ValueError(
            f"未登记的 HITL 证据别名：{unknown!r}（只认 HITL_RESUME_FIELD_ALIASES 键集合，"
            "新别名须先在 L0 契约登记——禁裸字符串扩展）")
    # 别名替换为对应 HITL 字段（同语义异名 ⇒ 同一判据）
    extra = tuple(HITL_RESUME_FIELD_ALIASES[a] for a in aliases)
    # 必填 = 未被别名覆盖的 HITL 字段 + 别名键（消费方提供的字段名本身即必填）。
    return tuple(f for f in HITL_EVIDENCE_FIELDS if f not in extra) + tuple(aliases)


def missing_hitl_evidence_fields(
    payload: Mapping[str, object],
    *,
    aliases: Iterable[str] = (),
) -> Tuple[str, ...]:
    """纯判定器：返回 payload 缺失的 HITL 证据字段（advisory 档生产观测面）。

    aliases：显式声明的别名通道（值须 ∈ HITL_RESUME_FIELD_ALIASES 键集合）。
    例如 resume 场景传 ``aliases=("resume_principal", "resumed_at", "basis")``，
    判据即等价切换为 RESUME_EVIDENCE_FIELDS 语义（同链可追，字段名不分裂）。
    """
    required = _effective_fields(aliases)
    return tuple(f for f in required if not payload.get(f))


def assert_hitl_evidence(
    payload: Mapping[str, object],
    *,
    aliases: Iterable[str] = (),
) -> None:
    """enforced 入口断言：HITL 证据三件套缺任何一项 ⇒ 抛 HITLEvidenceError。

    ⛔ 「无 approve 不可生效」的结构保证点：任何「PENDING 决释放 / 进化生效 /
    高危险动作放行」入口必须先过本断言（缺字段即抛错，不是跳过、不是文档提示）。
    """
    missing = missing_hitl_evidence_fields(payload, aliases=aliases)
    if missing:
        raise HITLEvidenceError(
            f"HITL 证据链缺失（无 approve 不可生效，结构保证非约定）：缺 {missing!r}；"
            f"必填字段={HITL_EVIDENCE_FIELDS!r}，"
            f"别名通道={tuple(HITL_RESUME_FIELD_ALIASES.keys())!r}")


def assert_transition(
    from_state: str,
    to_state: str,
    extra: Tuple[Tuple[str, str], ...] = (),
) -> None:
    """审批状态迁移断言：(from, to) ∈ APPROVAL_TRANSITIONS ∪ extra 方放行。

    extra：消费方显式传入的域扩展迁移边（CRM 修订①：加签/转办/退回/撤回回流）。
    ⛔ 禁裸字符串纪律：extra 的每条边须为 (str, str) 二元组且两端非空，
       形状非法即抛错——域扩展通道显式化，基座闭集永不被静默改写。
    """
    if (from_state, to_state) in APPROVAL_TRANSITIONS:
        return
    for edge in extra:
        if not (isinstance(edge, tuple) and len(edge) == 2
                and all(isinstance(s, str) and s for s in edge)):
            raise ValueError(
                f"extra 迁移边形状非法：{edge!r}（须为非空 (str, str) 二元组，禁裸字符串）")
    if (from_state, to_state) in tuple(extra):
        return
    raise ApprovalTransitionError(
        f"非法审批状态迁移：{(from_state, to_state)!r} ∉ "
        f"APPROVAL_TRANSITIONS ∪ extra（基座闭集={APPROVAL_TRANSITIONS!r}；"
        f"域扩展须显式传 extra 二元组，禁静默改写闭集）")
