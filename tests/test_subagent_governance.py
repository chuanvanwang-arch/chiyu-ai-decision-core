"""SubagentPool 治理三缰绳：depth_limit / max_concurrent / tier 分层 LLM + configure。"""
import pytest

from chiyu_kernel.api import SubagentDescriptor, SubagentPool


class FakeResp:
    def __init__(self, content="ok", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeLLM:
    """恒定回复（无工具调用），记录被使用的实例。"""
    def __init__(self, tag="base"):
        self.tag = tag
    def stream_chat(self, messages):
        return FakeResp(content=f"reply-from-{self.tag}")


class FakeSessions:
    """极简 SessionManager 替身：按 key 隔离事件列表。"""
    def __init__(self):
        self._logs = {}
    def get_or_create(self, key):
        return self._logs.setdefault(key, _Log())


class _Log:
    def __init__(self):
        self.items = []
    def append(self, kind, payload):
        self.items.append((kind, payload))
    def derive_messages(self):
        return [ {"role": m[0], "content": str(m[1])} for m in self.items
                 if m[0] in ("user/message", "assistant/message") ]


class FakeTools:
    def execute(self, name, args, scope=None, redline_guard=None):
        return {"ok": True}


def _pool(llm=None, **kw):
    return SubagentPool(llm=llm or FakeLLM(), tools=FakeTools(),
                        sessions=FakeSessions(), **kw)


def _desc(key="researcher", **kw):
    return SubagentDescriptor(key=key, role="研究", instruction="做研究", **kw)


def test_depth_limit_rejects_nested_delegation():
    p = _pool()
    p.register(_desc(depth_limit=1))
    # 第一层：parent 非 sub 会话 → depth 0，放行
    p.delegate("任务", subagent_key="researcher")
    assert p.depth_of("sub:researcher") == 0
    # 第二层：parent 已是 sub:researcher → depth 1 >= depth_limit=1 → 拒绝
    with pytest.raises(RuntimeError, match="depth_limit"):
        p.delegate("嵌套任务", subagent_key="researcher",
                   parent_session_id="sub:researcher")


def test_depth_allows_within_limit():
    p = _pool()
    p.register(_desc(depth_limit=2))
    p.delegate("任务", subagent_key="researcher", parent_session_id="sub:researcher")
    assert p.depth_of("sub:researcher") == 1


def test_max_concurrent_rejects_overflow():
    p = _pool()
    p.register(_desc(max_concurrent=1))
    p._inflight["researcher"] = 1  # 模拟已有 1 个在途
    with pytest.raises(RuntimeError, match="max_concurrent"):
        p.delegate("并发任务", subagent_key="researcher")


def test_tier_llm_selection():
    strong, base = FakeLLM("strong"), FakeLLM("base")
    p = _pool(llm=base, llm_by_tier={"lead": strong})
    p.register(_desc(tier="lead"))
    p.register(SubagentDescriptor(key="coder", role="编码", instruction="写代码"))  # tier=default
    out1 = p.delegate("t1", subagent_key="researcher")
    out2 = p.delegate("t2", subagent_key="coder")
    assert "reply-from-strong" in str(out1["messages"][-1])
    assert "reply-from-base" in str(out2["messages"][-1])


def test_configure_updates_limits():
    p = _pool()
    p.register(_desc())
    p.configure("researcher", depth_limit=3, max_concurrent=2, tier="lead")
    info = {d["key"]: d for d in p.describe_all()}["researcher"]
    assert info["depth_limit"] == 3 and info["max_concurrent"] == 2
    assert info["tier"] == "lead"
    with pytest.raises(KeyError):
        p.configure("no-such-key", depth_limit=1)
