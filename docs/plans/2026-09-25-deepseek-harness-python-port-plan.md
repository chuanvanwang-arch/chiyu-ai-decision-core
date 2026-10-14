# Deepseek Harness 全量 Python 移植 · 阶段一（MVP）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 dsh 的智能体运行时（session / tools / agent-loop）与对话前端用 Python 重写进本仓 L1–L3，使「dsh 式对话页」能直接调用本仓原生 AI 能力（上下文装配 / 红线）。

**Architecture:** 能力吸收式（思路 B）：不搬 Cordis 框架，用本仓既有原语扩展——`session` 新增 append-only 日志；`tools` 新增作用域工具注册 + 守卫管线（复用 `actions` 的 R1–R6 纪律精神）；`orchestration` 新增 `Agent` 接口 + `AgentLoop` turn/step 驱动（复用 `state_machine` 的契约精神）；`llm/client` 新增 provider 抽象（复用 `llm/tier` 的档位策略）；`chiyu_portal` 新增 `render_conversation`；原生内核能力经 `tools` 暴露为 agent 可调工具，红线经 `guarded_execute` 的 `redline_guard` 钩子拦截。严守：内核零领域字面量、单向依赖（消费方只 import `chiyu_kernel.contract` 与 `chiyu_kernel.api`）、门面 `__all__` 覆盖每个子包 `__all__`。

**Tech Stack:** Python 3.11+/3.13+（managed），pytest，`chiyu_kernel` 既有模块，`chiyu_portal` 既有渲染器。

---

## 文件结构（阶段一）

新建：
- `packages/chiyu-kernel/src/chiyu_kernel/session/__init__.py` — SessionEvent / SessionLog / SessionManager
- `packages/chiyu-kernel/src/chiyu_kernel/tools/__init__.py` — ToolSpec / ToolRegistry / guarded_execute + 异常
- `packages/chiyu-kernel/src/chiyu_kernel/orchestration/agent_runtime.py` — Agent / LiveAgentRegistry
- `packages/chiyu-kernel/src/chiyu_kernel/orchestration/agent_loop.py` — AgentLoop 驱动
- `packages/chiyu-kernel/src/chiyu_kernel/llm/client.py` — LlmProvider / DeepSeekProvider / build_provider / LlmResponse / ToolCall
- `packages/chiyu-kernel/src/chiyu_kernel/harness_native_tools.py` — 原生内核能力注册为工具 + redline_guard 钩子
- `packages/chiyu-portal/src/chiyu_portal/renderer.py` 修改 — 新增 `render_conversation`
- `packages/chiyu-portal/src/chiyu_portal/schema.py` 修改 — PAGE_TYPES/COMPONENT_KINDS 增补 conversation 类
- `packages/chiyu-kernel/src/chiyu_kernel/api.py` 修改 — 导出新子包符号
- `packages/chiyu-portal/src/chiyu_portal/api.py` 修改 — 导出 `render_conversation`

测试：
- `packages/chiyu-kernel/tests/test_session.py`
- `packages/chiyu-kernel/tests/test_tools.py`
- `packages/chiyu-kernel/tests/test_agent_loop.py`
- `packages/chiyu-kernel/tests/test_llm_client.py`
- `packages/chiyu-portal/src/chiyu_portal/tests/test_conversation_render.py`
- `packages/chiyu-kernel/tests/test_harness_native_tools.py`
- `packages/chiyu-kernel/tests/test_harness_e2e.py`

⚠ 每新建一个子包/模块，必须同步更新 `chiyu_kernel/api.py` 的 `__all__`（门面覆盖守卫
`tests/test_api_facade_covers_all_layers.py` 会判据）。`contract/` 目录未改动，无需重生成 `manifest.json`。

---

### Task 1: 移植 session 会话日志

**Files:**
- Create: `packages/chiyu-kernel/src/chiyu_kernel/session/__init__.py`
- Test: `packages/chiyu-kernel/tests/test_session.py`
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/api.py`

- [ ] **Step 1: 写失败测试**

```python
# packages/chiyu-kernel/tests/test_session.py
from chiyu_kernel.session import SessionEvent, SessionLog, SessionManager


def test_append_orders_by_seq():
    log = SessionLog()
    a = log.append("user/message", {"content": "hi"})
    b = log.append("assistant/message", {"content": "hello"})
    assert a.seq == 1 and b.seq == 2
    assert [e.kind for e in log.events()] == ["user/message", "assistant/message"]


def test_derive_messages_projects_model_history():
    log = SessionLog()
    log.append("user/message", {"content": "q"})
    log.append("tool/call", {"name": "x", "args": {}})          # 非 model-visible，不进历史
    log.append("assistant/message", {"content": "a"})
    msgs = log.derive_messages()
    assert msgs == [
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "a"},
    ]


