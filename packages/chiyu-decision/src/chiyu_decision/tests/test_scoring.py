"""S2 八要素 + 九尺子；S3 聚合（confidence 仅取 ratio）。"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.decision import (
    CONFIDENCE_SOURCE_KEY, EIGHT_ELEMENTS, RUBRIC_KEYS, RUBRIC_SCALE_MAX,
)
from chiyu_decision.errors import DecisionError
from chiyu_decision.scoring import (
    aggregate_confidence, check_elements, score_rubric,
)


def test_score_rubric_ratio_is_mean_over_scale():
    scores = {k: 4.0 for k in RUBRIC_KEYS}
    rep = score_rubric(scores)
    assert rep.ratio == 1.0                      # 全 4 分 ⇒ ratio=1.0
    assert len(rep.scores) == len(RUBRIC_KEYS)


def test_score_rubric_reports_missing_keys():
    rep = score_rubric({"clarity": 4.0})          # 只评了 1 键
    assert set(rep.missing) == set(RUBRIC_KEYS) - {"clarity"}


def test_score_rubric_zero_is_not_missing():
    scores = {k: 0.0 for k in RUBRIC_KEYS}        # 评了但全 0
    rep = score_rubric(scores)
    assert rep.missing == () and rep.ratio == 0.0  # hits=0 合法，非缺失


def test_aggregate_confidence_only_accepts_ratio():
    rep = score_rubric({k: 3.0 for k in RUBRIC_KEYS})
    assert aggregate_confidence(rep) == rep.ratio
    with pytest.raises(DecisionError) as ei:   # R8：禁止 fused 冒充，结构化错误码
        aggregate_confidence(rep, source_key="fused")
    assert ei.value.code == "ENGINE_FAULT"


def test_check_elements_reports_missing():
    rep = check_elements({"intent": "…"})
    assert set(rep.missing) == set(EIGHT_ELEMENTS) - {"intent"}


def test_rubric_scale_max_is_four():
    assert RUBRIC_SCALE_MAX == 4


def test_api_exports_aggregate_confidence():
    """R1：聚合置信度须经门面导出，消费方不必绕开 api 去 import .scoring。

    `from chiyu_decision import aggregate_confidence` 与 `from chiyu_decision.api
    import aggregate_confidence` 都应可导入，且聚合结果恒等于 rubric.ratio。
    """
    from chiyu_decision import aggregate_confidence as ac_top
    from chiyu_decision.api import aggregate_confidence as ac_api

    assert ac_top is ac_api                  # 门面与包顶导出同一对象
    rep = score_rubric({k: 4.0 for k in RUBRIC_KEYS})
    assert ac_top(rep) == rep.ratio
    assert ac_api(rep) == rep.ratio
