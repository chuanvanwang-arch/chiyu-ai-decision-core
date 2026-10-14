"""阶段四 T1 — workflow 数据模型（吸收 dsh workflow 词汇表）。

TDD：先写失败测试 → 跑红 → 实现 → 跑绿。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.workflow import (
    WORKFLOW_STEP_STATES,
    Workflow,
    WorkflowError,
    WorkflowMeta,
    WorkflowPhase,
    WorkflowResult,
    WorkflowRunId,
    WorkflowStep,
    WorkflowStopReason,
    is_fatal_workflow_error,
)


# ---- WorkflowStep + 状态机 ----

def test_step_default_state_is_pending():
    s = WorkflowStep(name="a", prompt="do a")
    assert s.status == "pending"


def test_step_invalid_state_rejected():
    with pytest.raises(AssertionError):
        WorkflowStep(name="a", prompt="x", status="bogus")


def test_step_state_machine_transitions():
    s = WorkflowStep(name="a", prompt="x")
    s.transition("in_progress")
    assert s.status == "in_progress"
    s.transition("done")
    assert s.status == "done"
    # 允许回退重做
    s.transition("pending")
    assert s.status == "pending"


def test_step_illegal_transition_rejected():
    s = WorkflowStep(name="a", prompt="x")
    with pytest.raises(Exception):  # PlanStateError / ValueError 任一类
        s.transition("done")  # pending → done 非法


def test_step_states_closed_union():
    assert WORKFLOW_STEP_STATES == ("pending", "in_progress", "done", "failed")


# ---- WorkflowMeta 校验 ----

def test_meta_requires_kebab_name_and_description():
    m = WorkflowMeta(name="my-wf", description="does things")
    assert m.name == "my-wf"
    with pytest.raises(AssertionError):
        WorkflowMeta(name="", description="x")  # 空 name
    with pytest.raises(AssertionError):
        WorkflowMeta(name="my_wf", description="x")  # 非 kebab-case


def test_meta_optional_fields():
    m = WorkflowMeta(
        name="my-wf",
        description="d",
        when_to_use="when many files",
        phases=[WorkflowPhase(title="discover", detail="scan")],
    )
    assert m.when_to_use == "when many files"
    assert m.phases[0].title == "discover"


# ---- WorkflowRunId branded ----

def test_run_id_brand():
    rid = WorkflowRunId("run-123")
    assert rid == "run-123"
    assert isinstance(rid, str)


# ---- Workflow DAG：拓扑排序 + 环检测 ----

def test_topo_order_linear():
    wf = Workflow(
        meta=WorkflowMeta(name="wf", description="d"),
        steps=[
            WorkflowStep(name="a", prompt="x"),
            WorkflowStep(name="b", prompt="y", depends_on=["a"]),
            WorkflowStep(name="c", prompt="z", depends_on=["b"]),
        ],
    )
    order = wf.topo_order()
    assert order.index("a") < order.index("b") < order.index("c")


def test_topo_order_fan_in():
    wf = Workflow(
        meta=WorkflowMeta(name="wf", description="d"),
        steps=[
            WorkflowStep(name="a", prompt="x"),
            WorkflowStep(name="b", prompt="y"),
            WorkflowStep(name="c", prompt="z", depends_on=["a", "b"]),
        ],
    )
    order = wf.topo_order()
    assert order.index("a") < order.index("c")
    assert order.index("b") < order.index("c")


def test_cycle_detected():
    wf = Workflow(
        meta=WorkflowMeta(name="wf", description="d"),
        steps=[
            WorkflowStep(name="a", prompt="x", depends_on=["b"]),
            WorkflowStep(name="b", prompt="y", depends_on=["a"]),
        ],
    )
    with pytest.raises(ValueError):  # 环检测
        wf.topo_order()


def test_depends_on_missing_step_rejected():
    wf = Workflow(
        meta=WorkflowMeta(name="wf", description="d"),
        steps=[
            WorkflowStep(name="a", prompt="x", depends_on=["ghost"]),
        ],
    )
    with pytest.raises(ValueError):  # 依赖不存在的 step
        wf.topo_order()


# ---- WorkflowResult / stopReason ----

def test_result_completed():
    r = WorkflowResult(value={"ok": 1}, stop_reason="completed", agents_started=3)
    assert r.stop_reason == "completed"
    assert r.value == {"ok": 1}


def test_stop_reason_closed_union():
    assert WorkflowStopReason.__args__ == ("completed", "cancelled", "error")


# ---- WorkflowError + fatal ----

def test_workflow_error_fatal_by_default():
    e = WorkflowError("boom", "META_INVALID")
    assert e.fatal is True
    assert e.code == "META_INVALID"


def test_workflow_error_non_fatal_flag():
    e = WorkflowError("soft", "AGENT_RESULT", fatal=False)
    assert e.fatal is False


def test_is_fatal_workflow_error():
    assert is_fatal_workflow_error(WorkflowError("x", "META_INVALID")) is True
    assert is_fatal_workflow_error(WorkflowError("x", "AGENT_RESULT", fatal=False)) is False
    assert is_fatal_workflow_error(ValueError("not a workflow error")) is False
