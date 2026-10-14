"""chiyu-decision 的唯一公开门面。

消费方只许 import 本模块（chiyu_decision.api）与 chiyu_kernel.contract；
本包其余模块（spine / scoring / redline）为内部实现，不在公开消费面内。
"""
from __future__ import annotations

from chiyu_kernel.contract.decision import SPINE_ORDER, validate_spine_order

from .redline import RedlineVerdict, autonomous_release, evaluate_redline
from .scoring import (
    RubricReport, aggregate_confidence, cap_rubric_by_elements, check_elements,
    score_rubric,
)
from .errors import DECISION_ERROR_CODES, DecisionError
from .outcome import append_outcome, list_outcomes
from .spine import SpineResult, resume_spine, run_spine

__all__ = [
    "SPINE_ORDER", "validate_spine_order", "run_spine", "resume_spine",
    "SpineResult",
    "score_rubric", "RubricReport", "check_elements", "evaluate_redline",
    "cap_rubric_by_elements",
    "RedlineVerdict", "autonomous_release", "aggregate_confidence",
    "DecisionError", "DECISION_ERROR_CODES",
    # P-1（D1.5）：结局采集 API —— 决策→执行→结局→复盘 闭环第一环
    "append_outcome", "list_outcomes",
]
