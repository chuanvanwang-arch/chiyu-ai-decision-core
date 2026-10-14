"""G3 PENDING 续跑入口 `resume_spine` + G4 审计事件契约常量。

⛔ 反假绿判据（每条对应破坏性构造，判据失效必转红）：
   1. 冻结裁定：resume 前后裁定字段逐项相等 —— 改动 = "批的是甲、落的是乙"；
   2. REJECTED 不得复活：非 PENDING 结果 resume 必抛；
   3. 幂等：已 persisted 的结果二次 resume 不重复落库、不重复留痕；
   4. G4 契约常量：spine 源码禁裸字符串审计事件（AST 层断言，I1 升级：
      任意引号形态 / f-string / 拼接拆分变体均拦；回归守卫，防倒退回硬编码）。
"""
from __future__ import annotations

import ast
import inspect
from typing import List

import pytest

from chiyu_kernel.approval import (
    DecisionApprovalVerdict, DecisionVerdictState, HITLEvidenceError,
)
from chiyu_kernel.contract.decision import (
    AUDIT_APPROVAL_EVENTS, AUDIT_EVENT_APPROVAL_PENDING,
    AUDIT_EVENT_APPROVAL_REJECTED, AUDIT_EVENT_APPROVAL_RESUMED,
    EIGHT_ELEMENTS, RUBRIC_KEYS,
)
from chiyu_kernel.contract.security import RESUME_EVIDENCE_FIELDS

import chiyu_decision.api as decision_api
from chiyu_decision import spine as spine_mod
from chiyu_decision.errors import DecisionError
from chiyu_decision.spine import SpineResult, resume_spine, run_spine


class _PendingGate:
    def decide(self, **kw) -> DecisionApprovalVerdict:
        return DecisionApprovalVerdict(
            state=DecisionVerdictState.PENDING, reason="策略性转人工",
            requires_human=True)


def _run_pending(decision_id: str = "dR") -> SpineResult:
    return run_spine(
        context={"text": "普通事项", "decision_id": decision_id}, profile=None,
        rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
        elements={e: "x" for e in EIGHT_ELEMENTS},
        approval_gate=_PendingGate(),
    )


_VERDICT_FIELDS = ("decision_id", "stage_reached", "confidence",
                   "rubric_missing", "elements_missing", "redline_hit",
                   "redline_reasons", "autonomous", "approval_rejected", "pending")

# P-3（D4）：resume 入口 HITL 证据三件套（结构保证，无 approve 不可生效）
_RESUME_EVIDENCE: dict = {
    "resume_principal": "approver-u1",
    "resumed_at": "2026-10-13T10:00:00",
    "basis": "approval-77",
}


def test_resume_persists_frozen_verdict_and_audits_resumed():
    """续跑主路径：只补落库，裁定冻结，审计留 approval_resumed（含 approval_ref）。"""
    res = _run_pending()
    assert res.pending is True and res.persisted is False
    before = {f: getattr(res, f) for f in _VERDICT_FIELDS}

    persisted: List[str] = []
    audits: List[tuple] = []
    out = resume_spine(
        res, persister=lambda r: persisted.append(r.decision_id) or True,
        audit_sink=lambda t, p: audits.append((t, p)),
        approval_ref="approval-77", resume_evidence=dict(_RESUME_EVIDENCE))

    assert out is res, "resume 应原地补完同一结果对象（消费方回派时手持的就是它）"
    assert res.persisted is True
    assert persisted == ["dR"]
    after = {f: getattr(res, f) for f in _VERDICT_FIELDS}
    assert after == before, "⛔ 裁定字段被改动 ⇒『批的是甲、落的是乙』"
    assert len(audits) == 1
    assert audits[0][0] == AUDIT_EVENT_APPROVAL_RESUMED == "approval_resumed"
    assert audits[0][1]["approval_ref"] == "approval-77"
    assert audits[0][1]["persisted"] is True
    # J8（2026-10-10）：RESUMED 回显 PENDING 冻结裁定字段 —— 「批的是甲、回显的是乙」根治。
    #   reason/requires_human 来自 run_spine PENDING 分支冻结值；redline_hit 为决策红线态。
    assert audits[0][1]["reason"] == "策略性转人工"
    assert audits[0][1]["requires_human"] is True
    assert audits[0][1]["redline_hit"] is False
    # P-3（D4）：resume 证据三键随审计 payload 同链可追（APS P0-B 收口）
    assert audits[0][1]["resume_principal"] == "approver-u1"
    assert audits[0][1]["resumed_at"] == "2026-10-13T10:00:00"
    assert audits[0][1]["basis"] == "approval-77"


def test_resume_without_persister_audits_only():
    res = _run_pending()
    audits: List[tuple] = []
    out = resume_spine(res, audit_sink=lambda t, p: audits.append((t, p)),
                       resume_evidence=dict(_RESUME_EVIDENCE))
    assert out.persisted is False, "persister=None ⇒ 不落库（与 run_spine 同语义）"
    assert len(audits) == 1 and audits[0][0] == "approval_resumed"


