"""计划 / 待办数据模型 —— dsh `plan` / `todo` 能力吸收（L2）。

忠实吸收 dsh 的**数据模型与状态语义**：
- `todo`：`TodoItem[]` + 整值替换（dsh `todo/write` 每次携带完整列表，fold 为 last-wins）
- `plan`：`PlanStep` 步骤状态机 + `Plan` / `PlanMode` 协作态 `{active, pending}`
  （faithful to dsh `PlanProjection`）

⛔ 本模块是纯数据模型 + 状态转移，不引入 dsh 的 session-projection 框架——消费方（对话页 /
subagent）直接持有并渲染，避免与本仓 `session` 重复。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from dataclasses import dataclass, field
from typing import Any

TODO_STATES = ("pending", "in_progress", "completed", "cancelled")
PLAN_STEP_STATES = ("pending", "in_progress", "done", "failed")

# (from, to) 合法转移（dsh plan 步骤的有向推进）
_ALLOWED_STEP = {
    ("pending", "in_progress"),
    ("in_progress", "done"),
    ("in_progress", "failed"),
    ("done", "pending"),          # 允许回退重做
    ("failed", "pending"),        # 失败后重排
}


class PlanStateError(KernelError):
    code = "CONTRACT_VIOLATION"
    """非法的步骤状态转移。"""


@dataclass
class TodoItem:
    """待办项（dsh `TodoItem` 的 Python 对应）。"""

    content: str
    status: str = "pending"
    active_form: str = ""

    def __post_init__(self) -> None:
        if self.status not in TODO_STATES:
            raise AssertionError(f"非法 todo 状态：{self.status!r}")

    def render(self) -> dict[str, str]:
        return {"content": self.content, "status": self.status, "active_form": self.active_form}


class TodoList:
    """待办列表：整值替换语义（last-wins，faithful to dsh）。"""

    def __init__(self) -> None:
        self._items: list[TodoItem] = []

    def write(self, items: list[TodoItem]) -> None:
        """整值替换当前列表（dsh `todo/write` 携带完整列表）。"""
        self._items = [TodoItem(i.content, i.status, i.active_form) for i in items]

    def mark(self, content: str, status: str) -> None:
        if status not in TODO_STATES:
            raise AssertionError(f"非法 todo 状态：{status!r}")
        for it in self._items:
            if it.content == content:
                it.status = status
                return
        raise KeyError(f"待办项不存在：{content!r}")

    @property
    def items(self) -> list[TodoItem]:
        return list(self._items)

    def render(self) -> list[dict[str, str]]:
        return [i.render() for i in self._items]


@dataclass
class PlanStep:
    """计划步骤（dsh plan step 的 Python 对应）。"""

    content: str
    status: str = "pending"

    def __post_init__(self) -> None:
        if self.status not in PLAN_STEP_STATES:
            raise AssertionError(f"非法步骤状态：{self.status!r}")

    def transition(self, to: str) -> None:
        if to not in PLAN_STEP_STATES:
            raise AssertionError(f"非法步骤状态：{to!r}")
        if (self.status, to) not in _ALLOWED_STEP:
            raise PlanStateError(f"步骤状态转移非法：{self.status!r} → {to!r}")
        self.status = to

    def render(self) -> dict[str, Any]:
        return {"content": self.content, "status": self.status}


class Plan:
    """计划：有序步骤集合 + 协作态投影。"""

    def __init__(self, steps: list[PlanStep] | None = None) -> None:
        self.steps: list[PlanStep] = [
            PlanStep(s.content, s.status) for s in (steps or [])
        ]
        self._mode = PlanMode()

    def enter_mode(self) -> None:
        self._mode.enter()

    def exit_mode(self) -> None:
        self._mode.exit()

    def projection(self) -> dict[str, Any]:
        proj = self._mode.projection()
        proj["steps"] = [s.render() for s in self.steps]
        return proj


class PlanMode:
    """计划协作态（faithful to dsh `PlanProjection{active, pending}`）。"""

    def __init__(self) -> None:
        self.active: bool = False
        self.pending: bool = False

    def enter(self) -> None:
        self.active = True

    def exit(self) -> None:
        self.active = False
        self.pending = False

    def projection(self) -> dict[str, bool]:
        return {"active": self.active, "pending": self.pending}


__all__ = [
    "TodoItem", "TodoList", "PlanStep", "Plan", "PlanMode", "PlanStateError",
]
