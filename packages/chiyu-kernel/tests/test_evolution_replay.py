"""T3 守卫：影子重放 —— 判别力自证。

⛔ 最关键的一条是**空样本必须 reject**：若空缺返回 pass，夜批恰好在没攒够样本的
   那些天会全量盲改，而守卫看上去是绿的（经典假绿）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.evolution.replay import BASELINE_FIELD, shadow_replay


def _formula(p):
    """与运行引擎同源的形态：得分 ≥ 阈值即放行。"""
    return p["score"] >= p["threshold"]


def _sample(score, expected, **extra):
    return {**extra, "score": score, BASELINE_FIELD: expected}


# ── 空样本 / 样本不足 ⇒ 拒绝（不得静默通过）─────────────────────────
def test_empty_samples_is_rejected_not_passed():
    v = shadow_replay([], _formula, {"threshold": 0.5})
    assert v.verdict == "reject"
    assert v.ok is False
    assert "blind patch" in v.reason


def test_below_min_samples_is_rejected():
    samples = [_sample(0.9, True)]
    v = shadow_replay(samples, _formula, {"threshold": 0.5}, min_samples=3)
    assert v.verdict == "reject"
    assert v.checked == 1                      # 已检样本数仍如实上报


# ── 正常通过 ──────────────────────────────────────────────────────────
def test_matching_replay_passes():
    samples = [
        _sample(0.9, True, threshold=0.5),
        _sample(0.1, False, threshold=0.5),
    ]
    v = shadow_replay(samples, _formula, {"threshold": 0.5})
    assert v.verdict == "pass" and v.checked == 2 and v.mismatches == []


def test_numeric_tolerance_accepts_float_noise():
    def f(p):
        return p["x"] * 0.1
    samples = [{"x": 3, BASELINE_FIELD: 0.3}]
    assert shadow_replay(samples, f, {}).verdict == "pass"


# ── 失配检出（含"缺基线不跳过"）──────────────────────────────────────
def test_mismatch_is_detected():
    samples = [_sample(0.9, False, threshold=0.5)]     # 基线写错：0.9 应放行
    v = shadow_replay(samples, _formula, {"threshold": 0.5})
    assert v.verdict == "reject" and len(v.mismatches) == 1


def test_missing_baseline_counts_as_mismatch_not_skip():
    """跳过缺基线的样本 ⇒ "没有基线"会伪装成"全部通过"。"""
    samples = [{"score": 0.9}]                          # 无 __expected
    v = shadow_replay(samples, _formula, {"threshold": 0.5})
    assert v.verdict == "reject"
    assert any("基线" in m for m in v.mismatches)


def test_formula_exception_is_fail_safe_reject():
    def boom(p):
        raise RuntimeError("引擎炸了")
    samples = [_sample(0.9, True)]
    v = shadow_replay(samples, boom, {})
    assert v.verdict == "reject" and any("异常" in m for m in v.mismatches)


# ── 禁字符串公式 ──────────────────────────────────────────────────────
def test_non_callable_formula_is_rejected():
    v = shadow_replay([_sample(0.9, True)], "score >= threshold", {})
    assert v.verdict == "reject"
    assert "字符串公式" in v.reason


# ── 新参数确实参与重算（守卫不得空跑）─────────────────────────────────
def test_new_params_actually_change_the_outcome():
    samples = [_sample(0.9, True, threshold=0.5)]       # 旧阈值下放行
    v = shadow_replay(samples, _formula, {"threshold": 0.95})
    assert v.verdict == "reject"                        # 新阈值下应被拦 ⇒ 检出漂移
