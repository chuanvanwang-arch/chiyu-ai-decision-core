"""T1 — guard 环路卫生：重复调用提醒 + 轮次预算（吸收 dsh guard）。

TDD：先红（LoopGuard / AgentLoop.loop_guard 尚不存在）→ 绿。
"""
from chiyu_kernel.llm.client import StubProvider, ToolCall, LlmResponse
from chiyu_kernel.orchestration.agent_runtime import Agent, LiveAgentRegistry
from chiyu_kernel.orchestration.agent_loop import AgentLoop
from chiyu_kernel.orchestration.loop_guard import LoopGuard, StepVerdict
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import ToolRegistry


def _build_loop(*, guard, steps_until_stop: int):
    """构造一个会反复调用同一工具、直到 guard 终止或响应耗尽的 AgentLoop。"""
    tools = ToolRegistry()
    calls = {"n": 0}

    def impl(args):
        calls["n"] += 1
        return f"result:{calls['n']}"

    tools.register(
        ToolSpec := __import__("chiyu_kernel.tools", fromlist=["ToolSpec"]).ToolSpec(
            name="lookup", description="lookup", scope="", high_risk=False),
        impl,
    )
    # 让 stub 反复返回同一工具调用
    responses = [
        LlmResponse(content="", tool_calls=[ToolCall(name="lookup", args={"q": "x"})])
        for _ in range(steps_until_stop)
    ]
    llm = StubProvider(responses=responses)
    live = LiveAgentRegistry()
    live.register(Agent(key="a", system_prompt="", tools_scope="", pre_step=None))
    sessions = SessionManager()
    return AgentLoop(llm=llm, tools=tools, sessions=sessions, live_agents=live,
                     redline_guard=None, loop_guard=guard)


def test_repeat_reminder_injected_at_threshold():
    # 阈值 [3,5,8]；模型每步都调同一 lookup → 第 3 步应注入提醒
    guard = LoopGuard(thresholds=(3, 5, 8), max_steps=100)
    loop = _build_loop(guard=guard, steps_until_stop=6)
    out = loop.run_turn("a", "go")
    kinds = [e.kind for e in loop.sessions.get_or_create("a")._events]
    assert "system/reminder" in kinds, f"未注入提醒，事件={kinds}"
    # 提醒文本：首阈值(3)为 gentle；后续阈值(5)为 detailed（点名工具+次数）
    reminders = [e.payload["content"] for e in loop.sessions.get_or_create("a")._events
                 if e.kind == "system/reminder"]
    assert any("lookup" in r for r in reminders), f"详细提醒未点名工具：{reminders}"
    assert any("repeating the exact same tool call" in r.lower() for r in reminders), \
        f"gentle 提醒缺失：{reminders}"


def test_loop_budget_terminates():
    # max_steps=3 → 第 3 步后终止，不应跑满 6 步
    guard = LoopGuard(thresholds=(3, 5, 8), max_steps=3)
    loop = _build_loop(guard=guard, steps_until_stop=6)
    out = loop.run_turn("a", "go")
    assert out["steps"] <= 3, f"预算未生效 steps={out['steps']}"
    kinds = [e.kind for e in loop.sessions.get_or_create("a")._events]
    assert "loop/terminated" in kinds


def test_no_guard_passes_through():
    # 不接 guard：行为与阶段一一致，无提醒/终止事件
    loop = _build_loop(guard=None, steps_until_stop=4)
    out = loop.run_turn("a", "go")
    kinds = [e.kind for e in loop.sessions.get_or_create("a")._events]
    assert "system/reminder" not in kinds
    assert "loop/terminated" not in kinds


def test_step_verdict_shape():
    v = StepVerdict(terminate="budget", reminder="r")
    assert v.terminate == "budget" and v.reminder == "r"
