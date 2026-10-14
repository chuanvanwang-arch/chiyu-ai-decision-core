"""向量覆盖率与存量回填 —— 写时物化的**监控闭环**。

⛔ 为什么覆盖率必须是可查指标而不是日志：
   "降级不中断"是好事，但降级**静默**就是坏事——真向量通道断了以后，
   系统照常运转、检索结果缓慢变差，直到有人发现"怎么搜都不准"。覆盖率
   是把这件事变成数字的**唯一**手段（demo 审计 §P2-1 记的正是这个缺口）。

口径（可执行）：
   coverage = 有真向量(provider 非 hash) 的粒子数 / 应物化粒子数
   min_coverage 由 profile 声明（默认 0.8）；低于阈值 ⇒ vector_degraded=True
   ⛔ 分母是"应物化"（类型在 profile.vectorized_types 内），不是"全部粒子"
      —— 否则不参与语义检索的粒子会稀释指标，覆盖率永远达不到阈值。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

DEFAULT_MIN_COVERAGE = 0.8
HASH_PROVIDER = "hash"


@dataclass(frozen=True)
class CoverageReport:
    expected: int
    materialized: int
    hash_fallback: int
    min_coverage: float

    @property
    def coverage(self) -> float:
        return (self.materialized / self.expected) if self.expected else 1.0

    @property
    def degraded(self) -> bool:
        return self.coverage < self.min_coverage

    def as_metrics(self) -> Mapping[str, float]:
        return {
            "vector_coverage": round(self.coverage, 4),
            "vector_expected": float(self.expected),
            "vector_materialized": float(self.materialized),
            "vector_hash_fallback": float(self.hash_fallback),
            "vector_degraded": 1.0 if self.degraded else 0.0,
        }


def compute_coverage(rows: Iterable[Mapping], min_coverage: float = DEFAULT_MIN_COVERAGE) -> CoverageReport:
    """rows 形如 [{"provider": "model"|"model-p384"|"hash"|None}, ...]（仅应物化粒子）。"""
    expected = 0
    materialized = 0
    fallback = 0
    for r in rows:
        expected += 1
        prov = r.get("provider")
        if prov is None or prov == HASH_PROVIDER:
            fallback += 1
        else:
            materialized += 1
    return CoverageReport(expected, materialized, fallback, min_coverage)


def backfill_plan(rows: Iterable[Mapping], limit: int = 500) -> list:
    """待回填清单（有 provider=hash 或 None 的粒子 id），按 limit 截断。

    ⛔ 只产出计划不执行写入 —— 回填是**写操作**，须经决策第 0 闸（本项目纪律）。
    """
    out = []
    for r in rows:
        if r.get("provider") in (None, HASH_PROVIDER):
            out.append(r.get("particle_id"))
        if len(out) >= limit:
            break
    return [x for x in out if x]


__all__ = ["CoverageReport", "compute_coverage", "backfill_plan",
           "DEFAULT_MIN_COVERAGE", "HASH_PROVIDER"]
