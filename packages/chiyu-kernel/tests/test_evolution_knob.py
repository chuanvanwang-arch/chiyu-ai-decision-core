"""T2 守卫：参数白名单 + 风险分档 + 放宽方向 —— 判别力自证。

⛔ 必须能**拒绝**：若 `autonomy_related=True` 却未声明 `widen_direction` 仍可构造，
   则平台可静默放宽自己的自主权阈值（自我扩权），且无人能检出方向。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.evolution.knob import (
    KnobError,
    KnobSpec,
    KnobTable,
    classify_change,
    is_forbidden_change,
)


def _autonomy_knob() -> KnobSpec:
    """自主权阈值：值变小 = 放宽（更容易自动放行）。"""
    return KnobSpec(name="gate", tier="auto", min_value=0.0, max_value=1.0,
                    default=0.79, widen_direction="down", autonomy_related=True)


def _cooldown_knob() -> KnobSpec:
    """冷却天数：值变小 = 收紧（更容易被冷却挡住），与自主权无关。"""
    return KnobSpec(name="cooldown", widen_direction="down", default=3.0)


# ── 构造期拒绝：把自我扩权拦在构造期 ──────────────────────────────────
def test_autonomy_knob_without_direction_is_rejected():
    with pytest.raises(KnobError, match="widen_direction"):
        KnobSpec(name="gate", autonomy_related=True)


def test_unknown_tier_is_rejected():
    with pytest.raises(KnobError, match="风险档"):
        KnobSpec(name="x", tier="maybe")


def test_inverted_bounds_is_rejected():
    with pytest.raises(KnobError, match="区间倒置"):
        KnobSpec(name="x", min_value=9.0, max_value=1.0)


def test_default_out_of_bounds_is_rejected():
    with pytest.raises(KnobError, match="兜底值"):
        KnobSpec(name="x", min_value=0.0, max_value=1.0, default=2.0)


# ── 方向判定：同一方向在不同参数上语义相反 ────────────────────────────
def test_direction_depends_on_declared_semantics():
    assert classify_change(_autonomy_knob(), 0.79, 0.50) == "widen"
    assert classify_change(_autonomy_knob(), 0.50, 0.90) == "tighten"
    assert classify_change(_cooldown_knob(), 3.0, 1.0) == "widen"      # 变小也是 widen
    assert classify_change(_cooldown_knob(), 3.0, 3.0) == "flat"


def test_non_numeric_or_undeclared_is_flat():
    assert classify_change(_cooldown_knob(), "a", "b") == "flat"
    plain = KnobSpec(name="label")                                     # 未声明方向
    assert classify_change(plain, 1, 2) == "flat"


# ── G1：放宽永不自动 ──────────────────────────────────────────────────
def test_widen_of_autonomy_knob_is_forbidden():
    spec = _autonomy_knob()
    assert is_forbidden_change(spec, "widen") is True


def test_tighten_of_autonomy_knob_is_allowed():
    """收紧可自动 —— 非对称护栏的另一半（否则平台永远无法自愈）。"""
    assert is_forbidden_change(_autonomy_knob(), "tighten") is False


def test_unrelated_knob_widen_is_not_forbidden_by_g1():
    assert is_forbidden_change(_cooldown_knob(), "widen") is False


def test_forbidden_tier_and_redline_are_always_forbidden():
    spec = KnobSpec(name="locked", tier="forbidden")
    assert is_forbidden_change(spec, "flat") is True
    assert is_forbidden_change(_cooldown_knob(), "flat", redline_hit=True) is True


# ── 白名单三条硬化 ────────────────────────────────────────────────────
def test_unknown_keys_are_ignored_and_reported():
    table = KnobTable([_autonomy_knob()])
    out, rejected = table.read({"gate": 0.6, "shadow_key": 1})
    assert out == {"gate": 0.6}
    assert any("shadow_key" in r and "非白名单" in r for r in rejected)


def test_illegal_value_falls_back_to_default_and_leaves_trace():
    table = KnobTable([_autonomy_knob()])
    out, rejected = table.read({"gate": 9.9})          # 越界
    assert out == {"gate": 0.79}                       # 回落出厂兜底
    assert rejected and "上限" in rejected[0]


def test_missing_key_falls_back_to_default():
    table = KnobTable([_autonomy_knob()])
    out, rejected = table.read({})
    assert out == {"gate": 0.79}
    assert rejected == []                              # 未配不算脏配置


def test_duplicate_registration_and_unknown_lookup_raise():
    with pytest.raises(KnobError, match="重复注册"):
        KnobTable([_autonomy_knob(), _autonomy_knob()])
    table = KnobTable([_autonomy_knob()])
    with pytest.raises(KnobError, match="非白名单参数"):
        table.spec("nope")


def test_clean_config_produces_no_rejection():
    table = KnobTable([_autonomy_knob(), _cooldown_knob()])
    out, rejected = table.read({"gate": 0.8, "cooldown": 5})
    assert rejected == []
    assert out == {"gate": 0.8, "cooldown": 5}
