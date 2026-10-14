"""T7 守卫：只读护栏 G2 / G3 —— 判别力自证。

⛔ 反向用例是重点：只读前缀必须真的拦得住写入尝试，而不是只出现在文档里。
   追认记录（设计稿 §12.7）明确：护栏被绕过 ⇒ 追认自动失效。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.evolution.guard import (
    READONLY_PATH_PREFIXES,
    GuardViolation,
    assert_not_baseline_skill,
    assert_writable,
    g2_suspend_on_redline,
    meta_redline_hits,
)


# ── G3：L0 契约目录物理只读 ───────────────────────────────────────────
def test_contract_path_is_readonly():
    with pytest.raises(GuardViolation, match="只读路径"):
        assert_writable("chiyu_kernel.contract.decision")


def test_contract_subpath_is_readonly():
    with pytest.raises(GuardViolation, match="只读路径"):
        assert_writable("chiyu_kernel.contract.evolution.SPINE_ORDER")


def test_baseline_skill_dir_is_readonly():
    with pytest.raises(GuardViolation, match="只读路径"):
        assert_writable("skills/ai-memory-lifecycle")


def test_normal_path_is_writable():
    assert assert_writable("skills/method-quote-engine") == "skills/method-quote-engine"
    assert assert_writable("config/runtime.json") == "config/runtime.json"


def test_empty_path_is_rejected():
    with pytest.raises(GuardViolation, match="为空"):
        assert_writable("   ")


# ── G3：基线命名空间 ──────────────────────────────────────────────────
def test_baseline_namespace_is_rejected():
    with pytest.raises(GuardViolation, match="基线命名空间"):
        assert_not_baseline_skill("ai-memory-lifecycle")


def test_new_namespace_is_accepted():
    assert assert_not_baseline_skill("method-quote-engine") == "method-quote-engine"


# ── G2：红线命中 ⇒ 挂起 ───────────────────────────────────────────────
def test_redline_hit_forces_suspend():
    assert g2_suspend_on_redline(True) is True
    assert g2_suspend_on_redline(False) is False
    assert g2_suspend_on_redline("") is False    # 假值不当真（不猜语义）


# ── 元红线检出（供次日报告）──────────────────────────────────────────
def test_meta_redlines_are_detected():
    hits = meta_redline_hits(["knob_tune", "threshold_widen", "baseline_write",
                              "redline_auto", "unknown_action"])
    assert set(hits) == {"threshold_widen", "baseline_write", "redline_auto"}


def test_no_meta_redline_returns_empty():
    assert meta_redline_hits(["knob_tune"]) == []


# ── 守卫自身不得空跑 ──────────────────────────────────────────────────
def test_readonly_prefixes_are_non_empty_and_specific():
    assert len(READONLY_PATH_PREFIXES) >= 2
    assert any("contract" in p for p in READONLY_PATH_PREFIXES)
