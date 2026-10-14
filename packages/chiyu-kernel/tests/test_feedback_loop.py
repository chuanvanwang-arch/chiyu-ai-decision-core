"""GAP-6 feedback_loop 守卫（Batch-2b，2026-10-14）。

覆盖：指标模板资格断言（B1）/ 安全表达式子集 / 加权评估三档 + undecidable
第三态（B2/B7）/ fail-closed 求值 / 拒绝出方守卫（B4）/ HITL 校准闸（B3）/
连通性统计双条件 / 门面与契约同一对象 / APS 锚点 parity 形态。

parity 锚点（APS 仓只读，file:line 可反证）：
    · ``platform/feedback_loop.py:97``   REQUIRED_KEYS 七要素资格断言
    · ``platform/feedback_loop.py:224``  evaluate 三档 + undecidable
    · ``platform/feedback_loop.py:287``  propose_calibration 拒绝出方守卫
    · ``platform/feedback_loop.py:342``  approve_calibration 仅 pending→approved
    · ``platform/feedback_loop.py:366``  calibration_stats 双条件连通性
"""
from __future__ import annotations

import pytest

from chiyu_kernel import api
from chiyu_kernel import feedback
from chiyu_kernel.contract import feedback_loop as contract_fl
from chiyu_kernel.contract.feedback_loop import (
    CalibrationStateError,
    ExpressionError,
    FeedbackTemplateError,
)
from chiyu_kernel.feedback import (
    EvalItem,
    EvaluatorSpec,
    MetricTemplate,
    approve_transition,
    assert_template_complete,
    calibration_stats,
    evaluate,
    expression_variables,
    prescribe_guard,
    safe_eval,
)


def _tmpl(**over) -> MetricTemplate:
    base = dict(
        metric_template_id="mt-1", loop="demo", name="按时率", type="ratio",
        direction="higher_better", formula="on_time/total", target={"min": 0.9},
        alert={"below": 0.8}, sources=["mes"], owner_agent="qa",
        evaluator_skill="ai-feedback-loop", adjust_actions=("retune",),
    )
    base.update(over)
    return MetricTemplate(**base)


# ── B1 指标模板资格断言 ────────────────────────────────────────────────

def test_template_complete_passes():
    assert_template_complete(_tmpl())  # 不抛即过


def test_template_missing_elements_rejected():
    tmpl = _tmpl(owner_agent="", adjust_actions=())
    with pytest.raises(FeedbackTemplateError, match="owner_agent.*adjust_actions"):
        assert_template_complete(tmpl)


def test_template_required_keys_are_contract_vocabulary():
    # 契约必填面 = APS REQUIRED_KEYS 同集（parity）
    assert set(contract_fl.METRIC_TEMPLATE_REQUIRED) == {
        "name", "loop", "type", "direction", "formula", "target", "alert",
        "sources", "owner_agent", "evaluator_skill", "adjust_actions",
    }


# ── 安全表达式子集 ────────────────────────────────────────────────────

def test_expression_variables_extracted():
    assert expression_variables("accuracy >= 0.9 and coverage > 0") == (
        "accuracy", "coverage")


def test_expression_variables_syntax_error_raises():
    with pytest.raises(ExpressionError):
        expression_variables("accuracy >=")


def test_safe_eval_allows_arithmetic_comparison_membership():
    assert safe_eval("a >= 0.9 and b < 3", {"a": 0.95, "b": 1}) is True
    assert safe_eval("a + 1 == 3", {"a": 2}) is True
    assert safe_eval("x in (1, 2, 3)", {"x": 2}) is True
    assert safe_eval("not flag", {"flag": False}) is True


def test_safe_eval_rejects_call_attribute_subscript():
    with pytest.raises(ExpressionError):
        safe_eval("__import__('os')", {})
    with pytest.raises(ExpressionError):
        safe_eval("abs(x)", {"x": -1})
    with pytest.raises(ExpressionError):
        safe_eval("x.y", {"x": 1})
    with pytest.raises(ExpressionError):
        safe_eval("x[0]", {"x": [1]})


