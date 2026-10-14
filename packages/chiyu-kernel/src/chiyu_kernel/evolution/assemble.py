"""处方组装核（Batch-1b-4 assemble_prescription）—— 纯函数，零 IO。

收敛 CRM `calibration/patchAssembler.js` 的 **enrichPatchesAndSave 组装段**：
attribute 结果 →（delta → from/to/target）→ 影子重放预期影响 → 幂等键。
⛔ 落库（savePatches）、第 0 闸（produceDecision）、幂等去重落库留消费方——
本核只产出「富化未落库形」+ blocked_by，HTTP 路由与 MCP 工具共用地消费本核
（CRM 单一事实源定位同构）。

⛔ 与 shadow_replay 同纪律：replay 必须**同源可调用对象**（禁字符串公式），
产出投影缺预期影响字段即 fail-closed 拒绝（无对照预期 = 盲改）。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping, Sequence

from chiyu_kernel.contract.evolution import (
    ASSEMBLE_AUTO_KNOBS, ASSEMBLE_EXPECTED_IMPACT_FIELDS, AssembleError,
)

__all__ = ["assemble_prescription"]

_ReplayFn = Callable[[Sequence[Mapping[str, Any]], Mapping[str, Any]], Mapping[str, Any]]


def _replay_metrics(replay: _ReplayFn,
                    decisions: Sequence[Mapping[str, Any]],
                    conf: Mapping[str, Any]) -> Mapping[str, Any]:
    """重放并校验指标投影齐备（缺任一字段 = fail-closed，禁半截对照）。"""
    if not callable(replay):
        raise AssembleError("replay 不可调用 ⇒ 拒绝组装（禁字符串公式，与 shadow_replay 同纪律）")
    out = replay(decisions, conf)
    if not isinstance(out, Mapping):
        raise AssembleError(f"replay 产出须为 Mapping，实得 {type(out).__name__}")
    missing = [k for k in ASSEMBLE_EXPECTED_IMPACT_FIELDS if k not in out]
    if missing:
        raise AssembleError(f"replay 产出缺预期影响字段：{missing}（无对照即盲改，拒绝）")
    return out


def _idem_key(knob: str, target: Any,
              from_value: Mapping[str, Any],
              to_value: Mapping[str, Any]) -> str:
    """幂等键：由 knob/target/from/to 规范化派生（同输入恒同键；落库去重留消费方）。"""
    canon = json.dumps(
        {"knob": knob, "target": target, "from": from_value, "to": to_value},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def assemble_prescription(*, decisions: Sequence[Mapping[str, Any]],
                          conf: Mapping[str, Any],
                          attribute_result: Mapping[str, Any],
                          replay: _ReplayFn) -> Mapping[str, Any]:
    """组装富化处方（CRM enrichPatchesAndSave 纯函数化；零 IO）。

    :param decisions: 历史决策样本（重放入参；计数进 expected_impact.sample_size）。
    :param conf: 当前校准配置 ``{"threshold": number, "weights": {...}}``。
    :param attribute_result: attribute() 产出 ``{"guards": [...], "patches": [...]}``；
        patches 元素形如 ``{"id", "label", "knob", "delta", "evidence"}``。
    :param replay: 场景重放可调用对象 ``replay(decisions, conf) -> {"autonomy",
        "escalated", "estimated_override_rate"}``（同源纪律，见模块 docstring）。
    :returns: ``{"blocked_by", "patches", "skipped", "sample"}``；
        patches = 富化未落库形（含 from_value/to_value/expected_impact/idempotency_key）；
        skipped = 非 threshold/weight knob（不自动产出，走消费方手动分支）。
    """
    att = attribute_result or {}
    sample = len(decisions or ())
    guards = att.get("guards") or ()
    if guards:
        # 守卫命中 ⇒ 不出处方（CRM blocked_by 同口径）
        return {"blocked_by": [{"rule_id": (g or {}).get("id"),
                                "reason": (g or {}).get("reason")} for g in guards],
                "patches": [], "skipped": [], "sample": sample}
    threshold = (conf or {}).get("threshold")
    weights = dict((conf or {}).get("weights") or {})
    baseline = _replay_metrics(replay, decisions or (), conf or {})
    enriched, skipped = [], []
    for p in (att.get("patches") or ()):
        row = dict(p or {})
        knob = row.get("knob")
        if knob not in ASSEMBLE_AUTO_KNOBS:
            # 非 threshold/weight 不自动产出（required_dims 走消费方手动分支）
            skipped.append({"knob": knob, "id": row.get("id"),
                            "reason": "non_auto_knob"})
            continue
        delta = dict(row.get("delta") or {})
        if knob == "threshold":
            base = threshold if threshold is not None else None
            base_n = base if isinstance(base, (int, float)) and not isinstance(base, bool) else None
            if base_n is None:
                raise AssembleError("conf.threshold 缺失或非数值，无法组装 threshold 处方")
            d = delta.get("threshold") or 0
            if isinstance(d, bool) or not isinstance(d, (int, float)):
                raise AssembleError(f"threshold delta 非数值：{d!r}")
            from_value = {"threshold": base_n}
            to_value = {"threshold": base_n + d}
            target = None
            next_conf: Mapping[str, Any] = {**conf, "threshold": to_value["threshold"]}
        else:   # weight
            wdelta = dict(delta.get("weights") or {})
            if len(wdelta) != 1:
                raise AssembleError(
                    f"weight delta 须恰一目标键（多键歧义禁猜），实得 {sorted(wdelta)}")
            target = next(iter(wdelta))
            if target not in weights:
                raise AssembleError(f"conf.weights 缺目标键 {target!r}（禁对未登记权重出处方）")
            dv = wdelta[target]
            if isinstance(dv, bool) or not isinstance(dv, (int, float)):
                raise AssembleError(f"weight delta 非数值：{dv!r}")
            from_value = {"weights": {target: weights[target]}}
            to_value = {"weights": {target: weights[target] + dv}}
            next_conf = {**conf, "weights": {**weights, target: to_value["weights"][target]}}
        after = _replay_metrics(replay, decisions or (), next_conf)
        enriched.append({
            **row, "knob": knob, "target": target,
            "from_value": from_value, "to_value": to_value,
            "evidence": {"rule_id": row.get("id"), "reason": row.get("label"),
                         "metrics": row.get("evidence")},
            "expected_impact": {
                "autonomy_before": baseline["autonomy"],
                "autonomy_after": after["autonomy"],
                "escalated_before": baseline["escalated"],
                "escalated_after": after["escalated"],
                "estimated_override_rate": after["estimated_override_rate"],
                "sample_size": sample,
            },
            "idempotency_key": _idem_key(knob, target, from_value, to_value),
        })
    return {"blocked_by": [], "patches": enriched, "skipped": skipped,
            "sample": sample}
