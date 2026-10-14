"""三级降级召回（SKILL #4 L2 历史决策）—— 内核版，去领域化。

抽取自 demo `context/retrieval.py`（2026-09-21，P1 T4）。顺序**写死**：

    1. `fts+vector`  FTS 预过滤 + 池内向量排序（理想）
    2. `vector`      纯向量排序（FTS 0 命中时放宽）
    3. `fts`         纯 FTS 排序（无向量 / 向量 0 命中）

每次调用返回 `retrieval` 自证（tier / vectorUsed / ftsPrefiltered /
embeddingCoverage / notes）——防「降级但没记录」的假绿（红线 ④）。

⛔ 诚实声明（防「注释声称≠已实现」）：
  - FTS 档位是**代理口径**（查询词子串命中数），中文短文本无分词器；
  - 向量档位在 `query_vector` 缺失时**如实降级**，不伪造语义分。

对接 assembly：`to_supply_layer(result, layer=...)` 把结果转成 `assemble()` 的
供给侧 `{layer: [{"dim":..., "key":..., "value":...}]}` 形态。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

# Batch-2a（GAP-2）：三级降级召回档位与阈值上收
# `chiyu_kernel/contract/context.py`（sanctioned 契约面单一事实源）。
from chiyu_kernel.contract.context import (
    MIN_EMBEDDING_COVERAGE,
    TIER_FTS,
    TIER_FTS_VECTOR,
    TIER_NONE,
    TIER_ORDER,
    TIER_VECTOR,
    VTIER_FTS,
    VTIER_FTS_VECTOR,
    VTIER_NONE,
    VTIER_ORDER,
    VTIER_VECTOR,
)


@dataclass(frozen=True)
class RecalledItem:
    """单条召回结果。`score` 语义随档位变化（向量档=余弦，FTS 档=命中数）。"""

    key: str
    score: float
    fts_hits: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "score": round(self.score, 6), "ftsHits": self.fts_hits}


@dataclass(frozen=True)
class RetrievalEvidence:
    """`retrieval` 自证：降级必须留痕（红线 ④）。"""

    tier: str
    pool_size: int
    vector_used: bool
    fts_prefiltered: bool
    embedding_coverage: float
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "poolSize": self.pool_size,
            "vectorUsed": self.vector_used,
            "ftsPrefiltered": self.fts_prefiltered,
            "embeddingCoverage": round(float(self.embedding_coverage), 6),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class RetrievalResult:
    items: tuple[RecalledItem, ...]
    evidence: RetrievalEvidence

    def to_dict(self) -> dict[str, Any]:
        return {"items": [i.to_dict() for i in self.items],
                "retrieval": self.evidence.to_dict()}


def to_supply_layer(result: RetrievalResult, *,
                    layer: str = "L2", dim: str = "precedent") -> dict:
    """（+T4 对接）检索结果 → `assemble()` 供给侧形态。

    返回 `{layer: [{"dim": dim, "key": item.key, "value": item.score}, ...]}`。
    """
    return {layer: [
        {"dim": dim, "key": item.key, "value": item.score}
        for item in result.items
    ]}


def _fts_hits(terms: Sequence[str], text: str) -> int:
    """FTS 代理口径：查询词在文本中的子串命中数（无分词器，显式声明为代理）。"""
    if not text:
        return 0
    low = str(text).lower()
    return sum(1 for t in terms if t and str(t).lower() in low)


def _cosine(a: Optional[Sequence[float]], b: Any) -> float:
    """余弦相似度。任一为空/长度不等/零模 → 0.0（不抛异常）。"""
    if not isinstance(a, (list, tuple)) or not isinstance(b, (list, tuple)):
        return 0.0
    if len(a) == 0 or len(a) != len(b):
        return 0.0
    try:
        dot = sum(float(x) * float(y) for x, y in zip(a, b))
        na = math.sqrt(sum(float(x) * float(x) for x in a))
        nb = math.sqrt(sum(float(y) * float(y) for y in b))
    except (TypeError, ValueError):
        return 0.0
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (na * nb)


def degraded_recall(
    query_terms: Sequence[str],
    pool: Optional[Sequence[Mapping[str, Any]]],
    *,
    query_vector: Optional[Sequence[float]] = None,
    top_k: int = 10,
    min_coverage: float = MIN_EMBEDDING_COVERAGE,
) -> RetrievalResult:
    """L2 三级降级召回。

    `pool` 元素契约（缺键按缺失处理，不伪造）：
      - `key`    : str  稳定标识（回链粒子 identity）
      - `text`   : str  参与 FTS 预过滤的文本
      - `vector` : list[float] | None  参与池内排序的向量

    `query_vector` 为 None ⇒ 真向量通道未就绪 ⇒ 如实降级到 `fts` 档并留痕。
    """
    rows = [r for r in (pool or []) if isinstance(r, Mapping)]
    terms = [str(t).strip() for t in (query_terms or []) if str(t).strip()]
    n = len(rows)
    if n == 0:
        return RetrievalResult((), RetrievalEvidence(
            tier=TIER_NONE, pool_size=0, vector_used=False, fts_prefiltered=False,
            embedding_coverage=0.0,
            notes=("召回池为空（L2 记忆语料尚未落地）",)))

    vectors = [r.get("vector") for r in rows]
    with_vec = sum(1 for v in vectors if isinstance(v, (list, tuple)) and len(v) > 0)
    coverage = with_vec / n
    vector_usable = query_vector is not None and with_vec > 0

    hits = [_fts_hits(terms, str(r.get("text") or "")) for r in rows]
    n_hit = sum(1 for h in hits if h >= 1)
    scores = [_cosine(query_vector, v) if vector_usable else 0.0 for v in vectors]
    vec_positive = any(s > 0.0 for s in scores)

    notes: list[str] = []
    if not vector_usable:
        notes.append("查询向量未提供或池内无向量 → 真向量通道未就绪，如实降级")
    if coverage < min_coverage:
        notes.append(f"向量覆盖率 {coverage:.0%} < {min_coverage:.0%}，结果可靠性低")

    def _key(i: int) -> str:
        return str(rows[i].get("key") or i)

    # ── 档位选择：写死顺序 1→2→3，任一失败不抛 ──────────────────────
    if vector_usable and n_hit > 0 and vec_positive:
        tier = TIER_FTS_VECTOR
        cand = [i for i in range(n) if hits[i] >= 1]
        order = sorted(cand, key=lambda i: (-scores[i], -hits[i], _key(i)))
    elif vector_usable and n_hit == 0 and vec_positive:
        tier = TIER_VECTOR
        notes.append("FTS 0 命中，按降级链放宽为纯向量排序")
        order = sorted(range(n), key=lambda i: (-scores[i], -hits[i], _key(i)))
    else:
        tier = TIER_FTS
        if vector_usable:
            notes.append("向量 0 命中，退化为纯 FTS 排序")
        order = sorted(range(n), key=lambda i: (-hits[i], _key(i)))
        # FTS 亦 0 命中 ⇒ 显式空结果（不伪造候选）
        if n_hit == 0:
            notes.append("FTS 0 命中且无可用向量 → 本次无候选（显式空，不伪造）")
            return RetrievalResult((), RetrievalEvidence(
                tier=tier, pool_size=n, vector_used=False, fts_prefiltered=False,
                embedding_coverage=coverage, notes=tuple(notes)))
        order = [i for i in order if hits[i] >= 1]

    use_vec_score = tier in (TIER_FTS_VECTOR, TIER_VECTOR)
    items = tuple(
        RecalledItem(key=_key(i),
                     score=float(scores[i]) if use_vec_score else float(hits[i]),
                     fts_hits=hits[i])
        for i in order[:max(0, int(top_k))]
    )
    return RetrievalResult(items, RetrievalEvidence(
        tier=tier, pool_size=n, vector_used=use_vec_score,
        fts_prefiltered=(tier == TIER_FTS_VECTOR),
        embedding_coverage=coverage, notes=tuple(notes)))


__all__ = [
    "VTIER_FTS_VECTOR", "VTIER_VECTOR", "VTIER_FTS", "VTIER_NONE", "VTIER_ORDER",
    "TIER_FTS_VECTOR", "TIER_VECTOR", "TIER_FTS", "TIER_NONE", "TIER_ORDER",
    "RecalledItem", "RetrievalEvidence", "RetrievalResult",
    "degraded_recall", "to_supply_layer",
]
