# -*- coding: utf-8 -*-
"""图写 MCP 端点真库 E2E（补 T48 §2.1 纸面缺口；`@pytest.mark.pg`）。

红线双保险与 test_graph_edges_pg.py 同款：DSN 硬编码本地便携 PG（chiyu_test），
导入期断言 host，无本地 PG 自动 skip。

判据（经 MCP 端点真实落库并读回——把"纸面通道"坐实为真线）：
① 经 write_controlled_edges 端点两阶段确认 → 真库 graph_edge 写入 → PgCteGraphStore 读回（同表闭环）；
② 闭集经 MCP 通道生效：edge_source="consumer" ⇒ 0 落库。
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
from chiyu_kernel.graph.mcp import (  # noqa: E402
    WRITE_CONTROLLED_EDGES_TOOL, build_graph_write_server,
)
from chiyu_kernel.persist import PgVectorStorePersister  # noqa: E402
from chiyu_kernel.store import (  # noqa: E402
    PgVectorStore, drop_test_schema, ensure_schema,
)
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
    "domain": "graph-mcp-e2e",
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
    schema = "t_gmcp_e2e_" + uuid.uuid4().hex[:8]
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


def _write_via_mcp(store, profile, edges, *, secret: str = "s") -> dict:
    """经 foundation 图写 MCP 端点（两阶段）写入，返回第二次调用结果。

    ⛔ 确认令牌走 params.confirm_token（McpServer.call 不转发令牌）。
    """
    srv = build_graph_write_server(
        store, profile=profile, auth=lambda ctx: True, secret=secret)
    r1 = srv.call(WRITE_CONTROLLED_EDGES_TOOL, {"edges": edges}, ctx={"principal": "crm"})
    assert r1["result"]["status"] == "confirmation_required", r1
    token = r1["result"]["confirm_token"]
    r2 = srv.handle_request(
        {"id": 1, "method": "tools/call",
         "params": {"name": WRITE_CONTROLLED_EDGES_TOOL, "arguments": {"edges": edges},
                    "confirm_token": token}},
        ctx={"principal": "crm"})
    return r2


def test_pg_mcp_write_read_loop(pg) -> None:
    """判据①：经 MCP 端点写入 → 只读派生视图读回（写读同表闭环）。"""
    store, profile = pg["store"], pg["profile"]
    _persist_decision(store, profile, "gm-a")
    _persist_decision(store, profile, "gm-b")
    r2 = _write_via_mcp(store, profile, [{
        "from_id": "gm-a", "to_id": "gm-b", "predicate": "OVERRIDES",
        "edge_source": "rule", "weight": 0.9}])
    assert r2["result"]["written"] == 1
    graph = PgCteGraphStore(store, predicates=("OVERRIDES",))
    view = relation_view(graph, "gm-a", max_hops=2, direction="out")
    got = {(e["from"], e["to"], e["predicate"]) for e in view["edges"]}
    assert ("gm-a", "gm-b", "OVERRIDES") in got


def test_pg_mcp_closed_set_rejects_bad_source(pg) -> None:
    """判据②：edge_source='consumer' 经 MCP 通道 ⇒ 0 落库。"""
    store, profile = pg["store"], pg["profile"]
    _persist_decision(store, profile, "gm-c")
    _persist_decision(store, profile, "gm-d")
    r2 = _write_via_mcp(store, profile, [{
        "from_id": "gm-c", "to_id": "gm-d", "predicate": "OVERRIDES",
        "edge_source": "consumer"}])
    assert r2["error"]["code"] == -32000
    row = store.execute_fetch(
        f"SELECT count(*)::int AS n FROM {pg['schema']}.graph_edge "
        "WHERE from_id = %s", ("gm-c",))
    assert row["n"] == 0, "闭集拒绝必须零落库"
