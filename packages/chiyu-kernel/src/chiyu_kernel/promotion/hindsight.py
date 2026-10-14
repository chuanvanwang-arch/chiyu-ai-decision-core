"""后见之明决策核心（纯函数）。

上迁源：APS ``reflux.hindsight_check`` / ``deviation_rate`` 的**裁决段**
（落库/事件发射/基线读取留消费方）。

三条纪律（有守卫测试）：
    · **AND 条件**：单决策偏差超阈 **且** 窗口偏差率超告警才出方——写成 OR
      会让单次抖动就触发，处方洪水随即而来；
    · **每次校验都留痕**（无论是否触发）：否则"没触发"的样本消失，窗口偏差率
      被系统性高估（只统计触发过的）——这是很隐蔽的统计假绿；
    · **no_data ≠ healthy**：空窗口显式区分，防"没数据"被读作"运行良好"。
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Sequence, Tuple

from chiyu_kernel.contract.promotion import (
    DEFAULT_CHANNEL,
    DEFAULT_REFLUX_POLICY,
    WINDOW_STATUSES,
)

__all__ = ["default_reflux_policy", "deviation", "should_prescribe",
           "window_status", "deviation_rate"]

_SECONDS_PER_DAY = 86400.0


def default_reflux_policy() -> Dict[str, Any]:
    """回流策略默认值（threshold / rate_alarm / window_days）。"""
    return dict(DEFAULT_REFLUX_POLICY)


def deviation(observed: float, baseline: float) -> float:
    """单决策偏差 = |observed − baseline|。"""
    return abs(float(observed) - float(baseline))


def should_prescribe(*, delta: float, threshold: float, rate: float,
                     rate_alarm: float) -> bool:
    """出方条件：**单条超阈 AND 窗口告警**（AND 不是 OR）。"""
    return bool(delta > threshold) and bool(rate > rate_alarm)


def window_status(*, samples: int, deviations: int, approved: int,
                  rate: float, rate_alarm: float) -> str:
    """窗口状态四判定。

    - ``no_data``：窗口内无样本（**"没数据" ≠ "健康"**）；
    - ``stagnant``：有偏差但零批准 ⇒ 系统空转（问题反复检出却无改善落地）；
    - ``alarm``：偏差率超告警线；
    - ``healthy``：其余。
    """
    if samples == 0:
        return "no_data"
    if deviations > 0 and approved == 0:
        return "stagnant"
    if rate > rate_alarm:
        return "alarm"
    return "healthy"


def deviation_rate(
    effects: Sequence[Tuple[float, float]], *,
    approved_prescriptions: int = 0,
    threshold: float = 0.3, rate_alarm: float = 0.3,
    window_days: int = 90, now: Optional[float] = None,
) -> Dict[str, Any]:
    """窗口偏差率 + 空转判据（纯函数对账形态）。

    :param effects: ``[(observed_at, delta), ...]`` 窗口内后见之明效应
                    （消费方从 append-only 存储取出后传入）。
    :returns: 与 APS ``reflux.deviation_rate`` 同键集的结构（parity）。
    """
    ref = time.time() if now is None else float(now)
    since = ref - int(window_days) * _SECONDS_PER_DAY
    vals = [float(d) for ts, d in (effects or ()) if float(ts) >= since]
    n = len(vals)
    d = sum(1 for v in vals if v > threshold)
    rate = (d / n) if n else 0.0
    approved = int(approved_prescriptions)
    status = window_status(samples=n, deviations=d, approved=approved,
                           rate=rate, rate_alarm=rate_alarm)
    assert status in WINDOW_STATUSES  # 防词汇漂移（契约闭集对拍）
    return {
        "window_days": int(window_days), "threshold": float(threshold),
        "rate_alarm": float(rate_alarm),
        "samples": n, "deviations": d, "rate": rate, "alarm": rate > rate_alarm,
        "approved_prescriptions": approved,
        "stagnant": status == "stagnant", "status": status,
    }
