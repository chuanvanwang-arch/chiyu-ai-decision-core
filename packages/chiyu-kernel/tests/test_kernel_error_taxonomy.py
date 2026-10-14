"""错误 taxonomy 守卫（Batch-7a · 2026-10-14）。

对应 Batch-6 §二 G1：契约层错误此前普遍继承泛型 ``ValueError``，导致
``except ValueError`` 无差别吞掉全部契约错误、机器不可路由。本测试对拍：

- 契约错误全部继承 ``KernelError``，且**不**继承 ``ValueError``（根治 G1）；
- 每个契约错误都携闭集 ``code``（消费方可按 code 路由，禁按 message）；
- 门面 ``chiyu_kernel.api`` 双面 re-export 了 ``KernelError`` / ``KERNEL_ERROR_CODES``
  以及全部契约错误类（漏导即红）；
- 朴素 ``except ValueError`` 无法再误吞契约错误（G1 修复的直接证明）；
- ``KernelError`` 拒非法码（删码表判据即红）。

变异自证：删 ``KernelError.__init__`` 的码表校验分支 ⇒ 本文件
``test_kernelerror_rejects_bad_code`` 转红；删任一契约错误的 ``code`` 类属性
⇒ ``test_all_contract_errors_have_valid_code`` 转红。
"""
from __future__ import annotations

import pytest

from chiyu_kernel import api
from chiyu_kernel.errors import KERNEL_ERROR_CODES, KernelError


#: 契约层错误类（Batch-7a 已由 ValueError 上迁至 KernelError），门面须全部 re-export。
CONTRACT_ERROR_NAMES = [
    "SchedulerError", "ApprovalEngineError", "QuotaGateError", "ObservabilityError",
    "ParamHealthError", "NightlyReportError", "DecisionRequiredError",
    "DecisionCredentialError", "GateChainError", "RefluxChannelError",
    "PromotionPolicyError", "AssembleError", "AbExperimentError",
    "FeedbackTemplateError", "CalibrationStateError", "ExpressionError",
    "AttributionError", "Audit4QError", "CapabilityAuditError", "AgentRuntimeError",
    "ConflictStrategyError", "HITLEvidenceError", "ApprovalTransitionError",
    "GuardViolation", "PlanStateError", "SkillDraftError", "KnobError",
    "SkillConflict", "PrescriptionError", "AgentRegistryError", "TaskStateError",
]


def test_kernelerror_base_is_not_valueerror():
    # G1 根治：KernelError 不继承 ValueError，否则泛型 except 仍可误吞。
    assert not issubclass(KernelError, ValueError)
    assert issubclass(KernelError, Exception)


@pytest.mark.parametrize("name", CONTRACT_ERROR_NAMES)
def test_contract_error_is_kernel_error_not_value_error(name):
    cls = getattr(api, name)
    assert issubclass(cls, KernelError), f"{name} 应继承 KernelError"
    assert not issubclass(cls, ValueError), (
        f"{name} 仍继承 ValueError —— G1 反模式未消除（except ValueError 会误吞）"
    )


@pytest.mark.parametrize("name", CONTRACT_ERROR_NAMES)
def test_all_contract_errors_have_valid_code(name):
    cls = getattr(api, name)
    assert hasattr(cls, "code"), f"{name} 缺 code 类属性"
    assert cls.code in KERNEL_ERROR_CODES, (
        f"{name}.code={cls.code!r} 不在闭集 KERNEL_ERROR_CODES"
    )


def test_decision_required_error_uses_confirm_required():
    # 语义特例：写操作缺决策凭证 ⇒ CONFIRM_REQUIRED。
    assert api.DecisionRequiredError.code == "CONFIRM_REQUIRED"
    assert api.QuotaGateError.code == "CONTRACT_VIOLATION"


def test_kernelerror_rejects_bad_code():
    # 删码表校验分支 ⇒ 此用例转红（变异自证）。
    with pytest.raises(ValueError):
        KernelError("x", code="BOGUS_CODE")


def test_contract_error_not_swallowed_by_valueerror():
    # G1 修复的直接证明：朴素 except ValueError 无法再捕获契约错误。
    err = api.QuotaGateError("boom")
    caught_as_valueerror = False
    try:
        raise err
    except ValueError:
        caught_as_valueerror = True
    assert not caught_as_valueerror
    assert isinstance(err, KernelError)
    assert err.code == "CONTRACT_VIOLATION"


def test_facade_reexports_taxonomy():
    # 双面 re-export：门面须透出基类 + 码表 + 全部契约错误类。
    assert "KernelError" in api.__all__
    assert "KERNEL_ERROR_CODES" in api.__all__
    for name in CONTRACT_ERROR_NAMES:
        assert name in api.__all__, f"门面漏导契约错误类：{name}"
        assert getattr(api, name) is not None
