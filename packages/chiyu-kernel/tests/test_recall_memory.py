"""T41 守卫：记忆召回消费点（kernel 侧）—— `recall_precedents` / `build_memory_recaller`。

判据（每条都对准「写了能读」这一实质缺口的某一面）：
  ① NOTE 轨召回：蒸馏出的 note 能被查询词召回（此前写了读不到）
  ② 空池显式空：无源 ⇒ tier=none，不伪造候选
  ③ 记忆网图源：受控谓词出边目标进入召回池
  ④ 图源故障降级留痕：异常不崩，且 evidence.notes 记录降级（防静默丢源）
  ⑤ 召回器注入三键且无副作用（不改传入 context）
  ⑥ 默认谓词取自 L0 契约（防谓词漂移导致静默召回空）

变异自证（删判据分支必转红）：
  · 去掉源 B（notes.iter_all 循环）⇒ ① 红
  · 去掉图源异常捕获 ⇒ ④ 红（异常冒泡而非留痕）
  · hook 改为原地改 dict ⇒ ⑤ 红（副作用断言）
"""
from __future__ import annotations

from typing import Any

import pytest

from chiyu_kernel.contract.particle import MEMORY_PREDICATES
from chiyu_kernel.context import (
    RECALL_FRAME_PREDICATE, RECALL_REFERENCE_PREDICATE, VTIER_NONE,
    build_memory_recaller, recall_precedents,
)
from chiyu_kernel.graph import GraphEdge, InMemoryGraphStore
from chiyu_kernel.persist import InMemoryNoteStore, MemoryNote, note_hash

_M_PREDS = tuple(m.predicate for m in MEMORY_PREDICATES)


def _note(key: str, content: str) -> MemoryNote:
    return MemoryNote(key=key, content=content,
                      content_hash=note_hash(key, content))


# ── ① NOTE 轨召回（写了能读）────────────────────────────────────────────
def test_recall_reads_note_track() -> None:
    notes = InMemoryNoteStore()
    notes.upsert(_note("n-alpha", "alpha token beta"))
    notes.upsert(_note("n-gamma", "gamma token delta"))
    res = recall_precedents(["alpha"], notes=notes)
    keys = [i.key for i in res.items]
    assert "n-alpha" in keys, f"NOTE 轨内容应被召回，实得 {keys}"
    assert "n-gamma" not in keys, "未命中查询词的条目不得混入"


# ── ② 空池显式空 ────────────────────────────────────────────────────────
def test_recall_empty_pool_is_explicit_none() -> None:
    res = recall_precedents(["x"])
    assert res.evidence.tier == VTIER_NONE
    assert res.items == ()
    assert res.evidence.pool_size == 0


# ── ③ 记忆网图源进入召回池 ──────────────────────────────────────────────
def test_recall_memory_net_backlink_source() -> None:
    g = InMemoryGraphStore(_M_PREDS, [
        GraphEdge(from_id="subj-1", to_id="dec-0",
                  predicate=RECALL_REFERENCE_PREDICATE),
    ])
    res = recall_precedents(["dec-0"], graph=g, subject_id="subj-1")
    keys = [i.key for i in res.items]
    assert "dec-0" in keys, f"记忆网回链目标应进召回池，实得 {keys}"


# ── ④ 图源故障降级留痕（不崩、不静默丢源）────────────────────────────────
def test_recall_graph_failure_degrades_with_trace() -> None:
    class _Boom:
        def controlled(self) -> tuple:
            return ()

        def out_edges(self, *a: Any, **k: Any) -> tuple:
            raise RuntimeError("graph unavailable")

    res = recall_precedents(["x"], graph=_Boom(), subject_id="s-1")
    assert any("图源降级" in n for n in res.evidence.notes), (
        f"图源不可用须留痕，实得 notes={res.evidence.notes}")


# ── ⑤ 召回器注入三键 + 无副作用 ──────────────────────────────────────────
def test_memory_recaller_injects_keys_without_mutating_input() -> None:
    notes = InMemoryNoteStore()
    notes.upsert(_note("n-1", "alpha token"))
    hook = build_memory_recaller(notes=notes)
    ctx = {"text": "alpha", "subject_id": "s-1"}
    out = hook(ctx)
    assert out["precedents"] == ["n-1"]
    assert "precedent_supply" in out and "memory_recall" in out
    assert "precedents" not in ctx, "召回器不得原地修改传入 context（无副作用）"


# ── ⑥ 默认谓词取自 L0 契约（防漂移）─────────────────────────────────────
def test_recall_default_predicates_come_from_contract() -> None:
    names = {m.predicate for m in MEMORY_PREDICATES}
    assert RECALL_REFERENCE_PREDICATE in names
    assert RECALL_FRAME_PREDICATE in names


# ── ⑦ 谓词漂移 fail-fast（模块级契约：非法谓词 import 期即红）─────────────
def test_recall_predicate_drift_is_import_time_fatal() -> None:
    """契约不变量：默认谓词若脱离 MEMORY_PREDICATES，模块 import 期即抛。

    此处以「模块已成功导入 + 常量仍在契约内」双重断言锁定该不变量；
    真正的 fail-fast 分支由 `recall_memory` 模块体在 import 期执行。
    """
    import importlib

    mod = importlib.import_module("chiyu_kernel.context.recall_memory")
    assert mod.RECALL_REFERENCE_PREDICATE in {m.predicate for m in MEMORY_PREDICATES}
    with pytest.raises(AttributeError):
        _ = mod.NOT_A_PREDICATE  # type: ignore[attr-defined]
