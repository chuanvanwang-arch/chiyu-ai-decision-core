"""真库 E2E（v1.0 发布判据 §2-3）—— `@pytest.mark.pg`。

⛔ 红线双保险：
  1. DSN 在本文件内**硬编码**为本地便携 PG（chiyu@127.0.0.1:5432/chiyu_test），
     不留 env 覆盖口（防误指生产）；导入期即断言 host ∈ {127.0.0.1, localhost}。
  2. store.dsn.validate_dsn 的 FORBIDDEN_HOSTS / FORBIDDEN_ROLES 仍照常拦截。

无本地 PG 时自动 skip（不算失败）；有 PG 时实跑三判据：
  ① 三表落库读回（event/particle/graph_edge 经真 run_spine + 真 persister，含幂等）
  ② 零硬删除在真库门面上被拦（DELETE / TRUNCATE）
  ③ 图视图只读派生（递归 CTE 遍历受控谓词 + 决策回链），且幻影谓词不进视图
"""
from __future__ import annotations

import os
import sys
import uuid
from typing import Any, Dict, Tuple

import psycopg2
import pytest

# 自举：单文件直跑时包内 conftest 只装 kernel src，这里补齐 decision src
# （组合跑由根 conftest 统一装配，此处幂等追加，零影响）。
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DEC_SRC = os.path.join(_ROOT, "packages", "chiyu-decision", "src")
if os.path.isdir(_DEC_SRC) and _DEC_SRC not in sys.path:
    sys.path.append(_DEC_SRC)

from chiyu_decision.api import run_spine  # noqa: E402  (sanctioned 面)
from chiyu_kernel.approval import RedlinePriorityGate  # noqa: E402
from chiyu_kernel.contract.decision import EIGHT_ELEMENTS, RUBRIC_KEYS  # noqa: E402
from chiyu_kernel.contract.particle import MEMORY_PREDICATES  # noqa: E402
from chiyu_kernel.domain import profile_from_dict  # noqa: E402
from chiyu_kernel.graph import (  # noqa: E402
    PgCteGraphStore, decision_backlinks, relation_view,
)
from chiyu_kernel.persist import PgVectorStorePersister  # noqa: E402
from chiyu_kernel.store import (  # noqa: E402
    PgVectorStore, ensure_schema, drop_test_schema,
)
from chiyu_kernel.store.dsn import parse_dsn  # noqa: E402

# ── 红线：DSN 硬编码，绝不留 env 覆盖口 ──────────────────────────────────
PG_DSN = "postgresql://chiyu@127.0.0.1:5432/chiyu_test"

_parsed = parse_dsn(PG_DSN)
assert _parsed.get("host") in ("127.0.0.1", "localhost"), (
    f"E2E DSN 红线被破坏：host={_parsed.get('host')!r}，"
    "真库用例只许连本地便携 PG")


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

# 中性域（与 examples/reference_consumer 同构，内核测试不得携带真实业务词）
_PROFILE_DICT: Dict[str, Any] = {
    "domain": "pg-e2e-demo",
    "particle_types": {"names": ["unstructured_asset", "entity", "decision",
                                 "memory", "knowledge", "document"]},
    "predicates": {"knowledge": [
        {"predicate": "DESCRIBES", "from_type": "knowledge",
         "to_type": "document", "layer": "K", "source": "rule"},
    ]},
    "autonomous_threshold": 0.79,
}

REFERENCES: Dict[str, Tuple[str, ...]] = {
    "subject": ("doc-1",), "precedents": ("dec-0",), "exceptions": ("kb-2",),
    "frames": ("kb-3",), "causes": ("task-1",), "influencers": ("dec-9",),
    "overrides": (),
}


@pytest.fixture(scope="module")
def pg():
    """独立 schema 全生命周期：ensure → 用例 → drop（零残留）。"""
    os.environ["CHIYU_DB_DSN_TEST"] = PG_DSN
    os.environ["CHIYU_TEST"] = "1"
    schema = "t_pg_e2e_" + uuid.uuid4().hex[:8]
    os.environ["CHIYU_DB_SCHEMA"] = schema
    profile = profile_from_dict(_PROFILE_DICT)
    report = ensure_schema(profile=profile, testing=True, schema=schema)
    assert report["schema"] == schema and not report.get("skipped"), report
    store = PgVectorStore(profile, schema=schema)
    yield {"store": store, "profile": profile, "schema": schema}
    drop_test_schema(schema)


def _persist_once(store: PgVectorStore, profile, decision_id: str) -> Any:
    persister = PgVectorStorePersister(store, profile, materialize=False)

    def persist() -> Any:
        return run_spine(
            context={"text": "普通事项", "decision_id": decision_id},
            profile=profile,
            rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
            elements={e: "x" for e in EIGHT_ELEMENTS},
            redline_items=(),
            approval_gate=RedlinePriorityGate(),
            persister=lambda r: persister.persist(
                r, subject_id="subj-1", references=REFERENCES) or True,
        )
    return persist