def test_safe_eval_rejects_call_even_when_callable_in_variables():
    # 覆盖洞修复（MUTANT-5 实证）：上面的用例只走「未知函数名」路径，
    # 而 Call 节点在「函数名恰在变量表」时同样必须拒——否则求值面即成
    # 任意代码执行面（变量由调用方传入，含可调用对象是完全可能的）。
    with pytest.raises(ExpressionError):
        safe_eval("f(1)", {"f": len})


def test_safe_eval_unknown_variable_raises():
    with pytest.raises(ExpressionError, match="未提供变量"):
        safe_eval("missing > 1", {})


# ── B2/B7 加权评估 ────────────────────────────────────────────────────

def _spec(**over) -> EvaluatorSpec:
    base = dict(
        name="ev", loop="demo",
        items=(
            EvalItem(name="acc", weight=2, pass_rule="accuracy >= 0.9"),
            EvalItem(name="cov", weight=1, pass_rule="coverage >= 0.8"),
        ),
    )
    base.update(over)
    return EvaluatorSpec(**base)


def test_evaluate_all_pass_verdict_pass():
    out = evaluate(_spec(), {"accuracy": 0.95, "coverage": 0.85})
    assert out["score"] == 100.0
    assert out["verdict"] == "pass"
    assert out["undecidable"] is False


def test_evaluate_weighted_review_and_reject():
    # 阈值可注入：human_review=60 时 2/3 权重过（66.67）⇒ review
    spec = _spec(human_review=60)
    out = evaluate(spec, {"accuracy": 0.95, "coverage": 0.5})
    assert out["score"] == 66.67
    assert out["verdict"] == "review"
    # 1/3 权重过（33.33）⇒ reject
    out2 = evaluate(spec, {"accuracy": 0.5, "coverage": 0.85})
    assert out2["score"] == 33.33
    assert out2["verdict"] == "reject"
    # 默认阈值（70）下 66.67 仍判 reject —— 三档口径以契约为准
    out3 = evaluate(_spec(), {"accuracy": 0.95, "coverage": 0.5})
    assert out3["verdict"] == "reject"


def test_evaluate_missing_variable_is_undecidable_never_pass():
    # B7：coverage 缺失 ⇒ undecidable，即便 accuracy 满分也不得判 pass
    out = evaluate(_spec(), {"accuracy": 1.0})
    assert out["undecidable"] is True
    assert out["verdict"] == "undecidable"
    unqualified = [i for i in out["items"] if not i["qualified"]]
    assert unqualified and unqualified[0]["missing_vars"] == ["coverage"]
    assert unqualified[0]["passed"] is False


def test_evaluate_broken_expression_fails_closed():
    # 算不出的判据 ⇒ passed=False（fail-closed），不是异常上抛也不是算过
    spec = _spec(items=(EvalItem(name="bad", weight=1, pass_rule="accuracy / 0 > 1"),))
    out = evaluate(spec, {"accuracy": 0.5})
    assert out["items"][0]["passed"] is False
    assert out["verdict"] == "reject"


def test_evaluate_action_mapping_verdict_then_default():
    spec = _spec(actions={"pass": "auto_tune", "default": "notify"})
    assert evaluate(spec, {"accuracy": 0.95, "coverage": 0.85})["action"] == "auto_tune"
    out = evaluate(spec, {"accuracy": 0.5, "coverage": 0.5})
    assert out["action"] == "notify"


def test_evaluate_output_shape_matches_aps_anchor():
    # parity 形态守卫：与 APS feedback_loop.py:261-269 返回键集一致
    out = evaluate(_spec(), {"accuracy": 0.95, "coverage": 0.85})
    assert set(out) == {
        "evaluator", "loop", "score", "verdict", "undecidable", "items", "action",
    }


# ── B4 拒绝出方守卫 ───────────────────────────────────────────────────

def test_prescribe_guard_blocks_insufficient_sample():
    out = prescribe_guard(sample_size=5, coverage=0.9)
    assert out["status"] == "blocked"
    assert out["emit"] is False
    assert "样本量 5 < 门槛 30" in out["blocked_by"]


def test_prescribe_guard_blocks_low_coverage():
    out = prescribe_guard(sample_size=100, coverage=0.3)
    assert out["status"] == "blocked"
    assert out["emit"] is False
    assert "覆盖率 0.300 < 门槛 0.600" in out["blocked_by"]


