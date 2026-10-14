# chiyu-host session.prompt 接入 L1–L2 上下文装配（复用 AgentLoop）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `session.prompt` 从「仅 append 事件不调 LLM」升级为「复用 AgentLoop 真跑一轮 LLM，并把 L1–L2 上下文装配结果注入模型上下文」，返回契约不变的 `{accepted:true}`。

**Architecture:** 复用已落地的 `AgentLoop` + `LiveAgentRegistry`（与 subagent 同链、共享 `redline_guard`）。按 `sid` 惰性注册一个 session 主 agent，其 `pre_step` 钩子调用 `chiyu_kernel.context.assemble(L1–L2, provided={})` 把装配 facts 作为 system 上下文消息插入消息首部，并把结构化缺口（`missing`/`degraded_layers`）写入会话日志 `context/assemble` 事件（fail-safe 不抛错）。不连 pg、不直接 import `chiyu_kernel.api` 门面（与 M0/M1 同策略）。

**Tech Stack:** Python 3.13（managed venv）、pytest、chiyu_kernel（session / orchestration.agent_loop / orchestration.agent_runtime / context.assembly / harness_native_tools）。

---

## 文件结构

- Modify: `packages/chiyu-host/src/chiyu_host/methods.py`
  - 顶部新增 import：`AgentLoop` / `Agent` / `assemble` / `KnowledgeNeed` / `KNOWLEDGE_NEEDS_DEFAULT_DIMS`。
  - 模块级新增 `_SESSION_CTX_NEEDS`（L1–L2 中性装配需求）。
  - 新增 `_ctx_inject(sid)`（pre_step 装配钩子）与 `_ensure_session_agent(sid)`（惰性注册）。
  - 改写 `session_prompt`：复用 `AgentLoop` 同步委派（不再自行 append user 事件）。
- Create: `packages/chiyu-host/tests/test_rpc_session_prompt_context.py`
  - 主判别项（真调 LLM + 装配元数据落档）+ 变异自证（移除钩子转红）。

---

## Task 1: 写失败测试（session.prompt 装配判别项）

**Files:**
- Create: `packages/chiyu-host/tests/test_rpc_session_prompt_context.py`

- [ ] **Step 1: 写失败测试**

```python
"""session.prompt 接入 L1–L2 上下文装配（复用 AgentLoop 同步委派）测试。

判别项（防假绿）：
- session.prompt 返回 {accepted:true} 且该 session 会话真现 assistant/message（证明真调 LLM）；
- 会话日志须含 context/assemble 事件（装配元数据结构化落档，missing 暴露 L1/L2 缺口）；
- 变异自证：移除 pre_step 装配钩子后，context/assemble 判别项须转红（防假绿）。
"""
from __future__ import annotations

from chiyu_host.methods import session_create, session_prompt, session_history


def _kinds(sid: str):
    return [e["event"].get("type") for e in session_history({"sessionId": sid})["events"]]


def test_session_prompt_returns_accepted_and_runs_llm_turn():
    """session.prompt 须返回 accepted:true 且会话真现 assistant/message（真调 LLM 闭环）。"""
    sid = session_create({"sessionId": "sp-1"})["sessionId"]
    v = session_prompt({"sessionId": sid, "content": [{"type": "text", "text": "你好"}]})
    assert v == {"accepted": True}
    kinds = _kinds(sid)
    assert "user/message" in kinds
    assert "assistant/message" in kinds, "session.prompt 必须真调 LLM（否则假绿）"
    assert "turn/end" in kinds


def test_session_prompt_records_l1l2_assembly_metadata():
    """会话日志须含 context/assemble 事件：L1–L2 装配缺口结构化暴露（provided 为空 → missing 非空）。"""
    sid = session_create({"sessionId": "sp-2"})["sessionId"]
    session_prompt({"sessionId": sid, "content": [{"type": "text", "text": "装配"}]})
    events = [e["event"] for e in session_history({"sessionId": sid})["events"]]
    asm = [e for e in events if e.get("type") == "context/assemble"]
    assert asm, "会话缺 context/assemble 装配元数据（假绿）"
    missing = asm[0].get("missing", [])
    # provided 为空 → L1/L2 均未供给 → missing 含两层（结构化，非吞）
    assert ("L1", "") in missing and ("L2", "") in missing, f"expected L1/L2 missing, got {missing}"


def test_session_prompt_assembly_metadata_requires_pre_step(monkeypatch):
    """变异自证：移除 pre_step 装配钩子 → 主判别项 context/assemble 须消失（证明判别项非真空绿）。"""
    from chiyu_host import methods
    def _no_ctx_inject(_sid):
        return lambda messages: messages  # 装配钩子被删：不写 context/assemble
    monkeypatch.setattr(methods, "_ctx_inject", _no_ctx_inject)
    sid = session_create({"sessionId": "sp-mut-1"})["sessionId"]
    session_prompt({"sessionId": sid, "content": [{"type": "text", "text": "x"}]})
    kinds = _kinds(sid)
    assert "context/assemble" not in kinds, "主判别项依赖装配钩子，移除后须转红（防假绿）"
```

