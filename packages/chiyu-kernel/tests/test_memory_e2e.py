"""T43 真库 E2E：记忆全链路「写了真被读」（memory 毕业批次四，`@pytest.mark.pg`）。

⛔ 红线双保险（与 `test_pg_e2e.py` 同款，逐字沿用）：
  1. DSN 在本文件内**硬编码**为本地便携 PG（chiyu@127.0.0.1:5432/chiyu_test），
     不留 env 覆盖口；导入期断言 host ∈ {127.0.0.1, localhost}。
  2. store.dsn.validate_dsn 的 FORBIDDEN_HOSTS / FORBIDDEN_ROLES 照常拦截。

无本地 PG 时自动 skip（不算失败）；有 PG 时实跑**完整闭环**：

    决策落库（写记忆网到真 PG）
      → 双轨蒸馏（LOG→NOTE，真 PG）
      → recall_precedents（记忆网回链 + NOTE 两源 → RRF 融合）
      → run_spine(memory_recaller=...)（召回结果真的进决策回路）

判据（每条都是「反假绿」探针，任一环节断了就红）：
  ① 记忆网边确实落到真 PG（6 条受控谓词边）—— 写侧不丢
  ② 召回真的读到记忆网的先例 dec-0 —— **写了能读**（本批次的核心）
  ③ 蒸馏出的 NOTE 也能被召回 —— 双轨在真库上闭环
  ④ run_spine 注入后 context["precedents"] 含先例 —— 召回进了决策回路
  ⑤ 幂等：同内容二次蒸馏不产生伪 NOTE 变更

变异自证（删判据分支必转红）：
  · 去掉 persist 的记忆网写边分支 ⇒ ①② 红（库里没边、召回不到）
  · 去掉 spine 的 memory_recaller 调用 ⇒ ④ 红（召回没进回路）
  · 去掉 PgNoteStore 的 content_hash 幂等比对 ⇒ ⑤ 红（伪变更）
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import psycopg2
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DEC_SRC = os.path.join(_ROOT, "packages", "chiyu-decision", "src")
if os.path.isdir(_DEC_SRC) and _DEC_SRC not in sys.path:
    sys.path.append(_DEC_SRC)

from chiyu_decision.api import run_spine  # noqa: E402  (sanctioned 面)
from chiyu_decision.redline import RedlineVerdict  # noqa: E402
from chiyu_kernel.approval import RedlinePriorityGate  # noqa: E402
from chiyu_kernel.contract.decision import EIGHT_ELEMENTS, RUBRIC_KEYS  # noqa: E402
from chiyu_kernel.contract.particle import MEMORY_PREDICATES  # noqa: E402
from chiyu_kernel.context import build_memory_recaller, recall_precedents  # noqa: E402
from chiyu_kernel.domain import profile_from_dict  # noqa: E402
from chiyu_kernel.graph import PgCteGraphStore  # noqa: E402
from chiyu_kernel.persist import (  # noqa: E402
    PgMemoryLogStore, PgNoteStore, PgVectorStorePersister,
    MemoryLogEntry, distill,
)
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

_MEM_PREDICATES = tuple(m.predicate for m in MEMORY_PREDICATES)

_PROFILE_DICT: Dict[str, Any] = {
    "domain": "pg-memory-e2e",
    "particle_types": {"names": ["unstructured_asset", "entity", "decision",
                                 "memory", "knowledge", "document"]},
    "predicates": {"knowledge": [
        {"predicate": "DESCRIBES", "from_type": "knowledge",
         "to_type": "document", "layer": "K", "source": "rule"},
    ]},
    "autonomous_threshold": 0.79,
}

#: prepped 先例节点；overrides 为空（不计边）
REFERENCES: Dict[str, Any] = {
    "subject": ("doc-1",), "precedents": ("dec-0",), "exceptions": ("kb-2",),
    "frames": ("kb-3",), "causes": ("task-1",), "influencers": ("dec-9",),
    "overrides": (),
}

_DECISION_ID = "pg-mem-e2e-1"
_NOW_ISO = "2026-10-10T00:00:00+00:00"


@pytest.fixture(scope="module")
def pg():
    """独立 schema 全生命周期：ensure → 用例 → drop（零残留）。"""
    os.environ["CHIYU_DB_DSN_TEST"] = PG_DSN
    os.environ["CHIYU_TEST"] = "1"
    schema = "t_pg_memx_" + uuid.uuid4().hex[:8]
    os.environ["CHIYU_DB_SCHEMA"] = schema
    profile = profile_from_dict(_PROFILE_DICT)
    report = ensure_schema(profile=profile, testing=True, schema=schema)
    assert report["schema"] == schema and not report.get("skipped"), report
    store = PgVectorStore(profile, schema=schema)
    yield {"store": store, "profile": profile, "schema": schema}
    drop_test_schema(schema)


def _persist_decision(pg, decision_id: str) -> None:
    """决策落库：写 event + particle + 记忆网（真 PG）。"""
    store, profile = pg["store"], pg["profile"]
    persister = PgVectorStorePersister(store, profile, materialize=False)
    run_spine(
        context={"text": "普通事项", "decision_id": decision_id,
                 "subject_id": decision_id},
        profile=profile,
        rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
        elements={e: "x" for e in EIGHT_ELEMENTS},
        redline_items=(),
        approval_gate=RedlinePriorityGate(),
        persister=lambda r: persister.persist(
            r, subject_id=decision_id, references=REFERENCES) or True,
    )


def _probe(sink: Dict[str, Any]) -> Any:
    def _cb(*, context: Any, redline_items: Any) -> RedlineVerdict:
        sink.update(context)
        return RedlineVerdict(hit=False, reasons=())
    return _cb


# ── ① 记忆网边确实落到真 PG（写侧不丢）──────────────────────────────────
def test_memory_net_edges_persisted(pg) -> None:
    _persist_decision(pg, _DECISION_ID)
    row = pg["store"].execute_fetch(
        f"SELECT count(*)::int AS n FROM {pg['schema']}.graph_edge "
        "WHERE predicate = ANY(%s)", (list(_MEM_PREDICATES),), fetch_all=False)
    assert row["n"] == 6, f"记忆网应落 6 条受控边，实得 {row['n']}"


# ── ② 写了能读：召回读到记忆网的先例 ────────────────────────────────────
def test_recall_reads_memory_net_written_by_decision(pg) -> None:
    _persist_decision(pg, _DECISION_ID)
    graph = PgCteGraphStore(pg["store"], predicates=_MEM_PREDICATES)
    res = recall_precedents(["dec-0"], graph=graph, subject_id=_DECISION_ID)
    keys = [i.key for i in res.items]
    assert "dec-0" in keys, (
        f"⛔ 写了却读不到：决策落库写了 REFERENCED_PRECEDENT→dec-0，"
        f"召回却没读到（实得 {keys}）")


# ── ③ 双轨蒸馏出的 NOTE 也能被召回（真库闭环）────────────────────────────
def test_recall_reads_distilled_notes_on_real_db(pg) -> None:
    store, profile = pg["store"], pg["profile"]
    log = PgMemoryLogStore(store, profile)
    notes = PgNoteStore(store, profile)
    log.append(MemoryLogEntry(entry_id="me-note-1", kind="note",
                              payload={"v": "me-note-1"}, created_at=_NOW_ISO,
                              explicit=True))
    distill(log, notes, now=datetime(2026, 10, 10, tzinfo=timezone.utc))
    assert notes.get("me-note-1") is not None, "蒸馏产物须落到真库 NOTE 轨"
    res = recall_precedents(["me-note-1"], notes=notes)
    assert any(i.key == "me-note-1" for i in res.items), (
        f"蒸馏出的 NOTE 应被召回，实得 {[i.key for i in res.items]}")


# ── ④ 召回真的进决策回路（run_spine 注入）────────────────────────────────
def test_recall_enters_decision_loop_via_run_spine(pg) -> None:
    _persist_decision(pg, _DECISION_ID)
    graph = PgCteGraphStore(pg["store"], predicates=_MEM_PREDICATES)
    notes = PgNoteStore(pg["store"], pg["profile"])
    sink: Dict[str, Any] = {}
    run_spine(
        context={"text": "dec-0", "decision_id": "pg-mem-e2e-2",
                 "subject_id": _DECISION_ID},
        profile=pg["profile"],
        rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
        elements={e: "x" for e in EIGHT_ELEMENTS},
        redline_items=(), approval_gate=RedlinePriorityGate(),
        memory_recaller=build_memory_recaller(notes=notes, graph=graph),
        redline_callback=_probe(sink),
    )
    assert "dec-0" in sink.get("precedents", []), (
        f"召回结果未进入决策回路：{sink.get('precedents')}")


# ── ⑤ 幂等：同内容二次蒸馏不产生伪 NOTE 变更 ─────────────────────────────
def test_distill_twice_is_idempotent_on_real_db(pg) -> None:
    store, profile = pg["store"], pg["profile"]
    log = PgMemoryLogStore(store, profile)
    notes = PgNoteStore(store, profile)
    log.append(MemoryLogEntry(entry_id="me-idem-1", kind="note",
                              payload={"v": "me-idem-1"}, created_at=_NOW_ISO,
                              explicit=True))
    now = datetime(2026, 10, 10, tzinfo=timezone.utc)
    first = distill(log, notes, now=now)
    second = distill(log, notes, now=now)
    assert first.promoted >= 1
    assert second.skipped_idempotent >= 1, (
        "同内容二次蒸馏须经 content_hash 幂等跳过（禁伪 updated_at）")
