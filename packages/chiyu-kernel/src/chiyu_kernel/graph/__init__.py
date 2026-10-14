"""图存储抽象（WS8）—— 单源双视图的**只读派生**面。

⛔ 定位（与专利族 H 对应，中性化表述）
────────────────────────────────
图不是第二份存储。`particle` + `graph_edge` + `event` 三张表是**唯一事实源**，
本包只提供**只读派生视图**：

  1. 关系图谱视图 `relation_view()`  —— 受控边多跳遍历（一/二跳邻域 + 路径）
  2. 时间线叙事视图 `timeline_view()` —— 四源只读聚合，按决策时间基准排序
  3. 决策回链 `decision_backlinks()`  —— 审计可答「被谁引用 / 覆盖谁 / 源自哪条例外」

⛔ 禁另起可写图库：GraphStore 协议**不暴露任何写方法**。写边一律走
`chiyu_kernel.persist.write_decision_memory_net` / `ontology.OntologyGraph`，
否则「单源」即刻退化为「双写」，跨轨一致性无从校验。

⛔ 零领域字面量（内核铁律）
──────────────────────
受控谓词**一律由消费方注入的 `profile.predicates`** 提供（知识谓词 K 层 + 记忆谓词 M 层）。
请求了未受控谓词 ⇒ **抛**（有界谓词，与 `OntologyGraph.link` 同纪律），不静默返回空。

⛔ AGE 等价（不是 AGE 封装）
──────────────────────
本包提供**与图数据库等价的查询能力**（多跳遍历 / 邻域 / 路径 / 回链），
参考实现 `PgCteGraphStore` 走**纯 PostgreSQL 递归 CTE**，**零新扩展依赖**。
消费方若已部署 AGE：只要实现同一 `GraphStore` 协议即可替换后端，内核无需改动
（协议即接缝）。内核**不内置** AGE 适配器 —— 未接 AGE 服务的适配器无法验证，
ship 不可测代码即假绿，故留在消费方仓。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

# M 层记忆谓词名（决策回链审计的默认谓词；取自 L0 契约，非本包发明）
from chiyu_kernel.contract.particle import MEMORY_PREDICATES

# R9 方案 A 可消费通道（write_controlled_edges MCP 端点 builder；补 T48 §2.1 纸面缺口）
from chiyu_kernel.graph.mcp import (
    WRITE_CONTROLLED_EDGES_TOOL, build_graph_write_server,
    make_graph_write_profile, open_graph_write_store,
)

# ── 决策时间基准（专利族 H：COALESCE(decided_at, created_at)）───────────────
# 语义：决策**实际作出**的时刻优先；缺失时回落到记录创建时刻。
# ⛔ 不用 ts（那是写库时刻），否则「决策时间线」会退化成「落库时间线」。
DECISION_TIME_BASIS = "COALESCE(decided_at, created_at)"

# 遍历深度上限：防无界递归（CTE 自环 / 稠密图爆炸）
MAX_TRAVERSAL_HOPS = 3

# 四源（单源双视图的时间线来源；只读聚合，禁脑补缺源）
TIMELINE_SOURCES: Tuple[str, ...] = ("particle", "graph_edge", "event", "decision")


# ── 数据形状 ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class GraphEdge:
    """一条受控边（只读投影；字段与 `graph_edge` 表对齐）。"""

    from_id: str
    to_id: str
    predicate: str
    layer: str = "M"
    weight: Optional[float] = None
    relation_confidence: Optional[float] = None
    edge_source: str = "engine"
    ts: Any = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "GraphEdge":
        return cls(
            from_id=row["from_id"], to_id=row["to_id"],
            predicate=row["predicate"], layer=row.get("layer") or "M",
            weight=row.get("weight"),
            relation_confidence=row.get("relation_confidence"),
            edge_source=row.get("edge_source") or "engine",
            ts=row.get("ts"),
        )


@dataclass(frozen=True)
class TraversalResult:
    """多跳遍历结果（含路径，供图谱视图渲染与回链审计）。"""

    root: str
    nodes: Tuple[str, ...] = ()
    edges: Tuple[GraphEdge, ...] = ()
    paths: Tuple[Tuple[str, ...], ...] = ()
    truncated: bool = False          # 触及深度上限 ⇒ True（不谎称"已全量"）


# ── 协议（只读；禁写方法）───────────────────────────────────────────────────
class GraphStore(ABC):
    """图存储协议：**只读**派生。实现方须自带受控谓词集（来自 profile）。

    ⛔ 协议里**没有** `link()` / `add_edge()`：图可写 ⇒ 事实源分裂。
       AGE 等外部图库若要接入，实现本协议的这四个只读方法即可。
    """

    @abstractmethod
    def controlled(self) -> Tuple[str, ...]:
        """受控谓词清单（消费方注入；空 = 无受控边 ⇒ 遍历必为空，不伪造）。"""

    @abstractmethod
    def out_edges(self, node_id: str,
                  predicates: Optional[Iterable[str]] = None) -> Tuple[GraphEdge, ...]:
        """出边（默认限受控谓词）。"""

    @abstractmethod
    def in_edges(self, node_id: str,
                 predicates: Optional[Iterable[str]] = None) -> Tuple[GraphEdge, ...]:
        """入边（默认限受控谓词）。"""

    @abstractmethod
    def traverse(self, start: str, *, predicates: Optional[Iterable[str]] = None,
                 max_hops: int = 2,
                 direction: str = "out") -> TraversalResult:
        """多跳遍历（带环检测 + 深度上限）。"""

    # ── 共用实现：受控谓词闸 ────────────────────────────────────────
    def _resolve(self, predicates: Optional[Iterable[str]]) -> Tuple[str, ...]:
        """解析并校验谓词集：None ⇒ 全部受控；未知谓词 ⇒ 抛（有界，非空转）。"""
        controlled = set(self.controlled())
        if predicates is None:
            return tuple(sorted(controlled))
        asked = tuple(dict.fromkeys(predicates))
        unknown = [p for p in asked if p not in controlled]
        if unknown:
            raise ValueError(
                f"未受控谓词：{unknown}（须 ∈ profile.predicates；"
                f"当前受控={sorted(controlled)}）")
        return asked


# ── 实现 1：内存（语义参考实现，无 PG 亦可全绿）─────────────────────────────
class InMemoryGraphStore(GraphStore):
    """内存图存储：受控谓词由构造注入；**只读**（边经构造函数一次性载入）。

    用途：① 无 PG 环境下的语义基准；② 与其它后端做对拍（同输入须同结果）。
    """

    def __init__(self, predicates: Iterable[str],
                 edges: Iterable[GraphEdge] = ()) -> None:
        self._predicates: Tuple[str, ...] = tuple(sorted(set(predicates)))
        self._out: dict = {}
        self._in: dict = {}
        for e in edges:
            self._out.setdefault(e.from_id, []).append(e)
            self._in.setdefault(e.to_id, []).append(e)

    def controlled(self) -> Tuple[str, ...]:
        return self._predicates

    def out_edges(self, node_id: str,
                  predicates: Optional[Iterable[str]] = None) -> Tuple[GraphEdge, ...]:
        preds = set(self._resolve(predicates))
        return tuple(e for e in self._out.get(node_id, ()) if e.predicate in preds)

    def in_edges(self, node_id: str,
                 predicates: Optional[Iterable[str]] = None) -> Tuple[GraphEdge, ...]:
        preds = set(self._resolve(predicates))
        return tuple(e for e in self._in.get(node_id, ()) if e.predicate in preds)

    def traverse(self, start: str, *, predicates: Optional[Iterable[str]] = None,
                 max_hops: int = 2, direction: str = "out") -> TraversalResult:
        hops = _check_hops(max_hops)
        preds = set(self._resolve(predicates))
        edges_out: list = []
        paths: list = []
        seen: set = {start}
        truncated = False
        frontier: list = [(start, (start,))]

        for _ in range(hops):                      # 深度上限 = 硬闸，非软建议
            nxt: list = []
            for node, path in frontier:
                step = (self.out_edges(node, preds) if direction != "in"
                        else self.in_edges(node, preds))
                for e in step:
                    other = e.to_id if direction != "in" else e.from_id
                    edges_out.append(e)
                    if other in seen:              # 环检测：已访问不再展开
                        continue
                    seen.add(other)
                    new_path = path + (other,)
                    paths.append(new_path)
                    nxt.append((other, new_path))
            if not nxt:
                break
            if len(paths) and _ == hops - 1 and nxt:
                truncated = True                   # 触上限仍有 frontier ⇒ 未全量
            frontier = nxt
        return TraversalResult(
            root=start, nodes=tuple(sorted(seen)), edges=tuple(edges_out),
            paths=tuple(paths), truncated=truncated)


# ── 实现 2：纯 PG 递归 CTE（参考实现，零新扩展依赖）─────────────────────────
class PgCteGraphStore(GraphStore):
    """PostgreSQL 递归 CTE 图存储：**只读**，与 AGE 等价能力但零扩展依赖。

    构造参数：
        store       PgVectorStore（同一 schema、同一事实源）
        predicates  受控谓词（来自 profile.predicates；空 ⇒ 遍历恒空）
    """

    def __init__(self, store: Any, predicates: Iterable[str]) -> None:
        self.store = store
        self._predicates: Tuple[str, ...] = tuple(sorted(set(predicates)))

    def controlled(self) -> Tuple[str, ...]:
        return self._predicates

    # ── 读：一跳 ────────────────────────────────────────────────────
    def out_edges(self, node_id: str,
                  predicates: Optional[Iterable[str]] = None) -> Tuple[GraphEdge, ...]:
        return self._one_hop(node_id, predicates, direction="out")

    def in_edges(self, node_id: str,
                 predicates: Optional[Iterable[str]] = None) -> Tuple[GraphEdge, ...]:
        return self._one_hop(node_id, predicates, direction="in")

    def _one_hop(self, node_id: str, predicates: Optional[Iterable[str]],
                 *, direction: str) -> Tuple[GraphEdge, ...]:
        preds = self._resolve(predicates)
        if not preds:
            return ()                              # 无受控谓词 ⇒ 无受控边（不伪造）
        anchor = "from_id" if direction == "out" else "to_id"
        sql, params = self._edge_sql(anchor, preds)
        rows = self.store.query("graph_edge", where=f"{anchor} = %s AND predicate = ANY(%s)",
                                params=(node_id, list(preds)))
        return tuple(GraphEdge.from_row(r) for r in rows)

    # ── 读：多跳（递归 CTE，带环检测 + 深度上限）─────────────────────
    def traverse(self, start: str, *, predicates: Optional[Iterable[str]] = None,
                 max_hops: int = 2, direction: str = "out") -> TraversalResult:
        hops = _check_hops(max_hops)
        preds = self._resolve(predicates)
        if not preds:
            return TraversalResult(root=start, truncated=False)
        sql, params = self._cte_sql(preds, hops, direction)
        rows = self.store.execute_fetch(sql, (start,) + params, fetch_all=True) or []
        nodes: list = []
        edges: list = []
        paths: list = []
        seen: set = set()
        for r in rows:
            edges.append(GraphEdge.from_row(r))
            path = tuple(r.get("path") or ())
            if path:
                paths.append(path)
            for n in (r.get("from_id"), r.get("to_id")):
                if n and n not in seen:
                    seen.add(n)
                    nodes.append(n)
        truncated = any(int(r.get("depth") or 0) >= hops for r in rows)
        return TraversalResult(root=start, nodes=tuple(sorted(seen)),
                               edges=tuple(edges), paths=tuple(paths),
                               truncated=truncated)

    # ── SQL 构造（只读；禁 DELETE/DROP 由 store 侧硬拦）──────────────
    def _q(self, table: str) -> str:
        from chiyu_kernel.store.dsn import assert_safe_identifier
        assert_safe_identifier(table, what="table")
        return f"{self.store.schema}.{table}"

    def _edge_sql(self, anchor: str, preds: Sequence[str]) -> Tuple[str, tuple]:
        """一跳查询（保留供审计/对拍；实际走 store.query 以保证标识符安全）。"""
        return (f"SELECT * FROM {self._q('graph_edge')} "
                f"WHERE {anchor} = %s AND predicate = ANY(%s)", ())

    def _cte_sql(self, preds: Sequence[str], hops: int,
                 direction: str) -> Tuple[str, tuple]:
        """递归 CTE：深度上限 + 路径环检测，两者缺一即可能无限展开。"""
        edge = self._q("graph_edge")
        anchor_col, next_col = (("from_id", "to_id") if direction == "out"
                                else ("to_id", "from_id"))
        return (
            "WITH RECURSIVE walk AS ("
            f"  SELECT e.{anchor_col} AS from_id, e.to_id AS to_id, "
            f"         e.from_id AS src_id, e.predicate, e.layer, e.weight, "
            f"         e.relation_confidence, e.edge_source, e.ts, "
            "         1 AS depth, ARRAY[e.from_id, e.to_id] AS path "
            f"    FROM {edge} e "
            f"   WHERE e.{anchor_col} = %s AND e.predicate = ANY(%s) "
            "  UNION ALL "
            f"  SELECT e.from_id, e.to_id, e.from_id AS src_id, e.predicate, "
            f"         e.layer, e.weight, e.relation_confidence, e.edge_source, "
            "         e.ts, w.depth + 1, w.path || e.to_id "
            f"    FROM {edge} e JOIN walk w ON e.{anchor_col} = w.{next_col} "
            "   WHERE w.depth < %s AND NOT (e.to_id = ANY(w.path)) "
            "     AND e.predicate = ANY(%s)"
            ") SELECT from_id, to_id, predicate, layer, weight, "
            "         relation_confidence, edge_source, ts, depth, path FROM walk",
            (list(preds), hops, list(preds)))

def _check_hops(max_hops: int) -> int:
    """深度闸：越界即抛（防无界递归被当成"配置"绕过）。"""
    try:
        hops = int(max_hops)
    except (TypeError, ValueError):
        raise ValueError(f"max_hops 须为整数：{max_hops!r}")
    if hops < 1 or hops > MAX_TRAVERSAL_HOPS:
        raise ValueError(
            f"max_hops 须 ∈ [1, {MAX_TRAVERSAL_HOPS}]：{hops!r}"
            "（无界遍历会打爆 CTE，也违背受控边的有界原则）")
    return hops


# ── 视图 1：关系图谱（受控边 + 多跳 + 路径）─────────────────────────────────
def relation_view(store: GraphStore, root: str, *,
                  predicates: Optional[Iterable[str]] = None,
                  max_hops: int = 2,
                  direction: str = "out") -> dict:
    """关系图谱视图：只读派生，禁写。返回节点/边/路径 + `truncated` 诚实标记。"""
    res = store.traverse(root, predicates=predicates, max_hops=max_hops,
                         direction=direction)
    return {
        "root": res.root,
        "nodes": list(res.nodes),
        "edges": [
            {"from": e.from_id, "to": e.to_id, "predicate": e.predicate,
             "layer": e.layer, "weight": e.weight,
             "confidence": e.relation_confidence, "source": e.edge_source}
            for e in res.edges
        ],
        "paths": [list(p) for p in res.paths],
        "truncated": res.truncated,
        "controlled": list(store.controlled()),
    }


# ── 视图 2：时间线叙事（四源只读聚合，按决策时间基准排序）───────────────────
def timeline_view(*, particles: Iterable[Mapping[str, Any]] = (),
                  edges: Iterable[Mapping[str, Any]] = (),
                  events: Iterable[Mapping[str, Any]] = (),
                  decisions: Iterable[Mapping[str, Any]] = (),
                  subject_id: Optional[str] = None,
                  limit: int = 200) -> list:
    """时间线叙事视图：**四源只读聚合**，不写库、不脑补缺源。

    时间基准 = `DECISION_TIME_BASIS`（decided_at 优先，回落 created_at）。
    ⛔ 源缺失即该源无行 —— 不用别的源去填，否则叙事变成编造。
    """
    rows: list = []
    for src, items in (("particle", particles), ("graph_edge", edges),
                       ("event", events), ("decision", decisions)):
        for it in items:
            if subject_id is not None:
                sid = it.get("subject_id") or it.get("particle_id") or it.get("from_id")
                if sid != subject_id:
                    continue
            rows.append({
                "source": src,
                "time_basis": _time_basis(it),
                "subject": (it.get("subject_id") or it.get("particle_id")
                            or it.get("from_id")),
                "kind": it.get("event_type") or it.get("predicate") or it.get("type"),
                "ref": (it.get("decision_id") or it.get("id") or it.get("to_id")),
            })
    rows.sort(key=lambda r: (r["time_basis"] is None, r["time_basis"]),
              reverse=False)
    return rows[: int(limit)]


def _time_basis(row: Mapping[str, Any]) -> Any:
    """决策时间基准：decided_at 优先，回落 created_at/ts。"""
    return row.get("decided_at") or row.get("created_at") or row.get("ts")


# ── 视图 3：决策回链审计 ────────────────────────────────────────────────────
def decision_backlinks(store: GraphStore, decision_id: str, *,
                       reference_predicate: str = "REFERENCED_PRECEDENT",
                       override_predicate: str = "OVERRIDES",
                       exception_predicate: str = "DERIVED_FROM_EXCEPTION") -> dict:
    """决策回链：审计四问 —— 被谁引用 / 覆盖谁 / 源自哪条例外 / 是否受控。

    ⛔ 缺省谓词名来自 L0 契约 `MEMORY_PREDICATES`（非本包发明）；
       消费方可注入自己的受控谓词名覆盖。未受控 ⇒ `uncontrolled` 列出并抛。
    """
    controlled = set(store.controlled())
    asked = [reference_predicate, override_predicate, exception_predicate]
    uncontrolled = [p for p in asked if p not in controlled]
    if uncontrolled:
        raise ValueError(
            f"回链谓词未受控：{uncontrolled}（须 ∈ profile.predicates；"
            f"契约默认 M 层谓词={[p.predicate for p in MEMORY_PREDICATES]}）")

    referenced_by = tuple(e.from_id for e in store.in_edges(decision_id, [reference_predicate]))
    overrides = tuple(e.to_id for e in store.out_edges(decision_id, [override_predicate]))
    overridden_by = tuple(e.from_id for e in store.in_edges(decision_id, [override_predicate]))
    from_exception = tuple(e.to_id for e in store.out_edges(decision_id, [exception_predicate]))
    return {
        "decision_id": decision_id,
        "referenced_by": referenced_by,     # 谁把我当前例
        "overrides": overrides,             # 我覆盖了谁
        "overridden_by": overridden_by,     # 谁覆盖了我（失效链）
        "from_exception": from_exception,   # 我源自哪条例外
        "controlled": sorted(controlled),
    }


__all__ = [
    "DECISION_TIME_BASIS", "MAX_TRAVERSAL_HOPS", "TIMELINE_SOURCES",
    "GraphEdge", "TraversalResult", "GraphStore",
    "InMemoryGraphStore", "PgCteGraphStore",
    "relation_view", "timeline_view", "decision_backlinks",
    "WRITE_CONTROLLED_EDGES_TOOL", "build_graph_write_server",
    "make_graph_write_profile", "open_graph_write_store",
]