- [ ] **Step 2: 运行测试确认失败（实现尚未写）**

Run: `cd /d/system/chiyu-foundation && python -m pytest packages/chiyu-host/tests/test_rpc_session_prompt_context.py -v`
Expected: FAIL（`ImportError` 或 `session_prompt` 不写 `context/assemble` → `test_session_prompt_records_l1l2_assembly_metadata` 断言 `asm` 为空）

---

## Task 2: 实现 session.prompt（复用 AgentLoop + L1–L2 装配）

**Files:**
- Modify: `packages/chiyu-host/src/chiyu_host/methods.py`

- [ ] **Step 1: 顶部新增 import（紧贴现有 orchestration 导入之后）**

在 `from chiyu_kernel.orchestration.subagent import SubagentDescriptor, SubagentPool` 之后新增：

```python
from chiyu_kernel.orchestration.agent_loop import AgentLoop
from chiyu_kernel.orchestration.agent_runtime import Agent
from chiyu_kernel.context import assemble, KnowledgeNeed, KNOWLEDGE_NEEDS_DEFAULT_DIMS
```

- [ ] **Step 2: 模块级新增 session 装配需求（紧贴 `_goal_index` 声明之后）**

```python
# session.prompt 装配策略（bridge 层默认中性；foundation-builder 契约授权 L1–L2）
# ⛔ 不声明 L3/L4 need——契约 scope 收敛授权层，避免越界（校验器会拦 L3/L4）。
_SESSION_CTX_NEEDS = (
    KnowledgeNeed(layer="L1", dims=KNOWLEDGE_NEEDS_DEFAULT_DIMS),
    KnowledgeNeed(layer="L2", dims=KNOWLEDGE_NEEDS_DEFAULT_DIMS),
)
```

- [ ] **Step 3: 新增 `_ctx_inject` 与 `_ensure_session_agent`（紧贴 `session_prompt` 之前）**

```python
def _ctx_inject(sid: str):
    """装配钩子（pre_step）：把 L1–L2 装配结果作为上下文消息注入模型上下文首部；
    并把结构化缺口（missing/degraded_layers）写入会话日志 `context/assemble` 事件（供追踪/测试判别）。

    provided 默认空（无领域供给）→ missing 结构化暴露，不抛错（fail-safe）。
    消费方接真实 TenantProfile/检索后注入 provided 即补齐（机制已接通）。
    """

    def _pre(messages):
        result = assemble(_SESSION_CTX_NEEDS, {})
        log = _session_index.get(sid)
        if log is not None:
            log.append("context/assemble", {
                "facts": result.facts,
                "missing": list(result.supply_report.missing),
                "degraded_layers": list(result.supply_report.degraded_layers),
            })
        ctx_msg = {
            "role": "system",
            "content": (
                "[运行时上下文装配 L1–L2]\n"
                f"缺口(missing)：{list(result.supply_report.missing)}\n"
                f"降级层(degraded)：{list(result.supply_report.degraded_layers)}\n"
                "（机制已接通；消费方注入 TenantProfile/检索后补齐 provided）"
            ),
        }
        return [ctx_msg] + list(messages)

    return _pre


def _ensure_session_agent(sid: str) -> None:
    """按 sid 惰性注册 session 主 agent（含 L1–L2 装配 pre_step）到子 agent 同一条 live 注册表。

    复用 AgentLoop 同链；key=sid 与 sub:* 前缀不冲突；已注册则跳过（判重 live.get(sid)）。
    """
    if _subagent_pool._live.get(sid) is None:
        _subagent_pool._live.register(Agent(key=sid, tools_scope="", pre_step=_ctx_inject(sid)))
```

- [ ] **Step 4: 改写 `session_prompt`（替换原 L186–197 整段）**

