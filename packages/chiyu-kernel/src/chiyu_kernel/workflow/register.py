"""workflow 模型面工具（吸收 dsh `tool-workflow`，声明式 steps 替代 JS 脚本）。

dsh 的 `tool-workflow` 暴露一个 `workflow` 工具，参数 `script`(JS 串) + `meta` + `args`。
本仓无 JS 运行时（R2 偏差，见 phase4 计划 §4），等价地暴露同名工具，参数改为
`meta`(身份块) + `steps`(声明式步骤) + `args?`，执行经 `WorkflowRunner` 复用 `SubagentPool`。
返回 dsh 同构的 `WorkflowResult` JSON（runId / agentsStarted / result / stopReason / error）。
"""
from __future__ import annotations

import uuid
from typing import Any

from chiyu_kernel.tools import ToolRegistry, ToolSpec

from . import (
    Workflow,
    WorkflowError,
    WorkflowMeta,
    WorkflowPhase,
    WorkflowResult,
    WorkflowRunId,
    WorkflowStep,
)
from .runner import WorkflowRunner

_DESCRIPTION = (
    "Run a declarative workflow that fans out subagents. Use for work spanning many "
    "independent pieces (an audit over many files, multi-angle research, adversarial "
    "verification). Provide `meta` (name kebab-case + description) and `steps` (each with "
    "name + prompt + optional depends_on). Steps run in DAG order; a step may depend on "
    "others via `depends_on`. For one or two delegations, prefer plain subagent calls."
)


def register_workflow_tools(registry: ToolRegistry, pool) -> None:
    """注册 model-facing `workflow` 工具（执行体复用 `WorkflowRunner`）。"""

    def _impl(args: dict) -> dict:
        meta_raw = args.get("meta") or {}
        steps_raw = args.get("steps") or []

        name = meta_raw.get("name")
        description = meta_raw.get("description")
        if not name or not description:
            raise ValueError("workflow meta 必须含 name 与 description")

        phases = [
            WorkflowPhase(
                title=p.get("title", ""),
                detail=p.get("detail"),
                provider=p.get("provider"),
                model=p.get("model"),
            )
            for p in (meta_raw.get("phases") or [])
        ]
        meta = WorkflowMeta(
            name=name,
            description=description,
            when_to_use=meta_raw.get("when_to_use"),
            phases=phases,
        )
        steps = [
            WorkflowStep(
                name=s["name"],
                prompt=s["prompt"],
                depends_on=list(s.get("depends_on") or []),
            )
            for s in steps_raw
        ]
        wf = Workflow(meta=meta, steps=steps)
        res: WorkflowResult = WorkflowRunner(pool).run(wf)
        rid = WorkflowRunId(f"wf-{uuid.uuid4().hex[:8]}")
        return {
            "runId": rid,
            "agentsStarted": res.agents_started,
            "result": res.value,
            "stopReason": res.stop_reason,
            "error": res.error,
        }

    registry.register(
        ToolSpec(name="workflow", description=_DESCRIPTION, scope="", high_risk=False),
        _impl,
    )


__all__ = ["register_workflow_tools"]
