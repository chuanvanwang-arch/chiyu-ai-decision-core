"""决策可审计性「四问」评分核（Batch-1b-3 audit_4q）—— 纯函数，零 IO、零查询。

收敛 CRM `decision/auditability.js` computeAudit4q 的**评分判据**（单一事实源，
per-decision 端点 / 平台聚合 / SLA 物化 / 趋势闭环四者共用同一口径）。
⛔ 图/溯源/冲突/影响证据由消费方注入（trace/impact/prov/snapshot 查询留消费方）；
判据算法与口径常量在基座（评分口径永不漂移）。

⛔ 反假绿判据（变异自证着力点）：
  Q2 空链不可自称 OK（verifyChain 对空集天然 OK 的假绿，显式要求证据>0 且覆盖
  context_supply）；生命周期事件条目（entry_type 以 "event:" 形态前缀）不入证据口径；
  Q3 零实体扫描 = 无证据 ⇒ warn 非 pass；Q4 孤立决策 warn 不 fail；空窗口 pct=null。
"""
from __future__ import annotations

from typing import Any, Iterable, List, Mapping, Optional, Sequence

from chiyu_kernel.contract.audit_4q import (
    AUDIT4Q_KEYS, Audit4QError, Q1_MIN_SUPPLIED_DIMS,
)

__all__ = ["evaluate_4q", "aggregate_4q"]

_EVENT_PREFIX = "event:"


def evaluate_4q(*, supplied_dims: Optional[int],
                chain_status: str,
                prov_entries: Sequence[Mapping[str, Any]] = (),
                entities_scanned: int = 0,
                unresolved_conflicts: int = 0,
                downstream_count: int = 0,
                impact_error: Optional[str] = None,
                ) -> Mapping[str, Any]:
    """单决策四问评分（证据注入；返回 health + 逐问明细）。

    :param supplied_dims: 上下文快照的维度供给数（None = 无可用快照/被篡改 ⇒ warn）。
    :param chain_status: 溯源链状态（∈ contract.audit.CHAIN_VERIFY_STATUSES 口径：
        ok/tampered/forked/broken_head；消费方自有词表须先映射）。
    :param prov_entries: 溯源条目投影（``{"entry_type": ...}`` 最小形）。
    """
    # Q1：维度供给达标才 pass；无证据 ⇒ warn（不拿 rationale 顶替）
    q1 = "pass" if (supplied_dims is not None
                    and supplied_dims >= Q1_MIN_SUPPLIED_DIMS) else "warn"
    # Q2：链完整 且 证据条目>0 且覆盖 context_supply（空链不可自称 OK）
    evidence = [e for e in (prov_entries or ())
                if not str((e or {}).get("entry_type") or "").startswith(_EVENT_PREFIX)]
    events = len(list(prov_entries or ())) - len(evidence)
    supplies = [e for e in evidence if (e or {}).get("entry_type") == "context_supply"]
    if chain_status == "tampered":
        q2 = "fail"
    elif chain_status == "ok" and evidence and supplies:
        q2 = "pass"
    else:
        q2 = "warn"
    # Q3：有未裁决冲突 ⇒ warn；无冲突但零实体扫描 = 无证据 ⇒ warn；否则 pass
    if unresolved_conflicts > 0:
        q3 = "warn"
    elif entities_scanned > 0:
        q3 = "pass"
    else:
        q3 = "warn"
    # Q4：影响计算失败 ⇒ fail；有下游 ⇒ pass；孤立/叶子 ⇒ warn（合法但需关注）
    q4 = "fail" if impact_error else ("pass" if downstream_count > 0 else "warn")
    statuses = {"Q1": q1, "Q2": q2, "Q3": q3, "Q4": q4}
    score = sum(1 for v in statuses.values() if v == "pass")
    return {
        "health": {"score": score, "total": 4, "statuses": statuses,
                   "needs_review_count": unresolved_conflicts},
        "questions": {
            "Q1": {"status": q1, "supplied_dims": supplied_dims,
                   "min_supplied_dims": Q1_MIN_SUPPLIED_DIMS},
            "Q2": {"status": q2, "chain_status": chain_status,
                   "entries": len(evidence), "event_entries": events,
                   "context_supply_entries": len(supplies)},
            "Q3": {"status": q3, "entities_scanned": entities_scanned,
                   "unresolved_count": unresolved_conflicts},
            "Q4": {"status": q4, "downstream_count": downstream_count,
                   "impact_error": impact_error},
        },
    }


def aggregate_4q(results: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    """平台级聚合（CRM aggregateAuditability 的纯函数化；窗口选择/并发/超时留消费方）。

    超时/异常条目由调用方以 None 占位传入 ⇒ 跳过不计入 scored（诚实暴露未评，
    不掩盖为绿）。空窗口 auditability_pct=null（不报 0 充数）。
    """
    per_status = {q: {"pass": 0, "warn": 0, "fail": 0} for q in AUDIT4Q_KEYS}
    full = with_conflict = tampered = 0
    score_sum = 0
    decisions: List[Mapping[str, Any]] = []
    for r in results or ():
        if r is None:
            continue
        h = r.get("health") or {}
        statuses = h.get("statuses") or {}
        for q in AUDIT4Q_KEYS:
            s = statuses.get(q)
            if s not in ("pass", "warn", "fail"):
                raise Audit4QError(f"非法四问状态：{q}={s!r}")
            per_status[q][s] += 1
        score = h.get("score")
        if not isinstance(score, int) or not 0 <= score <= 4:
            raise Audit4QError(f"非法四问得分：{score!r}（须 0..4）")
        if score == 4:
            full += 1
        if (h.get("needs_review_count") or 0) > 0:
            with_conflict += 1
        if statuses.get("Q2") == "fail":
            tampered += 1
        score_sum += score
        decisions.append({"decision_id": r.get("decision_id"),
                          "score": score, "statuses": statuses})
    scored = len(decisions)
    pct = round((score_sum / scored / 4) * 100) if scored else None
    return {"scored": scored, "full": full, "with_conflict": with_conflict,
            "tampered": tampered, "auditability_pct": pct,
            "per_status": per_status, "decisions": decisions}
