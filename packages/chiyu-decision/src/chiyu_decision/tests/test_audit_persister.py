"""RFE audit-first 落库模式守卫（2026-10-12 裁定接纳，APS 诉求收编）。

⛔ 反假绿判据（每条对应破坏性构造，判据失效必转红）：
   1. REJECTED/PENDING 分支在 audit_sink 之外调用 audit_persister（扩展载荷：
      record_kind=AUDIT_RECORD_KIND + context_snapshot + rubric_scores + elements）；
   2. APPROVED 分支绝不调用 audit_persister（审计轨 ≠ 业务轨）；
   3. audit_sink 收到的仍是基础 payload（不含扩展键）—— 既有消费方零破坏；
   4. 缺省 None ⇒ 行为逐字不变；
   5. audit_persister 抛错 ⇒ 原样上抛（fail-closed：审计优先落库保证禁止静默丢失）；
   6. resume_spine 不收 audit_persister（审计轨不影响 resume 三铁律）。
"""
from __future__ import annotations

import inspect

import pytest

from chiyu_kernel.approval import DecisionApprovalVerdict, DecisionVerdictState
from chiyu_kernel.contract.decision import (
    AUDIT_EVENT_APPROVAL_PENDING, AUDIT_EVENT_APPROVAL_REJECTED,
    AUDIT_RECORD_KIND, EIGHT_ELEMENTS, RUBRIC_KEYS,
)

from chiyu_decision.spine import SpineResult, resume_spine, run_spine

_BASE_KEYS_PENDING = {"decision_id", "approved", "pending", "reason",
                      "requires_human", "redline_hit", "sensitive_hits", "confidence"}
_BASE_KEYS_REJECTED = {"decision_id", "approved", "reason",
                       "requires_human", "redline_hit", "sensitive_hits", "confidence"}
_EXPANSION_KEYS = {"record_kind", "context_snapshot", "rubric_scores", "elements"}


def _full_scores() -> dict:
    return {k: 4.0 for k in RUBRIC_KEYS}


def _full_elements() -> dict:
    return {e: "x" for e in EIGHT_ELEMENTS}


class _PendingGate:
    def decide(self, **kw) -> DecisionApprovalVerdict:
        return DecisionApprovalVerdict(
            state=DecisionVerdictState.PENDING, reason="策略性转人工",
            requires_human=True)


class _RejectGate:
    def decide(self, **kw) -> DecisionApprovalVerdict:
        return DecisionApprovalVerdict(
            state=DecisionVerdictState.REJECTED, reason="闸拒：越权操作",
            requires_human=True)


def _run_rejected(sink, ap) -> SpineResult:
    """闸裁 REJECTED 路径（显式注入闸；透传路径红线只屏蔽自主放行不进 REJECTED 分支）。"""
    return run_spine(
        context={"text": "越权导出客户数据", "decision_id": "dA"}, profile=None,
        rubric_scores=_full_scores(), elements=_full_elements(),
        approval_gate=_RejectGate(), audit_sink=sink, audit_persister=ap)


class _PendingGate:
    def decide(self, **kw) -> DecisionApprovalVerdict:
        return DecisionApprovalVerdict(
            state=DecisionVerdictState.PENDING, reason="策略性转人工",
            requires_human=True)


def test_rejected_path_calls_audit_persister_with_expanded_payload():
    """判据 1+3：REJECTED 分支双轨各就各位 —— audit_sink 基础载荷 / persister 扩展载荷。"""
    sink_calls: list = []
    ap_calls: list = []
    res = _run_rejected(lambda t, p: sink_calls.append((t, p)),
                        lambda r, t, p: ap_calls.append((r, t, p)))

    assert res.approval_rejected and res.persisted is False
    assert len(sink_calls) == 1 and sink_calls[0][0] == AUDIT_EVENT_APPROVAL_REJECTED
    # 既有消费方零破坏：audit_sink 载荷不含扩展键（形状与 RFE 前逐键一致）
    assert set(sink_calls[0][1]) == _BASE_KEYS_REJECTED
    # 审计轨：扩展载荷 + result 在场（消费方可据 SpineResult 补齐自有字段）
    assert len(ap_calls) == 1
    r_arg, event, payload = ap_calls[0]
    assert r_arg is res
    assert event == AUDIT_EVENT_APPROVAL_REJECTED == "approval_rejected"
    assert _BASE_KEYS_REJECTED <= set(payload)
    assert _EXPANSION_KEYS <= set(payload)
    assert payload["record_kind"] == AUDIT_RECORD_KIND == "audit"
    assert payload["context_snapshot"] == {"text": "越权导出客户数据", "decision_id": "dA"}
    assert payload["rubric_scores"] == _full_scores()
    assert payload["elements"] == _full_elements()


def test_pending_path_calls_audit_persister():
    """判据 1：PENDING 分支同样双轨（approval_pending + 扩展载荷）。"""
    ap_calls: list = []
    res = run_spine(
        context={"text": "普通事项", "decision_id": "dP"}, profile=None,
        rubric_scores=_full_scores(), elements=_full_elements(),
        approval_gate=_PendingGate(),
        audit_persister=lambda r, t, p: ap_calls.append((r, t, p)))

    assert res.pending is True and res.persisted is False
    assert len(ap_calls) == 1
    r_arg, event, payload = ap_calls[0]
    assert r_arg is res
    assert event == AUDIT_EVENT_APPROVAL_PENDING == "approval_pending"
    assert payload["record_kind"] == AUDIT_RECORD_KIND
    assert payload["context_snapshot"]["decision_id"] == "dP"
    assert _BASE_KEYS_PENDING <= set(payload) and _EXPANSION_KEYS <= set(payload)


def test_approved_path_never_calls_audit_persister():
    """判据 2：APPROVED 走 persister 业务轨，审计轨绝不触发。"""
    ap_calls: list = []
    persisted: list = []
    res = run_spine(
        context={"text": "普通事项", "decision_id": "dOK"}, profile=None,
        rubric_scores=_full_scores(), elements=_full_elements(),
        persister=lambda r: persisted.append(r.decision_id) or True,
        audit_persister=ap_calls.append)

    assert res.persisted is True and res.pending is False
    assert persisted == ["dOK"]
    assert ap_calls == [], "⛔ APPROVED 分支触发审计轨 = 审计轨/业务轨混淆"


def test_default_none_keeps_existing_behavior():
    """判据 4+3：缺省 None ⇒ audit_sink 收到的仍是基础载荷（逐键一致）。"""
    sink_calls: list = []
    res = _run_rejected(lambda t, p: sink_calls.append((t, p)), None)
    assert res.approval_rejected
    assert len(sink_calls) == 1
    assert set(sink_calls[0][1]) == _BASE_KEYS_REJECTED
    assert "record_kind" not in sink_calls[0][1]


def test_audit_persister_failure_fails_closed():
    """判据 5：审计轨抛错 ⇒ 原样上抛（审计优先落库保证禁止静默丢失）。"""
    def _boom(result, event, payload):
        raise RuntimeError("审计轨落库失败")

    with pytest.raises(RuntimeError, match="审计轨落库失败"):
        _run_rejected(None, _boom)


def test_resume_has_no_audit_persister_seam():
    """判据 6：resume_spine 不引入审计轨接缝 —— resume 三铁律不受 RFE 影响。"""
    params = inspect.signature(resume_spine).parameters
    assert "audit_persister" not in params