def test_prescribe_guard_pending_when_thresholds_met():
    out = prescribe_guard(sample_size=30, coverage=0.6)
    assert out == {"status": "pending", "blocked_by": None, "emit": True}


def test_prescribe_guard_thresholds_injectable():
    out = prescribe_guard(sample_size=3, coverage=0.5, min_sample=2, min_coverage=0.4)
    assert out["status"] == "pending"


# ── B3 HITL 校准闸 ────────────────────────────────────────────────────

def test_approve_transition_pending_to_approved():
    assert approve_transition("pending") == "approved"


@pytest.mark.parametrize("bad", ["blocked", "approved", "rejected"])
def test_approve_transition_rejects_non_pending(bad):
    with pytest.raises(CalibrationStateError, match="不可重复裁决"):
        approve_transition(bad)


# ── 连通性统计（双条件，防"非空即通过"）─────────────────────────────

def test_calibration_stats_requires_rows_and_events():
    # 有候选无事件 ⇒ 不判绿
    assert calibration_stats(by_status={"pending": 2}, candidate_events=0)["closed_loop"] is False
    # 有事件无候选 ⇒ 不判绿
    assert calibration_stats(by_status={}, candidate_events=5)["closed_loop"] is False
    # 双条件齐备 ⇒ 绿
    out = calibration_stats(by_status={"pending": 1, "approved": 1}, candidate_events=2)
    assert out["closed_loop"] is True
    assert out["total"] == 2
    # 仅 blocked（拒绝出方）不算闭环候选
    assert calibration_stats(by_status={"blocked": 9}, candidate_events=3)["closed_loop"] is False


# ── 不变式清单 + 门面/契约同一对象 ───────────────────────────────────

def test_invariants_vocabulary_complete():
    assert set(contract_fl.FEEDBACK_INVARIANTS) == {
        "template_incomplete_rejected", "scope_dual_counting",
        "undecidable_never_pass", "blocked_never_emits",
        "hitl_only_to_approved", "repeat_adjudication_rejected",
    }


def test_facade_exports_all_feedback_symbols():
    names = [
        "METRIC_TEMPLATE_FIELDS", "METRIC_TEMPLATE_REQUIRED", "METRIC_SCOPES",
        "RUNTIME_SCOPE", "SEED_SCOPE", "EVAL_VERDICT_KINDS", "EVAL_VERDICT_PASS",
        "EVAL_VERDICT_REVIEW", "EVAL_VERDICT_REJECT", "EVAL_VERDICT_UNDECIDABLE",
        "CALIBRATION_STATUSES", "CALIBRATION_PENDING", "CALIBRATION_APPROVED",
        "CALIBRATION_BLOCKED", "CALIBRATION_MIN_SAMPLE", "CALIBRATION_MIN_COVERAGE",
        "DEFAULT_AUTO_PASS", "DEFAULT_HUMAN_REVIEW", "FEEDBACK_INVARIANTS",
        "FeedbackTemplateError", "CalibrationStateError", "ExpressionError",
        "MetricTemplate", "assert_template_complete", "missing_template_keys",
        "EvalItem", "EvaluatorSpec", "evaluate", "expression_variables",
        "safe_eval", "prescribe_guard", "approve_transition", "calibration_stats",
    ]
    for n in names:
        assert hasattr(api, n), f"门面缺 {n}"
        assert n in api.__all__, f"__all__ 缺 {n}"


def test_facade_symbols_are_same_objects_as_contract_and_mechanism():
    # 契约词汇：门面对象 == contract.feedback_loop 对象（防误绑）
    for n in ("CALIBRATION_PENDING", "EVAL_VERDICT_UNDECIDABLE",
              "CALIBRATION_MIN_SAMPLE", "FeedbackTemplateError"):
        assert getattr(api, n) is getattr(contract_fl, n)
    # 机制：门面对象 == feedback 包对象
    for n in ("evaluate", "prescribe_guard", "approve_transition",
              "calibration_stats", "safe_eval", "MetricTemplate"):
        assert getattr(api, n) is getattr(feedback, n)
