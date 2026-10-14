"""WorkflowRunner —— 复用 `SubagentPool` 按 DAG 派发子智能体（dsh agent()/pipeline() 概念本仓等价物）。

不移植 dsh 的 JS 脚本执行引擎（R2 能力吸收，见 phase4 计划 §4）：编排以**声明式 steps** 表达，
执行体复用阶段二已落地的 `SubagentPool.delegate()`。

失败语义（faithful to dsh 组合子纪律）：
- 非 fatal 子失败（含 `rejected=True` 与普通异常）→ 该 step 结果 `None`，其余继续（`.filter(Boolean)`）。
- fatal `WorkflowError` → 整个 run `error` 终止（`WorkflowError.fatal` 驱动）。
- 取消信号（`signal.cancelled`）→ run `cancelled`。
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from chiyu_kernel.orchestration.subagent import SubagentDescriptor, SubagentPool

from . import Workflow, WorkflowError, WorkflowResult, WorkflowStep
from .host import WorkerRun


def _extract_content(res: Mapping[str, Any]) -> Optional[str]:
    """从 `delegate` 返回的 run_turn 结果里抽取 assistant 文本（dsh 的 value）。"""
    msgs = res.get("messages", []) if isinstance(res, Mapping) else []
    texts = [
        m.get("content")
        for m in msgs
        if isinstance(m, Mapping) and m.get("role") == "assistant" and m.get("content")
    ]
    return "\n".join(texts) if texts else None


class WorkflowRunner:
    """按 DAG 拓扑派发子智能体执行一个声明式 `Workflow`。"""

    def __init__(self, pool: SubagentPool, *, grace_ms: int = 5000) -> None:
        self._pool = pool
        self._registered: set[str] = set()
        self._grace_ms = grace_ms

    def _ensure(self, step: WorkflowStep) -> None:
        """幂等注册：每个 step 作为子智能体注册一次（跨多次 run 安全）。"""
        if step.name not in self._registered:
            self._pool.register(
                SubagentDescriptor(key=step.name, role=step.name, instruction=step.prompt)
            )
            self._registered.add(step.name)

    def run(self, workflow: Workflow, signal: Any = None) -> WorkflowResult:
        for s in workflow.steps:
            self._ensure(s)
        # 忠实 dsh：signal 在启动前即已取消 → 不启动子进程（已取消即不启动）。
        # 运行中途取消改由 WorkerRun.cancel()（grace→terminate）承担（host 测试覆盖）。
        if signal is not None and getattr(signal, "cancelled", False):
            return WorkflowResult(
                value={}, stop_reason="cancelled", agents_started=0)
        init = {
            "steps": [
                {"name": s.name, "prompt": s.prompt, "depends_on": list(s.depends_on)}
                for s in workflow.steps
            ],
            "max_concurrency": workflow.meta.max_concurrency,
        }
        run = WorkerRun(self._pool, init, dispose_grace_ms=self._grace_ms)
        run.start()
        return run.result()


__all__ = ["WorkflowRunner"]
