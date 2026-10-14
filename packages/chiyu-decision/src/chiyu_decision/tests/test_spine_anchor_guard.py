"""A4 判据（S1→S5 时序守卫）—— 参数化版本（非位置/字符串硬编码断言）。

⛔ 判据不是"文件在就对"，而是：本包运行时的 SPINE_ORDER 与契约逐项相等；
   confidence 来源为 ratio 而非 fused；红线在链末（不得前置/跳过）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.decision import (
    CONFIDENCE_SOURCE_KEY, RUBRIC_KEYS, SPINE_ORDER as CONTRACT_ORDER,
)
from chiyu_decision import SPINE_ORDER as RUNTIME_ORDER
from chiyu_decision.errors import DecisionError
from chiyu_decision.scoring import aggregate_confidence, score_rubric
from chiyu_decision.redline import autonomous_release
from chiyu_decision.spine import run_spine


@pytest.mark.parametrize("expected,actual", [(tuple(CONTRACT_ORDER), tuple(RUNTIME_ORDER))])
def test_spine_order_matches_contract(expected, actual):
    assert actual == expected, "决策脊柱顺序被改动（S1→S5 不可重排，铁律 C-A）"


def test_confidence_source_is_ratio_not_fused():
    rubric = score_rubric({k: 4.0 for k in RUBRIC_KEYS})
    with pytest.raises(DecisionError) as ei:   # R8：结构化错误码锁定 S3 违约
        aggregate_confidence(rubric, source_key="fused")
    assert ei.value.code == "ENGINE_FAULT"
    # 修正计划笔误：confidence 唯一来源是 ratio，不得与 CONFIDENCE_SOURCE_KEY 字符串混淆
    assert aggregate_confidence(rubric) == rubric.ratio and rubric.ratio == 1.0


def test_redline_block_release_even_with_high_confidence():
    # 红线在链末仍生效：高 confidence + 红线命中 ⇒ 不自主放行
    scores = {k: 4.0 for k in RUBRIC_KEYS}
    res = run_spine(context={"text": "卫生健康", "decision_id": "g1"}, profile=None,
                     rubric_scores=scores, elements={}, redline_items=("卫生健康",))
    assert res.redline_hit and not res.autonomous


def test_spine_end_to_end_reaches_s5_in_order():
    scores = {k: 4.0 for k in RUBRIC_KEYS}
    res = run_spine(context={"text": "普通", "decision_id": "g2"}, profile=None,
                     rubric_scores=scores, elements={"intent": "x"})
    assert res.stage_reached == "S5_persist" and res.autonomous
