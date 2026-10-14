"""跨消费方导入面回归守卫（严格加法的**唯一验收口径**：既有导入面零失效）。

⛔ 为什么要有本守卫：R2–R14 / B1–B3 / N1–N7 的改造原则是"严格加法 + 弃用标注"，
   但"加法零破坏"不能靠自觉 —— 必须把**三消费方曾依赖的符号**固化为断言。
   任何一项被移除/改名，本文件即红（在改造者跑回归时当场拦截，而非等消费方接入时暴雷）。

模拟方式：以改造后的门面模拟消费方 import 语句可成功（**只读验证 foundation 侧**，
不改消费方代码 —— 仓边界纪律：本仓不向 APS / enterprise 写任何产物）。
"""
from __future__ import annotations

import importlib
import os
import sys

# 兄弟包 src 上 sys.path（单跑本文件时 root conftest 的装配可能不在收集链上，
# 这里自举一次，幂等：已在路径上则不重复插）。
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
for _pkg in ("chiyu-decision", "chiyu-kernel"):
    _src = os.path.join(_ROOT, "packages", _pkg, "src")
    if os.path.isdir(_src) and _src not in sys.path:
        sys.path.insert(0, _src)


def test_aps_facade_import_surface_still_available() -> None:
    """APS 侧曾依赖的符号（模拟其 import 语句）仍可从门面拿到。"""
    api = importlib.import_module("chiyu_kernel.api")
    # ⛔ 判据逐符号放对层：评分/红线函数与谓词表分属决策门面与 L0 契约面
    #   （见下方对应断言），kernel 门面只核 store/版本/弃用别名等本层符号。
    for n in ("assert_safe_identifier", "validate_dsn",
              "assert_no_hard_delete", "pg_to_vec", "vec_to_pg", "pad_to_dim",
              # R10 弃用别名（政策：先 warn 一版，不得提前移除）
              "TIER_FTS_VECTOR", "TIER_VECTOR", "TIER_FTS", "TIER_NONE",
              # R11/R4 版本与能力出口
              "api_version", "capabilities"):
        assert hasattr(api, n), f"APS 依赖的 {n} 失效 ⇒ 严格加法被破坏"


def test_enterprise_facade_import_surface_still_available() -> None:
    """enterprise 侧曾依赖的符号仍可用（含 B1/N2 后的新 sanctioned 面）。"""
    api = importlib.import_module("chiyu_kernel.api")
    for n in ("PgVectorStore", "open_store", "ddl_statements", "vector_index_ddl",
              # B3：审批闸三态
              "DecisionApprovalVerdict", "DecisionVerdictState",
              "RedlinePriorityGate", "DecisionPassThroughGate"):
        assert hasattr(api, n), f"enterprise 依赖的 {n} 失效"

    # B1：run_spine 经 chiyu_decision.api（sanctioned 面）可达
    dec = importlib.import_module("chiyu_decision.api")
    for n in ("run_spine", "SpineResult", "SPINE_ORDER"):
        assert hasattr(dec, n), f"决策门面缺 {n} ⇒ B1/N2 sanctioned 面被破坏"


def test_decision_package_surface_still_available() -> None:
    """决策包门面（R1 已补 aggregate_confidence）仍完整；L0 契约面可达。"""
    dec = importlib.import_module("chiyu_decision.api")
    for n in ("score_rubric", "check_elements", "autonomous_release",
              "evaluate_redline", "aggregate_confidence"):
        assert hasattr(dec, n), f"决策门面 {n} 失效"

    contract = importlib.import_module("chiyu_kernel.contract")
    assert hasattr(contract, "MEMORY_PREDICATES"), "L0 记忆谓词表不可达"
    assert hasattr(contract, "EDGE_LAYERS"), "L0 边层表不可达"


def test_decision_spine_result_backward_compatible() -> None:
    """B3 兼容性：SpineResult 旧字段不缺、pending 新字段有默认值。"""
    import dataclasses

    from chiyu_decision.api import SpineResult
    names = {f.name for f in dataclasses.fields(SpineResult)}
    for legacy in ("decision_id", "stage_reached", "confidence", "rubric_missing",
                   "elements_missing", "redline_hit", "redline_reasons",
                   "autonomous", "persisted", "approval_rejected"):
        assert legacy in names, f"SpineResult 旧字段 {legacy} 被移除 ⇒ 破坏性变更"
    assert "pending" in names, "B3 pending 状态位缺失"
