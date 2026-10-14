from chiyu_kernel.orchestration.agent_runtime import Agent, LiveAgentRegistry
from chiyu_kernel.orchestration.agent_loop import AgentLoop
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import ToolRegistry, ToolSpec
from chiyu_kernel.llm.client import StubProvider, LlmResponse, ToolCall


def _loop():
    agents = LiveAgentRegistry()
    agents.register(Agent(key="a", tools_scope="g1"))
    tools = ToolRegistry()
    tools.register(ToolSpec("lookup", "查", scope="g1"), lambda a: {"ok": True})
    llm = StubProvider(
        responses=[LlmResponse(content="", tool_calls=[ToolCall("lookup", {"q": 1})]),
                   LlmResponse(content="done", tool_calls=[])]
    )
    return AgentLoop(llm=llm, tools=tools, sessions=SessionManager(),
                     live_agents=agents), agents


def test_turn_runs_multi_step_and_calls_tool():
    loop, _ = _loop()
    res = loop.run_turn("a", "查一下")
    assert res["rejected"] is False
    assert res["steps"] == 2
    msgs = loop.sessions.get_or_create("a").derive_messages()
    assert msgs[-1] == {"role": "assistant", "content": "done"}


def test_pre_step_can_reject():
    agents = LiveAgentRegistry()
    agents.register(Agent(key="a", pre_step=lambda msgs: None))   # 返回 None = 拒绝
    loop = AgentLoop(llm=StubProvider(responses=[LlmResponse(content="x")]),
                     tools=ToolRegistry(), sessions=SessionManager(), live_agents=agents)
    res = loop.run_turn("a", "hi")
    assert res["rejected"] is True


def test_unknown_agent_raises():
    loop, _ = _loop()
    try:
        loop.run_turn("ghost", "hi")
        assert False, "应抛 KeyError"
    except KeyError:
        pass
