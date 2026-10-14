"""T40 守卫：双轨记忆 PG 落库（真库 `@pytest.mark.pg`，memory 毕业批次一）。

⛔ 红线双保险（与 `test_pg_e2e.py` 同款，逐字沿用）：
  1. DSN 在本文件内**硬编码**为本地便携 PG（chiyu@127.0.0.1:5432/chiyu_test），
     不留 env 覆盖口；导入期断言 host ∈ {127.0.0.1, localhost}。
  2. store.dsn.validate_dsn 的 FORBIDDEN_HOSTS / FORBIDDEN_ROLES 照常拦截。

无本地 PG 时自动 skip（不算失败）；有 PG 时实跑下列判据：
  ① LOG 轨：append → 真库读回（字段逐一对齐，jsonb 往返无损）
  ② append-only：同 id 二次 append **不覆盖**（PG 形态 = ON CONFLICT DO NOTHING）
  ③ LOG 轨排序：按 seq 原序返回
  ④ NOTE 轨：upsert → get 读回（五属性全部对齐）
  ⑤ NOTE 幂等：同 content_hash 二次 upsert ⇒ False（禁伪 updated_at）
  ⑥ NOTE 变更：内容变 ⇒ True 且读回新内容
  ⑦ 构造期校验：未登记 note_type ⇒ ValueError（而非运行期撞 CHECK）
  ⑧ 协议同形：`PgMemoryLogStore` 无 update/delete 通道
  ⑨ 真库蒸馏闭环：LOG → distill → PgNoteStore（显式晋升 + 价值视界淘汰）

变异自证（本测试的判别力来源，删任一判据分支必转红）：
  · ② 若把 `DO NOTHING` 改成 `DO UPDATE` ⇒ 内容被覆盖，断言转红
  · ⑤ 若去掉 upsert 前的 content_hash 比对 ⇒ 幂等返回 True，断言转红
  · ⑦ 若去掉构造期类型校验 ⇒ 不抛异常，断言转红
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
for _p in (os.path.join(_ROOT, "packages", "chiyu-decision", "src"),):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.append(_p)

from chiyu_kernel.domain import profile_from_dict  # noqa: E402
from chiyu_kernel.persist import (  # noqa: E402
    PgMemoryLogStore, PgNoteStore, MemoryLogEntry, MemoryNote, distill, note_hash,
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

# 中性域（内核测试不得携带真实业务词）；memory 属 CORE_ROLES，任何合法 profile 必含
_PROFILE_DICT: Dict[str, Any] = {
    "domain": "pg-memory-demo",
    "particle_types": {"names": ["unstructured_asset", "entity", "decision",
                                 "memory", "knowledge", "document"]},
    "predicates": {"knowledge": [
        {"predicate": "DESCRIBES", "from_type": "knowledge",
         "to_type": "document", "layer": "K", "source": "rule"},
    ]},
    "autonomous_threshold": 0.79,
}

_NOW = "2026-10-10T00:00:00+00:00"
_OLD = "2000-01-01T00:00:00+00:00"          # 远超价值视界（30 天）


def _entry(eid: str, *, payload: Any = None, created_at: str = _NOW,
           transient: bool = False, explicit: bool = False,
           src: str = "") -> MemoryLogEntry:
    return MemoryLogEntry(
        entry_id=eid, kind="note", payload={"v": eid} if payload is None else payload,
        created_at=created_at, source_decision_id=src,
        transient=transient, explicit=explicit)


def _note(key: str, content: str, *, horizon: int = 30,
          explicit: bool = False, sources: tuple = ()) -> MemoryNote:
    return MemoryNote(key=key, content=content,
                      content_hash=note_hash(key, content),
                      horizon_days=horizon, explicit=explicit,
                      updated_at=_NOW, source_entry_ids=sources)


@pytest.fixture(scope="module")
def pg():
    """独立 schema 全生命周期：ensure → 用例 → drop（零残留）。"""
    os.environ["CHIYU_DB_DSN_TEST"] = PG_DSN
    os.environ["CHIYU_TEST"] = "1"
    schema = "t_pg_mem_" + uuid.uuid4().hex[:8]
    os.environ["CHIYU_DB_SCHEMA"] = schema
    profile = profile_from_dict(_PROFILE_DICT)
    report = ensure_schema(profile=profile, testing=True, schema=schema)
    assert report["schema"] == schema and not report.get("skipped"), report
    store = PgVectorStore(profile, schema=schema)
    yield {"store": store, "profile": profile, "schema": schema}
    drop_test_schema(schema)


def test_pg_memory_dsn_redline_selfcheck() -> None:
    """判据自证：本文件 DSN 恒为本地库（任何人改动立即红）。"""
    p = parse_dsn(PG_DSN)
    assert p["host"] == "127.0.0.1" and p["db"] == "chiyu_test"


# ── ① LOG 轨落库读回 ────────────────────────────────────────────────────
def test_pg_memory_log_append_readback(pg) -> None:
    log = PgMemoryLogStore(pg["store"], pg["profile"])
    log.append(_entry("ml-1", payload={"a": 1, "b": ["x", "y"]}, src="dec-1",
                      explicit=True))
    rows = [e for e in log.iter_all() if e.entry_id == "ml-1"]
    assert len(rows) == 1, f"LOG 落库应有且仅有一条 ml-1，实得 {len(rows)}"
    e = rows[0]
    assert e.kind == "note"
    assert e.payload == {"a": 1, "b": ["x", "y"]}, "jsonb 往返须无损"
    assert e.source_decision_id == "dec-1"
    assert e.explicit is True and e.transient is False
    assert len(log) >= 1


# ── ② append-only：同 id 二次 append 不覆盖 ──────────────────────────────
def test_pg_memory_log_append_only_never_overwrites(pg) -> None:
    log = PgMemoryLogStore(pg["store"], pg["profile"])
    log.append(_entry("ml-2", payload={"v": "first"}))
    log.append(_entry("ml-2", payload={"v": "second"}))   # 同 id、不同内容
    rows = [e for e in log.iter_all() if e.entry_id == "ml-2"]
    assert len(rows) == 1, "append-only：同 id 不得产生第二条"
    assert rows[0].payload == {"v": "first"}, (
        "⛔ 覆盖写 = 破坏 append-only（协议无 update，PG 绑定不得开后门）")


# ── ③ LOG 轨按写入顺序返回 ──────────────────────────────────────────────
def test_pg_memory_log_iter_all_preserves_sequence(pg) -> None:
    log = PgMemoryLogStore(pg["store"], pg["profile"])
    for i in range(3):
        log.append(_entry(f"ml-seq-{i}"))
    ids = [e.entry_id for e in log.iter_all()]
    seq = [i for i in ids if i.startswith("ml-seq-")]
    assert seq == ["ml-seq-0", "ml-seq-1", "ml-seq-2"], f"写入顺序丢失：{seq}"


# ── ④ NOTE 轨 upsert 读回 ───────────────────────────────────────────────
def test_pg_note_upsert_readback(pg) -> None:
    notes = PgNoteStore(pg["store"], pg["profile"])
    n = _note("n-1", "hello", explicit=True, sources=("ml-1",))
    assert notes.upsert(n) is True
    got = notes.get("n-1")
    assert got is not None
    assert got.key == "n-1" and got.content == "hello"
    assert got.content_hash == n.content_hash
    assert got.horizon_days == 30 and got.explicit is True
    assert got.source_entry_ids == ("ml-1",)


# ── ⑤ NOTE 幂等：同 hash 二次 upsert 不产生变更 ──────────────────────────
def test_pg_note_upsert_idempotent_by_content_hash(pg) -> None:
    notes = PgNoteStore(pg["store"], pg["profile"])
    n = _note("n-2", "same")
    assert notes.upsert(n) is True
    assert notes.upsert(n) is False, "同 content_hash 二次 upsert 须幂等跳过"


# ── ⑥ NOTE 内容变更 ⇒ 真变更 ────────────────────────────────────────────
def test_pg_note_upsert_applies_on_content_change(pg) -> None:
    notes = PgNoteStore(pg["store"], pg["profile"])
    assert notes.upsert(_note("n-3", "v1")) is True
    assert notes.upsert(_note("n-3", "v2")) is True
    assert notes.get("n-3").content == "v2"


# ── ⑦ 构造期校验：未登记 note_type 立即红 ────────────────────────────────
def test_pg_note_type_must_be_registered_in_profile(pg) -> None:
    with pytest.raises(ValueError, match="不在 profile.particle_types"):
        PgNoteStore(pg["store"], pg["profile"], note_type="ghost_type")


# ── ⑧ 协议同形：无 update/delete 通道 ───────────────────────────────────
def test_pg_memory_log_store_exposes_no_mutation_channel() -> None:
    for name in ("update", "delete", "remove", "clear", "pop", "upsert"):
        assert not hasattr(PgMemoryLogStore, name), (
            f"LOG 轨不得提供 {name}（append-only 由协议形状保证）")


# ── ⑨ 真库蒸馏闭环：LOG → distill → NOTE ────────────────────────────────
def test_pg_distill_end_to_end_on_real_db(pg) -> None:
    log = PgMemoryLogStore(pg["store"], pg["profile"])
    notes = PgNoteStore(pg["store"], pg["profile"])
    log.append(_entry("d-explicit", payload={"x": 1}, explicit=True))
    log.append(_entry("d-stale", payload={"x": 2}, created_at=_OLD))
    now = datetime(2026, 10, 10, tzinfo=timezone.utc)
    rep = distill(log, notes, now=now, value_horizon_days=30)
    assert rep.explicit_promoted >= 1, f"显式条目须晋升：{rep}"
    assert rep.dropped_horizon >= 1, f"超视界条目须淘汰：{rep}"
    assert notes.get("d-explicit") is not None, "显式条目须落到 NOTE 轨"
    assert notes.get("d-stale") is None, "被价值视界淘汰的条目不得进 NOTE 轨"