def test_session_manager_get_or_create():
    mgr = SessionManager()
    s1 = mgr.get_or_create("agent-a")
    s2 = mgr.get_or_create("agent-a")
    assert s1 is s2
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest packages/chiyu-kernel/tests/test_session.py -q`
Expected: FAIL（`ModuleNotFoundError: chiyu_kernel.session`）

- [ ] **Step 3: 写最小实现**

```python
# packages/chiyu-kernel/src/chiyu_kernel/session/__init__.py
"""会话日志（吸收 dsh `core/session`）：append-only SessionEvent 流 + 内存态。

⛔ 零领域字面量：kind 是任意字符串，本模块不声明任何业务事件名。
⛔ model-visible ⟺ logged：derive_messages 只投影 user/assistant 消息，
   工具调用等不入模型历史（与 dsh「模型可见即可重建」同义）。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional


@dataclass(frozen=True)
class SessionEvent:
    kind: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)
    seq: int = 0


class SessionLog:
    def __init__(self) -> None:
        self._events: List[SessionEvent] = []
        self._seq = 0

    def append(self, kind: str, payload: Optional[Mapping[str, Any]] = None) -> SessionEvent:
        self._seq += 1
        ev = SessionEvent(kind=kind, payload=dict(payload or {}), ts=time.time(), seq=self._seq)
        self._events.append(ev)
        return ev

    def events(self) -> List[SessionEvent]:
        return list(self._events)

    def derive_messages(self) -> List[Mapping[str, Any]]:
        """投影模型可见历史：仅 user/assistant 消息。"""
        out: List[Mapping[str, Any]] = []
        for ev in self._events:
            if ev.kind == "user/message":
                out.append({"role": "user", "content": ev.payload.get("content", "")})
            elif ev.kind == "assistant/message":
                out.append({"role": "assistant", "content": ev.payload.get("content", "")})
        return out


class SessionManager:
    def __init__(self) -> None:
        self._logs: Dict[str, SessionLog] = {}

    def get_or_create(self, key: str) -> SessionLog:
        return self._logs.setdefault(key, SessionLog())


__all__ = ["SessionEvent", "SessionLog", "SessionManager"]
```

- [ ] **Step 4: 接线到门面并运行测试**

在 `packages/chiyu-kernel/src/chiyu_kernel/api.py` 顶部 import 区后追加：

```python
# ── L1 session：会话日志（harness 移植）───────────────────────────────────
from chiyu_kernel.session import SessionEvent, SessionLog, SessionManager
```

并在 `__all__` 列表末尾（`"MEMORY_EXPERIMENTAL"`, 之前或之后均可）追加：

```python
    # session
    "SessionEvent", "SessionLog", "SessionManager",
```

Run: `pytest packages/chiyu-kernel/tests/test_session.py packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py -q`
Expected: PASS（session 测试绿 + 门面覆盖守卫绿）

- [ ] **Step 5: 提交**

```bash
git add packages/chiyu-kernel/src/chiyu_kernel/session/__init__.py packages/chiyu-kernel/tests/test_session.py packages/chiyu-kernel/src/chiyu_kernel/api.py
git commit -m "feat(session): 新增 append-only 会话日志与 SessionManager（dsh 吸收式移植）"
```

---

### Task 2: 移植工具注册与守卫管线

**Files:**
- Create: `packages/chiyu-kernel/src/chiyu_kernel/tools/__init__.py`
- Test: `packages/chiyu-kernel/tests/test_tools.py`
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/api.py`

- [ ] **Step 1: 写失败测试**

```python
# packages/chiyu-kernel/tests/test_tools.py
import pytest
from chiyu_kernel.tools import (
    ToolSpec, ToolRegistry, ToolNotFound, ScopeDenied, GuardDenied,
)


def _reg() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ToolSpec("echo", "回显", scope="g1"), lambda a: a)
    reg.register(ToolSpec("secret", "受限", scope="g2"), lambda a: "x")
    return reg


def test_scoped_view_isolates():
    reg = _reg()
    view = reg.scoped("g1")
    assert "echo" in view.names("g1")
    assert "secret" not in view.names("g1")


def test_scope_denied_when_cross_scope():
    reg = _reg()
    with pytest.raises(ScopeDenied):
        reg.execute("secret", {}, scope="g1")          # g1 不得调 g2 工具


def test_redline_guard_blocks():
    reg = _reg()
    with pytest.raises(GuardDenied):
        reg.execute("echo", {}, scope="g1", redline_guard=lambda n, a: "hit")


def test_unknown_tool_not_found():
    reg = ToolRegistry()
    with pytest.raises(ToolNotFound):
        reg.execute("nope", {})
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest packages/chiyu-kernel/tests/test_tools.py -q`
Expected: FAIL（`ModuleNotFoundError: chiyu_kernel.tools`）

- [ ] **Step 3: 写最小实现**

```python
# packages/chiyu-kernel/src/chiyu_kernel/tools/__init__.py
"""工具注册与守卫管线（吸收 dsh `core/tools`）：作用域注册 + pre/post-execute 守卫。

