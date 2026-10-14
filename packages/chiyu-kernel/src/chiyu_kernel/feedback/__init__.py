"""反馈闭环机制层（GAP-6，Batch-2b）—— 纯函数，零 IO。

上迁源：APS ``platform/feedback_loop.py``（design #9 回流边 ⑤⑥⑦⑧ 的裁决逻辑）。
落库 / 事件发射 / DDL 装配留消费方；本包只提供资格断言、加权评估、
拒绝出方守卫、HITL 校准闸与连通性统计的纯函数核心。
"""
from .calibration import approve_transition, calibration_stats, prescribe_guard
from .evaluate import EvalItem, EvaluatorSpec, evaluate, expression_variables, safe_eval
from .template import MetricTemplate, assert_template_complete, missing_template_keys

__all__ = [
    "MetricTemplate", "assert_template_complete", "missing_template_keys",
    "EvalItem", "EvaluatorSpec", "evaluate", "expression_variables", "safe_eval",
    "prescribe_guard", "approve_transition", "calibration_stats",
]
