"""冲突仲裁判决核（Batch-1b-3 conflict_resolver）—— 纯函数，零 IO。

收敛 CRM `decision/conflict.js` G4 五策略的 **winner 选择 + 采用标记**判定算法；
断言存储（DDL/CRUD）、第 0 闸 produceDecision 接线、租户隔离留消费方。

⛔ 与 CRM 的分工差异（同保证、异形态）：CRM human_arbitration 经注入的
produceDecision 回调当场产决策行（回调=IO 边界）；基座纯函数化——调用方须先经
第 0 闸取得 decision_ref 再传入，缺 ref 即抛（保证不变：「人工裁决必挂真实决策行」，
且基座零回调零领域字面量）。
"""
from __future__ import annotations

from typing import Any, Iterable, List, Mapping, Optional, Sequence

from chiyu_kernel.contract.conflict_resolver import (
    CONFLICT_STRATEGIES, ConflictStrategyError,
)

__all__ = [
    "detect_conflicts", "mark_conflict", "pick_winner", "adopt_verdict",
    "resolve_conflict",
]

_DEFAULT_CREDIBILITY = 0.5


def detect_conflicts(assertions: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    """冲突现状检测（CRM `detectConflicts` 纯函数化）。

    :returns: ``{"has_conflict": 不同值数>1, "needs_review": 任一断言待裁决}``。
    """
    rows = list(assertions or ())
    distinct = {str(r.get("value")) for r in rows}
    return {"has_conflict": len(distinct) > 1,
            "needs_review": any(bool(r.get("needs_review")) for r in rows)}


def mark_conflict(assertions: Sequence[Mapping[str, Any]]) -> List[dict]:
    """新断言落位后的整组标记（CRM recordAssertion 后置步骤纯函数化）：

    同组存在**不同值** ⇒ 全组 needs_review=True（保留分歧、待裁决）；否则原样拷贝。
    恒返回新列表（禁原地改——输入可能是消费方存储层投影）。
    """
    rows = [dict(r) for r in (assertions or ())]
    values = {str(r.get("value")) for r in rows}
    if len(values) > 1:
        for r in rows:
            r["needs_review"] = True
    return rows


def pick_winner(assertions: Sequence[Mapping[str, Any]], strategy: str, *,
                sources: Optional[Iterable[Mapping[str, Any]]] = None) -> Optional[Mapping[str, Any]]:
    """按策略选 winner（CRM resolveConflict 的选择段纯函数化；不做采用标记）。

    - timestamp: created_at 最新者（同型可比性由调用方保证，TypeError 冒泡禁猜测；
      平局**先到者胜**——CRM reduce 严格 `>` 同效）；
    - source_priority: 优先级表注入（缺省 0；平局**先到者胜**，CRM reduce 同序）；
    - confidence_weighted: source_credibility 最高（缺省 0.5；平局先到者胜）；
    - merge: winner = ``{"value": [全部值]}``（needs_review 解除由 adopt_verdict 处理）；
    - human_arbitration: 与 confidence_weighted 同选（裁决依据由 decision_ref 承载）。

    :returns: 胜出断言（原行）；空断言组 ⇒ None。
    """
    if strategy not in CONFLICT_STRATEGIES:
        raise ConflictStrategyError(f"未知冲突策略：{strategy!r}")
    rows = list(assertions or ())
    if not rows:
        return None
    if strategy == "timestamp":
        return max(rows, key=lambda r: r.get("created_at"))
    if strategy == "merge":
        # 多值合并：无单一胜出行，winner = {"value": [全部值]}（CRM conflict.js merge 分支同口径）
        return {"value": [r.get("value") for r in rows]}
    if strategy == "source_priority":
        pri = {str(s.get("source_id")): s.get("priority") or 0
               for s in (sources or ())}
        winner = rows[0]
        for r in rows[1:]:
            if (pri.get(str(r.get("source_id")), 0)
                    > pri.get(str(winner.get("source_id")), 0)):
                winner = r          # 严格大于：平局保持先到（CRM pa>=pb ? a : b 同效）
        return winner
    # confidence_weighted / human_arbitration
    winner = rows[0]
    for r in rows[1:]:
        if ((r.get("source_credibility") if r.get("source_credibility") is not None
             else _DEFAULT_CREDIBILITY)
            > (winner.get("source_credibility")
               if winner.get("source_credibility") is not None
               else _DEFAULT_CREDIBILITY)):
            winner = r
    return winner


def adopt_verdict(assertions: Sequence[Mapping[str, Any]],
                  winner_value: Any) -> List[dict]:
    """采用标记（CRM adoptValue 纯函数化）：权威 valid=True + needs_review=False，
    其余 valid=False；**物理保留不删**（CONFLICT_INVARIANTS.adoption_is_marking_not_deletion）。"""
    out = []
    for r in (assertions or ()):
        row = dict(r)
        if str(row.get("value")) == str(winner_value):
            row["valid"] = True
            row["needs_review"] = False
        else:
            row["valid"] = False
        out.append(row)
    return out


def resolve_conflict(assertions: Sequence[Mapping[str, Any]], strategy: str, *,
                     sources: Optional[Iterable[Mapping[str, Any]]] = None,
                     decision_ref: Optional[str] = None) -> Mapping[str, Any]:
    """一步裁决：选 winner + 采用标记（零 IO；落库与事件发射留消费方）。

    ⛔ human_arbitration 必须携带第 0 闸产出的 ``decision_ref``（缺即抛）——
    「人工裁决必挂真实决策行」的结构保证（MUTANT 自证着力点）。
    """
    if strategy not in CONFLICT_STRATEGIES:
        raise ConflictStrategyError(f"未知冲突策略：{strategy!r}")
    if strategy == "human_arbitration" and not decision_ref:
        raise ConflictStrategyError(
            "human_arbitration 需要 decision_ref（须经决策第 0 闸产出，禁无决策依据改值）")
    rows = list(assertions or ())
    if not rows:
        return {"strategy": strategy, "winner": None, "decision_ref": decision_ref,
                "assertions": [], "has_conflict": False}
    winner = pick_winner(rows, strategy, sources=sources)
    winner_value = (winner or {}).get("value")
    if strategy == "merge":
        # 合并：保留全部值，needs_review 解除，valid 不动（CRM merge 分支同口径）；
        # winner 由 pick_winner 产出 = {"value": [全部值]}
        merged = [dict(r, needs_review=False) for r in rows]
        return {"strategy": strategy, "winner": winner,
                "decision_ref": decision_ref, "assertions": merged,
                "has_conflict": True}
    marked = adopt_verdict(rows, winner_value)
    det = detect_conflicts(marked)
    return {"strategy": strategy,
            "winner": {"source_id": (winner or {}).get("source_id"),
                       "value": winner_value},
            "decision_ref": decision_ref, "assertions": marked,
            "has_conflict": det["has_conflict"]}