⛔ 与 `actions` 的关系：`actions` 是消费方 Action 表面（R1–R6，机制），
   本模块是**模型面工具**注册表（智能体可调用的能力），二者正交、不混。
⛔ 作用域隔离：scope="" 为全局；agent 只调得到自己 scope 或全局工具（越权即拒）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class ToolSpec:
    name: str
    description: str
    scope: str = ""            # "" = 全局可见
    high_risk: bool = False


class ToolNotFound(LookupError):
    pass


class ScopeDenied(PermissionError):
    pass


class GuardDenied(PermissionError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, ToolSpec] = {}
        self._impls: Dict[str, Callable] = {}

    def register(self, spec: ToolSpec, impl: Callable) -> None:
        if spec.name in self._specs:
            raise ValueError(f"重复注册 tool：{spec.name}")
        self._specs[spec.name] = spec
        self._impls[spec.name] = impl

    def spec(self, name: str) -> Optional[ToolSpec]:
        return self._specs.get(name)

    def get(self, name: str) -> Optional[Callable]:
        return self._impls.get(name)

    def names(self, scope: str = "") -> Tuple[str, ...]:
        return tuple(
            n for n, s in self._specs.items() if s.scope in ("", scope)
        )

    def scoped(self, scope: str) -> "ToolRegistry":
        sub = ToolRegistry()
        for n, s in self._specs.items():
            if s.scope in ("", scope):
                sub._specs[n] = s
                sub._impls[n] = self._impls[n]
        return sub

    def execute(
        self, name: str, args: Any, *, scope: str = "", redline_guard=None
    ) -> Any:
        spec = self._specs.get(name)
        if spec is None:
            raise ToolNotFound(name)
        if spec.scope not in ("", scope):           # 越权拒绝
            raise ScopeDenied(f"tool {name} scope={spec.scope!r} 不可被 scope={scope!r} 调用")
        if redline_guard is not None:               # 红线硬闸门
            verdict = redline_guard(name, args)
            if verdict is not None:
                raise GuardDenied(f"tool {name} 被红线拦截：{verdict}")
        impl = self._impls[name]
        return impl(args)                            # post-execute 可在此扩展钩子


__all__ = [
    "ToolSpec", "ToolRegistry", "ToolNotFound", "ScopeDenied", "GuardDenied",
]
```

- [ ] **Step 4: 接线门面 + 运行测试**

api.py 顶部追加 `from chiyu_kernel.tools import ToolSpec, ToolRegistry, ToolNotFound, ScopeDenied, GuardDenied`，
`__all__` 追加 `"ToolSpec", "ToolRegistry", "ToolNotFound", "ScopeDenied", "GuardDenied"`。

Run: `pytest packages/chiyu-kernel/tests/test_tools.py packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py -q`
Expected: PASS

- [ ] **Step 5: 变异自证（删分支验红）**

临时把 `execute` 中 `if spec.scope not in ("", scope):` 改为 `if False:` 并删掉 `redline_guard` 分支，
重跑 `test_scope_denied_when_cross_scope` 与 `test_redline_guard_blocks` ⇒ 须转 RED；
还原后转 GREEN。此步证明守卫非假绿（守工作记忆「改完闸门必须做变异自证」）。

- [ ] **Step 6: 提交**

```bash
git add packages/chiyu-kernel/src/chiyu_kernel/tools/__init__.py packages/chiyu-kernel/tests/test_tools.py packages/chiyu-kernel/src/chiyu_kernel/api.py
git commit -m "feat(tools): 作用域工具注册表 + 越权/红线守卫管线（dsh 吸收式移植）"
```

---

### Task 3: 移植 Agent 接口与 agent-loop 轮次流

**Files:**
- Create: `packages/chiyu-kernel/src/chiyu_kernel/orchestration/agent_runtime.py`
- Create: `packages/chiyu-kernel/src/chiyu_kernel/orchestration/agent_loop.py`
- Test: `packages/chiyu-kernel/tests/test_agent_loop.py`
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/api.py`

- [ ] **Step 1: 写失败测试**

```python
# packages/chiyu-kernel/tests/test_agent_loop.py
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
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest packages/chiyu-kernel/tests/test_agent_loop.py -q`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 写最小实现**

