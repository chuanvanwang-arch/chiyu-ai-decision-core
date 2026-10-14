"""归因规则机制层（Batch-1b-3 attribution）—— R0-R3 分类树 + HITL 回写，纯函数零 IO。

收敛 CRM `decision/rootCauseClassifier.js`（T27 分类树，命中即止）+
`monitor/attribution.js`（applyHumanDisposition T29 七态升级 + applyOutcome +
computeEdgeCompliance）。⛔ 旋钮（knob）映射、边规格（serves_dimension 绑定）、
边类型闭集由消费方注入（域值留消费方）。

⛔ 防误判护栏（变异自证着力点）：edge_compliance 的 present/missing 投影不构成
「应连未连」证据——仅 required_missing 显式非空才判 E 缺；全 missing = 未查实，
喂分类器会误判 EDGE_MISSING。
"""
from __future__ import annotations

import copy
from typing import Any, Iterable, List, Mapping, Optional, Sequence

from chiyu_kernel.contract.attribution import (
    AttributionError, HUMAN_DISPOSITIONS, ROOT_CAUSE_LAYERS,
)

__all__ = [
    "classify_root_cause", "apply_human_disposition", "apply_outcome",
    "required_edges_for_dims", "compute_edge_compliance",
]

_LAYER_BY_CODE = dict(ROOT_CAUSE_LAYERS)

# 旧三态（applyHumanDisposition 重推的判据面；七态判定保留不覆盖）
_LEGACY_STATES = ("ok", "input_missing", "inference_bias")


def _l_missing(attribution: Optional[Mapping[str, Any]]) -> bool:
    fill = ((attribution or {}).get("required_fill") or {})
    missing = fill.get("missing") or []
    return len(missing) > 0


def _e_missing(attribution: Optional[Mapping[str, Any]]) -> bool:
    """E 缺 = 应连未连（required_missing）显式非空；无该字段 = 未提供证据 → 不判缺。"""
    ec = (attribution or {}).get("edge_compliance") or {}
    rm = ec.get("required_missing")
    return isinstance(rm, (list, tuple)) and len(rm) > 0


def _result(code: str, severity: str, evidence: List[str]) -> Mapping[str, Any]:
    return {"code": code, "layer": _LAYER_BY_CODE.get(code, "unknown"),
            "severity": severity, "evidence": evidence}


def classify_root_cause(*, feedback: Optional[Mapping[str, Any]] = None,
                        attribution: Optional[Mapping[str, Any]] = None,
                        particle_checks: Optional[Mapping[str, Any]] = None
                        ) -> Mapping[str, Any]:
    """R0-R3 分类树（命中即止，优先级不可重排）：

    R3 无反馈信号 ⇒ UNKNOWN/unknown（进人工归因队列）；
    R2 可用且非重大 ⇒ UNKNOWN/none（正向强化，无需干预）；
    R0/R1 不可用 ⇒ 粒子三检（field > info > stale）→ L 维缺 → E 边缺
      → 重大偏差 ⇒ DATA_QUALITY_PRECEDENT → 非重大 ⇒ NEED_DIM_ORDER。
    """
    fb = feedback or {}
    attr = attribution or {}
    pc = particle_checks or {}
    has_feedback = ("usable" in fb) or ("major_deviation" in fb)
    usable = fb.get("usable") is True
    major = fb.get("major_deviation") is True
    if not has_feedback:
        return _result("UNKNOWN", "unknown", ["无明确反馈信号"])
    if usable and not major:
        return _result("UNKNOWN", "none", ["业务可用且非重大偏差：正向强化，无根因干预"])
    if not usable:
        severity = "major" if major else "minor"
        if pc.get("field_mismatch"):
            return _result("FIELD_MISMATCH", severity, ["usable=false", "field_mismatch=true"])
        if pc.get("info_incomplete"):
            return _result("INFO_INCOMPLETE", severity, ["usable=false", "info_incomplete=true"])
        if pc.get("input_stale"):
            return _result("INPUT_STALE", severity, ["usable=false", "input_stale=true"])
        if _l_missing(attr):
            return _result("DIM_MISSING", severity, ["usable=false", "L 维度缺失"])
        if _e_missing(attr):
            return _result("EDGE_MISSING", severity, ["usable=false", "E 边缺失"])
        if major:
            return _result("DATA_QUALITY_PRECEDENT", severity,
                           ["usable=false", "major_deviation=true", "L+E 全齐但参考先例/标杆污染"])
        return _result("NEED_DIM_ORDER", severity, ["usable=false", "非重大", "疑似优化次序/补齐维度"])
    return _result("UNKNOWN", "unknown", ["反馈信号不足"])


