"""多源召回融合（T42：memory 毕业批次三）—— RRF（Reciprocal Rank Fusion）。

⛔ 为何用 RRF 而不是分数归一：各源 `score` **量纲不同档**——向量档是余弦
   （0~1）、FTS 档是子串命中数（0~n）。跨源直接比分数等于把不同量纲相加，
   得到的是**伪精确**的排序。RRF 只用**名次**：

       score(d) = Σ_sources  1 / (k + rank_source(d))

   量纲无关、无需校准，是融合异构排序源的标准做法（k 默认 60 为常用取值）。

⛔ 诚实留痕（防「融合了却看不出是哪档」的假绿）：
   · 融合结果的 `tier` = 参与源中**最好**的档位（按 `VTIER_ORDER` 次序）；
   · `notes` 显式列出源数、各源档位与 k 值；
   · `pool_size` 为各源之和，`embedding_coverage` 按池大小加权平均（不简单取
     算术平均，避免小池把覆盖率拉高）。

⛔ 空源语义：无任何源 ⇒ 显式 `VTIER_NONE` 空结果（不伪造候选）——与
   `degraded_recall` 的空池语义一致。
"""
from __future__ import annotations

from typing import Sequence

from .retrieval import (
    RecalledItem, RetrievalEvidence, RetrievalResult, VTIER_NONE, VTIER_ORDER,
)

__all__ = ["RRF_K_DEFAULT", "rrf_fuse"]

#: RRF 平滑常数（越大 ⇒ 名次差异越被平滑；60 为常见默认）
RRF_K_DEFAULT = 60

_ORDER_INDEX = {t: i for i, t in enumerate(VTIER_ORDER)}


def rrf_fuse(results: Sequence[RetrievalResult], *,
             k: int = RRF_K_DEFAULT,
             top_k: int = 10) -> RetrievalResult:
    """多源 RRF 融合：名次倒数加权求和 → 统一 `RetrievalResult`。

    同 key 出现在多源时累加各自名次贡献（被多源同时召中 ⇒ 排名更靠前，
    这正是 RRF 的预期行为）。`fts_hits` 取各源最大值（命中数是事实，不叠加）。
    """
    if not results:
        return RetrievalResult((), RetrievalEvidence(
            tier=VTIER_NONE, pool_size=0, vector_used=False,
            fts_prefiltered=False, embedding_coverage=0.0,
            notes=("RRF 融合源为空 ⇒ 显式空结果（不伪造候选）",)))

    acc: dict = {}
    total_pool = 0
    vector_used = False
    fts_prefiltered = False
    cov_weighted = 0.0
    src_tiers: list = []
    best_tier: str = VTIER_NONE

    for r in results:
        ev = r.evidence
        total_pool += ev.pool_size
        vector_used = vector_used or ev.vector_used
        fts_prefiltered = fts_prefiltered or ev.fts_prefiltered
        cov_weighted += float(ev.embedding_coverage) * int(ev.pool_size)
        src_tiers.append(ev.tier)
        if _ORDER_INDEX.get(ev.tier, len(VTIER_ORDER)) < _ORDER_INDEX.get(
                best_tier, len(VTIER_ORDER)):
            best_tier = ev.tier
        for rank, item in enumerate(r.items):
            slot = acc.setdefault(item.key, {"score": 0.0, "fts": 0})
            slot["score"] += 1.0 / (k + rank + 1)
            slot["fts"] = max(slot["fts"], item.fts_hits)

    ordered = sorted(acc.items(), key=lambda kv: (-kv[1]["score"], kv[0]))
    items = tuple(RecalledItem(key=key, score=v["score"], fts_hits=v["fts"])
                  for key, v in ordered[:max(0, int(top_k))])
    coverage = cov_weighted / total_pool if total_pool else 0.0
    notes = (f"RRF 融合 {len(results)} 源（各源档位：{', '.join(src_tiers)}；k={k}）",)
    return RetrievalResult(items, RetrievalEvidence(
        tier=best_tier, pool_size=total_pool, vector_used=vector_used,
        fts_prefiltered=fts_prefiltered, embedding_coverage=coverage,
        notes=notes))