def test_resume_rejects_non_pending():
    """REJECTED 是红线终态，不得经 resume 复活；非 pending 构造同样拒绝。"""
    rejected = SpineResult(
        decision_id="dX", stage_reached="S5_persist", confidence=0.9,
        rubric_missing=(), elements_missing=(), redline_hit=False,
        redline_reasons=(), autonomous=True, approval_rejected="人工驳回")
    with pytest.raises(DecisionError) as ei:
        resume_spine(rejected)
    assert ei.value.code == "ENGINE_FAULT"
    plain = SpineResult(
        decision_id="dY", stage_reached="S5_persist", confidence=0.9,
        rubric_missing=(), elements_missing=(), redline_hit=False,
        redline_reasons=(), autonomous=True)
    with pytest.raises(DecisionError) as ei2:
        resume_spine(plain)
    assert ei2.value.code == "ENGINE_FAULT"


def test_resume_idempotent_after_persisted():
    res = _run_pending()
    calls: List[str] = []
    resume_spine(res, persister=lambda r: calls.append(r.decision_id) or True,
                 resume_evidence=dict(_RESUME_EVIDENCE))
    audits: List[tuple] = []
    out = resume_spine(res, persister=lambda r: calls.append(r.decision_id) or True,
                       audit_sink=lambda t, p: audits.append((t, p)),
                       resume_evidence=dict(_RESUME_EVIDENCE))
    assert out is res and res.persisted is True
    assert calls == ["dR"], "幂等被破坏 ⇒ 重复落库"
    assert audits == [], "幂等被破坏 ⇒ 重复审计留痕"


def test_resume_requires_hitl_evidence_breaking():
    """P-3（D4）：resume_evidence 为必填（breaking）；缺 ⇒ 拒续跑且不计持久化。"""
    res = _run_pending()
    calls: List[str] = []
    with pytest.raises(HITLEvidenceError):
        resume_spine(res, persister=lambda r: calls.append(r.decision_id) or True)
    assert calls == [], "⛔ 缺证据却落库 ⇒ 无 approve 不可生效被破坏"


def test_resume_rejects_insufficient_hitl_evidence():
    """P-3（D4）：三键不全 ⇒ 拒续跑（变异自证：删任一键必红）。"""
    res = _run_pending()
    for missing_one in (
        {"resumed_at": "t", "basis": "b"},             # 缺 resume_principal
        {"resume_principal": "u", "basis": "b"},        # 缺 resumed_at
        {"resume_principal": "u", "resumed_at": "t"},  # 缺 basis
    ):
        with pytest.raises(HITLEvidenceError):
            resume_spine(res, resume_evidence=missing_one)


def test_resume_evidence_checked_before_persist():
    """P-3：证据校验在 persister 之前 —— 即便 persister 已注入，缺证据也不落库。"""
    res = _run_pending()
    called = []
    with pytest.raises(HITLEvidenceError):
        resume_spine(
            res,
            persister=lambda r: called.append(r.decision_id) or True,
            resume_evidence={"resume_principal": "u"},  # 仅 1 键，不足
        )
    assert called == [], "证据不足时 persister 不得被调用"


def _spine_string_constants() -> List[str]:
    """收集 spine 源码全部字符串字面量（AST 层，含 f-string 片段；排除 dict 键位）。

    dict 键位排除的语义依据：payload 键是 schema 名（如 "pending"/"approval_ref"），
    不是事件值；裸字符串攻击面只存在于"作为事件值传给 audit_sink"的位置。
    """
    tree = ast.parse(inspect.getsource(spine_mod))
    out: List[str] = []
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            if (isinstance(child, ast.Constant) and isinstance(child.value, str)
                    and not (isinstance(parent, ast.Dict) and child in parent.keys)):
                out.append(child.value)
    return out


def test_g4_audit_event_constants_are_the_single_source():
    """G4/I1：契约常量是单一事实源；spine 源码禁以**任何字面量形态**出现审计事件。

    判据升级（enterprise I1：原"双引号字面量子串"可被单引号/拼接绕过）：
      R1  值 == 事件名 ⇒ 拦（任意引号形态、f-string 片段均在 AST 常量面内）；
      R2  值与事件名互为子串且 len(值) ≥ 8 且值**仅由该事件名的字符集构成**
          ⇒ 拦（覆盖 chr(97)+"pproval_xxx" 式拆前缀拼接：残片是纯事件名碎片）。
          字符集纯度用于排除诊断文案对字段名的"提及"
          （如 resume 报错文案 '，approval_rejected=' 含中文标点，非事件值）。
    残余盲区（显式声明，不装看不见）：逐字符 chr() 链构造 —— AST 不可见，
    由运行时行为守卫兜底（本文件各测试断言 audit 事件值逐字等于契约常量）。
    """
    assert AUDIT_EVENT_APPROVAL_PENDING == "approval_pending"
    assert AUDIT_EVENT_APPROVAL_REJECTED == "approval_rejected"
    assert AUDIT_EVENT_APPROVAL_RESUMED == "approval_resumed"
    assert AUDIT_APPROVAL_EVENTS == (
        "approval_pending", "approval_rejected", "approval_resumed")
    for value in _spine_string_constants():
        for event in AUDIT_APPROVAL_EVENTS:
            if value == event:
                raise AssertionError(
                    f"⛔ spine 出现裸字符串审计事件 {value!r}（须引用契约常量）")
            if (len(value) >= 8 and (value in event or event in value)
                    and set(value) <= set(event)):
                raise AssertionError(
                    f"⛔ spine 出现审计事件字面量变体 {value!r}（与 {event!r} 互为子串，"
                    "疑似拼接拆分构造；须引用契约常量）")


def test_resume_exported_via_decision_facade():
    assert "resume_spine" in decision_api.__all__
    assert decision_api.resume_spine is resume_spine
