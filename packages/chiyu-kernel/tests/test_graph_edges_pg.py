# -*- coding: utf-8 -*-
"""受控边写真库 E2E（T47，R9 方案 A 实现稿）—— `@pytest.mark.pg`。

红线双保险与 test_pg_e2e.py 同款：DSN 本文件硬编码本地便携 PG（chiyu_test），
导入期断言 host，无本地 PG 自动 skip。

判据（写读同表闭环——方案 A 的核心可行性证明）：
① 受控边写 → 真库 graph_edge → PgCteGraphStore 只读派生读回（写/读同表闭环）；
② upsert 幂等：同 from/to/predicate 重写更新元数据不重行；
③ 悬空边：strict 真库抛；非 strict 跳过留痕且无行落库；
④ 未受控谓词 fail-fast：一条不落。
"""
from __future__ import annotations

import os
import sys
import uuid
from typing import Any, Dict

import psycopg2
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DEC_SRC = os.path.join(_ROOT, "packages", "chiyu-decision", "src")
if os.path.isdir(_DEC_SRC) and _DEC_SRC not in sys.path:
    sys.path.append(_DEC_SRC)

from chiyu_decision.api import run_spine  # noqa: E402
from chiyu_kernel.approval import RedlinePriorityGate  # noqa: E402
from chiyu_kernel.contract.decision import EIGHT_ELEMENTS, RUBRIC_KEYS  # noqa: E402
from chiyu_kernel.domain import profile_from_dict  # noqa: E402
from chiyu_kernel.graph import PgCteGraphStore, relation_view  # noqa: E402
from chiyu_kernel.persist import (  # noqa: E402
    EdgeWrite, PgVectorStorePersister, write_controlled_edges,
)
from chiyu_kernel.store import PgVectorStore, drop_test_schema, ensure_schema  # noqa: E402
from chiyu_kernel.store.dsn import parse_dsn  # noqa: E402

PG_DSN = "postgresql://chiyu@127.0.0.1:5432/chiyu_test"
assert parse_dsn(PG_DSN).get("host") in ("127.0.0.1", "localhost"), (
    "E2E DSN 红线被破坏：真库用例只许连本地便携 PG")


def _pg_available() -> bool:
    try:
        c = psycopg2.connect(PG_DSN, connect_timeout=2)
        c.close()
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.pg,
    pytest.mark.skipif(not _pg_available(),
                       reason="本地便携 PG chiyu_test 未运行（判据允许跳过）"),
]

_PROFILE_DICT: Dict[str, Any] = {
    "domain": "graph-edges-demo",
    "particle_types": {"names": ["unstructured_asset", "entity", "decision",
                                 "memory", "knowledge", "document"]},
    "predicates": {"knowledge": []},
    "autonomous_threshold": 0.79,
}

REFERENCES: Dict[str, tuple] = {
    "subject": (), "precedents": (), "exceptions": (), "frames": (),
    "causes": (), "influencers": (), "overrides": (),
}


@pytest.fixture(scope="module")
def pg():
    os.environ["CHIYU_DB_DSN_TEST"] = PG_DSN
    os.environ["CHIYU_TEST"] = "1"
    schema = "t_ge_e2e_" + uuid.uuid4().hex[:8]
    os.environ["CHIYU_DB_SCHEMA"] = schema
    profile = profile_from_dict(_PROFILE_DICT)
    report = ensure_schema(profile=profile, testing=True, schema=schema)
    assert report["schema"] == schema and not report.get("skipped"), report
    store = PgVectorStore(profile, schema=schema)
    yield {"store": store, "profile": profile, "schema": schema}
    drop_test_schema(schema)


def _persist_decision(store, profile, decision_id: str) -> None:
    """真 run_spine → 真 persister 落一个决策粒子（受控边的顶点前提）。"""
    persister = PgVectorStorePersister(store, profile, materialize=False)
    run_spine(
        context={"text": "普通事项", "decision_id": decision_id},
        profile=profile,
        rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
        elements={e: "x" for e in EIGHT_ELEMENTS},
        redline_items=(),
        approval_gate=RedlinePriorityGate(),
        persister=lambda r: persister.persist(
            r, subject_id=decision_id + "-subj", references=REFERENCES) or True,
    )


def _edge_count(pg, from_id: str, predicate: str = "OVERRIDES") -> int:
    row = pg["store"].execute_fetch(
        f"SELECT count(*)::int AS n FROM {pg['schema']}.graph_edge "
        "WHERE from_id = %s AND predicate = %s", (from_id, predicate))
    return row["n"]


def test_pg_controlled_edge_write_read_loop(pg) -> None:
    """判据①：受控写 → graph_edge → 只读派生视图读回（同表闭环）。"""
    store, profile = pg["store"], pg["profile"]
    _persist_decision(store, profile, "ge-a")
    _persist_decision(store, profile, "ge-b")

    rep = write_controlled_edges(store, [EdgeWrite(
        from_id="ge-a", to_id="ge-b", predicate="OVERRIDES",
        edge_source="rule", weight=0.9)], profile=profile)
    assert rep.written == 1 and rep.skipped == ()

    graph = PgCteGraphStore(store, predicates=("OVERRIDES",))
    view = relation_view(graph, "ge-a", max_hops=2, direction="out")
    got = {(e["from"], e["to"], e["predicate"]) for e in view["edges"]}
    assert ("ge-a", "ge-b", "OVERRIDES") in got, (
        f"受控边须经只读派生视图读回（写读同表闭环）：{got}")


def test_pg_upsert_idempotent(pg) -> None:
    """判据②：同 from/to/predicate 重写 → 不重行，元数据更新生效。"""
    store = pg["store"]
    write_controlled_edges(store, [EdgeWrite(
        from_id="ge-a", to_id="ge-b", predicate="OVERRIDES",
        edge_source="rule", weight=0.7)], profile=pg["profile"])
    assert _edge_count(pg, "ge-a") == 1, "upsert 不得产生重复行"
    row = store.execute_fetch(
        f"SELECT weight FROM {pg['schema']}.graph_edge "
        "WHERE from_id = %s AND to_id = %s AND predicate = %s",
        ("ge-a", "ge-b", "OVERRIDES"))
    assert row is not None and row["weight"] == 0.7, "重写必须更新元数据"


def test_pg_dangling_edge_rejected(pg) -> None:
    """判据③：悬空边 strict 抛（不隐式建顶点）；非 strict 跳过留痕无落库。"""
    store, profile = pg["store"], pg["profile"]
    before = _edge_count(pg, "ge-a")
    with pytest.raises(ValueError, match="悬空边拒绝"):
        write_controlled_edges(store, [EdgeWrite(
            from_id="ge-a", to_id="ghost-particle", predicate="CAUSED")],
            profile=profile)
    rep = write_controlled_edges(store, [EdgeWrite(
        from_id="ge-a", to_id="ghost-particle", predicate="CAUSED")],
        profile=profile, strict=False)
    assert rep.written == 0 and len(rep.skipped) == 1
    assert _edge_count(pg, "ge-a") == before, "悬空边被跳过后不得有行落库"


def test_pg_uncontrolled_predicate_fail_fast(pg) -> None:
    """判据④：未受控谓词 fail-fast，真库零落库。"""
    store, profile = pg["store"], pg["profile"]
    before = _edge_count(pg, "ge-a")
    with pytest.raises(ValueError, match="未受控谓词"):
        write_controlled_edges(store, [EdgeWrite(
            from_id="ge-a", to_id="ge-b", predicate="GHOST_PREDICATE")],
            profile=profile)
    assert _edge_count(pg, "ge-a") == before, "fail-fast 必须发生在落库之前"
