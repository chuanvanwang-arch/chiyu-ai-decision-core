"""R8 决策错误分类 —— 结构化错误码（CRM R8 · 2026-10-09）。

CRM 回信 R8 要求统一错误码分类法，供跨语言迁移时的错误语义对齐。
此前 spine/scoring 为泛型 ValueError，catch 侧无法机器判别。

核心断言：
- 决策失败均为 `DecisionError`（带 `code`，属于闭集 `DECISION_ERROR_CODES`）。
- 非法错误码在构造期即抛（闭集 fail-fast，与注册表 `ScenarioRegistryError` 同纪律）。
- 变异自证：将 `spine.run_spine` 的 `DecisionError("ENGINE_FAULT", …)` 换成泛型
  `ValueError` → 本测试立即转红。
"""
from __future__ import annotations

import pytest

from chiyu_decision.api import DECISION_ERROR_CODES, DecisionError, run_spine


def _run_empty_context():
    return run_spine(context={}, profile=None, rubric_scores={}, elements={})


def test_run_spine_empty_context_raises_structured_error():
    """S1 缺失必须抛 DecisionError(ENGINE_FAULT)，而非泛型 ValueError。"""
    with pytest.raises(DecisionError) as ei:
        _run_empty_context()
    assert ei.value.code == "ENGINE_FAULT"


def test_error_codes_are_closed_set():
    assert isinstance(DECISION_ERROR_CODES, frozenset)
    assert {"ENGINE_FAULT", "UNKNOWN_SCENARIO", "DIM_MISMATCH", "CONTRACT_VIOLATION"} <= DECISION_ERROR_CODES


def test_invalid_error_code_rejected_at_construction():
    with pytest.raises((ValueError, DecisionError)):
        DecisionError("NO_SUCH_CODE", "x")


def test_structured_error_is_machine_routable():
    err = DecisionError("DIM_MISMATCH", "维度不符")
    assert err.code == "DIM_MISMATCH"
    assert err.message == "维度不符"
    assert "DIM_MISMATCH" == err.code


def test_decision_error_is_exception_subclass():
    assert issubclass(DecisionError, Exception)
