"""T6 守卫：方法论草稿闸 + 命名空间隔离 —— 判别力自证。

⛔ 两条最关键的反向用例：
   ① 落入基线命名空间的草稿必须被拒（基线不得新增/删除/重编号）；
   ② verdict 非 pass 的晋升必须抛（"草稿绝不自动生效"的机器形式）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.evolution.skill_draft import (
    SkillDraft,
    SkillDraftError,
    promote,
    validate_draft,
)

KNOWN = ("submit_request", "sync_particle")


def _draft(name="quote-engine", ns="method", calls=("submit_request",)) -> SkillDraft:
    return SkillDraft(name=name, namespace=ns, calls_actions=calls)


# ── 命名空间隔离 ──────────────────────────────────────────────────────
def test_baseline_namespace_is_rejected():
    d = _draft(ns="ai", name="memory-lifecycle")     # fq = "ai-memory-lifecycle"
    assert d.is_baseline() is True
    verdict, errs = validate_draft(d, action_names=KNOWN)
    assert verdict == "reject"
    assert any("基线命名空间" in e for e in errs)


def test_namespace_outside_allowed_set_is_rejected():
    d = _draft(ns="random")
    verdict, errs = validate_draft(d, action_names=KNOWN)
    assert verdict == "reject"
    assert any("不在允许集" in e for e in errs)


def test_new_namespace_is_accepted():
    verdict, errs = validate_draft(_draft(), action_names=KNOWN)
    assert verdict == "pass" and errs == []


# ── 所调动作必须已注册 ────────────────────────────────────────────────
def test_unknown_action_is_rejected():
    d = _draft(calls=("ghost_action",))
    verdict, errs = validate_draft(d, action_names=KNOWN)
    assert verdict == "reject"
    assert any("未注册" in e for e in errs)


def test_empty_calls_is_rejected_not_passed():
    """未声明所调动作 = 无可校验对象 ⇒ 拒绝（不是"没查出错就放行"）。"""
    d = _draft(calls=())
    verdict, errs = validate_draft(d, action_names=KNOWN)
    assert verdict == "reject"
    assert any("无可校验对象" in e for e in errs)


def test_empty_name_is_rejected():
    verdict, _ = validate_draft(_draft(name="  "), action_names=KNOWN)
    assert verdict == "reject"


# ── 晋升闸 ────────────────────────────────────────────────────────────
def test_promote_with_reject_verdict_raises():
    with pytest.raises(SkillDraftError, match="禁止晋升"):
        promote(_draft(), verdict="reject")


def test_promote_with_pass_verdict_succeeds():
    d = promote(_draft(), verdict="pass")
    assert d.status == "validated"
    assert d.fq_name() == "method-quote-engine"


def test_double_promote_is_rejected():
    d = promote(_draft(), verdict="pass")
    with pytest.raises(SkillDraftError, match="仅 draft 可晋升"):
        promote(d, verdict="pass")


def test_promote_of_missing_verdict_is_rejected():
    """没给结论 ⇒ 不得晋升（默认保守，与处方的 fail-safe 同口径）。"""
    with pytest.raises(SkillDraftError):
        promote(_draft(), verdict="")
