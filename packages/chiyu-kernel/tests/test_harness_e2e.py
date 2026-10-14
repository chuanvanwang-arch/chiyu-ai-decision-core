from chiyu_kernel.contract import TenantProfile
from chiyu_kernel.contract.particle import ParticleTypeSet
from chiyu_kernel.orchestration.agent_runtime import Agent, LiveAgentRegistry
from chiyu_kernel.orchestration.agent_loop import AgentLoop
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import ToolRegistry
from chiyu_kernel.llm.client import StubProvider, LlmResponse, ToolCall
from chiyu_kernel.harness_native_tools import register_native_tools, native_redline_guard
from chiyu_portal.renderer import render_conversation


def test_dsh_style_turn_then_render():
    profile = TenantProfile(
        domain="demo",
        particle_types=ParticleTypeSet(
            ("unstructured_asset", "entity", "decision", "memory", "knowledge")),
    )
    tools = ToolRegistry()
    register_native_tools(tools, profile=profile)
    agents = LiveAgentRegistry()
    agents.register(Agent(key="copilot", tools_scope=""))
    llm = StubProvider(responses=[
        LlmResponse(content="", tool_calls=[
            ToolCall("native-context-assemble",
                     {"needs": [{"layer": "L1", "dims": ["semantics"]}],
                      "provided": {"L1": [{"dim": "semantics", "key": "k", "value": "v"}]}})]),
        LlmResponse(content="已为你装配上下文", tool_calls=[]),
    ])
    loop = AgentLoop(llm=llm, tools=tools, sessions=SessionManager(),
                     live_agents=agents, redline_guard=native_redline_guard(profile=profile))
    res = loop.run_turn("copilot", "帮我查 L1 语义")
    assert res["rejected"] is False and res["steps"] == 2

    log = loop.sessions.get_or_create("copilot")
    msgs = [{"role": e.kind.split("/")[0], "content": e.payload.get("content", "")}
            for e in log.events() if e.kind in ("user/message", "assistant/message")]
    page = render_conversation(events=msgs, goal="客户助手")
    assert page.ok and "已为你装配上下文" in page.html