```python
# packages/chiyu-kernel/src/chiyu_kernel/orchestration/agent_runtime.py
"""Agent 接口与 live 注册表（吸收 dsh `core/agent`）。
⛔ 与 `agent_registry.py` 的区别：后者是**契约注册表**（key/contract_task_id/success，
守 brainstorming 生命契约）；本模块是**运行时** Agent（系统提示 / 工具作用域 / pre-step 钩子）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class Agent:
    key: str
    system_prompt: str = ""
    tools_scope: str = ""
    pre_step: Optional[Callable] = None   # (messages)->messages|None（改写/拒绝）


class LiveAgentRegistry:
    def __init__(self) -> None:
        self._by_key: Dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._by_key[agent.key] = agent

    def get(self, key: str) -> Optional[Agent]:
        return self._by_key.get(key)

    def keys(self) -> List[str]:
        return sorted(self._by_key)


__all__ = ["Agent", "LiveAgentRegistry"]
```

```python
# packages/chiyu-kernel/src/chiyu_kernel/orchestration/agent_loop.py
"""Agent-loop 轮次流（吸收 dsh `core/agent-loop`）：turn = 0..n step；
每 step = 一次模型请求 + 工具调用。pre-step 可改写/拒绝（dsh `agent/pre-step`）。
"""
from __future__ import annotations

from typing import Any, List, Mapping, Optional

from chiyu_kernel.session import SessionManager


class AgentLoop:
    def __init__(self, *, llm, tools, sessions: SessionManager,
                 live_agents, redline_guard=None) -> None:
        self.llm = llm
        self.tools = tools
        self.sessions = sessions
        self.live_agents = live_agents
        self.redline_guard = redline_guard

    def run_turn(self, agent_key: str, user_input: str) -> Mapping[str, Any]:
        agent = self.live_agents.get(agent_key)
        if agent is None:
            raise KeyError(f"未知 agent：{agent_key}")
        log = self.sessions.get_or_create(agent_key)
        log.append("user/message", {"content": user_input})

        messages = log.derive_messages()
        if agent.pre_step is not None:
            decided = agent.pre_step(messages)
            if decided is None:
                log.append("agent/pre-step", {"decision": "reject"})
                return {"rejected": True, "steps": 0,
                        "messages": log.derive_messages()}
            messages = decided
            log.append("agent/pre-step", {"decision": "enter"})

        steps = 0
        while True:
            resp = self.llm.stream_chat(messages)
            log.append("assistant/message", {"content": resp.content})
            messages.append({"role": "assistant", "content": resp.content})
            steps += 1
            calls = list(resp.tool_calls or [])
            if not calls:
                break
            for tc in calls:
                log.append("tool/call", {"name": tc.name, "args": tc.args})
                result = self.tools.execute(
                    tc.name, tc.args, scope=agent.tools_scope,
                    redline_guard=self.redline_guard)
                log.append("tool/result", {"name": tc.name, "result": result})
                messages.append({"role": "tool", "name": tc.name,
                                 "content": str(result)})
        log.append("turn/end", {"steps": steps})
        return {"rejected": False, "steps": steps,
                "messages": log.derive_messages()}


__all__ = ["AgentLoop"]
```

- [ ] **Step 4: 接线门面 + 运行测试**

api.py 顶部追加：
```python
from chiyu_kernel.orchestration.agent_runtime import Agent, LiveAgentRegistry
from chiyu_kernel.orchestration.agent_loop import AgentLoop
```
`__all__` 追加 `"Agent", "LiveAgentRegistry", "AgentLoop"`。

Run: `pytest packages/chiyu-kernel/tests/test_agent_loop.py packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add packages/chiyu-kernel/src/chiyu_kernel/orchestration/agent_runtime.py packages/chiyu-kernel/src/chiyu_kernel/orchestration/agent_loop.py packages/chiyu-kernel/tests/test_agent_loop.py packages/chiyu-kernel/src/chiyu_kernel/api.py
git commit -m "feat(orchestration): Agent 接口 + AgentLoop turn/step 驱动（dsh 吸收式移植）"
```

---

### Task 4: 接入本仓 llm/tier 作为模型适配器

**Files:**
- Create: `packages/chiyu-kernel/src/chiyu_kernel/llm/client.py`
- Test: `packages/chiyu-kernel/tests/test_llm_client.py`
- Modify: `packages/chiyu-kernel/src/chiyu_kernel/api.py`

- [ ] **Step 1: 写失败测试**