def apply_human_disposition(attribution: Mapping[str, Any],
                            human_disposition: str) -> Mapping[str, Any]:
    """人工处置回写（CRM T29 升级版同序）：

    - 推翻（OVERRIDDEN/CORRECTED）：accuracy_signal=inaccurate；已七态判定**保留**
      （更精细不覆盖）；仍旧三态才按 R0 树重推（usable=false & major=true），
      且全齐仍推翻 = 推理偏差（DATA_QUALITY_PRECEDENT → inference_bias 兼容）。
    - 确认（CONFIRMED/APPROVED）：category=ok，accuracy_signal=accurate。
    恒深拷贝返回（禁原地改）。
    """
    if human_disposition not in HUMAN_DISPOSITIONS:
        raise AttributionError(
            f"非法人工处置：{human_disposition!r} ∉ HUMAN_DISPOSITIONS")
    a = copy.deepcopy(dict(attribution or {}))
    overturned = human_disposition in ("OVERRIDDEN", "CORRECTED")
    if overturned:
        if a.get("category") and a["category"] not in _LEGACY_STATES:
            a["accuracy_signal"] = "inaccurate"
            return a
        ec = a.get("edge_compliance") or {}
        rm = ec.get("required_missing")
        cls = classify_root_cause(
            feedback={"usable": False, "major_deviation": True},
            attribution={"required_fill": a.get("required_fill"),
                         "edge_compliance": (ec if isinstance(rm, (list, tuple)) and rm else {})},
            particle_checks=a.get("particle_checks") or {})
        # 全齐仍推翻 = 推理侧偏差（兼容旧态 inference_bias）
        a["category"] = ("inference_bias"
                         if cls["code"] == "DATA_QUALITY_PRECEDENT" else cls["code"])
        if cls["code"] != "UNKNOWN":
            a["root_cause"] = cls
    else:
        a["category"] = "ok"
    a["accuracy_signal"] = "inaccurate" if overturned else "accurate"
    return a


def apply_outcome(attribution: Mapping[str, Any],
                  outcome: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    """业务结果滞后回写（迟滞校验当初判得对不对；恒深拷贝返回）。"""
    a = copy.deepcopy(dict(attribution or {}))
    a["outcome_verified"] = dict(outcome) if outcome else None
    return a


def required_edges_for_dims(required_dims: Optional[Iterable[Any]],
                            spec: Iterable[Mapping[str, Any]]) -> Optional[List[str]]:
    """应连边推导（维度-边交叉校验；**边规格由消费方注入**）。

    :param required_dims: 场景必填维度（None ⇒ None：无应连边依据，不可判 E 缺）。
    :param spec: ``[{"edge_type": ..., "serves_dimension": dim | [dim, ...]}]``。
    """
    if required_dims is None:
        return None
    dims = [d for d in required_dims]
    dim_set = {d if isinstance(d, str) else (d or {}).get("dim")
               for d in dims if isinstance(d, str) or isinstance(d, Mapping)}
    dim_set.discard(None)
    if not dim_set:
        return []
    out = []
    for r in spec or ():
        served = r.get("serves_dimension")
        served_list = served if isinstance(served, (list, tuple)) else [served]
        if any(d in dim_set for d in served_list):
            out.append(r.get("edge_type"))
    return out


def compute_edge_compliance(actual_edges: Iterable[str], *,
                            required_edges: Optional[Iterable[str]] = None,
                            required_dims: Optional[Iterable[Any]] = None,
                            spec: Iterable[Mapping[str, Any]] = (),
                            known_edges: Optional[Iterable[str]] = None,
                            ) -> Mapping[str, Any]:
    """E1-E7 边合规三元组（实存/应存/缺；CRM computeEdgeCompliance 域无关化）。

    :param known_edges: 全边闭集（消费方注入，如 CRM EDGES）——仅用于 present/missing
        投影；缺省时投影只覆盖 actual。
    :returns: ``{edge: present|missing 投影, required_edges, required_missing, known}``；
        无应连边依据（required_edges 与 required_dims 均缺）⇒ known=False（E 缺不可判）。
    """
    actual = set(actual_edges or ())
    out: dict = {}
    for e in (known_edges if known_edges is not None else actual):
        out[str(e)] = "present" if str(e) in actual else "missing"
    req = (list(required_edges) if required_edges is not None
           else required_edges_for_dims(required_dims, spec))
    if isinstance(req, list):
        out["required_edges"] = req
        out["required_missing"] = [k for k in req if k not in actual]
        out["known"] = True
    else:
        out["required_edges"] = []
        out["required_missing"] = []
        out["known"] = False
    return out
