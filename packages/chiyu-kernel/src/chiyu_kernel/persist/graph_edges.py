"""受控边写原语（R9 方案 A 实现稿，T47）—— `graph_edge` 的**唯一落库点**。

定位（承 T46 设计评估 §3 收口清单）：
- 本文件是全仓**唯一**允许出现 `INSERT INTO ... graph_edge` 的源文件
  （`tools/check_single_source_memory.py` 守卫白名单只登记此处）；
  `write_decision_memory_net` 经 `upsert_graph_edge` 共用同一落库函数——
  "单源"落到**文件粒度可机检**：一份 SQL，一个写入口。
- 写入端闭集 fail-fast：谓词须 ∈ `profile.predicates`（M 层七边 ∪ K 层消费方注入），
  layer ∈ `EDGE_LAYERS`，edge_source ∈ `EDGE_SOURCES`；未受控即抛，不静默。
- 悬空边拒绝：from_id / to_id 必须指向已存在的 particle（**不隐式建顶点**——
  顶点的唯一归宿是粒子写，这是与 AGE `MERGE` 隐式建点行为的本质分界，
  也是方案 A 与方案 B 的分界）。strict=True 抛；strict=False 跳过并留痕。

零行为变更承诺：`PgVectorStorePersister._store_write_edge` 委托
`upsert_graph_edge`，SQL 与参数序与原实现逐字节一致（既有守卫不改判据）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence, Tuple

from chiyu_kernel.contract.particle import EDGE_LAYERS, EDGE_SOURCES


def _q(schema: str, table: str) -> str:
    return f"{schema}.{table}"


@dataclass(frozen=True)
class EdgeWrite:
    """一条受控边（写前校验的载体；字段与 graph_edge 列一一对应）。"""

    from_id: str
    to_id: str
    predicate: str
    layer: str = "M"
    serves_dims: Sequence[str] = ()
    edge_source: str = "engine"
    evidence_ref: Optional[str] = None
    valid_from: Any = None
    valid_until: Any = None
    weight: Optional[float] = None
    confidence: Optional[float] = None


@dataclass(frozen=True)
class EdgeWriteReport:
    """受控边写结果（skipped 留痕：悬空边被跳过的显式记录，禁静默丢）。"""

    written: int
    skipped: Tuple[Tuple[str, str, str, str], ...] = ()


def upsert_graph_edge(store: Any, edge: EdgeWrite) -> None:
    """唯一 `graph_edge` 落库点：upsert（同 from/to/predicate 更新元数据不重行）。"""
    schema = store.schema
    store.execute(
        f"INSERT INTO {_q(schema, 'graph_edge')} "
        f"(from_id, to_id, predicate, layer, serves_dims, edge_source, "
        f"evidence_ref, valid_from, valid_until, weight, relation_confidence) "
        f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
        f"ON CONFLICT (from_id, to_id, predicate) DO UPDATE SET "
        f"serves_dims=EXCLUDED.serves_dims, edge_source=EXCLUDED.edge_source, "
        f"evidence_ref=EXCLUDED.evidence_ref, valid_from=EXCLUDED.valid_from, "
        f"valid_until=EXCLUDED.valid_until, weight=EXCLUDED.weight, "
        f"relation_confidence=EXCLUDED.relation_confidence",
        (edge.from_id, edge.to_id, edge.predicate, edge.layer,
         list(edge.serves_dims), edge.edge_source, edge.evidence_ref,
         edge.valid_from, edge.valid_until, edge.weight, edge.confidence))


def _validate_closed_sets(edge: EdgeWrite, allowed: frozenset) -> None:
    """闭集 fail-fast（谓词 / 层 / 来源三个枚举面，一次全查不逐个炸）。"""
    problems = []
    if edge.predicate not in allowed:
        problems.append(
            f"未受控谓词 {edge.predicate!r}（须 ∈ profile.predicates 的 M∪K 合并视图）")
    if edge.layer not in EDGE_LAYERS:
        problems.append(f"layer 须 ∈ {EDGE_LAYERS}：{edge.layer!r}")
    if edge.edge_source not in EDGE_SOURCES:
        problems.append(f"edge_source 须 ∈ {EDGE_SOURCES}：{edge.edge_source!r}")
    if problems:
        raise ValueError(f"受控边写校验失败（from={edge.from_id!r} "
                         f"to={edge.to_id!r}）：" + "；".join(problems))


def write_controlled_edges(store: Any, edges: Sequence[EdgeWrite], *,
                           profile: Any, strict: bool = True) -> EdgeWriteReport:
    """受控边写入口（方案 A 的 sanctioned 面）。

    判据（T46 §2.2 三判据）：
    1. 谓词 ∈ profile.predicates（M∪K 合并视图）+ layer / edge_source 闭集，
       任一违规 **一条都不写**（先全量校验再落库，fail-fast 不半途）；
    2. from_id / to_id 必须指向已存在的 particle（不隐式建顶点）：
       strict=True 悬空即抛；strict=False 跳过悬空边并在 report.skipped 留痕；
    3. 落库走 `upsert_graph_edge`（本文件内唯一 SQL，重放幂等）。
    """
    allowed = frozenset(p.predicate for p in profile.predicates.all())
    for e in edges:                                    # 判据 1：先全量校验
        _validate_closed_sets(e, allowed)

    ids = sorted({e.from_id for e in edges} | {e.to_id for e in edges})
    rows = store.execute_fetch(
        f"SELECT particle_id FROM {_q(store.schema, 'particle')} "
        f"WHERE particle_id = ANY(%s)", (ids,), fetch_all=True) or []
    existing = {r["particle_id"] for r in rows}

    skipped: list = []
    writable: list = []
    for e in edges:                                    # 判据 2：悬空边裁定
        missing = [pid for pid in (e.from_id, e.to_id) if pid not in existing]
        if missing:
            if strict:
                raise ValueError(
                    f"悬空边拒绝（不隐式建顶点）：{e.from_id!r}→{e.to_id!r} "
                    f"谓词 {e.predicate!r}，缺失粒子 {missing}；"
                    f"顶点须经粒子写显式落库后再建边")
            skipped.append((e.from_id, e.to_id, e.predicate,
                            f"悬空：缺失粒子 {missing}"))
            continue
        writable.append(e)

    for e in writable:                                 # 判据 3：唯一落库点
        upsert_graph_edge(store, e)
    return EdgeWriteReport(written=len(writable), skipped=tuple(skipped))


__all__ = [
    "EdgeWrite", "EdgeWriteReport", "upsert_graph_edge", "write_controlled_edges",
]
