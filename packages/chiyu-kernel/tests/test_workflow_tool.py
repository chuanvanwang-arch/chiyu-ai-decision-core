"""阶段四 T3 — workflow 模型面工具（吸收 dsh tool-workflow，声明式 steps 替代 JS 脚本）。

TDD：先红后绿。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.llm.client import LlmResponse
from chiyu_kernel.orchestration.subagent import SubagentPool
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import ToolRegistry
from chiyu_kernel.workflow import register_workflow_tools


def _pool(responses):
    from chiyu_kernel.llm.client import StubProvider

    return SubagentPool(llm=StubProvider(responses=list(responses)),
                        tools=ToolRegistry(), sessions=SessionManager())


def test_register_and_execute_workflow_tool():
    pool = _pool([LlmResponse(content="a ok"), LlmResponse(content="b ok")])
    reg = ToolRegistry()
    register_workflow_tools(reg, pool)
    assert reg.spec("workflow") is not None

    out = reg.execute("workflow", {
        "meta": {"name": "wf-1", "description": "demo"},
        "steps": [
            {"name": "a", "prompt": "do a"},
            {"name": "b", "prompt": "do b", "depends_on": ["a"]},
        ],
    })
    assert out["stopReason"] == "completed"
    assert out["agentsStarted"] == 2
    assert "a ok" in out["result"]["a"]
    assert "b ok" in out["result"]["b"]
    assert "runId" in out


def test_workflow_tool_requires_meta_name():
    reg = ToolRegistry()
    register_workflow_tools(reg, _pool([]))
    with pytest.raises(ValueError):
        reg.execute("workflow", {"meta": {"description": "no name"}, "steps": []})


def test_workflow_tool_reports_error_stop_reason():
    pool = _pool([])

    def fake(task, *, subagent_key):
        if subagent_key == "b":
            from chiyu_kernel.workflow import WorkflowError

            raise WorkflowError("boom", "AGENT_START", fatal=True)
        return {"rejected": False, "messages": [{"role": "assistant", "content": f"{subagent_key} ok"}]}

    pool.delegate = fake  # type: ignore[assignment]
    reg = ToolRegistry()
    register_workflow_tools(reg, pool)
    out = reg.execute("workflow", {
        "meta": {"name": "wf-2", "description": "d"},
        "steps": [
            {"name": "a", "prompt": "do a"},
            {"name": "b", "prompt": "do b", "depends_on": ["a"]},
        ],
    })
    assert out["stopReason"] == "error"
    assert "boom" in (out["error"] or "")