def test_pg_e2e_dsn_redline_selfcheck() -> None:
    """判据自证：本文件 DSN 恒为本地库（任何人改动立即红）。"""
    p = parse_dsn(PG_DSN)
    assert p["host"] == "127.0.0.1" and p["db"] == "chiyu_test"


def test_pg_three_table_persist_readback(pg) -> None:
    """判据①：真 run_spine → 真 persister → 三表落库 → 真库读回（含幂等）。"""
    store, profile = pg["store"], pg["profile"]
    run = _persist_once(store, profile, "pg-e2e-1")
    res = run()
    assert res.persisted is True and res.approval_rejected is None

    mem_preds = {m.predicate for m in MEMORY_PREDICATES}
    # event 读回：恰一条 decision 事件（event 主键 = id = decision_id）
    ev = store.execute_fetch(
        f"SELECT id, event_type FROM {pg['schema']}.event "
        "WHERE id = %s", ("pg-e2e-1",))
    assert ev is not None and ev["event_type"] == "decision"
    # particle 读回：决策粒子在库（particle_id = decision_id，type='decision'）
    row = store.execute_fetch(
        f"SELECT particle_id, type FROM {pg['schema']}.particle "
        "WHERE particle_id = %s", ("pg-e2e-1",))
    assert row is not None and row["type"] == "decision"
    # 记忆网读回：6 条（overrides 为空不计）
    n = store.execute_fetch(
        f"SELECT count(*)::int AS n FROM {pg['schema']}.graph_edge "
        "WHERE predicate = ANY(%s)", (sorted(mem_preds),))
    assert n["n"] == 6, f"记忆网边数应为 6，实得 {n['n']}"
    # 幂等：同内容二次落库不产生伪变更
    run()
    n2 = store.execute_fetch(
        f"SELECT count(*)::int AS n FROM {pg['schema']}.graph_edge "
        "WHERE predicate = ANY(%s)", (sorted(mem_preds),))
    assert n2["n"] == 6, "同内容二次 persist 不得新增记忆网边"


def test_pg_zero_hard_delete_enforced(pg) -> None:
    """判据②：DELETE / TRUNCATE 在真库门面上被拦（异常抛出，而非静默）。"""
    store = pg["store"]
    with pytest.raises(ValueError, match="禁 DELETE"):
        store.execute(f"DELETE FROM {pg['schema']}.particle")
    with pytest.raises(ValueError, match="禁 DELETE"):
        store.execute(f"TRUNCATE {pg['schema']}.event")


def test_pg_graph_view_derivation(pg) -> None:
    """判据③：递归 CTE 图视图只读派生 + 决策回链；幻影谓词不进视图。"""
    store, profile = pg["store"], pg["profile"]
    graph = PgCteGraphStore(store, predicates=("DESCRIBES",))
    # 受控边：subj-1 → doc-1（DESCRIBES）
    store.execute(
        f"INSERT INTO {pg['schema']}.graph_edge "
        "(from_id, to_id, predicate, layer, edge_source) VALUES (%s,%s,%s,%s,%s)",
        ("subj-1", "doc-1", "DESCRIBES", "K", "engine"))
    view = relation_view(graph, "subj-1", max_hops=2, direction="out")
    got = {(e["from"], e["to"], e["predicate"]) for e in view["edges"]}
    assert ("subj-1", "doc-1", "DESCRIBES") in got
    assert view["truncated"] is False
    # 幻影谓词（未受控）不得出现在遍历结果
    store.execute(
        f"INSERT INTO {pg['schema']}.graph_edge "
        "(from_id, to_id, predicate, layer, edge_source) VALUES (%s,%s,%s,%s,%s)",
        ("doc-1", "ghost-x", "DESCRIBES_PHANTOM", "K", "engine"))
    got2 = {(e["from"], e["to"], e["predicate"])
            for e in relation_view(graph, "subj-1", max_hops=2)["edges"]}
    assert not any(p == "DESCRIBES_PHANTOM" for _, _, p in got2)
    # 决策回链（审计四问之"被谁引用"）：判据①落的记忆网边
    #   pg-e2e-1 --REFERENCED_PRECEDENT--> dec-0 ⇒ dec-0 的 referenced_by 含 pg-e2e-1
    mem_preds = tuple(m.predicate for m in MEMORY_PREDICATES)
    graph_all = PgCteGraphStore(store, predicates=("DESCRIBES",) + mem_preds)
    links = decision_backlinks(graph_all, "dec-0")
    assert "pg-e2e-1" in links["referenced_by"], links
    assert "REFERENCED_PRECEDENT" in links["controlled"]
