"""WS3 审批闸接入 run_spine 的集成测试 + 反假绿探针。

⛔ 探针 `test_probe_gate_blocks_persist_on_redline` 是**判别力自证**：断言「红线命中 +
   注入 RedlinePriorityGate ⇒ 不落库 + 审计留痕」。若有人绕过审批闸（例如把门面闸
   改成恒透传），本用例必转红。详见 ws3 变异自证步骤。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.approval import RedlinePriorityGate
from chiyu_kernel.contract.decision import EIGHT_ELEMENTS, RUBRIC_KEYS

from chiyu_decision.spine import run_spine


def _good() -> dict:
    return {k: 4.0 for k in RUBRIC_KEYS}


def _full_elements() -> dict:
    return {e: "x" for e in EIGHT_ELEMENTS}


def test_gate_rejects_redline_blocks_persist_and_audits():
    audits = []
    persisted = []

    def _audit(event_type, payload):
        audits.append((event_type, payload))

    def _persist(r):
        persisted.append(r.decision_id)
        return True

    res = run_spine(
        context={"text": "卫生健康", "decision_id": "dR"}, profile=None,
        rubric_scores=_good(), elements={}, redline_items=("卫生健康",),
        approval_gate=RedlinePriorityGate(), audit_sink=_audit, persister=_persist,
    )
    assert res.redline_hit is True
    assert res.approval_rejected is not None
    assert res.persisted is False
    assert persisted == [], "审批驳回仍调用了落库回调 ⇒ 闸门被绕过"
    assert len(audits) == 1
    assert audits[0][0] == "approval_rejected"
    assert audits[0][1]["decision_id"] == "dR"
    assert audits[0][1]["requires_human"] is True


def test_gate_approves_clean_decision_persists():
    captured = {}

    def _persist(r):
        captured["id"] = r.decision_id
        return True

    res = run_spine(
        context={"text": "普通", "decision_id": "dO"}, profile=None,
        rubric_scores=_good(), elements=_full_elements(), approval_gate=RedlinePriorityGate(),
        persister=_persist,
    )
    assert res.redline_hit is False
    assert res.approval_rejected is None
    assert res.persisted is True
    assert captured["id"] == "dO"


def test_default_none_preserves_prior_behavior():
    # approval_gate=None ⇒ 透传，保留 run_spine 既有行为：红线只屏蔽自主放行、不阻断落库
    captured = {}

    def _persist(r):
        captured["id"] = r.decision_id
        return True

    res = run_spine(
        context={"text": "卫生健康", "decision_id": "dOld"}, profile=None,
        rubric_scores=_good(), elements={}, redline_items=("卫生健康",),
        persister=_persist,
    )
    assert res.redline_hit is True
    assert res.autonomous is False
    assert res.approval_rejected is None
    assert res.persisted is True
    assert captured["id"] == "dOld"


def test_probe_gate_blocks_persist_on_redline():
    """反假绿探针：红线命中 + 注入 RedlinePriorityGate ⇒ 必须不落库。

    这是 WS3 与 run_spine 接线正确性的核心不变量。变异自证时临时删除
    `RedlinePriorityGate.decide` 的 `if redline_hit:` 分支（相当于闸门失效），
    本用例必须转红（persisted 为真 / approval_rejected 为空）。
    """
    persisted = []

    def _persist(r):
        persisted.append(r.decision_id)
        return True

    res = run_spine(
        context={"text": "卫生健康", "decision_id": "probe"}, profile=None,
        rubric_scores=_good(), elements=_full_elements(), redline_items=("卫生健康",),
        approval_gate=RedlinePriorityGate(), persister=_persist,
    )
    assert res.approval_rejected is not None, "红线命中却未填报驳回原因 ⇒ 闸门失效"
    assert persisted == [], "红线命中仍落库 ⇒ 闸门被绕过"
