"""S1 装配钩子 + S4 域红线回调钩子（缺口收敛到 foundation 的公共形态）。

判据：
- S4 ``redline_callback`` 是通用可选形参，替代 ``evaluate_redline`` 的目录匹配；
  域逻辑（tier 分档 / 人工在环）由消费方在回调内实现，基座不持领域字面量。
- S1 ``context_factory`` 是通用可选形参，在 S1_context 校验前装配 context；
  仅当消费方要 run_spine 持有装配编排时需要（可选架构对称诉求）。
- 两者严格加法：不传时行为与现状完全一致（回归保护）。
"""
from __future__ import annotations

from chiyu_decision.api import RedlineVerdict, run_spine
from chiyu_kernel.contract.decision import RUBRIC_KEYS


def _good_scores() -> dict:
    return {k: 4.0 for k in RUBRIC_KEYS}


# ---- S4 域红线回调钩子 ----

def test_redline_callback_overrides_directory_match():
    """回调返回未命中 ⇒ 即使 context 含目录词也不命中（回调替代目录匹配）。"""
    def _cb(context, redline_items):
        return RedlineVerdict(hit=False, reasons=())
    res = run_spine(
        context={"text": "卫生健康", "decision_id": "r1"}, profile=None,
        rubric_scores=_good_scores(), elements={},
        redline_items=("卫生健康",), redline_callback=_cb,
    )
    assert res.redline_hit is False, "redline_callback 未生效：仍走了目录匹配"


def test_redline_callback_detects_domain_redline():
    """回调基于域逻辑命中 ⇒ redline_hit=True（证明回调式域红线生效）。"""
    def _cb(context, redline_items):
        hit = "禁售" in context.get("text", "")
        return RedlineVerdict(hit=hit, reasons=("DOMAIN_FORBID",) if hit else ())
    res = run_spine(
        context={"text": "该供应商禁售", "decision_id": "r2"}, profile=None,
        rubric_scores=_good_scores(), elements={}, redline_callback=_cb,
    )
    assert res.redline_hit is True


def test_redline_callback_absent_uses_directory():
    """不传 redline_callback ⇒ 仍走 evaluate_redline 目录匹配（严格加法回归）。"""
    res = run_spine(
        context={"text": "卫生健康", "decision_id": "r3"}, profile=None,
        rubric_scores=_good_scores(), elements={}, redline_items=("卫生健康",),
    )
    assert res.redline_hit is True


# ---- S1 装配钩子 ----

def test_context_factory_assembles_before_s1():
    """context_factory 装配的 context 被后续阶段使用（如 decision_id）。"""
    def _assemble(seed):
        return dict(seed, decision_id="assembled-1", text="普通")
    captured = {}
    res = run_spine(
        context={"seed": True}, profile=None,
        rubric_scores=_good_scores(), elements={}, context_factory=_assemble,
    )
    assert res.decision_id == "assembled-1", "context_factory 装配未生效"


def test_context_factory_absent_unchanged():
    """不传 context_factory ⇒ 直接用传入 context（严格加法回归）。"""
    res = run_spine(
        context={"text": "普通", "decision_id": "r4"}, profile=None,
        rubric_scores=_good_scores(), elements={},
    )
    assert res.decision_id == "r4"
