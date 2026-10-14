"""AgentLoop dispatch：parallel 时同轮多工具调用并发执行、结果按声明顺序回填。

T6：派发策略（sequential 默认 / parallel 多工具并发）。
验证：
  1) parallel 时同轮多工具调用真并发（慢的 a 不阻塞快的 b 完成）；
  2) 默认 sequential 串行执行（顺序 [a, b]）。
"""
from chiyu_kernel.api import AgentLoop


class _Resp:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _TC:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class _TwoCallLLM:
    """首轮返回两个工具调用，次轮返回纯文本。"""
    def __init__(self):
        self.round = 0
    def stream_chat(self, messages):
        self.round += 1
        if self.round == 1:
            return _Resp("calling", [_TC("a", {}), _TC("b", {})])
        return _Resp("done")


class _SlowTools:
    def __init__(self):
        self.order = []
    def execute(self, name, args, scope=None, redline_guard=None):
        import time
        if name == "a":
            time.sleep(0.15)  # a 慢；串行则 b 必然晚于 a 完成
        self.order.append(name)
        return {"tool": name}


class _Logs:
    def __init__(self):
        self._m = {}
    def get_or_create(self, k):
        return self._m.setdefault(k, _L())


class _L:
    def __init__(self):
        self.items = []
    def append(self, kind, payload):
        self.items.append((kind, payload))
    def derive_messages(self):
        return [{"role": "user", "content": "hi"}]


class _FakeLive:
    def get(self, key):
        return _FakeAgent()


class _FakeAgent:
    key = "agent-x"
    tools_scope = ""
    pre_step = None


def test_parallel_tools_overlap():
    tools = _SlowTools()
    loop = AgentLoop(llm=_TwoCallLLM(), tools=tools, sessions=_Logs(),
                     live_agents=_FakeLive(), dispatch="parallel")
    loop.run_turn("agent-x", "hi")
    assert tools.order == ["b", "a"]  # b 快先完成 = 真并发（串行必为 ["a","b"]）


def test_default_is_sequential():
    tools = _SlowTools()
    loop = AgentLoop(llm=_TwoCallLLM(), tools=tools, sessions=_Logs(),
                     live_agents=_FakeLive())
    loop.run_turn("agent-x", "hi")
    assert tools.order == ["a", "b"]
