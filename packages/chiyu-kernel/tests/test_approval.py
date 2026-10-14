"""T6 — 审批闸门（吸收 dsh `interaction/permission-presets` + 审批）：高风险动作 HITL。

TDD：先红（chiyu_kernel.interaction 尚不存在）→ 绿。
"""
from chiyu_kernel.llm.client import StubProvider, ToolCall, LlmResponse
from chiyu_kernel.orchestration.agent_runtime import Agent, LiveAgentRegistry
from chiyu_kernel.orchestration.agent_loop import AgentLoop
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import GuardDenied, ToolRegistry
from chiyu_kernel.tools import ToolSpec
from chiyu_kernel.interaction import ApprovalGate


def _build(high_risk_tool=True):
    reg = ToolRegistry()
    called = {"n": 0}
    reg.register(
        ToolSpec(name="danger", description="d", scope="", high_risk=True),
        lambda args: (called.__setitem__("n", called["n"] + 1) or "done"),
    )
    reg.register(
        ToolSpec(name="safe", description="s", scope="", high_risk=False),
        lambda args: "ok",
    )
    gate = ApprovalGate(reg)
    llm = StubProvider(responses=[LlmResponse(content="", tool_calls=[ToolCall(name="danger", args={"x": 1})])])
    live = LiveAgentRegistry()
    live.register(Agent(key="a", system_prompt="", tools_scope="", pre_step=None))
    loop = AgentLoop(llm=llm, tools=reg, sessions=SessionManager(), live_agents=live,
                     redline_guard=gate.guard)
    return reg, gate, loop, called


def test_high_risk_blocked_before_approval():
    reg, gate, loop, called = _build()
    raised = None
    try:
        loop.run_turn("a", "go")
    except GuardDenied as e:
        raised = e
    assert raised is not None, "高危险工具未批却未拦截"
    assert called["n"] == 0
    # 应有待批请求
    assert len(gate.pending()) >= 1


def test_approve_then_executes():
    reg, gate, loop, called = _build()
    try:
        loop.run_turn("a", "go")
    except GuardDenied:
        pass
    aid = next(iter(gate.pending()))
    gate.approve(aid)
    # 重新跑（新 stub 同样的调用）
    llm = StubProvider(responses=[LlmResponse(content="", tool_calls=[ToolCall(name="danger", args={"x": 1})])])
    live = LiveAgentRegistry()
    live.register(Agent(key="a", system_prompt="", tools_scope="", pre_step=None))
    loop2 = AgentLoop(llm=llm, tools=reg, sessions=SessionManager(), live_agents=live,
                      redline_guard=gate.guard)
    loop2.run_turn("a", "go")
    assert called["n"] == 1, "批准后仍未执行"


def test_deny_stays_blocked():
    reg, gate, loop, called = _build()
    try:
        loop.run_turn("a", "go")
    except GuardDenied:
        pass
    aid = next(iter(gate.pending()))
    gate.deny(aid)
    raised = False
    try:
        llm = StubProvider(responses=[LlmResponse(content="", tool_calls=[ToolCall(name="danger", args={"x": 1})])])
        live = LiveAgentRegistry()
        live.register(Agent(key="a", system_prompt="", tools_scope="", pre_step=None))
        AgentLoop(llm=llm, tools=reg, sessions=SessionManager(), live_agents=live,
                  redline_guard=gate.guard).run_turn("a", "go")
    except GuardDenied:
        raised = True
    assert raised and called["n"] == 0


def test_safe_tool_needs_no_approval():
    reg, gate, loop, called = _build()
    # 改 stub 调 safe
    llm = StubProvider(responses=[LlmResponse(content="", tool_calls=[ToolCall(name="safe", args={})])])
    live = LiveAgentRegistry()
    live.register(Agent(key="a", system_prompt="", tools_scope="", pre_step=None))
    AgentLoop(llm=llm, tools=reg, sessions=SessionManager(), live_agents=live,
              redline_guard=gate.guard).run_turn("a", "go")
    assert called  # safe 直接执行，无待批
    assert len(gate.pending()) == 0