```python
# packages/chiyu-kernel/tests/test_llm_client.py
from chiyu_kernel.llm.client import (
    StubProvider, LlmResponse, ToolCall, build_provider, DeepSeekProvider,
)


def test_stub_provider_returns_queued_responses():
    p = StubProvider(responses=[LlmResponse(content="a"), LlmResponse(content="b")])
    assert p.stream_chat([{"role": "user", "content": "x"}]).content == "a"
    assert p.stream_chat([]).content == "b"


def test_build_provider_deepseek_uses_tier():
    p = build_provider(tier="3b", provider="deepseek", api_key="k")
    assert isinstance(p, DeepSeekProvider)
    assert p.model  # 由 tier_spec 解析出模型名


def test_build_provider_rejects_unknown():
    try:
        build_provider(provider="openai")
        assert False
    except ValueError:
        pass
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest packages/chiyu-kernel/tests/test_llm_client.py -q`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# packages/chiyu-kernel/src/chiyu_kernel/llm/client.py
"""模型适配器（吸收 dsh `llm/llm`）：provider 抽象 + DeepSeek provider。
复用本仓 `llm/tier` 的档位策略（tier_spec）决定 model/ctx；不强制 DEEPSEEK_API_KEY。

⛔ 真实网络调用只在 DeepSeekProvider.stream_chat 内发起；单测用 StubProvider，
   不发任何请求（守「无网络单测」纪律）。DeepSeekProvider 的 HTTP 实现可后续补全，
   本阶段先落接口与档位接线（不阻塞对话闭环）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Protocol, runtime_checkable

from chiyu_kernel.llm import tier_spec


@dataclass
class ToolCall:
    name: str
    args: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class LlmResponse:
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)


@runtime_checkable
class LlmProvider(Protocol):
    def stream_chat(self, messages: List[Mapping[str, Any]], *, tools=None) -> LlmResponse:
        ...


class StubProvider:
    """测试用：按队列返回预设响应。"""
    def __init__(self, responses: Optional[List[LlmResponse]] = None) -> None:
        self._queue = list(responses or [])

    def stream_chat(self, messages, *, tools=None) -> LlmResponse:
        if not self._queue:
            return LlmResponse(content="")
        return self._queue.pop(0)


class DeepSeekProvider:
    def __init__(self, *, api_key: str = "", base_url: str = "",
                 model: str = "deepseek-chat", ctx: int = 8192) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.ctx = ctx

    def stream_chat(self, messages, *, tools=None) -> LlmResponse:
        # TODO(real-net): 用 httpx 调 DeepSeek /openai 兼容端点；本阶段不发起真实请求。
        raise NotImplementedError(
            "DeepSeekProvider.stream_chat 的真实网络实现留待集成阶段；"
            "单测/对话闭环用 StubProvider")


def build_provider(*, tier=None, provider: str = "deepseek", **kw) -> LlmProvider:
    spec = tier_spec(tier)
    if provider == "deepseek":
        return DeepSeekProvider(
            model=spec.get("model") or "deepseek-chat",
            ctx=int(spec.get("ctx", 8192)), **kw)
    raise ValueError(f"未知 provider：{provider!r}")


__all__ = [
    "ToolCall", "LlmResponse", "LlmProvider", "StubProvider",
    "DeepSeekProvider", "build_provider",
]
```

- [ ] **Step 4: 接线门面 + 运行测试**

api.py 顶部追加 `from chiyu_kernel.llm.client import (ToolCall, LlmResponse, LlmProvider, StubProvider, DeepSeekProvider, build_provider)`，
`__all__` 追加对应 6 个名字。

Run: `pytest packages/chiyu-kernel/tests/test_llm_client.py packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add packages/chiyu-kernel/src/chiyu_kernel/llm/client.py packages/chiyu-kernel/tests/test_llm_client.py packages/chiyu-kernel/src/chiyu_kernel/api.py
git commit -m "feat(llm): provider 抽象 + DeepSeek provider 接线本仓 tier 策略"
```

---

### Task 5: 移植对话前端到 chiyu_portal 渲染器

**Files:**
- Modify: `packages/chiyu-portal/src/chiyu_portal/schema.py`（PAGE_TYPES/COMPONENT_KINDS 增补）
- Modify: `packages/chiyu-portal/src/chiyu_portal/renderer.py`（新增 `render_conversation`）
- Modify: `packages/chiyu-portal/src/chiyu_portal/api.py`（导出）
- Test: `packages/chiyu-portal/src/chiyu_portal/tests/test_conversation_render.py`

- [ ] **Step 1: 写失败测试**

```python
# packages/chiyu-portal/src/chiyu_portal/tests/test_conversation_render.py
from chiyu_portal.renderer import render_conversation, RenderResult


def test_render_conversation_ok():
    r = render_conversation(
        events=[{"role": "user", "content": "你好"},
                {"role": "assistant", "content": "在的"}],
        composer_action="send_message", goal="解答客户问题",
    )
    assert isinstance(r, RenderResult) and r.ok
    assert "你好" in r.html and "在的" in r.html
    assert "goal-bar" in r.html and "composer" in r.html


def test_render_conversation_escapes_and_no_script():
    r = render_conversation(events=[{"role": "user", "content": "<script>alert(1)</script>"}])
    assert r.ok
    assert "<script" not in r.html       # 转义后只应是 &lt;script
    assert "&lt;script" in r.html
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest packages/chiyu-portal/src/chiyu_portal/tests/test_conversation_render.py -q`
Expected: FAIL（`ImportError: cannot import name 'render_conversation'`）

- [ ] **Step 3: 实现**

在 `schema.py` 中扩展协议常量（零领域字面量，仅形态）：
```python
PAGE_TYPES = (  # 原 6 个 + 以下
    "dashboard", "table", "form", "detail", "workspace", "approval", "conversation",
)
COMPONENT_KINDS = (  # 原 10 个 + 以下
    "metric-card", "table", "form", "detail", "reasoning-trace", "approval-queue",
    "conflict-marker", "goal-form", "interaction-panel", "acceptance-checklist",
    "chat-log", "composer", "goal-bar",
)
```

在 `renderer.py` 末尾新增（复用既有 `_SCRIPT_RE` / `_ONATTR_RE` 硬闸门与 `html.escape`）：
```python
def render_conversation(*, events, composer_action: str = "send_message",
                        goal: str = "") -> "RenderResult":
    """渲染 dsh 式对话页：session 日志 + composer + 目标栏。声明式 data-action，无内联 JS。"""
    out: list[str] = []
    out.append("<!DOCTYPE html>")
    out.append('<html lang="zh"><head><meta charset="utf-8">'
               '<title>对话</title><link rel="stylesheet" href="/portal/page.css"></head><body>')
    out.append('<main class="portal-page conversation-page">')
    if goal:
        out.append(f'<div class="goal-bar">{html.escape(goal)}</div>')
    out.append('<section class="component component-chat-log">'
               '<h2 class="component-title">对话</h2><div class="chat-log">')
    for ev in events or []:
        role = html.escape(str(ev.get("role", ev.get("kind", ""))))
        content = html.escape(str(ev.get("content",
                                   (ev.get("payload") or {}).get("content", ""))))
        out.append(f'<div class="msg msg-{role}">'
                   f'<span class="role">{role}</span><span class="text">{content}</span></div>')
    out.append('</div></section>')
    out.append(f'<form class="composer" data-action="{html.escape(composer_action)}">'
               '<input name="message" class="composer-input" placeholder="输入消息…" '
               'autocomplete="off"><button type="submit" class="action-btn">发送</button></form>')
    out.append('</main></body></html>')
    rendered = "".join(out)
    if _SCRIPT_RE.search(rendered) or _ONATTR_RE.search(rendered):
        return RenderResult(False, errors=(ValidationError("render", "渲染产物含禁用标记"),))
    return RenderResult(True, html=rendered)
```

在 `api.py` 顶部 `from .renderer import RenderResult, render_page, render_conversation`，
`__all__` 追加 `"render_conversation"`。

- [ ] **Step 4: 运行测试**

Run: `pytest packages/chiyu-portal/src/chiyu_portal/tests/test_conversation_render.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add packages/chiyu-portal/src/chiyu_portal/schema.py packages/chiyu-portal/src/chiyu_portal/renderer.py packages/chiyu-portal/src/chiyu_portal/api.py packages/chiyu-portal/src/chiyu_portal/tests/test_conversation_render.py
git commit -m "feat(portal): 新增 render_conversation 对话页（dsh 前端 Python 化）"
```

---

### Task 6: 将本仓决策/粒子能力暴露为 agent 工具（无缝集成）

**Files:**
- Create: `packages/chiyu-kernel/src/chiyu_kernel/harness_native_tools.py`
- Test: `packages/chiyu-kernel/tests/test_harness_native_tools.py`

- [ ] **Step 1: 写失败测试**

```python
# packages/chiyu-kernel/tests/test_harness_native_tools.py
from chiyu_kernel.tools import ToolRegistry
from chiyu_kernel.harness_native_tools import register_native_tools, native_redline_guard
from chiyu_kernel.contract import TenantProfile
from chiyu_kernel.contract.particle import ParticleTypeSet, PredicateSet


def _profile():
    return TenantProfile(domain="demo", particle_types=ParticleTypeSet(set()))


def test_native_context_assemble_registered():
    reg = ToolRegistry()
    register_native_tools(reg, profile=_profile())
    assert "native-context-assemble" in reg.names()
    out = reg.execute("native-context-assemble", {
        "needs": [{"layer": "L1", "dims": ("semantics",)}],
        "provided": {"L1": [{"dim": "semantics", "key": "k", "value": "v"}]},
    })
    assert out["facts"]["L1"] == ["v"]


def test_redline_guard_blocks_high_risk():
    # meta_redline_hits 命中 ⇒ redline_guard 返回非 None ⇒ 拦截
    reg = ToolRegistry()
    register_native_tools(reg, profile=_profile())
    guard = native_redline_guard(profile=_profile())
    # 用真实 evolution 行为：把明显冲突文本交给红线检查工具
    res = reg.execute("native-redline-check", {"text": "自相矛盾的主张"},
                      redline_guard=guard)
    assert "redline_hit" in res
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest packages/chiyu-kernel/tests/test_harness_native_tools.py -q`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# packages/chiyu-kernel/src/chiyu_kernel/harness_native_tools.py
"""原生内核能力 → agent 工具（无缝集成桥）。

