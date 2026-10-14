"""阶段二 Task 2：subagent 子智能体委派（dsh `subagent` 能力吸收）。

忠实吸收 dsh subagent 的**委派语义**：构造一个子 agent（含 role/instruction/tools_scope），
经阶段一已落地的 `AgentLoop` 跑一轮到完成，返回结果。不引入 dsh 的 out-of-process/ACP/continuation。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.llm.client import StubProvider, ToolCall, LlmResponse
from chiyu_kernel.tools import ToolRegistry, ToolSpec
from chiyu_kernel.session import SessionManager
from chiyu_kernel.orchestration.subagent import SubagentDescriptor, SubagentPool


def _provider(*responses):
    return StubProvider(responses=list(responses))


def _tools_with(scope: str, impl):
    reg = ToolRegistry()
    reg.register(ToolSpec(name="research-tool", description="调研工具", scope=scope), impl)
    return reg


def test_delegate_runs_subagent_turn():
    llm = _provider(LlmResponse(content="调研结论：A 成立"))
    tools = ToolRegistry()
    sessions = SessionManager()
    pool = SubagentPool(llm=llm, tools=tools, sessions=sessions)
    pool.register(SubagentDescriptor(key="researcher", role="研究员",
                                     instruction="你负责调研", tools_scope="research"))
    res = pool.delegate("调研 X", subagent_key="researcher")
    assert res["rejected"] is False
    contents = [m["content"] for m in res["messages"] if m.get("role") == "assistant"]
    assert "调研结论：A 成立" in contents


def test_delegate_respects_tools_scope():
    captured = {}

    def impl(args):
        captured["args"] = args
        return {"ok": True, "result": "found"}

    # 第一步模型请求调工具，第二步给出结论
    llm = _provider(
        LlmResponse(content="", tool_calls=[ToolCall(name="research-tool", args={"q": "X"})]),
        LlmResponse(content="基于调研：结论成立"),
    )
    tools = _tools_with("research", impl)
    pool = SubagentPool(llm=llm, tools=tools, sessions=SessionManager())
    pool.register(SubagentDescriptor(key="researcher", role="研究员",
                                     instruction="调研", tools_scope="research"))
    res = pool.delegate("调研 X", subagent_key="researcher")
    assert captured.get("args") == {"q": "X"}
    assert any("结论成立" in m["content"] for m in res["messages"] if m.get("role") == "assistant")


def test_delegate_unknown_key_raises():
    pool = SubagentPool(llm=_provider(), tools=ToolRegistry(), sessions=SessionManager())
    with pytest.raises(KeyError):
        pool.delegate("x", subagent_key="ghost")
