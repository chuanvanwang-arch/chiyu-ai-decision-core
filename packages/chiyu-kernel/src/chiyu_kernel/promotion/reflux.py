"""回流处方守卫（纯函数）—— C3 配置处方出方前的四道闸。

上迁源：APS ``reflux.prescribe`` 的**守卫段**（白名单 → 可解析 → 依据非空；
落库/事件发射留消费方）。

纪律（专利 F 权 5 同口径）：可处方键**集合外的键直接拒绝**，不是降级为
"待人工判断"；集合内但配置解析失败 ⇒ 同样拒绝（防据不存在的键改配置）。
处方恒 PENDING——本函数只给裁决，**从不**改配置。
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

from chiyu_kernel.contract.promotion import (
    PRESCRIPTION_PENDING,
    REJECTED,
)

__all__ = ["reflux_prescribe_guard"]


def reflux_prescribe_guard(
    *, key: str, value: Any, rationale: str,
    prescribable: Sequence[str] = (),
    resolvable: bool = True, current: Any = None,
) -> dict:
    """C3 配置处方守卫：四道闸按序判定，任一不过即 ``rejected`` + 原因。

    :param prescribable: 可处方键闭集（消费方注入；**显式枚举，禁止通配**）。
    :param resolvable:   该键能否在消费方配置中解析到当前值（防配置漂移空转）。
    :param current:      解析到的当前值（仅 resolvable=True 时有意义）。
    :returns: ``{"status": "pending"|"rejected", "reason", "key", "from", "to"}``
              —— ``pending`` 仅表示"允许出方"，处方落库恒 PENDING（HITL 把守）。
    """
    allowed = tuple(prescribable or ())
    if key not in allowed:
        return {"status": REJECTED, "key": key, "value": value, "from": None,
                "to": value, "reason": (
                    f"{key!r} 不在可处方键集合（n={len(allowed)}）；"
                    "超出所述集合的键**直接拒绝**，不降级为待人工判断。")}
    if not resolvable:
        return {"status": REJECTED, "key": key, "value": value, "from": None,
                "to": value, "reason": (
                    f"{key!r} 虽在白名单内，但配置中**解析失败**"
                    "（配置已漂移/键名失效）→ 拒绝出方，防据不存在的键改配置。")}
    if not str(rationale or "").strip():
        return {"status": REJECTED, "key": key, "value": value, "from": current,
                "to": value, "reason": "rationale 为空：无依据不得出方（不写空依据）。"}
    return {"status": PRESCRIPTION_PENDING, "key": key, "value": value,
            "from": current, "to": value, "reason": None}
