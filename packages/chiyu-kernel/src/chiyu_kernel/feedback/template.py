"""指标模板与资格断言（B1）—— 纯函数，零 IO。

上迁源：APS ``platform/feedback_loop.py`` 的 ``MetricTemplate`` +
``define_metric_template`` 的资格断言段（落库/发射留消费方）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Tuple

from chiyu_kernel.contract.feedback_loop import (
    METRIC_TEMPLATE_REQUIRED,
    FeedbackTemplateError,
)

__all__ = ["MetricTemplate", "missing_template_keys", "assert_template_complete"]


@dataclass(frozen=True)
class MetricTemplate:
    """指标模板（design §3.2 七要素 + owner/evaluator/adjust_actions）。

    ``target``/``alert`` 为结构化字典（阈值/告警线），``sources`` 为数据来源列表；
    域指标名（如 APS 的钢卷宽高）由消费方构造时注入，内核不内置。
    """

    metric_template_id: str
    loop: str
    name: str
    type: str
    direction: str
    formula: str
    target: Mapping[str, Any]
    alert: Mapping[str, Any]
    sources: Sequence[str]
    owner_agent: Optional[str] = None
    evaluator_skill: Optional[str] = None
    adjust_actions: Tuple[str, ...] = ()


def missing_template_keys(tmpl: MetricTemplate) -> Tuple[str, ...]:
    """返回必填面中**空值**的键（B1：七要素缺一即不可判）。"""
    return tuple(
        k for k in METRIC_TEMPLATE_REQUIRED if not getattr(tmpl, k, None)
    )


def assert_template_complete(tmpl: MetricTemplate) -> None:
    """B1 资格断言：必填要素齐备才允许登记，否则明确报缺哪几项。"""
    missing = missing_template_keys(tmpl)
    if missing:
        raise FeedbackTemplateError(
            f"指标模板缺要素（B1 资格断言失败）: {list(missing)}"
        )
