"""workflow 声明式编排数据模型 —— dsh `workflow` 能力吸收（L2）。

忠实吸收 dsh 的**词汇表与编排概念**：
- `WorkflowMeta`/`WorkflowPhase`：身份块（name kebab-case + description + 可选 phases）
- `WorkflowStep`：声明式步骤（含 `depends_on` DAG 依赖 + 状态机）
- `Workflow`：步骤集合 + 拓扑排序 + 环检测（与 `plan` 的有序步骤不同，workflow 带依赖图）
- `WorkflowResult`/`WorkflowStopReason`：运行结果（completed/cancelled/error）
- `WorkflowError`(fatal flag) + 错误码族：机器可路由的失败分类
- `WorkflowRunId`：branded id

⛔ 不移植 dsh 的 JS 脚本执行引擎（R2 能力吸收，见 phase4 计划 §4）。执行体在
`runner.py` 复用 `orchestration/subagent.SubagentPool`，本文件仅为纯数据模型 + 校验。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

import re
from dataclasses import dataclass, field
from typing import Any, Literal, NewType, Optional

WORKFLOW_STEP_STATES = ("pending", "in_progress", "done", "failed")

# 忠实吸收 dsh AGENT_CAP：worker 池默认并发上限
DEFAULT_MAX_CONCURRENCY = 4

# dsh `WorkflowErrorCode` 族（忠实吸收；保留定义，不进公共门面 __all__）。
WORKFLOW_ERROR_CODES = (
    "SCRIPT_PARSE",
    "META_INVALID",
    "INVALID_ARGUMENT",
    "UNSUPPORTED_OPTION",
    "UNSUPPORTED_SCHEMA",
    "AGENT_CAP",
    "ITEM_CAP",
    "AGENT_START",
    "AGENT_RESULT",
    "RESULT_UNSERIALIZABLE",
    "CANCELLED",
)

# (from, to) 合法步骤转移（与 plan 的 _ALLOWED_STEP 同构，状态集更小）
_ALLOWED_STEP = {
    ("pending", "in_progress"),
    ("in_progress", "done"),
    ("in_progress", "failed"),
    ("done", "pending"),          # 允许回退重做
    ("failed", "pending"),        # 失败后重排
}

_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class WorkflowStateError(KernelError):
    code = "CONTRACT_VIOLATION"
    """非法的步骤状态转移。"""


# branded id：运行时即 str（identity function），满足测试 `isinstance(rid, str)`。
WorkflowRunId = NewType("WorkflowRunId", str)


@dataclass
class WorkflowPhase:
    """进度阶段声明（phases 分组，仅信息性，不施加执行结构，faithful to dsh）。"""

    title: str
    detail: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


@dataclass
class WorkflowMeta:
    """workflow 身份块（faithful to dsh `WorkflowMeta`）。"""

    name: str
    description: str
    when_to_use: Optional[str] = None
    phases: list[WorkflowPhase] = field(default_factory=list)
    max_concurrency: Optional[int] = None  # worker 池并发上限（dsh AGENT_CAP）；None→DEFAULT_MAX_CONCURRENCY

    def __post_init__(self) -> None:
        if not self.name or not _KEBAB_RE.match(self.name):
            raise AssertionError(f"workflow name 必须为 kebab-case：{self.name!r}")
        if self.max_concurrency is not None and self.max_concurrency < 1:
            raise AssertionError(f"max_concurrency 必须 ≥1：{self.max_concurrency!r}")


@dataclass
class WorkflowStep:
    """声明式步骤（dsh 脚本内一个 `agent()` 调用的本仓等价物）。"""

    name: str
    prompt: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"

    def __post_init__(self) -> None:
        if self.status not in WORKFLOW_STEP_STATES:
            raise AssertionError(f"非法步骤状态：{self.status!r}")

    def transition(self, to: str) -> None:
        if to not in WORKFLOW_STEP_STATES:
            raise AssertionError(f"非法步骤状态：{to!r}")
        if (self.status, to) not in _ALLOWED_STEP:
            raise WorkflowStateError(f"步骤状态转移非法：{self.status!r} → {to!r}")
        self.status = to

    def render(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "depends_on": list(self.depends_on),
        }


@dataclass
class WorkflowResult:
    """一次 workflow 运行的结算结果（faithful to dsh `WorkflowResult`）。"""

    value: Any = None
    stop_reason: str = "completed"
    agents_started: int = 0
    error: Optional[str] = None


# 闭合联合（引擎自有，消费方可穷尽）。`__args__` 供测试断言闭环。
WorkflowStopReason = Literal["completed", "cancelled", "error"]


class WorkflowError(Exception):
    """机器可路由的 workflow 失败（faithful to dsh `WorkflowError`）。

    `fatal` 驱动组合子纪律：fatal 错误必须杀死整 run（而非把单个 step 置 None）。
    """

    def __init__(self, message: str, code: str, fatal: bool = True) -> None:
        super().__init__(message)
        self.name = "WorkflowError"
        self.code = code
        self.fatal = fatal


def is_fatal_workflow_error(error: object) -> bool:
    """`error` 是否为 fatal workflow 错误（host `instanceof`，脚本 realm 无法伪造）。"""
    return isinstance(error, WorkflowError) and error.fatal


class Workflow:
    """声明式编排定义：步骤集合 + DAG 依赖 + 拓扑排序。"""

    def __init__(self, meta: WorkflowMeta, steps: list[WorkflowStep]) -> None:
        self.meta = meta
        self.steps: list[WorkflowStep] = [
            WorkflowStep(s.name, s.prompt, list(s.depends_on), s.status) for s in steps
        ]

    def topo_order(self) -> list[str]:
        """Kahn 拓扑排序；依赖不存在或成环均抛 `ValueError`。"""
        names = {s.name for s in self.steps}
        for s in self.steps:
            for d in s.depends_on:
                if d not in names:
                    raise ValueError(f"step {s.name!r} 依赖不存在的 step {d!r}")

        indeg = {s.name: 0 for s in self.steps}
        adj: dict[str, list[str]] = {s.name: [] for s in self.steps}
        for s in self.steps:
            for d in s.depends_on:
                adj[d].append(s.name)
                indeg[s.name] += 1

        import heapq

        heap = [n for n, deg in indeg.items() if deg == 0]
        heapq.heapify(heap)
        order: list[str] = []
        while heap:
            n = heapq.heappop(heap)
            order.append(n)
            for m in adj[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    heapq.heappush(heap, m)

        if len(order) != len(self.steps):
            raise ValueError("workflow 存在循环依赖（cycle detected）")
        return order

    def render(self) -> dict[str, Any]:
        return {
            "name": self.meta.name,
            "description": self.meta.description,
            "steps": [s.render() for s in self.steps],
        }


__all__ = [
    "WORKFLOW_STEP_STATES",
    "WorkflowRunId",
    "WorkflowPhase",
    "WorkflowMeta",
    "WorkflowStep",
    "WorkflowResult",
    "WorkflowStopReason",
    "WorkflowError",
    "is_fatal_workflow_error",
    "WorkflowStateError",
    "Workflow",
    "WorkflowRunner",
    "register_workflow_tools",
    "WorkerRun",
]

# 公开 API 重导出
from .runner import WorkflowRunner
from .register import register_workflow_tools
from .host import WorkerRun