```python
def session_prompt(payload: Dict[str, Any]) -> Dict[str, Any]:
    sid = payload["sessionId"]
    _session_or_raise(sid)            # 要求会话已存在（DSH 契约语义）
    content = payload.get("content") or []
    text = "".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    # 惰性注册 session 主 agent（含 L1–L2 装配 pre_step）
    _ensure_session_agent(sid)
    # 复用 AgentLoop 同链：run_turn 内部 append user/message → pre_step 注入装配 →
    # 真调 LLM(stream_chat) → assistant/message → turn/end（共享 redline_guard）
    loop = AgentLoop(
        llm=StubProvider(),
        tools=_tools,
        sessions=_session_manager,
        live_agents=_subagent_pool._live,
        redline_guard=_native_redline_guard(profile=None),
    )
    loop.run_turn(sid, text)
    # 发布最新 assistant 事件到总线（DSH session/event 实时扇出）
    log = _session_index.get(sid)
    if log is not None:
        assistant_ev = next((e for e in reversed(log.events())
                             if e.kind == "assistant/message"), None)
        if assistant_ev is not None:
            _bus.publish(
                {"id": str(uuid.uuid4()), "event_type": "session/event",
                 "sessionId": sid, "event": to_wire_session_event(assistant_ev)},
                persist=_noop_persist,
            )
    return {"accepted": True}
```

> ⚠️ 修正：原设计 §2.2 伪代码在 `session_prompt` 与 `run_turn` 两处都 append `user/message`，会重复。
> 本实现以 `run_turn` 内部 append 为准，`session_prompt` 不再自行 append（外部行为不变）。

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /d/system/chiyu-foundation && python -m pytest packages/chiyu-host/tests/test_rpc_session_prompt_context.py -v`
Expected: PASS（3 条全绿，含变异自证）

---

## Task 3: 全量回归 + 提交

**Files:**
- Modify: `packages/chiyu-host/src/chiyu_host/methods.py`
- Create: `packages/chiyu-host/tests/test_rpc_session_prompt_context.py`

- [ ] **Step 1: 全量回归（chiyu-host 包，零回归）**

Run: `cd /d/system/chiyu-foundation && python -m pytest packages/chiyu-host/tests -q`
Expected: PASS（原 36 + 新增 3 = **39 passed**，零回归）

- [ ] **Step 2: R3 矩阵回填 §6 标注 session.prompt 已真对接**

在 `docs/plans/2026-09-25-dsh-client-r3-coupling.md` 的 §6（或 §8 闭环回写表）追加一行：
`| session.prompt L1–L2 装配 | success | 会话真现 assistant + missing 结构化 | session 真现 assistant + missing 结构化 | 2026-09-26 | — |`

- [ ] **Step 3: 提交（分层、单行 -m、尾部附实测计数）**

```bash
cd /d/system/chiyu-foundation
git add packages/chiyu-host/src/chiyu_host/methods.py packages/chiyu-host/tests/test_rpc_session_prompt_context.py
git commit -m "T4: chiyu-host session.prompt 接入 L1-L2 上下文装配（复用 AgentLoop 同步委派·context/assemble 缺口结构化·39 passed）"
```

（R3 矩阵回填若随本次提交，单独再 `git add docs/plans/2026-09-25-dsh-client-r3-coupling.md` + `git commit -m "docs: R3 矩阵 §6 回填 session.prompt L1-L2 装配已真对接"`）

---

## 自审（spec → plan 覆盖核对）

1. **Spec 覆盖**：① 复用 AgentLoop 真调 LLM → Task 2 Step 4 + Task 1 `test_session_prompt_returns_accepted_and_runs_llm_turn`；② L1–L2 装配注入模型上下文 → `_ctx_inject` + Task 1 `test_session_prompt_records_l1l2_assembly_metadata`（missing 含 L1/L2）；③ 共享 redline_guard → `AgentLoop(redline_guard=_native_redline_guard(...))`；④ fail-safe 不抛错 → `assemble(..., {})` 恒成立、`context/assemble` 事件落档；⑤ 返回 `{accepted:true}` 不变 → Step 4；⑥ 契约 scope 收敛 L1–L2（不越界）→ `_SESSION_CTX_NEEDS` 仅 L1/L2；⑦ 变异自证 → `test_session_prompt_assembly_metadata_requires_pre_step`。
2. **占位扫描**：无 TBD/TODO；每步含完整代码与命令。
3. **类型一致性**：`KnowledgeNeed(layer, dims)`、`assemble(needs, provided)`、`Agent(key, tools_scope, pre_step)`、`AgentLoop(llm, tools, sessions, live_agents, redline_guard)`、`run_turn(agent_key, user_input)` 签名与内核源码一致；`context/assemble` 事件键与测试断言一致。
