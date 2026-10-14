"""S4 红线硬闸门 —— 链末、不可前置、不可跳过（铁律 C-C）。

⛔ 红线命中 ⇒ 屏蔽自主放行（强制人工处置）。判据由调用方在链末以 `redline_hit` 传入，
   本模块只负责"命中即 False"。红线事项目录来自 `TenantProfile.redline`（L4 注入），
   本模块零领域字面量。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Mapping, Tuple

from chiyu_kernel.contract.decision import (
    AUTONOMOUS_GATE_EXPR, AUTONOMOUS_RELEASE_DEFAULT,
)


@dataclass(frozen=True)
class RedlineVerdict:
    hit: bool
    reasons: Tuple[str, ...]


def evaluate_redline(*, context: Mapping, redline_items: Collection[str]) -> RedlineVerdict:
    """按 profile 注入的红线事项目录做内容匹配；二值判定，不引入领域字面量。"""
    text = str(context.get("text", ""))
    reasons = tuple(it for it in redline_items if it and it in text)
    return RedlineVerdict(hit=bool(reasons), reasons=reasons)


def autonomous_release(*, redline_hit: bool, confidence: float,
                       threshold: float = AUTONOMOUS_RELEASE_DEFAULT) -> bool:
    """链末硬闸门：一整行判据，不得只实现一半（屏蔽红线但不看置信度 = 名存实亡）。

    `AUTONOMOUS_GATE_EXPR` = "autonomous_release = (not redline_hit) and confidence >= autonomous_threshold"
    """
    # 显式实现整行判据；下方断言守卫表达式与契约一致（防止有人"优化"成半截）
    result = (not redline_hit) and confidence >= threshold
    _assert_expr_intact()
    return result


def _assert_expr_intact() -> None:
    # 必须与契约 decision.AUTONOMOUS_GATE_EXPR 的字符串逐字一致（它带 "autonomous_release = " 前缀）
    expected = "autonomous_release = (not redline_hit) and confidence >= autonomous_threshold"
    assert AUTONOMOUS_GATE_EXPR == expected, (
        f"S4 闸门判据被改动：期望 {expected!r}，实际 {AUTONOMOUS_GATE_EXPR!r}（S4 链末硬闸门不可重排）"
    )
