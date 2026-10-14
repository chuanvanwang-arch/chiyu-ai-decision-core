"""A/B 实验判据与收口核（Batch-1b-4 ab_experiment）—— 纯函数，零 IO。

收敛 CRM `decision/routingReview.js`（三取二判据 judgeArms + 收口分流）与
`context/routingExperiment.js`（applyExperimentArm 轨道投影）的**判定算法**；
实验登记/查询（running 窗口）、createExperiment 补对照、处方落库留消费方。

⛔ 红线（CRM 设计 §0 同口径）：收口**绝不自动写配置**——significant 只产
PENDING 处方（人工批准 + 第 0 闸后才 apply）；insufficient 只算反向臂，
append-only 新开一期，禁删原实验行。
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from chiyu_kernel.contract.ab_experiment import (
    AB_ARMS, AB_O_EPS_DEFAULT, AB_Q_EPS_DEFAULT, AB_R_EPS_DEFAULT,
    AB_MIN_ARM_SAMPLE_DEFAULT, AbExperimentError,
)
from chiyu_kernel.contract.promotion import PRESCRIPTION_PENDING

__all__ = ["judge_arms", "apply_arm", "close_decision", "JUDGE_CFG_DEFAULTS"]

#: 出厂兜底判据（阈值可被消费方 config 覆盖；显式 None 禁把阈值静默置 0——判据失效）。
JUDGE_CFG_DEFAULTS: Dict[str, float] = {
    "q_eps": AB_Q_EPS_DEFAULT,
    "o_eps": AB_O_EPS_DEFAULT,
    "r_eps": AB_R_EPS_DEFAULT,
    "min_arm_sample": AB_MIN_ARM_SAMPLE_DEFAULT,
}


def _num(x: Any) -> Optional[float]:
    """数值化（bool 不算数；不可数值 ⇒ None，禁 NaN 参与比较）。"""
    if isinstance(x, bool):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None   # NaN ⇒ None


def judge_arms(on: Optional[Mapping[str, Any]], off: Optional[Mapping[str, Any]],
               cfg: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
    """三取二判据（CRM judgeArms 逐分支同口径；方向以 ΔQ 为准）。

    :param on/off: 臂聚合投影 ``{"n", "qbar", "success_rate", "override_rate"}``。
    :param cfg: 阈值覆盖（q_eps/o_eps/r_eps/min_arm_sample；缺省用出厂兜底）。
    :returns: ``{"verdict", "delta", "significant", "reason"[, "hits", "samples"]}``。
    """
    c = dict(JUDGE_CFG_DEFAULTS)
    for k, v in (cfg or {}).items():
        if k not in c:
            raise AbExperimentError(f"未知判据键：{k!r}")
        n = _num(v)
        if n is None:
            raise AbExperimentError(f"判据键 {k!r} 非数值（显式 None 禁把阈值静默置 0）")
        c[k] = n
    empty = {"verdict": "insufficient", "delta": None, "significant": None,
             "reason": "no-data"}
    if not on or not off:
        return {**empty, "reason": "missing-arm"}
    n_on, n_off = _num((on or {}).get("n")), _num((off or {}).get("n"))
    if (n_on is None or n_off is None
            or n_on < c["min_arm_sample"] or n_off < c["min_arm_sample"]):
        return {**empty, "reason": "insufficient_evidence",
                "samples": {"on": (on or {}).get("n"), "off": (off or {}).get("n"),
                            "need": c["min_arm_sample"]}}
    q_on, q_off = _num((on or {}).get("qbar")), _num((off or {}).get("qbar"))
    s_on, s_off = _num((on or {}).get("success_rate")), _num((off or {}).get("success_rate"))
    r_on, r_off = _num((on or {}).get("override_rate")), _num((off or {}).get("override_rate"))
    if None in (q_on, q_off, s_on, s_off, r_on, r_off):
        return {**empty, "reason": "no-data"}   # 指标缺失 ≠ 零差异（不硬凑）
    dq = q_on - q_off
    d_o = s_on - s_off
    d_r = r_on - r_off
    q_sig = abs(dq) >= c["q_eps"]
    o_sig = (((d_o > 0) - (d_o < 0)) == ((dq > 0) - (dq < 0))
             and dq != 0 and abs(d_o) >= c["o_eps"])
    r_sig = d_r <= -c["r_eps"]                  # 覆写率下降才有利
    significant = {"quality": q_sig, "outcome": o_sig, "override": r_sig}
    hits = sum(1 for v in significant.values() if v)
    if hits < 2:
        return {"verdict": "insufficient", "delta": {"dq": dq, "dO": d_o, "dR": d_r},
                "significant": significant, "reason": "not-significant", "hits": hits}
    verdict = "prefer_on" if dq > 0 else "prefer_off"
    return {"verdict": verdict, "delta": {"dq": dq, "dO": d_o, "dR": d_r},
            "significant": significant, "reason": "significant", "hits": hits}


def apply_arm(tracks: Optional[Sequence[Any]],
              exp: Optional[Mapping[str, Any]]) -> List[Any]:
    """轨道投影（CRM applyExperimentArm 纯函数化）：on=加入 / off=移除。

    ⛔ fail-open：实验信息缺 track / 非法 arm ⇒ 轨道原样返回（实验读失败 ≠ 装配失败）。
    恒返回新列表（禁原地改——输入可能是消费方装配上下文投影）。
    """
    base = list(tracks) if tracks else []
    if (not exp or not exp.get("track")
            or exp.get("arm") not in AB_ARMS):
        return base
    track = exp["track"]
    if exp["arm"] == "on":
        return base if track in base else base + [track]
    return [t for t in base if t != track]


def close_decision(exp: Mapping[str, Any], judge: Mapping[str, Any],
                   current_tracks: Optional[Sequence[Any]] = None,
                   ) -> Mapping[str, Any]:
    """收口分流（CRM 每日收口判定段纯函数化；登记/落库 IO 留消费方）。

    - insufficient ⇒ ``action="next_arm"``（排反向臂补对照；禁删原行）；
    - significant 且偏好臂 == baseline ⇒ ``action="maintain"``（配置已经是对的）；
    - significant 且偏好臂 != baseline ⇒ ``action="patch"`` 产 PENDING 处方——
      to_value = **完整轨道数组**（禁只写单值），from_value = 当前配置原值
      （禁猜回滚目标，``current_tracks`` 缺失即抛）。
    """
    if (not exp or exp.get("arm") not in AB_ARMS
            or not exp.get("track") or exp.get("baseline") not in AB_ARMS):
        raise AbExperimentError(
            f"实验投影非法：arm/track/baseline 必备且 arm/baseline ∈ {AB_ARMS}")
    verdict = (judge or {}).get("verdict")
    if verdict not in ("prefer_on", "prefer_off", "insufficient"):
        raise AbExperimentError(f"判据结论非法：{verdict!r} ∉ AB_VERDICTS")
    if verdict == "insufficient":
        return {"action": "next_arm",
                "next_arm": "off" if exp["arm"] == "on" else "on",
                "patch": None, "reason": (judge or {}).get("reason"),
                "samples": (judge or {}).get("samples")}
    preferred = "on" if verdict == "prefer_on" else "off"
    if preferred == exp["baseline"]:
        return {"action": "maintain", "preferred": preferred, "patch": None,
                "reason": "preferred_equals_baseline"}
    if current_tracks is None:
        raise AbExperimentError(
            "缺 current_tracks：to_value 必须是完整轨道数组、from_value 必须是"
            "当前配置原值（禁猜回滚目标）")
    base = list(current_tracks)
    return {"action": "patch", "preferred": preferred,
            "patch": {"status": PRESCRIPTION_PENDING,
                      "track": exp["track"], "preferred_arm": preferred,
                      "from_tracks": base,
                      "to_tracks": apply_arm(base, {"track": exp["track"],
                                                    "arm": preferred})},
            "reason": "significant"}
