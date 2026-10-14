"""参数健康诊断核（Batch-1b-4 param_health_check）—— 纯函数，零 IO。

收敛 CRM `monitor/diagnosis.js` 的 **recommend 三档判据**与 **routing 系 knob
红线过滤**（只展示不产处方）；数据聚合（PG 查询/健康摘要）、红线前缀域清单
留消费方注入。

⛔ 反假绿：LOW 档无自动放行通道（缺档保守降 LOW ⇒ reject 方向，安全侧）；
红线过滤是**分离不是丢弃**——display_only 仍返回（可见性保留，禁静默吞）。
"""
from __future__ import annotations

from typing import Any, Iterable, List, Mapping, Optional, Sequence

from chiyu_kernel.contract.param_health import (
    HIGH_RISK_FAIL_RATE, PARAM_RISK_LEVELS, ParamHealthError,
)

__all__ = ["recommend_prescription", "split_red_line"]

_DEFAULT_RISK = "LOW"   # 缺档降 LOW：判据上永不自动 approve（fail-closed 方向）


def _num(x: Any, *, what: str) -> float:
    if isinstance(x, bool):
        raise ParamHealthError(f"参数健康判据 {what} 非数值（bool 不算数）")
    try:
        v = float(x)
    except (TypeError, ValueError) as exc:
        raise ParamHealthError(f"参数健康判据 {what} 非数值：{x!r}") from exc
    if v != v:
        raise ParamHealthError(f"参数健康判据 {what} 为 NaN")
    return v


def recommend_prescription(patch: Mapping[str, Any],
                           scenario_fail_rate: Any) -> Mapping[str, Any]:
    """推荐三档（CRM diagnosis recommend 确定性规则同口径）。

    - HIGH + 场景失败率 > HIGH_RISK_FAIL_RATE ⇒ approve（风险高但场景确实在坏）；
    - MEDIUM + 失败率 > 0 ⇒ approve；
    - 其余（含 LOW 全部）⇒ reject。

    :param patch: 处方投影（至少含 ``risk``；缺档 ⇒ 保守降 LOW）。
    :param scenario_fail_rate: 该处方场景的失败率（None ⇒ 0.0，CRM ``|| 0`` 同口径）。
    """
    risk = (patch or {}).get("risk") or _DEFAULT_RISK
    if risk not in PARAM_RISK_LEVELS:
        raise ParamHealthError(f"未知风险档：{risk!r} ∉ {PARAM_RISK_LEVELS}")
    fail = 0.0 if scenario_fail_rate is None else _num(
        scenario_fail_rate, what="scenario_fail_rate")
    if risk == "HIGH" and fail > HIGH_RISK_FAIL_RATE:
        rec = "approve"
    elif risk == "MEDIUM" and fail > 0:
        rec = "approve"
    else:
        rec = "reject"
    return {"recommend": rec, "risk": risk,
            "rationale": f"场景失败率 {fail * 100:.1f}%"}


def split_red_line(patches: Optional[Iterable[Mapping[str, Any]]],
                   red_line_prefixes: Optional[Iterable[str]] = None,
                   ) -> Mapping[str, List[Mapping[str, Any]]]:
    """红线分离（CRM isRoutingKnob 过滤纯函数化；前缀清单由消费方注入）。

    匹配语义与 CRM 同口径：knob 字符串**包含**前缀（大小写不敏感）即命中红线。
    ⛔ 分离不是丢弃：``display_only`` 仍返回（标 ``red_line=True``，只展示不产处方），
    禁静默吞——被过滤的处方从诊断页消失 = 红线变成盲区。

    :returns: ``{"prescribable": [...], "display_only": [...]}``（互斥完备）。
    """
    prefixes = [str(p).lower() for p in (red_line_prefixes or ())]
    prescribable: List[Mapping[str, Any]] = []
    display_only: List[Mapping[str, Any]] = []
    for p in (patches or ()):
        row = dict(p or {})
        knob = str(row.get("knob") or "").lower()
        if any(pref in knob for pref in prefixes):
            row["red_line"] = True
            display_only.append(row)
        else:
            prescribable.append(row)
    return {"prescribable": prescribable, "display_only": display_only}
