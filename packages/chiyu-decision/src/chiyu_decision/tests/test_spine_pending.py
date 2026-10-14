"""B3 PENDING 三态（方案 Z）—— 脊柱分支 + 红线优先不可覆盖 + 兼容性。

⛔ 三条反假绿探针（每条对应一处变异自证，删判据分支必转红）：
   1. pending 分支：PENDING ⇒ 不落正向边 + 审计 approval_pending + pending=True；
   2. 红线优先覆盖：闸裁成 PENDING/APPROVED 但红线命中 ⇒ 脊柱强制 REJECTED；
   3. pending 审计：删 audit 调用 ⇒ 审计断言转红。

兼容性判据：旧两态消费方读 `.approved` 不破；approval_gate=None 透传路径零影响。
"""
from __future__ import annotations

from typing import List, Tuple

import pytest

from chiyu_kernel.approval import (
    DecisionApprovalVerdict, DecisionVerdictState, RedlinePriorityGate,
)
from chiyu_kernel.contract.decision import EIGHT_ELEMENTS, RUBRIC_KEYS

from chiyu_decision.spine import SpineResult, run_spine


def _good() -> dict:
    return {k: 4.0 for k in RUBRIC_KEYS}


def _full_elements() -> dict:
    return {e: "x" for e in EIGHT_ELEMENTS}


class _PendingGate:
    """恒裁 PENDING 的闸（模拟消费方自定义"先转人工"策略）。"""

    def decide(self, **kw) -> DecisionApprovalVerdict:
        return DecisionApprovalVerdict(
            state=DecisionVerdictState.PENDING, reason="策略性转人工",
            requires_human=True)


class _AlwaysPendingEvenOnRedlineGate:
    """⛔ 反例闸：红线命中也裁 PENDING —— 脊柱必须覆盖它（红线优先不可被消费方闸绕过）。"""

    def decide(self, **kw) -> DecisionApprovalVerdict:
        return DecisionApprovalVerdict(
            state=DecisionVerdictState.PENDING, reason="闸失职", requires_human=True)


def _run(*, gate=None, elements=None, redline_items: Tuple[str, ...] = (),
         text: str = "普通事项",
         persist_sink: List[str] = None, audit_sink=None):
    return run_spine(
        context={"text": text, "decision_id": "dP"}, profile=None,
        rubric_scores=_good(), elements=elements if elements is not None else _full_elements(),
        redline_items=redline_items,
        approval_gate=gate, persister=(lambda r: persist_sink.append(r.decision_id) or True)
        if persist_sink is not None else None,
        audit_sink=audit_sink,
    )


def test_pending_does_not_persist_and_audits_approval_pending():
    """探针 1：PENDING ⇒ 不落正向边 + 审计 approval_pending + pending=True。"""
    persisted: List[str] = []
    audits: List[tuple] = []

    res = _run(gate=_PendingGate(), persist_sink=persisted,
               audit_sink=lambda t, p: audits.append((t, p)))

    assert res.pending is True, "PENDING 未置 pending=True ⇒ 三态分支缺失"
    assert res.approval_rejected is None, "待人工被错记为驳回（B3 要修的正是这个错值）"
    assert res.persisted is False
    assert persisted == [], "PENDING 仍调用了落库回调 ⇒ 未走 pending 分支"
    assert len(audits) == 1
    assert audits[0][0] == "approval_pending", f"审计事件错: {audits[0][0]}"
    assert audits[0][1]["requires_human"] is True
    assert audits[0][1]["pending"] is True


def test_default_gate_missing_criteria_is_pending_not_rejected():
    """RedlinePriorityGate：判据缺失 ⇒ PENDING（此前错记 rejected）。"""
    v = RedlinePriorityGate().decide(
        decision_id="d", confidence=0.9, redline_hit=False, redline_reasons=(),
        autonomous=True, rubric_missing=("k1",), elements_missing=(), threshold=0.79)
    assert v.state is DecisionVerdictState.PENDING
    assert v.approved is False          # 兼容：旧消费方读 .approved 不破
    assert v.pending is True
    assert v.requires_human is True


def test_redline_stays_rejected_and_cannot_be_downgraded():
    """探针 2（闸层）：红线命中 ⇒ REJECTED，判据再全也不豁免。"""
    v = RedlinePriorityGate().decide(
        decision_id="d", confidence=1.0, redline_hit=True, redline_reasons=("x",),
        autonomous=True, rubric_missing=(), elements_missing=(), threshold=0.79)
    assert v.state is DecisionVerdictState.REJECTED
    assert v.approved is False and v.pending is False


def test_spine_overrides_gate_that_pends_on_redline():
    """探针 2（脊柱层）：闸失职裁 PENDING 而红线命中 ⇒ 脊柱强制 REJECTED。"""
    audits: List[tuple] = []

    res = _run(gate=_AlwaysPendingEvenOnRedlineGate(),
               redline_items=("卫生健康",), text="卫生健康",
               audit_sink=lambda t, p: audits.append((t, p)))

    assert res.redline_hit is True
    assert res.pending is False, "红线被降级为 pending ⇒ 红线优先被绕过"
    assert res.approval_rejected is not None
    assert res.persisted is False
    assert audits and audits[0][0] == "approval_rejected"


def test_passthrough_none_path_unchanged():
    """approval_gate=None 透传路径零影响（既有消费方兼容判据）。"""
    persisted: List[str] = []
    res = _run(gate=None, redline_items=("卫生健康",), text="卫生健康",
               persist_sink=persisted)
    assert res.pending is False
    assert res.approval_rejected is None
    assert res.persisted is True and persisted == ["dP"]


def test_result_has_pending_field_default_false():
    """SpineResult 默认 pending=False（旧构造不破）。"""
    r = SpineResult(
        decision_id="d", stage_reached="S5_persist", confidence=0.9,
        rubric_missing=(), elements_missing=(), redline_hit=False,
        redline_reasons=(), autonomous=True)
    assert r.pending is False and r.approval_rejected is None
