"""校准链守卫（B3/B4）—— 纯函数，零 IO。

上迁源：APS ``platform/feedback_loop.py`` 的 ``propose_calibration``
（拒绝出方守卫段）/ ``approve_calibration``（HITL 闸）/ ``calibration_stats``。

落库与事件发射（``bus.conn.execute`` / ``bus.emit``）留消费方；本模块只给
**裁决逻辑**：能不能出方（guard）、允不允许裁决（transition）、闭环通不通（stats）。
"""
from __future__ import annotations

from typing import Dict, List, Mapping

from chiyu_kernel.contract.feedback_loop import (
    CALIBRATION_APPROVED,
    CALIBRATION_BLOCKED,
    CALIBRATION_MIN_COVERAGE,
    CALIBRATION_MIN_SAMPLE,
    CALIBRATION_PENDING,
    CalibrationStateError,
)

__all__ = ["prescribe_guard", "approve_transition", "calibration_stats"]


def prescribe_guard(
    *, sample_size: int, coverage: float,
    min_sample: int = CALIBRATION_MIN_SAMPLE,
    min_coverage: float = CALIBRATION_MIN_COVERAGE,
) -> Dict[str, object]:
    """B4 拒绝出方守卫：先判"能不能出"，再判"出什么"。

    样本量 / 覆盖率任一不达标 ⇒ ``status="blocked"`` + ``blocked_by`` 原因列明，
    且 ``emit=False``——**未达标绝不发射治理事件**（不制造假的待批动作）；
    达标 ⇒ ``status="pending"``（等 HITL），``emit=True``。
    """
    reasons: List[str] = []
    if sample_size < min_sample:
        reasons.append(f"样本量 {sample_size} < 门槛 {min_sample}")
    if coverage < min_coverage:
        reasons.append(f"覆盖率 {coverage:.3f} < 门槛 {min_coverage:.3f}")
    if reasons:
        return {"status": CALIBRATION_BLOCKED, "blocked_by": "; ".join(reasons),
                "emit": False}
    return {"status": CALIBRATION_PENDING, "blocked_by": None, "emit": True}


def approve_transition(current: str) -> str:
    """B3 HITL 裁决闸：仅 ``pending → approved`` 合法。

    对 ``blocked``/``approved``/``rejected`` 候选重复裁决 ⇒
    ``CalibrationStateError``（已裁决不得翻案重判）。生效（写回配置）属治理动作，
    本函数**只到 approved**，绝不自动 apply。
    """
    if current != CALIBRATION_PENDING:
        raise CalibrationStateError(
            f"校准候选已 {current!r}，不可重复裁决（仅 pending → approved 合法）"
        )
    return CALIBRATION_APPROVED


def calibration_stats(
    *, by_status: Mapping[str, int], candidate_events: int,
) -> Dict[str, object]:
    """闭环连通性自证（B3/B6）：候选落库 **且** 事件已发射，两个条件同时成立。

    ``by_status``：状态→计数（消费方从落库聚合）；``candidate_events``：
    候选事件发射数（消费方从事件表计数）。单表非空不判绿（防"非空即通过"假绿）。
    """
    by = dict(by_status or {})
    total = sum(by.values())
    closed = (
        sum(by.get(s, 0) for s in (CALIBRATION_PENDING, CALIBRATION_APPROVED,
                                   "rejected")) > 0
        and int(candidate_events) > 0
    )
    return {
        "total": total,
        "by_status": by,
        "candidate_events_emitted": int(candidate_events),
        "closed_loop": closed,
    }
