"""T5 — 钩子总线（吸收 dsh `hook-protocol`）：matcher 三态 + AgentLoop 生命周期接线。

TDD：先红（chiyu_kernel.hooks 尚不存在）→ 绿。
"""
from chiyu_kernel.hooks import HookBus, HookResult, matches
from chiyu_kernel.llm.client import StubProvider, ToolCall, LlmResponse
from chiyu_kernel.orchestration.agent_runtime import Agent, LiveAgentRegistry
from chiyu_kernel.orchestration.agent_loop import AgentLoop
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import ToolRegistry


def test_matcher_three_modes():
    # 全匹配
    assert matches(None, "anything") is True
    assert matches("*", "anything") is True
    # 字面量（claude-code，| 精确匹配）
    assert matches("a|b", "a") is True
    assert matches("a|b", "c") is False
    # 正则（未锚定）
    assert matches(r"foo.*", "xfooy") is True
    assert matches(r"foo.*", "bar") is False
    # 无效正则 → 非匹配（不抛）
    assert matches(r"[", "x") is False


def test_hook_bus_matcher_selectivity():
    bus = HookBus()
    fired = []
    bus.register("PreToolUse", "h1", lambda p: (fired.append("h1") or "pass"), matcher="fs_*")
    bus.register("PreToolUse", "h2", lambda p: (fired.append("h2") or "pass"), matcher="shell_*")
    bus.run("PreToolUse", "fs_read", {})
    assert fired == ["h1"], fired


def test_pre_tool_use_veto_skips_execution():
    tools = ToolRegistry()
    called = {"n": 0}

    def impl(args):
        called["n"] += 1
        return "done"

    tools.register(
        __import__("chiyu_kernel.tools", fromlist=["ToolSpec"]).ToolSpec(
            name="danger", description="d", scope="", high_risk=False),
        impl,
    )
    bus = HookBus()
    bus.register("PreToolUse", "gate", lambda p: "deny", matcher="danger")
    llm = StubProvider(responses=[LlmResponse(content="", tool_calls=[ToolCall(name="danger", args={})])])
    live = LiveAgentRegistry()
    live.register(Agent(key="a", system_prompt="", tools_scope="", pre_step=None))
    loop = AgentLoop(llm=llm, tools=tools, sessions=SessionManager(), live_agents=live,
                     hook_bus=bus)
    out = loop.run_turn("a", "go")
    # 工具未执行
    assert called["n"] == 0
    kinds = [e.kind for e in loop.sessions.get_or_create("a")._events]
    assert "tool/denied-by-hook" in kinds


def test_post_tool_use_and_stop_fire():
    tools = ToolRegistry()
    tools.register(
        __import__("chiyu_kernel.tools", fromlist=["ToolSpec"]).ToolSpec(
            name="ok", description="d", scope="", high_risk=False),
        lambda args: "r",
    )
    events = []

    def post(p):
        events.append(("post", p))
        return "pass"

    def stop(p):
        events.append(("stop", p))
        return "pass"

    bus = HookBus()
    bus.register("PostToolUse", "p1", post, matcher="ok")
    bus.register("Stop", "s1", stop)
    llm = StubProvider(responses=[LlmResponse(content="", tool_calls=[ToolCall(name="ok", args={})])])
    live = LiveAgentRegistry()
    live.register(Agent(key="a", system_prompt="", tools_scope="", pre_step=None))
    loop = AgentLoop(llm=llm, tools=tools, sessions=SessionManager(), live_agents=live,
                     hook_bus=bus)
    loop.run_turn("a", "go")
    assert any(k == "post" for k, _ in events)
    assert any(k == "stop" for k, _ in events)
