"""S4 红线：链末硬闸门，命中即屏蔽自主放行（铁律 C-C）。"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.decision import AUTONOMOUS_RELEASE_DEFAULT
from chiyu_decision.redline import autonomous_release, evaluate_redline


def test_redline_hit_reports_reason():
    v = evaluate_redline(context={"text": "涉及卫生健康事项"}, redline_items=("卫生健康", "劳动"))
    assert v.hit is True and "卫生健康" in v.reasons


def test_redline_no_hit_when_absent():
    v = evaluate_redline(context={"text": "普通决策"}, redline_items=("卫生健康",))
    assert v.hit is False and v.reasons == ()


def test_autonomous_release_gate_is_single_line():
    # 红线命中 ⇒ 即便 confidence 高也不放行（一整行判据，不得只实现一半）
    assert autonomous_release(redline_hit=True, confidence=1.0) is False
    assert autonomous_release(redline_hit=False, confidence=AUTONOMOUS_RELEASE_DEFAULT) is True
    assert autonomous_release(redline_hit=False, confidence=AUTONOMOUS_RELEASE_DEFAULT - 0.01) is False


def test_redline_items_empty_means_no_hit():
    assert evaluate_redline(context={"text": "X"}, redline_items=()).hit is False