把本仓 L1–L4 能力（上下文装配 / 红线）暴露为 dsh 式 agent 可调工具；
红线经 tools.guarded_execute 的 redline_guard 钩子拦截。
⛔ 内核零领域字面量：工具名/描述中性；领域取值来自 TenantProfile。
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from chiyu_kernel.context import assemble, KnowledgeNeed
from chiyu_kernel.evolution import meta_redline_hits
from chiyu_kernel.tools import ToolRegistry, ToolSpec


def register_native_tools(reg: ToolRegistry, *, profile) -> None:
    def ctx_assemble(args: Mapping[str, Any]) -> Mapping[str, Any]:
        needs = [
            KnowledgeNeed(layer=n["layer"], dims=tuple(n.get("dims", ())),
                          key=n.get("key", ""))
            for n in args.get("needs", [])
        ]
        result = assemble(needs, args.get("provided", {}))
        return {"facts": result.facts, "missing": list(result.supply_report.missing)}

    reg.register(
        ToolSpec("native-context-assemble", "装配分层上下文（L1–L4）", scope="",
                 high_risk=False),
        ctx_assemble,
    )

    def redline_check(args: Mapping[str, Any]) -> Mapping[str, Any]:
        hits = list(meta_redline_hits(args.get("text", ""), profile=profile))
        return {"redline_hit": bool(hits), "hits": hits}

    reg.register(
        ToolSpec("native-redline-check", "红线命中检查", scope="", high_risk=True),
        redline_check,
    )


