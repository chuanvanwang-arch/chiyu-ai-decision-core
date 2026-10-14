"""升格闸门（三态裁决，纯函数）。

上迁源：APS ``promotion.promote_gate``（T16-2）。

裁决顺序即不变式：白名单 → 证据数 → 一致性，任一不过即止。
产物恒 PENDING（第 3 闸 HITL 在外层把守）；本函数**零副作用**
（APS 版的 bus.emit 留消费方——``blocked`` 本就不发射，``rejected`` 的
治理留痕由消费方按本函数返回的 status 自行决定）。
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, Optional, Sequence

from chiyu_kernel.contract.promotion import (
    BLOCKED,
    DEFAULT_MIN_CONSISTENCY,
    DEFAULT_MIN_EVIDENCE,
    PROMOTED,
    REJECTED,
)

__all__ = ["promote_gate"]


def _canon(sample: Any) -> str:
    """样本归一：分段表等不可哈希样本也要能计数（不崩、不静默丢）。"""
    try:
        return json.dumps(sample, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return repr(sample)


def promote_gate(
    rule_key: str,
    samples: Sequence[Any],
    *,
    promotable: Sequence[str] = (),
    min_evidence: int = DEFAULT_MIN_EVIDENCE,
    min_consistency: float = DEFAULT_MIN_CONSISTENCY,
) -> Dict[str, Any]:
    """升格闸门：白名单 → 证据数 → 一致性，三态裁决。

    :returns: ``{"status": "promoted"|"blocked"|"rejected", "rule_key", "value",
                  "consistency", "evidence_count", "reason", ...}``
    """
    items = list(samples or ())
    n = len(items)

    # --- ① 白名单：集合外**直接拒绝**，不降级为"待人工判断" -----------------
    if rule_key not in tuple(promotable):
        return {"status": REJECTED, "rule_key": rule_key, "value": None,
                "consistency": 0.0, "evidence_count": n,
                "reason": (f"{rule_key!r} 不在可升格键集合（n={len(tuple(promotable))}）；"
                           "超出集合的键**直接拒绝**，不降级为待人工判断。")}

    canon = [_canon(s) for s in items]
    counts = Counter(canon)
    mode, mode_n = counts.most_common(1)[0] if counts else (None, 0)
    consistency = (mode_n / n) if n else 0.0

    # --- ② 证据数不足 ⇒ blocked（孤证不得上升为知识）----------------------
    if n < min_evidence:
        return {"status": BLOCKED, "rule_key": rule_key, "value": None,
                "consistency": round(consistency, 6), "evidence_count": n,
                "reason": f"证据不足：样本 {n} 条 < 门槛 {min_evidence} 条（孤证不得上升为知识）"}

    # --- ③ 一致性不足 ⇒ blocked（证据自相矛盾）----------------------------
    if consistency < min_consistency:
        return {"status": BLOCKED, "rule_key": rule_key, "value": None,
                "consistency": round(consistency, 6), "evidence_count": n,
                "reason": (f"证据不一致：众数占比 {consistency:.2f} < 门槛 {min_consistency:.2f}"
                           f"（{len(counts)} 种取值互相矛盾，不足以上升为知识）")}

    value = next(s for s, c in zip(items, canon) if c == mode)
    return {"status": PROMOTED, "rule_key": rule_key, "value": value,
            "consistency": round(consistency, 6), "evidence_count": n,
            "reason": (f"证据 {n} 条，众数占比 {consistency:.2f} ≥ 门槛；"
                       "产物恒 PENDING（第 3 闸 HITL 在外层把守）")}
