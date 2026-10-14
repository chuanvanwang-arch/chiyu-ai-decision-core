"""T4·δ3/δ4 守卫：Action 表面注册表 R1–R6 —— 判别力自证。

上游依据：计划 Step 5-6（actions/registry R1-R6 + 判别力自证测试）。
⛔ 必须能**拒绝**：若注册表允许「同能力多 Action」「高危写无 force」
（demo `/api/retro/*` 一能力 4 端点的同族事故），以下用例必须红。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.actions.registry import (
    ACTION_MAX,
    ACTION_MIN,
    ActionRegistry,
    ActionSpec,
)

_NAMES = [f"submit_{i}" for i in range(ACTION_MAX + 2)]


def _registry_with(n: int, cap: str = "ingest") -> ActionRegistry:
    r = ActionRegistry()
    for i in range(n):
        r.register(ActionSpec(name=_NAMES[i], capability=f"{cap}_{i}"))
    return r


# ── R5：同一能力重复注册 ⇒ 注册期拒绝 ────────────────────────────────
def test_r5_duplicate_capability_is_rejected():
    r = ActionRegistry()
    r.register(ActionSpec(name="submit_request", capability="submit"))
    with pytest.raises(ValueError, match="R5"):
        r.register(ActionSpec(name="submit_batch", capability="submit"))


# ── R2：动词+对象命名 ────────────────────────────────────────────────
def test_r2_bad_name_is_a_violation():
    spec = ActionSpec(name="RequestSubmit", capability="submit")
    assert any("R2" in v for v in spec.violations())


# ── R6 双向：高危写缺 force / 非高危带 force ─────────────────────────
def test_r6_high_risk_without_force_is_a_violation():
    spec = ActionSpec(name="delete_record", capability="delete", mutating=True,
                      high_risk=True, has_force=False)
    assert any("R6 高危写缺 force" in v for v in spec.violations())


def test_r6_non_high_risk_with_force_is_a_violation():
    spec = ActionSpec(name="update_status", capability="status", mutating=True,
                      high_risk=False, has_force=True)
    assert any("R6 非高危动作不应带 force" in v for v in spec.violations())


# ── R1：数量闸（5–9）─────────────────────────────────────────────────
def test_r1_over_limit_is_an_error():
    r = _registry_with(ACTION_MAX + 1)
    errors, _ = r.audit()
    assert any("R1" in e for e in errors)


def test_r1_below_min_is_a_warning():
    r = _registry_with(ACTION_MIN - 1)
    errors, warnings = r.audit()
    assert not errors
    assert any("R1" in w for w in warnings)


def test_clean_surface_has_no_errors():
    r = _registry_with(ACTION_MIN + 2)
    errors, warnings = r.audit()
    assert errors == []
    assert warnings == []
