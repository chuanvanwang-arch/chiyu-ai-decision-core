"""阶段二 Task 3：plan / todo 数据模型（dsh `plan` / `todo` 能力吸收）。

- `TodoList`：整值替换语义（dsh todo/write last-wins），状态机
- `PlanStep`：步骤状态机 pending→in_progress→done/failed
- `Plan` / `PlanMode`：计划协作态 {active, pending}（faithful to dsh `PlanProjection`）
"""
from __future__ import annotations

import pytest

from chiyu_kernel.plan import (
    TodoItem, TodoList, PlanStep, Plan, PlanMode, PlanStateError,
    TODO_STATES, PLAN_STEP_STATES,
)


def test_todo_states_constant():
    assert set(TODO_STATES) == {"pending", "in_progress", "completed", "cancelled"}


def test_todolist_whole_value_replace():
    tl = TodoList()
    tl.write([
        TodoItem(content="调研需求"),
        TodoItem(content="写方案", status="in_progress"),
    ])
    assert len(tl.items) == 2
    # 整值替换：新列表覆盖旧列表
    tl.write([TodoItem(content="交付", status="completed")])
    assert [i.content for i in tl.items] == ["交付"]
    assert tl.items[0].status == "completed"


def test_todolist_mark():
    tl = TodoList()
    tl.write([TodoItem(content="a"), TodoItem(content="b")])
    tl.mark("a", "completed")
    assert tl.items[0].status == "completed"
    assert tl.items[1].status == "pending"


def test_todo_invalid_status_rejected():
    with pytest.raises(AssertionError):
        TodoItem(content="x", status="nonsense")


def test_plan_step_state_machine():
    step = PlanStep(content="设计")
    assert step.status == "pending"
    step.transition("in_progress")
    assert step.status == "in_progress"
    step.transition("done")
    assert step.status == "done"
    with pytest.raises(PlanStateError):
        step.transition("in_progress")  # done→in_progress 非法


def test_plan_step_states_constant():
    assert set(PLAN_STEP_STATES) == {"pending", "in_progress", "done", "failed"}


def test_plan_mode_projection():
    mode = PlanMode()
    assert mode.projection() == {"active": False, "pending": False}
    mode.enter()
    assert mode.projection() == {"active": True, "pending": False}
    mode.exit()
    assert mode.projection() == {"active": False, "pending": False}


def test_plan_steps_projection():
    plan = Plan(steps=[PlanStep("a"), PlanStep("b")])
    plan.steps[0].transition("in_progress")
    proj = plan.projection()
    assert proj["active"] is False
    assert [s["content"] for s in proj["steps"]] == ["a", "b"]
    assert proj["steps"][0]["status"] == "in_progress"