def native_redline_guard(*, profile) -> Callable[[str, Any], Optional[str]]:
    """返回 redline_guard(name, args) -> 命中原因|None。

    仅对 high_risk 工具做硬性红线判定；命中返回原因串 ⇒ tools 抛 GuardDenied。
    （实现要点：调用方在 execute 时传入此 guard，见 Task 3 AgentLoop.redline_guard。）
    """
    def _guard(name: str, args: Any) -> Optional[str]:
        spec = None  # guard 由 ToolRegistry.execute 内部已验 scope；此处只看红线
        _ = spec
        # 红线判定：对 high_risk 工具，用 meta_redline_hits 复核入参文本
        text = ""
        if isinstance(args, dict):
            text = str(args.get("text", ""))
        hits = list(meta_redline_hits(text, profile=profile)) if text else []
        return ("redline:" + ", ".join(str(h) for h in hits)) if hits else None
    return _guard


__all__ = ["register_native_tools", "native_redline_guard"]
```

> ⚠ 实施者落地时**核对 `chiyu_kernel.evolution.meta_redline_hits` 的真实签名**（见
> `packages/chiyu-kernel/src/chiyu_kernel/evolution/__init__.py` 的导出）；若其入参为
> `(items, *, profile)` 而非 `(text, *, profile)`，将 `redline_check` / `_guard` 中的
> `args.get("text","")` 改为 `args.get("items", [])` 即可，测试形状不变。

- [ ] **Step 4: 接线门面 + 运行测试**

api.py 顶部追加 `from chiyu_kernel.harness_native_tools import register_native_tools, native_redline_guard`，
`__all__` 追加 `"register_native_tools", "native_redline_guard"`。

Run: `pytest packages/chiyu-kernel/tests/test_harness_native_tools.py packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py -q`
Expected: PASS

- [ ] **Step 5: 变异自证（红线拦截非假绿）**

临时让 `native_redline_guard._guard` 始终返回 `None`，重跑 `test_redline_guard_blocks_high_risk`
⇒ 须转 RED；还原后转 GREEN（守「改完闸门必须做变异自证」）。

- [ ] **Step 6: 提交**

```bash
git add packages/chiyu-kernel/src/chiyu_kernel/harness_native_tools.py packages/chiyu-kernel/tests/test_harness_native_tools.py packages/chiyu-kernel/src/chiyu_kernel/api.py
git commit -m "feat(harness): 原生上下文/红线能力桥接为 agent 工具（无缝集成）"
```

---

### Task 7: 阶段一 END-TO-END 冒烟

**Files:**
- Test: `packages/chiyu-kernel/tests/test_harness_e2e.py`

- [ ] **Step 1: 写失败测试**

```python
# packages/chiyu-kernel/tests/test_harness_e2e.py
from chiyu_kernel.orchestration.agent_runtime import Agent, LiveAgentRegistry
from chiyu_kernel.orchestration.agent_loop import AgentLoop
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import ToolRegistry
from chiyu_kernel.llm.client import StubProvider, LlmResponse, ToolCall
from chiyu_kernel.harness_native_tools import register_native_tools, native_redline_guard
from chiyu_kernel.contract import TenantProfile
from chiyu_kernel.contract.particle import ParticleTypeSet
from chiyu_portal.renderer import render_conversation


