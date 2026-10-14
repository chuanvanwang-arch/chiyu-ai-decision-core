"""覆盖率指标守卫：必须能区分「真向量」与「哈希降级」。"""
from __future__ import annotations

from chiyu_kernel.vector.coverage import backfill_plan, compute_coverage


def test_full_coverage_is_not_degraded():
    rows = [{"particle_id": "a", "provider": "model"},
            {"particle_id": "b", "provider": "model-p384"}]
    rep = compute_coverage(rows, min_coverage=0.8)
    assert rep.coverage == 1.0 and rep.degraded is False


def test_hash_fallback_makes_it_degraded():
    rows = [{"particle_id": "a", "provider": "model"},
            {"particle_id": "b", "provider": "hash"},
            {"particle_id": "c", "provider": None},
            {"particle_id": "d", "provider": "model-p384"},
            {"particle_id": "e", "provider": "model"}]
    rep = compute_coverage(rows, min_coverage=0.8)
    assert rep.coverage == 0.6 and rep.degraded is True
    assert rep.as_metrics()["vector_degraded"] == 1.0


def test_empty_denominator_is_not_zero_coverage():
    """⛔ 分母为 0 时不得报 0（否则无粒子阶段恒报红，指标失去意义）。"""
    assert compute_coverage([], 0.8).coverage == 1.0


def test_backfill_plan_lists_only_fallbacks():
    rows = [{"particle_id": "a", "provider": "model"},
            {"particle_id": "b", "provider": "hash"},
            {"particle_id": "c", "provider": None}]
    assert backfill_plan(rows) == ["b", "c"]
    assert backfill_plan(rows, limit=1) == ["b"]
