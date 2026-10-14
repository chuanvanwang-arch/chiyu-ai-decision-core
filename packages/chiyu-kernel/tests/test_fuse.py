"""T42 守卫：多源 RRF 融合（kernel 侧）—— `rrf_fuse` 与召回的多源分派。

判据：
  ① 空源 ⇒ 显式 VTIER_NONE 空结果（不伪造候选）
  ② RRF 分数公式：score = Σ 1/(k + rank + 1)（名次倒数，非原始分数）
  ③ 多源同 key ⇒ 名次贡献累加 ⇒ 排在最前（RRF 的预期行为）
  ④ 融合留痕：notes 记录源数、各源档位、k 值（防「融合了看不出哪档」）
  ⑤ tier 取参与源中最好档位（按 VTIER_ORDER）
  ⑥ 召回多源分派：≥2 源走 RRF；1 源留痕「不经 RRF 融合」；0 源显式空

变异自证（删判据分支必转红）：
  · 把 `1.0 / (k + rank + 1)` 改成直接用 item.score ⇒ ② 红
  · 去掉 k（用 rank+1）⇒ ② 红
  · 同 key 改为覆盖而非累加 ⇒ ③ 红
"""
from __future__ import annotations

from typing import Sequence

from chiyu_kernel.context import (
    VTIER_FTS, VTIER_FTS_VECTOR, VTIER_NONE, RRF_K_DEFAULT, rrf_fuse,
)
from chiyu_kernel.context.recall_memory import recall_precedents
from chiyu_kernel.context.retrieval import RecalledItem, RetrievalEvidence, RetrievalResult
from chiyu_kernel.graph import GraphEdge, InMemoryGraphStore
from chiyu_kernel.persist import InMemoryNoteStore, MemoryNote, note_hash
from chiyu_kernel.contract.particle import MEMORY_PREDICATES

_M_PREDS = tuple(m.predicate for m in MEMORY_PREDICATES)


def _res(keys: Sequence[str], tier: str = VTIER_FTS,
         coverage: float = 0.0) -> RetrievalResult:
    return RetrievalResult(
        tuple(RecalledItem(key=k, score=float(len(keys) - i))
              for i, k in enumerate(keys)),
        RetrievalEvidence(tier=tier, pool_size=len(keys), vector_used=False,
                          fts_prefiltered=False, embedding_coverage=coverage,
                          notes=()))


def _note(key: str, content: str) -> MemoryNote:
    return MemoryNote(key=key, content=content,
                      content_hash=note_hash(key, content))


# ── ① 空源显式空 ────────────────────────────────────────────────────────
def test_rrf_fuse_empty_sources_is_explicit_none() -> None:
    res = rrf_fuse([])
    assert res.evidence.tier == VTIER_NONE
    assert res.items == ()
    assert res.evidence.pool_size == 0


# ── ② RRF 分数 = 名次倒数（非原始分数）──────────────────────────────────
def test_rrf_score_is_rank_reciprocal_not_raw_score() -> None:
    res = rrf_fuse([_res(["a", "b", "c"])], k=60)
    got = {i.key: i.score for i in res.items}
    assert abs(got["a"] - 1.0 / 61) < 1e-9, f"rank0 应为 1/(60+1)，实得 {got['a']}"
    assert abs(got["b"] - 1.0 / 62) < 1e-9
    assert abs(got["c"] - 1.0 / 63) < 1e-9
    # 原始分数被忽略：_res 给的 score 是 3/2/1（降序），与 RRF 无关
    assert res.items[0].key == "a"


# ── ③ 多源同 key 累加 ⇒ 排最前 ──────────────────────────────────────────
def test_rrf_accumulates_across_sources() -> None:
    res = rrf_fuse([_res(["a", "b"]), _res(["a", "c"])], k=60)
    assert res.items[0].key == "a", "被多源同时召中的条目须排最前"
    got = {i.key: i.score for i in res.items}
    assert abs(got["a"] - 2.0 / 61) < 1e-9
    assert abs(got["b"] - 1.0 / 62) < 1e-9
    assert abs(got["c"] - 1.0 / 62) < 1e-9


# ── ④ 融合留痕：源数 / 各源档位 / k ─────────────────────────────────────
def test_rrf_fuse_leaves_fusion_trace() -> None:
    res = rrf_fuse([_res(["a"], tier=VTIER_FTS), _res(["b"], tier=VTIER_FTS_VECTOR)])
    joined = " ".join(res.evidence.notes)
    assert "RRF 融合 2 源" in joined, f"融合须留痕源数，实得 {res.evidence.notes}"
    assert VTIER_FTS in joined and VTIER_FTS_VECTOR in joined
    assert f"k={RRF_K_DEFAULT}" in joined


# ── ⑤ tier 取最好档位 ───────────────────────────────────────────────────
def test_rrf_fuse_tier_takes_best_source() -> None:
    res = rrf_fuse([_res(["a"], tier=VTIER_FTS), _res(["b"], tier=VTIER_FTS_VECTOR)])
    assert res.evidence.tier == VTIER_FTS_VECTOR


# ── ⑥ 召回多源分派：2 源走 RRF ──────────────────────────────────────────
def test_recall_two_sources_goes_through_rrf() -> None:
    g = InMemoryGraphStore(_M_PREDS, [
        GraphEdge(from_id="subj-1", to_id="dec-shared",
                  predicate="REFERENCED_PRECEDENT"),
    ])
    notes = InMemoryNoteStore()
    notes.upsert(_note("dec-shared", "dec-shared token"))
    res = recall_precedents(["dec-shared"], graph=g, subject_id="subj-1",
                            notes=notes)
    joined = " ".join(res.evidence.notes)
    assert "RRF 融合 2 源" in joined, f"两源须走 RRF，实得 {res.evidence.notes}"
    assert res.items and res.items[0].key == "dec-shared"


# ── ⑦ 单源留痕「不经 RRF 融合」──────────────────────────────────────────
def test_recall_single_source_skips_rrf_with_trace() -> None:
    notes = InMemoryNoteStore()
    notes.upsert(_note("n-1", "alpha token"))
    res = recall_precedents(["alpha"], notes=notes)
    joined = " ".join(res.evidence.notes)
    assert "不经 RRF 融合" in joined, f"单源须留痕走降级路径，实得 {res.evidence.notes}"


# ── ⑧ top_k 截断 ────────────────────────────────────────────────────────
def test_rrf_fuse_respects_top_k() -> None:
    res = rrf_fuse([_res(["a", "b", "c", "d"])], top_k=2)
    assert [i.key for i in res.items] == ["a", "b"]
