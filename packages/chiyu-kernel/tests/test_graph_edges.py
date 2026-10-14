# -*- coding: utf-8 -*-
"""受控边写原语守卫（T47，R9 方案 A 实现稿）。

判据（T46 §2.2 三判据 + 闭集枚举面）：
1. 未受控谓词 / 非法 layer / 非法 edge_source ⇒ fail-fast 且**一条都不写**；
2. 悬空边拒绝（不隐式建顶点）：strict 抛；非 strict 跳过且 report.skipped 留痕；
3. 落库走唯一写入口 upsert_graph_edge（SQL 含 ON CONFLICT 幂等），且
   write_decision_memory_net 委托同一函数（同参数序，零行为变更）。
"""
import json
from typing import Any

import pytest

from chiyu_kernel.contract.particle import MEMORY_PREDICATES, PredicateSet
from chiyu_kernel.persist import EdgeWrite, write_controlled_edges
from chiyu_kernel.persist.graph_edges import upsert_graph_edge


class Profile:
    """最小 profile 桩：只暴露 predicates。"""

    def __init__(self) -> None:
        self.predicates = PredicateSet()   # memory=七边默认，knowledge 空


class FakeStore:
    """不连 PG 的 store 桩：记录 SQL/参数，可配置存在的粒子集合。"""

    def __init__(self, existing_particles: tuple = ()) -> None:
        self.schema = "public"
        self.existing = set(existing_particles)
        self.executes: list = []
        self.fetches: list = []

    def execute(self, sql: str, params: Any = None) -> None:
        self.executes.append((sql, params))

    def execute_fetch(self, sql: str, params: Any = None, **kw) -> list:
        self.fetches.append((sql, params, kw))
        ids = params[0]
        return [{"particle_id": pid} for pid in ids if pid in self.existing]


def _e(**kw) -> EdgeWrite:
    base = dict(from_id="dec-1", to_id="dec-2", predicate="OVERRIDES")
    base.update(kw)
    return EdgeWrite(**base)


def test_uncontrolled_predicate_rejects_all_and_writes_nothing():
    """判据 1a：未受控谓词 fail-fast，且先全量校验——一条都不落库。"""
    store = FakeStore(existing_particles=("dec-1", "dec-2"))
    with pytest.raises(ValueError, match="未受控谓词"):
        write_controlled_edges(
            store,
            [_e(), _e(predicate="GHOST_PREDICATE")],
            profile=Profile())
    assert store.executes == [], "fail-fast 必须发生在任何落库之前"


def test_layer_and_edge_source_closed_sets():
    """判据 1b：layer / edge_source 闭集枚举面同 fail-fast。"""
    store = FakeStore(existing_particles=("dec-1", "dec-2"))
    with pytest.raises(ValueError, match="layer"):
        write_controlled_edges(store, [_e(layer="X")], profile=Profile())
    with pytest.raises(ValueError, match="edge_source"):
        write_controlled_edges(store, [_e(edge_source="consumer")], profile=Profile())


def test_dangling_edge_strict_raises_loose_skips_with_trace():
    """判据 2：悬空边——strict 抛（不隐式建顶点）；非 strict 跳过 + skipped 留痕。"""
    store = FakeStore(existing_particles=("dec-1",))     # dec-2 不存在
    with pytest.raises(ValueError, match="悬空边拒绝"):
        write_controlled_edges(store, [_e()], profile=Profile())
    rep = write_controlled_edges(
        store, [_e(), _e(from_id="dec-1", to_id="dec-1", predicate="CAUSED")],
        profile=Profile(), strict=False)
    assert rep.written == 1 and len(rep.skipped) == 1
    assert rep.skipped[0][2] == "OVERRIDES" and "dec-2" in rep.skipped[0][3]


def test_upsert_sql_is_single_writer_with_conflict_clause():
    """判据 3a：落库 SQL 含 ON CONFLICT 幂等子句（重放更新不重行）。"""
    store = FakeStore(existing_particles=("dec-1", "dec-2"))
    rep = write_controlled_edges(store, [_e(weight=0.9)], profile=Profile())
    assert rep.written == 1
    sql, params = store.executes[0]
    assert "ON CONFLICT (from_id, to_id, predicate) DO UPDATE" in sql
    assert params[0] == "dec-1" and params[2] == "OVERRIDES"


def test_memory_net_writer_delegates_same_upsert():
    """判据 3b：write_decision_memory_net 与受控写共用同一落库函数（零行为变更）。"""
    src = open(
        "packages/chiyu-kernel/src/chiyu_kernel/persist/__init__.py",
        encoding="utf-8").read()
    assert "INSERT INTO" not in src or "graph_edge" not in src.split("INSERT INTO")[1].split('"')[0], \
        "persist/__init__.py 不得再内联 graph_edge SQL（唯一落库点已迁 graph_edges.py）"
    assert "upsert_graph_edge" in src, "记忆网写边必须委托 upsert_graph_edge"
    # 谓词闭集含七边（写入端与 L0 契约同源，防漂移）
    allowed = {p.predicate for p in PredicateSet().all()}
    assert allowed == {m.predicate for m in MEMORY_PREDICATES}


def test_upsert_graph_edge_params_order_unchanged():
    """判据 3c：upsert 参数序与原内联实现逐字节一致（守卫既有 FakeStore 判据不破）。"""
    store = FakeStore(existing_particles=("a", "b"))
    upsert_graph_edge(store, EdgeWrite(
        from_id="a", to_id="b", predicate="CAUSED", serves_dims=("d1",),
        edge_source="rule", evidence_ref="ev-1", weight=0.5, confidence=0.8))
    _, params = store.executes[0]
    assert params == ("a", "b", "CAUSED", "M", ["d1"], "rule", "ev-1",
                      None, None, 0.5, 0.8)
