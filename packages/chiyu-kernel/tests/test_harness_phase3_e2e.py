"""T7 — 阶段三 END-TO-END 冒烟：loop_guard + mcp + fs + shell + hooks + approval 串联。

TDD：先红（尚未整体接线）→ 绿。覆盖：
A) 安全 MCP 工具调用成功 + 重复调用触发 LoopGuard 提醒 + 对话页渲染；
B) 高风险 shell 工具未批拦截（待批）+ 批准后放行。
"""
import tempfile

from chiyu_kernel.contract import CORE_ROLES, ParticleTypeSet, TenantProfile
from chiyu_kernel.harness_native_tools import register_native_tools
from chiyu_kernel.hooks import HookBus
from chiyu_kernel.interaction import ApprovalGate
from chiyu_kernel.llm.client import StubProvider, ToolCall, LlmResponse
from chiyu_kernel.mcp import InMemoryMcpServer, McpBridge
from chiyu_kernel.orchestration.agent_runtime import Agent, LiveAgentRegistry
from chiyu_kernel.orchestration.agent_loop import AgentLoop
from chiyu_kernel.orchestration.loop_guard import LoopGuard
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import GuardDenied, ToolRegistry
from chiyu_kernel.tools.fs import register_fs_tools
from chiyu_kernel.tools.shell import register_shell_tools
from chiyu_portal.renderer import render_conversation


def _profile():
    return TenantProfile(domain="demo", particle_types=ParticleTypeSet(set(CORE_ROLES)))


def _build(responses):
    """构造接满阶段三能力的 AgentLoop，返回 (reg, gate, loop)。"""
    from chiyu_kernel.mcp import _RESERVED
    _RESERVED.clear()  # 隔离全局命名空间预留，避免多次 _build 互相污染
    reg = ToolRegistry()
    register_native_tools(reg, profile=_profile())
    tmp = tempfile.mkdtemp()
    register_fs_tools(reg, tmp)
    register_shell_tools(reg, allowlist={"echo"})
    bridge = McpBridge(
        InMemoryMcpServer({"mcp_search": ("搜索", lambda a: f"found:{a.get('q')}")}),
        server_name="srv",
    )
    bridge.connect(reg)
    gate = ApprovalGate(reg)
    bus = HookBus()
    post = []
    bus.register("PostToolUse", "rec", lambda p: (post.append(p) or "pass"), matcher=None)
    llm = StubProvider(responses=responses)
    live = LiveAgentRegistry()
    live.register(Agent(key="a", system_prompt="", tools_scope="", pre_step=None))
    loop = AgentLoop(
        llm=llm, tools=reg, sessions=SessionManager(), live_agents=live,
        redline_guard=gate.guard, loop_guard=LoopGuard(thresholds=(2,), max_steps=10),
        hook_bus=bus,
    )
    return reg, gate, loop


def _session_tool_results(loop, agent_key="a"):
    """run_turn 的 derive_messages 有意剔除工具消息（模型历史不含工具结果），
    故工具执行结果需从 session 日志事件取（kind='tool/result'）。"""
    events = loop.sessions.get_or_create(agent_key).events()
    return [str(e.payload.get("result", "")) for e in events if e.kind == "tool/result"]


def _render_events(loop, agent_key="a"):
    """把 SessionEvent 投影成 render_conversation 接受的 {role, content} 形态。"""
    out = []
    for ev in loop.sessions.get_or_create(agent_key).events():
        role = ev.kind.split("/")[0]  # user/assistant/system/tool
        content = ev.payload.get("content") or ev.payload.get("result") or ev.payload.get("decision") or ""
        out.append({"role": role, "content": str(content)})
    return out


def test_e2e_safe_mcp_plus_repeat_reminder_and_render():
    _, _, loop = _build([
        LlmResponse(content="", tool_calls=[ToolCall(name="mcp__srv__mcp_search", args={"q": "x"})]),
        LlmResponse(content="", tool_calls=[ToolCall(name="mcp__srv__mcp_search", args={"q": "x"})]),
    ])
    loop.run_turn("a", "查一下")
    # MCP 工具结果出现（工具结果落 session 日志 tool/result）
    results = _session_tool_results(loop)
    assert any("found:x" in r for r in results), results
    # LoopGuard 重复提醒（阈值 2，跨 step）
    events = loop.sessions.get_or_create("a").events()
    assert any(e.kind == "system/reminder" for e in events)
    # 对话页渲染包含结果（取真实 session 事件）
    html = render_conversation(
        events=_render_events(loop),
        composer_action="send_message", goal="查询",
    ).html
    assert "found:x" in html
    assert "send_message" in html
    assert "<script" not in html.lower()


def test_e2e_high_risk_shell_needs_approval_then_executes():
    reg, gate, loop = _build([LlmResponse(content="", tool_calls=[ToolCall(name="shell_run", args={"cmd": "echo hi"})])])
    raised = None
    try:
        loop.run_turn("a", "跑命令")
    except GuardDenied as e:
        raised = e
    assert raised is not None, "高风险 shell 未批却未拦截"
    assert len(gate.pending()) >= 1
    aid = next(iter(gate.pending()))
    gate.approve(aid)
    # 批准后重跑：复用原 reg/gate（保持批准状态），重建 loop
    from chiyu_kernel.orchestration.agent_loop import AgentLoop as _AL
    from chiyu_kernel.session import SessionManager as _SM
    llm = StubProvider(responses=[LlmResponse(content="", tool_calls=[ToolCall(name="shell_run", args={"cmd": "echo hi"})])])
    live = LiveAgentRegistry()
    live.register(Agent(key="a", system_prompt="", tools_scope="", pre_step=None))
    loop3 = _AL(llm=llm, tools=reg, sessions=_SM(), live_agents=live,
                redline_guard=gate.guard, loop_guard=LoopGuard(thresholds=(2,), max_steps=10))
    loop3.run_turn("a", "跑命令")
    results = _session_tool_results(loop3)
    assert any("hi" in r for r in results), results
