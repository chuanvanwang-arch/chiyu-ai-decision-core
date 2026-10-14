"""反假绿探针（WS9 核心交付）—— 证明「真落库 / 真物化 / 真派生」，不是「表有行」。

⛔ 为什么需要这一层（ai-capability-audit 铁律）：
   「表里有行 / count>0 / 没报错」是**恒绿**判据 —— 即使机制整个失效也照样绿。
   本文件的每条探针都是**可证伪**的：机制失效 ⇒ 必 FAIL。收口时须做变异自证
   （故意破坏机制 ⇒ 探针转红），否则探针本身也是假绿。

探针设计原则：
  - **预期由调用方声明，探针只做比对** —— 不重算内核逻辑，避免「两套语义对不上」。
  - 每条探针返回 `ProbeResult(ok, reason, evidence)`，evidence 里给出可核对的细节。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Set, Tuple

from chiyu_kernel.api import content_hash

from .app import ConsumerApp, relations, run_decision

# persister 计算 content_hash 所覆盖的字段（与内核 persist 层一致，改一侧须改另一侧）
_HASH_KEYS: Tuple[str, ...] = (
    "confidence", "redline_hit", "redline_reasons", "autonomous",
    "rubric_missing", "elements_missing", "concept_refs", "disposition",
    "policy_version",
)

# 闭环八边（ai-feedback-loop）：K→D / M→D / D→M / D→K / 结果→D / 校准 / 参数生效 / M→K
CLOSED_LOOP_EDGES: Tuple[str, ...] = (
    "K→D", "M→D", "D→M", "D→K", "结果→D", "校准", "参数生效", "M→K",
)
# 底座在本样板中**保证接通**的边（缺失即为回归）；其余如实标注未接线，不脑补
REQUIRED_CLOSED_LOOP_EDGES: Tuple[str, ...] = ("K→D", "M→D", "D→M")


@dataclass(frozen=True)
class ProbeResult:
    """探针结果。⛔ `evidence` 必须给出可核对细节（否则无法区分「真绿」与「空转」）。"""

    name: str
    ok: bool
    reason: str = ""
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "reason": self.reason,
                "evidence": self.evidence}


# ── P1 决策真落库（不是「有行」）──────────────────────────────────────────────
def probe_decision_really_persisted(app: ConsumerApp, decision_id: str, *,
                                    expected: Mapping[str, Any]) -> ProbeResult:
    """判据：事件行存在 ∧ 关键字段逐项相符 ∧ content_hash 与内容重算一致。

    「有行」不证明落对了 —— 字段被写错、哈希与内容不符，都是真缺陷。
    """
    row = app.store.events.get(decision_id)
    if row is None:
        return ProbeResult("decision_really_persisted", False,
                           f"决策 {decision_id!r} 未落库（无事件行）",
                           {"known": sorted(app.store.events)})

    mismatched = {k: {"expected": v, "actual": row.get(k)}
                  for k, v in expected.items() if row.get(k) != v}
    recomputed = content_hash({k: row.get(k) for k in _HASH_KEYS})
    hash_ok = recomputed == row.get("content_hash")
    if mismatched or not hash_ok:
        return ProbeResult(
            "decision_really_persisted", False,
            "落库内容与预期不符" if mismatched else "content_hash 与内容不一致（伪写）",
            {"mismatched": mismatched, "stored_hash": row.get("content_hash"),
             "recomputed_hash": recomputed})
    return ProbeResult(
        "decision_really_persisted", True, "字段相符且内容哈希自洽",
        {"decision_id": decision_id, "fields": sorted(expected),
         "content_hash": recomputed})


# ── P2 记忆真物化（不是「边数 > 0」）──────────────────────────────────────────
def probe_memory_really_materialized(app: ConsumerApp, decision_id: str, *,
                                     expected_triples: Set[Tuple[str, str, str]]
                                     ) -> ProbeResult:
    """判据：以该决策为起点的边集**恰等于**预期，且全部 `edge_source='engine'`。

    ⛔ 「边数>0」恒绿：写错边、漏写边、边来源被改成人工，都照样绿。故逐条比对。
    """
    mine = [e for e in app.store.edges if e["from_id"] == decision_id]
    found = {(e["from_id"], e["to_id"], e["predicate"]) for e in mine}
    missing = sorted(expected_triples - found)
    unexpected = sorted(found - expected_triples)
    non_engine = sorted({(e["to_id"], e["predicate"]) for e in mine
                         if e["edge_source"] != "engine"})
    if missing or unexpected or non_engine:
        return ProbeResult(
            "memory_really_materialized", False,
            "记忆网边集与预期不符",
            {"missing": missing, "unexpected": unexpected,
             "non_engine_source": non_engine})
    return ProbeResult(
        "memory_really_materialized", True,
        f"{len(found)} 条受控记忆边已物化且来源为 engine",
        {"edges": sorted(found), "count": len(found)})


# ── P3 图真派生（不是第二份存储）──────────────────────────────────────────────
def probe_graph_is_derived(app: ConsumerApp, decision_id: str) -> ProbeResult:
    """判据：关系视图中的每个节点与每条边都能在 store 事实里找到（无幻影）。

    ⛔ H 单源双视图：图是派生面。视图里出现事实源没有的东西 ⇒ 事实源已分裂。
    """
    if app.graph is None:
        return ProbeResult("graph_is_derived", False, "派生图未同步", {})
    view = relations(app, decision_id, max_hops=2)

    fact_nodes = set(app.store.particles)
    for e in app.store.edges:
        fact_nodes.add(e["from_id"])
        fact_nodes.add(e["to_id"])
    fact_triples = app.store.edge_triples()

    view_nodes = set(view["nodes"])
    view_triples = {(e["from"], e["to"], e["predicate"]) for e in view["edges"]}
    phantom_nodes = sorted(view_nodes - fact_nodes - {decision_id})
    phantom_edges = sorted(view_triples - fact_triples)

    # ⛔ 只看可达子图会漏掉「挂在事实节点上但没被本次遍历走到」的幻影边 ⇒
    #    逐事实节点比对出入边（只读协议允许的最大可枚举面）。
    #    边界：完全游离于事实节点之外的边，只读协议无从枚举 —— 不谎称全覆盖。
    for node in sorted(fact_nodes | {decision_id}):
        for e in tuple(app.graph.out_edges(node)) + tuple(app.graph.in_edges(node)):
            triple = (e.from_id, e.to_id, e.predicate)
            if triple not in fact_triples and triple not in phantom_edges:
                phantom_edges.append(triple)
            if e.to_id not in fact_nodes and e.to_id not in phantom_nodes:
                phantom_nodes.append(e.to_id)
            if e.from_id not in fact_nodes and e.from_id not in phantom_nodes:
                phantom_nodes.append(e.from_id)
    phantom_edges = sorted(set(phantom_edges))
    phantom_nodes = sorted(set(phantom_nodes))

    if phantom_nodes or phantom_edges:
        return ProbeResult(
            "graph_is_derived", False,
            "视图出现事实源中不存在的节点/边 ⇒ 图已变成第二份存储",
            {"phantom_nodes": phantom_nodes, "phantom_edges": phantom_edges})
    return ProbeResult(
        "graph_is_derived", True,
        f"视图 {len(view_nodes)} 节点 / {len(view_triples)} 边全部可回溯到事实源",
        {"nodes": sorted(view_nodes), "edges": sorted(view_triples),
         "truncated": view["truncated"]})


# ── P4 闭环连通性（八边逐条报状态，未接线如实标注）────────────────────────────
def probe_closed_loop(app: ConsumerApp, decision_id: str, *,
                      references: Optional[Mapping[str, Sequence[str]]] = None,
                      concept_refs: Sequence[str] = ()) -> ProbeResult:
    """闭环八边：接通的须有证据，未接线的如实标 `not_wired`（禁止脑补为已通）。

    ⛔ 本项目铁律：不得把「未接线」说成「已跑通全链路」。
    """
    refs = dict(references or {})
    row = app.store.events.get(decision_id) or {}
    out_edges = [e for e in app.store.edges if e["from_id"] == decision_id]
    has_outcome = any(k.startswith(f"{decision_id}:outcome")
                      for k in app.store.events)

    report = {
        "K→D": (bool(row.get("concept_refs")),
                f"决策已携带知识引用 {list(concept_refs)}" if concept_refs
                else "决策未携带知识引用（concept_refs 为空）"),
        "M→D": (any(refs.values()),
                f"决策已注入记忆供给（{sum(len(v or ()) for v in refs.values())} 个目标）"
                if any(refs.values()) else "未提供记忆供给"),
        "D→M": (bool(out_edges),
                f"决策已回写 {len(out_edges)} 条记忆边" if out_edges
                else "决策未回写记忆边"),
        "结果→D": (has_outcome,
                   "已回填执行结果" if has_outcome
                   else "未回填执行结果（调 record_outcome 回填）"),
        "D→K": (False, "not_wired：底座未内置知识回流通道，需消费方自建"),
        "校准": (False, "not_wired：底座 evolution 旋钮可承载，本样板未接线"),
        "参数生效": (False, "not_wired：随校准通道一并接线"),
        "M→K": (False, "not_wired：底座无内置记忆提升通道"),
    }
    broken = [e for e in REQUIRED_CLOSED_LOOP_EDGES if not report[e][0]]
    evidence = {k: {"connected": v[0], "detail": v[1]} for k, v in report.items()}
    if broken:
        return ProbeResult("closed_loop", False,
                           f"底座保证的闭环边未接通：{broken}", evidence)
    return ProbeResult(
        "closed_loop", True,
        f"保证边 {list(REQUIRED_CLOSED_LOOP_EDGES)} 已接通；"
        f"未接线边 {[k for k, v in report.items() if not v[0]]} 如实标注",
        evidence)


# ── P5 硬约束先于置信度（红线命中即挡落库）────────────────────────────────────
def probe_redline_blocks_persist(app: ConsumerApp, *, decision_id: str,
                                 rubric_scores: Mapping[str, float],
                                 elements: Mapping[str, object],
                                 redline_items: Tuple[str, ...]) -> ProbeResult:
    """判据：满分 + 红线命中 ⇒ 仍不落库（`persisted=False` 且有驳回留痕）。

    ⛔ A 红线优先 / 金律26：高置信度不豁免硬约束。若红线被置信度压过 ⇒ 必 FAIL。
    """
    text = " ".join(redline_items)
    res = run_decision(
        app, decision_id=decision_id, text=text,
        rubric_scores=rubric_scores, elements=elements,
        redline_items=redline_items)
    persisted = bool(getattr(res, "persisted", False))
    rejected = getattr(res, "approval_rejected", None)
    row_exists = decision_id in app.store.events
    if persisted or row_exists or not rejected:
        return ProbeResult(
            "redline_blocks_persist", False,
            "红线命中却仍落库/无驳回留痕 ⇒ 硬约束被置信度压过",
            {"persisted": persisted, "row_exists": row_exists,
             "approval_rejected": rejected,
             "confidence": getattr(res, "confidence", None)})
    return ProbeResult(
        "redline_blocks_persist", True,
        f"红线命中即挂起（置信度 {getattr(res, 'confidence', None):.3f} 未豁免）",
        {"approval_rejected": rejected, "audit": [a[0] for a in app.audit]})


__all__ = [
    "ProbeResult", "CLOSED_LOOP_EDGES", "REQUIRED_CLOSED_LOOP_EDGES",
    "probe_decision_really_persisted", "probe_memory_really_materialized",
    "probe_graph_is_derived", "probe_closed_loop",
    "probe_redline_blocks_persist",
]
