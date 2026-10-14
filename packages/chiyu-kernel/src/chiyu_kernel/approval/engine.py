"""审批聚合裁决核（Batch-1b-2 approval_engine）—— 纯函数，零 IO、零 DB。

收敛 CRM `approval/ruleResolver.js`（resolveTier 档位解析 + 审批链拓扑）与
`approval/stateMachine.js`（approve_all/approve_any 会签/或签操作）的**判定算法**；
业务规则（R1-R4）、档位阈值与币种、审批人角色清单留消费方注入
（APPROVAL_ENGINE_INVARIANTS 的机制投影，变异自证着力点）。

⛔ fail-closed 四则：
  ① 空审批链 ⇒ 抛错（无人审批=自动通过是经典假绿）；
  ② 未知规则/档位 ⇒ 抛错（禁静默回落默认链——CRM 的 tierChains.R1 回落是域行为）；
  ③ 阈值缺键 ⇒ 抛错（基座禁带 ¥ 默认值，CRM `th.t3 ?? 5_000_000` 回落属域值）；
  ④ 空裁决集 ⇒ 抛错（all 模式空真陷阱：vacuous "全过" 不可放行）。
"""
from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from chiyu_kernel.contract.security import (
    APPROVAL_AGGREGATION_MODES, APPROVAL_CORE_STATES, APPROVAL_TIERS,
    ApprovalEngineError,
)

__all__ = ["resolve_tier", "chain_for_tier", "aggregate"]


def resolve_tier(amount: object, *, thresholds: Mapping[str, object],
                 major_project: bool = False, force_t3: bool = True) -> str:
    """档位解析（CRM `resolveTier` 的域无关化；阈值全量注入，缺键即抛）。

    :param amount: 金额（数值口径由消费方定义；None/非数值按 0 处理，CRM
        ``Number(amount) || 0`` 同口径）。
    :param thresholds: ``{"t2": ..., "t3": ...}``——缺任一键 ⇒ ApprovalEngineError
        （禁基座带币种默认值）。
    :returns: ``"T3"``（重大项目且 force_t3，或 amount > t3）/ ``"T2"``（amount > t2）
        / ``"T1"``。
    """
    for key in ("t2", "t3"):
        if key not in thresholds:
            raise ApprovalEngineError(
                f"thresholds 缺 {key!r}（阈值须全量注入，基座不带币种默认值）")
    if major_project and force_t3:
        return "T3"
    try:
        amt = float(amount)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        amt = 0.0
    t3 = float(thresholds["t3"])
    t2 = float(thresholds["t2"])
    if amt > t3:
        return "T3"
    if amt > t2:
        return "T2"
    return "T1"


def chain_for_tier(chains: Mapping[str, Mapping[str, Sequence[str]]],
                   rule_id: str, tier: str) -> tuple:
    """按规则+档位取审批链（CRM ``cfg.tierChains[ruleId][tier]`` 的 fail-closed 化）。

    ⛔ 未知规则 / 未知档位 / 空链 ⇒ ApprovalEngineError（禁静默回落、禁空链放行）。
    """
    if rule_id not in chains:
        raise ApprovalEngineError(f"未知审批规则：{rule_id!r}（规则表由消费方注入）")
    if tier not in APPROVAL_TIERS:
        raise ApprovalEngineError(f"未知档位：{tier!r} ∉ APPROVAL_TIERS")
    by_tier = chains[rule_id]
    if tier not in by_tier:
        raise ApprovalEngineError(f"规则 {rule_id!r} 缺档位 {tier!r} 的审批链")
    chain = tuple(by_tier[tier])
    if not chain:
        raise ApprovalEngineError(
            f"规则 {rule_id!r} 档位 {tier!r} 审批链为空（空链=自动通过，fail-closed 拒绝）")
    return chain


def aggregate(mode: str, verdicts: Iterable[str]) -> str:
    """会签/或签/链签聚合（CRM approve_all/approve_any + tierChains 有序链的收敛核）。

    :param mode: ``"all"`` 全过才过 / ``"any"`` 一过即过 / ``"seq"`` 按序推进
        （首个非 pending 裁决即定；前面席位必须 approved 才轮到后面）。
    :param verdicts: 各席位裁决（按链序；值 ∈ APPROVAL_CORE_STATES 的
        approved/rejected/pending；canceled 席位由消费方折算，基座不猜）。
    :returns: 聚合裁决 ∈ {"approved", "rejected", "pending"}。
    """
    if mode not in APPROVAL_AGGREGATION_MODES:
        raise ApprovalEngineError(
            f"未知聚合模式：{mode!r} ∉ APPROVAL_AGGREGATION_MODES")
    seats = list(verdicts)
    if not seats:
        raise ApprovalEngineError("空裁决集（all 的空真陷阱：无人审批 ≠ 全体通过）")
    allowed = {"approved", "rejected", "pending"}
    for v in seats:
        if v not in allowed:
            raise ApprovalEngineError(
                f"非法席位裁决：{v!r}（聚合输入只认 APPROVAL_CORE_STATES 三值；"
                "canceled 由消费方折算）")
        if v not in APPROVAL_CORE_STATES:
            raise ApprovalEngineError(f"席位裁决 {v!r} 不在 APPROVAL_CORE_STATES")
    if mode == "all":
        if "rejected" in seats:
            return "rejected"
        return "approved" if all(v == "approved" for v in seats) else "pending"
    if mode == "any":
        if "approved" in seats:
            return "approved"
        return "rejected" if all(v == "rejected" for v in seats) else "pending"
    # seq：按序推进——首个非 pending 决定；approved 则看下一席
    for v in seats:
        if v == "pending":
            return "pending"
        if v == "rejected":
            return "rejected"
    return "approved"
