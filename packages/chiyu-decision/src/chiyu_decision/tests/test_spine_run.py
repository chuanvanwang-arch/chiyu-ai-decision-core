"""S1→S5 主链：顺序即语义，confidence 仅取 ratio，红线在链末。"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.decision import AUTONOMOUS_RELEASE_DEFAULT, RUBRIC_KEYS
from chiyu_decision.errors import DecisionError
from chiyu_decision.spine import run_spine


def _good_scores() -> dict:
    return {k: 4.0 for k in RUBRIC_KEYS}


def test_spine_runs_in_order_and_reaches_s5():
    res = run_spine(context={"text": "普通", "decision_id": "d1"}, profile=None,
                     rubric_scores=_good_scores(), elements={"intent": "x"})
    assert res.stage_reached == "S5_persist"
    assert res.confidence == 1.0
    assert res.autonomous is True
    assert res.redline_hit is False


def test_spine_rejects_empty_context():
    with pytest.raises(DecisionError) as ei:  # R8：结构化错误码（非泛型 ValueError）
        run_spine(context={}, profile=None, rubric_scores=_good_scores(), elements={})
    assert ei.value.code == "ENGINE_FAULT"


def test_spine_redline_at_chain_end_blocks_release():
    res = run_spine(context={"text": "卫生健康", "decision_id": "d2"}, profile=None,
                     rubric_scores=_good_scores(), elements={}, redline_items=("卫生健康",))
    assert res.redline_hit is True
    assert res.autonomous is False          # 红线命中屏蔽自主放行
    assert res.stage_reached == "S5_persist"  # 红线不阻断落库，只屏蔽自主放行


def test_spine_low_confidence_not_autonomous():
    res = run_spine(context={"text": "普通", "decision_id": "d3"}, profile=None,
                     rubric_scores={k: 0.0 for k in RUBRIC_KEYS}, elements={})
    assert res.confidence == 0.0
    assert res.autonomous is False


def test_spine_persists_when_persister_given():
    captured = {}
    def _persist(r):
        captured["id"] = r.decision_id
        return True
    res = run_spine(context={"text": "普通", "decision_id": "d4"}, profile=None,
                     rubric_scores=_good_scores(), elements={}, persister=_persist)
    assert res.persisted is True and captured["id"] == "d4"
