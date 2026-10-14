"""WS3 决策脊柱审批闸单测 + 反假绿探针。

⛔ 探针 `test_probe_redline_priority_not_overridden_by_confidence` 是**判别力自证**：
   它断言「红线命中 + 高置信度 ⇒ 仍驳回」。若有人把 `RedlinePriorityGate` 的红线短路
   删掉（让高置信度覆盖红线），该用例必转红。详见 ws3 变异自证步骤。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.approval import (
    DecisionApprovalVerdict, DecisionPassThroughGate, RedlinePriorityGate,
)
from chiyu_kernel.contract.decision import RUBRIC_KEYS


def _good() -> dict:
    return {k: 4.0 for k in RUBRIC_KEYS}


def _verdict(**kw) -> DecisionApprovalVerdict:
    kw.setdefault("decision_id", "d")
    kw.setdefault("confidence", 0.9)
    kw.setdefault("redline_hit", False)
    kw.setdefault("redline_reasons", ())
    kw.setdefault("autonomous", True)
    kw.setdefault("rubric_missing", ())
    kw.setdefault("elements_missing", ())
    kw.setdefault("threshold", 0.79)
    return RedlinePriorityGate().decide(**kw)


def test_redline_priority_rejects_high_confidence():
    # A 红线优先 + 硬约束先于置信度：红线命中，置信度 0.99 也不豁免
    v = _verdict(redline_hit=True, confidence=0.99, autonomous=True,
                 redline_reasons=("卫生健康",))
    assert v.approved is False
    assert v.requires_human is True
    assert "红线" in v.reason


def test_no_redline_high_confidence_approved():
    v = _verdict(redline_hit=False, confidence=0.99, autonomous=True)
    assert v.approved is True


def test_missing_rubric_requires_human_even_if_autonomous():
    # 判据缺失 → 转人工，不因 autonomous=True 自动放行
    v = _verdict(redline_hit=False, confidence=0.99, autonomous=True,
                 rubric_missing=("r1",))
    assert v.approved is False
    assert v.requires_human is True


def test_low_confidence_requires_human():
    v = _verdict(redline_hit=False, confidence=0.5, autonomous=False)
    assert v.approved is False
    assert v.requires_human is True


def test_passthrough_approves():
    v = DecisionPassThroughGate().decide(
        decision_id="d", confidence=0.0, redline_hit=True, redline_reasons=("x",),
        autonomous=False, rubric_missing=("r",), elements_missing=(), threshold=0.79)
    assert v.approved is True


def test_probe_redline_priority_not_overridden_by_confidence():
    """反假绿探针：红线命中 + 置信度拉满，裁定必须为『不批准』。

    这是 WS3 的核心不变量（硬约束先于置信度）。变异自证时临时删除
    `RedlinePriorityGate.decide` 的 `if redline_hit:` 分支，本用例必须转红。
    """
    v = RedlinePriorityGate().decide(
        decision_id="probe", confidence=1.0, redline_hit=True,
        redline_reasons=("探针红线",), autonomous=True,
        rubric_missing=(), elements_missing=(), threshold=0.79)
    assert v.approved is False, "红线命中却被批准 ⇒ 硬约束先于置信度被破坏"
    assert v.requires_human is True
