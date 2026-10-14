"""策略外部化：JSON 策略读取 + 逐键回落（改参不改码）。

上迁源：APS ``promotion.load_promotion_policy`` / ``reflux.load_reflux_policy``
（两者同构，收敛为一份通用实现）。

纪律（有守卫测试）：
    · **未知键不进结果**（防配置漂移被静默吞进运行时）；
    · 键值非法 ⇒ **该键回落默认**，既不静默接受也不整体崩掉；
    · 缺文件/非 dict ⇒ 全量回落默认。
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Mapping, Optional

from chiyu_kernel.contract.promotion import PromotionPolicyError

__all__ = ["positive_int", "positive_float", "unit_float", "load_json_policy"]

#: 键校验器：返回 coercion 后的值；非法返回 None（⇒ 该键回落默认）。
Validator = Callable[[Any], Optional[Any]]


def _is_number(v: Any) -> bool:
    """数值判定：``bool`` 是 ``int`` 子类，但语义上不是数值。"""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def positive_int(v: Any) -> Optional[int]:
    return int(v) if _is_number(v) and int(v) > 0 else None


def positive_float(v: Any) -> Optional[float]:
    return float(v) if _is_number(v) and float(v) > 0 else None


def unit_float(v: Any) -> Optional[float]:
    return float(v) if _is_number(v) and 0.0 <= float(v) <= 1.0 else None


def load_json_policy(
    path: Optional[str], defaults: Mapping[str, Any],
    *, validators: Optional[Mapping[str, Validator]] = None,
) -> Dict[str, Any]:
    """读取 JSON 策略阈值；缺文件/键非法时**逐键**回落内建默认。

    Args:
        path: 策略文件路径（None 或不可读 ⇒ 全量默认）。
        defaults: 内建默认（键即策略面，未知键不进结果）。
        validators: 键 → 校验器（缺省键原样接受；校验器返回 None ⇒ 回落）。
    """
    out: Dict[str, Any] = dict(defaults)
    vals = dict(validators or {})
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return out
    if not isinstance(raw, dict):
        return out
    for key, default in defaults.items():
        if key not in raw:
            continue
        value = raw[key]
        validator = vals.get(key)
        if validator is not None:
            coerced = validator(value)
            out[key] = default if coerced is None else coerced
        else:
            out[key] = value
    return out