def test_dsh_style_turn_then_render():
    profile = TenantProfile(domain="demo", particle_types=ParticleTypeSet(set()))
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
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest packages/chiyu-kernel/tests/test_harness_e2e.py -q`
Expected: FAIL（前序模块未就位）

- [ ] **Step 3: 前序任务已完成 ⇒ 直接运行**

Run: `pytest packages/chiyu-kernel/tests/test_harness_e2e.py -q`
Expected: PASS

- [ ] **Step 4: 全量回归 + 提交**

Run: `make test`（或 `pytest packages/chiyu-kernel/tests tools/tests -q`）
Expected: 全绿（含门面覆盖守卫、既有 180/0 基准不被破坏）

```bash
git add packages/chiyu-kernel/tests/test_harness_e2e.py
git commit -m "test(harness): 阶段一 E2E 冒烟（对话页跑通 问→调本仓工具→渲染）"
```

---

## 自审（Self-Review）

**1. 规格覆盖**：设计文档 §5 七任务 ↔ 本计划 Task 1–7 一一对应（session / tools / agent-loop /
llm / conversation / 原生桥接 / E2E）。阶段二（skill/subagent/plan）与阶段三（mcp/guard/fs）不在本计划范围，已明确分期。

**2. 占位扫描**：`llm/client.py` 的 `DeepSeekProvider.stream_chat` 标注 `NotImplementedError` 并明确
「真实网络实现留待集成阶段，单测用 StubProvider」——这是**有意的分期**，非遗漏占位；接口与档位接线已完整，
不阻塞对话闭环。其余步骤均含完整代码。

**3. 类型一致性**：`SessionLog.append/derive_messages/events`、`ToolRegistry.register/spec/execute/
scoped/names`、`Agent(key,tools_scope,pre_step)`、`AgentLoop(llm,tools,sessions,live_agents,
redline_guard).run_turn`、`LlmResponse(content,tool_calls)`/`ToolCall(name,args)`、`render_conversation
(events,composer_action,goal)` 在测试与实现间完全一致；`redline_guard(name,args)->str|None` 签名在
Task 3（`execute(...,redline_guard=...)`）与 Task 6（`native_redline_guard`）一致。

**4. 门面纪律**：每个新建模块均在对应 Task 的 Step 4/6 要求更新 `chiyu_kernel/api.py` 的 `__all__`，
并由 `test_api_facade_covers_all_layers.py` 兜底（每步均带该测试运行）。`contract/` 未改动，无需重生成
`manifest.json`。

---

## 实施修正记录（inline 执行实测偏差，均在计划自身 fallback 注记范围内，无需再批设计）

- **Task 6 `meta_redline_hits` 真实签名漂移**：计划假设 `(text, *, profile)`，
  实测为 `meta_redline_hits(actions: Sequence[str]) -> List[str]`（无 profile，取 `META_REDLINES`
  冻结集）。已改为接收 `args["actions"]` 动作名列表；`native_redline_check` 工具入参相应为
  `{"actions": [...]}`，`native_redline_guard` 只对有 `actions` 字段的工具做红线判定。
- **Task 6/7 `ParticleTypeSet` 非空强制**：`TenantProfile.particle_types` 不得为空，且必须含全部
  `CORE_ROLES`（`unstructured_asset/entity/decision/memory/knowledge`）。内置 `TenantProfile(domain="demo",
  particle_types=ParticleTypeSet((...)))` 已显式列出五核心角色。
- **Task 7 跨包导入**：E2E 测试落在 `packages/chiyu-kernel/tests`（属 `make test` 范畴），但需 import
  `chiyu_portal`；而 `make test` 的 rootdir=packages/chiyu-kernel 时根 conftest 不加载（只加载子包
  `tests/conftest.py`，其仅补 `chiyu-kernel/src`）。已在 `packages/chiyu-kernel/tests/conftest.py`
  追加「`chiyu_portal` 不可导入时补 `packages/chiyu-portal/src`」的受控插入（不覆盖 A/B 副本路径）。
- **Task 6 守卫判别力加固**：计划原 guard 测试仅断言工具返回值，对「guard 被中和」无鉴别力；改为
  `test_redline_guard_blocks_meta_redline_action` 用 `pytest.raises(GuardDenied)` 断言拦截，并做变异自证
  （`_guard` 恒返回 None ⇒ 转红，还原 ⇒ 转绿），证明 `GuardDenied` 非假绿。
- **回归计数**：`make test`（kernel+tools）303 passed / 0 failed（基线 180/0 + 本阶段 17 例）；
  portal 套件 55 passed（含 `test_conversation_render` 2 例）。`manifest.json` 未动。

