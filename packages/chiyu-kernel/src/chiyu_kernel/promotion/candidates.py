"""M→K 候选抽取 + 漂移判定 + 覆盖守卫 + 产物载荷（纯函数）。

上迁源：APS ``promotion.extract_numeric_candidates`` / ``drift_detected`` /
``audit_drift`` / ``promotion_overwrite_guard`` / ``build_promotion_payload``。

★ 反假绿入选标准：只从**显式声明**抽取（``<key>: <数值>``），不从散文猜数字
  —— 猜出来的"证据"是臆造，升格后无法溯源。抽不到就交给闸门 blocked。
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from chiyu_kernel.contract.promotion import (
    PARAMS_SOURCE_PROMOTED,
    PROMOTION_STAGE,
    PROTECTED_STAGES,
    TRUTH_TOLERANCE,
)

__all__ = [
    "extract_numeric_candidates", "drift_detected", "audit_drift",
    "promotion_overwrite_guard", "build_promotion_payload",
]

#: 真值查询注入点：rule_key → 标定真值序列（无真值 ⇒ 空序列）。
TruthLookup = Callable[[str], Sequence[float]]


def extract_numeric_candidates(text: Any, param_key: str) -> List[float]:
    """从笔记正文抽取 ``<param_key>[:=]<数值>`` 形式的**显式声明**。

    ⚠ 只认显式声明，**不从散文里猜数字**——抽不到就是抽不到，
    交给闸门 ``blocked``，不硬凑。
    """
    if not text or not param_key:
        return []
    pat = re.compile(
        r"[\"']?" + re.escape(str(param_key)) + r"[\"']?\s*[:=]\s*(-?\d+(?:\.\d+)?)(?![\w.])")
    return [float(m.group(1)) for m in pat.finditer(str(text))]


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def drift_detected(
    value: Any, truth: Sequence[float], *, tolerance: float = TRUTH_TOLERANCE,
) -> Optional[bool]:
    """升格值是否与标定真值冲突。

    :returns: ``True`` 冲突 / ``False`` 一致 / ``None`` **不可比**（无真值，
              或真值序列全部非数值——消费方注入的真值表可能混入非数值项）。
    ⚠ ``None`` 必须**向上冒泡为告警**，不得当"无漂移"静默吞掉。

    与 APS ``promotion.drift_detected:237`` 的 parity：真值全为数值时逐值同结果；
    此处多一层 fail-safe——注入真值含非数值项时**不崩**（APS 版会 TypeError），
    过滤后无任何可比真值 ⇒ ``None``（不可比），与"无真值"同一冒泡语义。
    """
    ts = tuple(truth or ())
    if not ts:
        return None
    numeric = [float(t) for t in ts if _is_number(t)]
    if not numeric:
        return None                     # 真值全部非数值 ⇒ 不可比 ⇒ 告警
    if not _is_number(value):
        return True                     # 真值是标量而升格值不是 ⇒ 无法确认一致 ⇒ 告警
    v = float(value)
    return not any(abs(v - t) <= tolerance for t in numeric)


def audit_drift(
    rules: Iterable[Mapping[str, Any]], *, truth_lookup: TruthLookup,
) -> Dict[str, Any]:
    """对一批规则做漂移审计：参数值 vs 真值（真值查询由消费方注入）。

    :param rules: 每项形如 ``{"rule_key": "c2a_width_shrink", "params": {...},
                    "stage": ..., "params_source": ...}``
    ⚠ 只审计**有真值对应**的键。``summary["checked"] == 0`` 的含义是
      **"没有可审计项"**，不是"零漂移"——调用方不得把零命中读成"全通过"。
    """
    items: List[Dict[str, Any]] = []
    for r in rules or ():
        if not isinstance(r, Mapping):
            continue
        rk = str(r.get("rule_key") or "")
        params = r.get("params") or {}
        if not isinstance(params, Mapping):
            continue
        for pk, v in params.items():
            comp = f"{rk}.{pk}"
            truth = tuple(truth_lookup(comp) or ())
            if not truth:
                continue                      # 无真值 ⇒ 不可比 ⇒ 不审计（不臆断）
            d = drift_detected(v, truth)
            items.append({
                "rule_key": comp,
                "value": v,
                "truth": list(truth),
                "comparable": d is not None,
                "drift_alert": True if d is None else d,
                "stage": r.get("stage"),
                "params_source": r.get("params_source"),
            })
    return {
        "items": items,
        "summary": {
            "checked": len(items),
            "drifted": sum(1 for i in items if i["drift_alert"]),
            "incomparable": sum(1 for i in items if not i["comparable"]),
        },
    }


def promotion_overwrite_guard(existing_stage: Optional[str]) -> Tuple[bool, str]:
    """目标规则已存在时，升格**是否可以写入**。

    - ``None``（不存在）/ 其它阶段 ⇒ 可写；
    - ``calibrated`` ⇒ **禁止**：用 AI 归纳值覆盖已标定知识是知识污染，不可逆。
    """
    if existing_stage in PROTECTED_STAGES:
        return False, (
            f"目标规则已是 {existing_stage}：升格产物**不得覆盖已标定知识**"
            "（AI 归纳值冒充标定值 = 知识污染且不可事后审计）"
        )
    return True, ""


def build_promotion_payload(
    rule_key: str, *,
    value: Any,
    confidence: float,
    sources: Iterable[str] = (),
    title: Optional[str] = None,
    formula: Optional[str] = None,
    actor: str = "promoter",
    drift: Optional[bool] = None,
    drift_lookup: Optional[TruthLookup] = None,
) -> Dict[str, Any]:
    """构造**升格规则**载荷（不落库，纯函数 → 可单测）。

    恒带：``stage="promoted"`` / ``params_source="PROMOTED"`` /
    ``aiGenerated=True`` / ``rule_confidence`` / ``drift_alert``。
    ``drift`` 可预计算传入；也可传 ``drift_lookup`` 由本函数计算
    （不可比 ⇒ ``drift_alert=True`` 告警，不静默）。
    """
    constraint_key, _, param_key = rule_key.partition(".")
    srcs = tuple(sources or ())
    if drift is None and drift_lookup is not None:
        drift = drift_detected(value, drift_lookup(rule_key))
    return {
        "rule_key": constraint_key or rule_key,
        "title": title or rule_key,
        "stage": PROMOTION_STAGE,
        "formula": formula or f"promoted:{rule_key}",
        "params": {param_key: value} if param_key else {},
        "params_source": PARAMS_SOURCE_PROMOTED,       # ★ 红线：绝不写 CALIBRATED
        "evidence": (";".join(srcs) if srcs else "promotion:unspecified"),
        "aiGenerated": True,
        "rule_confidence": round(float(confidence), 6),
        "drift_alert": True if drift is None else drift,  # 不可比 ⇒ 告警，不静默
        "promoted_by": actor,
    }
