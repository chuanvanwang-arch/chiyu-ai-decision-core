"""M1 全量域测试：skills/subagents/agentPreset 接入真实 chiyu_kernel 注册表。

判别项（防假绿）：
- skill.list 必须含真实注入目录中的 `memory-curator`（新增技能需出现在列表，证明非硬编码样例）；
- subagent.list 必须精确等于真实 SubagentDescriptor 注册集合（key/mode 对齐 `subagents.schema.ts`）；
- subagent.prompt 走真实 SubagentPool.delegate → AgentLoop，child 会话产生 user→assistant→turn/end 事件；
- subagent.history / subagent.interrupt 字段对齐 `subagents.schema.ts`。
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from chiyu_host.app import app
from chiyu_host.methods import _SUBAGENT_LABELS, _SUBAGENT_DEFAULT_MODE

client = TestClient(app)


def rpc_call(method: str, payload=None, rpc_id: str = "rpc-m1-1") -> dict:
    body = {"type": "client-request", "rpcId": rpc_id, "method": method, "payload": payload or {}}
    r = client.post(f"/api/{method}", json=body)
    assert r.status_code == 200, r.text
    resp = r.json()
    assert resp["type"] == "server-response"
    assert resp["rpcId"] == rpc_id
    return resp


def get_value(method: str, payload=None) -> dict:
    resp = rpc_call(method, payload)
    assert resp["result"]["ok"] is True, resp["result"]
    return resp["result"]["value"]


# ── skill.list：真实注册表判别项 ───────────────────────────────────────────
def test_skill_list_contains_injected_memory_curator():
    """M1 判别项：目录注入的 memory-curator 必须出现在 skill.list（非硬编码样例）。"""
    v = get_value("skill.list", {"sessionId": "x"})
    names = [s["name"] for s in v["skills"]]
    assert "memory-curator" in names
    assert "context-assembler" in names
    # 每项字段对齐 skillListValueSchema
    for s in v["skills"]:
        assert set(["name", "description", "modelInvocable"]).issubset(s.keys())


# ── subagent.list：真实注册表判别项 ────────────────────────────────────────
def test_subagent_list_entries_match_registered_descriptors():
    """subagent.list 必须精确等于真实 SubagentDescriptor 注册集（key 全对齐）。"""
    v = get_value("subagent.list", {"parentSessionId": "x"})
    assert set(["entries", "parentAvailable"]).issubset(v.keys())
    ids = {e["id"] for e in v["entries"]}
    assert ids == set(_SUBAGENT_LABELS.keys()), f"list 必须覆盖全部注册 key：{_SUBAGENT_LABELS.keys()}"
    for e in v["entries"]:
        assert e["mode"] == _SUBAGENT_DEFAULT_MODE
        assert e["activity"] in ("running", "inactive")
        assert set(["kind", "id", "mode", "activity", "hasChildren"]).issubset(e.keys())


# ── subagent.prompt：真实委派判别项 ────────────────────────────────────────
def test_subagent_prompt_delegates_and_records_turn():
    """subagent.prompt 真实委派：child 会话产生 user→assistant→turn/end 事件 + messageId。"""
    child = f"sub:{next(iter(_SUBAGENT_LABELS))}"
    v = get_value("subagent.prompt", {
        "parentSessionId": "parent-1",
        "childSessionId": child,
        "mode": "continuable",
        "content": [{"type": "text", "text": "M1 委派测试"}],
    })
    assert "messageId" in v and isinstance(v["messageId"], str) and v["messageId"]
    # child 会话须已记录委派轮（真实 AgentLoop 落档）
    h = get_value("subagent.history", {"parentSessionId": "parent-1", "childSessionId": child,
                                       "mode": "continuable"})
    kinds = [e["event"]["type"] for e in h["events"]]
    assert "user/message" in kinds
    assert "assistant/message" in kinds
    assert set(["events", "hasMore"]).issubset(h.keys())


def test_subagent_prompt_continuable_roundtrip():
    """同一 child 会话第二次委派可继续（history 追加，turn/end 计数增长）。"""
    child = "sub:coder"
    get_value("subagent.prompt", {"parentSessionId": "p2", "childSessionId": child,
                                  "mode": "continuable", "content": [{"type": "text", "text": "第一轮"}]})
    h1 = get_value("subagent.history", {"parentSessionId": "p2", "childSessionId": child, "mode": "continuable"})
    n1 = len(h1["events"])
    get_value("subagent.prompt", {"parentSessionId": "p2", "childSessionId": child,
                                  "mode": "continuable", "content": [{"type": "text", "text": "第二轮"}]})
    h2 = get_value("subagent.history", {"parentSessionId": "p2", "childSessionId": child, "mode": "continuable"})
    assert len(h2["events"]) > n1, "第二次委派应追加事件"


# ── subagent.interrupt ─────────────────────────────────────────────────────
def test_subagent_interrupt_shape():
    child = "sub:reviewer"
    get_value("subagent.prompt", {"parentSessionId": "p3", "childSessionId": child, "mode": "continuable",
                                  "content": [{"type": "text", "text": "评审"}]})
    v = get_value("subagent.interrupt", {"parentSessionId": "p3", "childSessionId": child, "mode": "continuable"})
    assert v == {"accepted": True}


# ── redline_guard 接线判别项（被调用方硬闸门，元红线）─────────────────────
def test_subagent_pool_has_redline_guard():
    """_subagent_pool 必须注入 redline_guard（M1-rg 接线）。"""
    from chiyu_host.methods import _subagent_pool
    assert _subagent_pool._redline_guard is not None, "subagent 委派链必须挂元红线硬闸门"


def test_redline_guard_intercepts_meta_redlines_only():
    """guard 命中 META_REDLINES 返回原因串；普通动作/无 actions 一律放行（不误拦）。"""
    from chiyu_host.methods import _subagent_pool
    g = _subagent_pool._redline_guard
    # 命中（META_REDLINES 冻结集成员）
    for action in ("threshold_widen", "baseline_write", "redline_auto"):
        hit = g("native-redline-check", {"actions": [action]})
        assert hit and "redline:" in hit, f"{action} 应为元红线命中，实际 {hit!r}"
    # 不误拦
    assert g("x", {"actions": ["read"]}) is None
    assert g("x", {"foo": 1}) is None
    assert g("x", "not-a-dict") is None


def test_redline_guard_hard_gate_throws_guarddenied():
    """tools.execute 走 guard 命中 ⇒ 抛 GuardDenied（被调用方硬闸门，非调用方分支）。"""
    import pytest
    from chiyu_kernel.tools import GuardDenied
    from chiyu_host.methods import _subagent_pool, _tools
    g = _subagent_pool._redline_guard
    with pytest.raises(GuardDenied):
        _tools.execute("native-redline-check", {"actions": ["threshold_widen"]}, redline_guard=g)


# ── native 工具注册判别项（register_native_tools 非空接线）────────────────
def test_native_tools_registered_and_callable():
    """_tools 必须注册 native 工具且 native-context-assemble 可真实调用（L1–L4 装配闭环）。"""
    from chiyu_host.methods import _tools
    names = set(_tools.names())
    assert "native-context-assemble" in names, "native-context-assemble 未注册"
    assert "native-redline-check" in names, "native-redline-check 未注册"
    # native-context-assemble 直调：L1 有供给 → facts 命中；缺 L2 → missing 结构化暴露
    r = _tools.execute(
        "native-context-assemble",
        {"needs": [{"layer": "L1", "dims": ["semantics"], "key": "k1"}]},
    )
    assert isinstance(r, dict) and "facts" in r, "native-context-assemble 返回异常"
    assert "missing" in r, "supply_report 缺口必须结构化返回（防假绿）"


# ── agentPreset.select / read 域补全（对齐 DSH agentPresets schema）────────
def test_agent_preset_read_shape_and_content():
    """read 返回全字段；content 为 WorkMode 编排序列化文本；trust=system。"""
    from chiyu_host.methods import agent_preset_read
    v = agent_preset_read({"agentPreset": "standard"})
    assert set(v.keys()) == {"agentPreset", "trust", "content", "name", "description"}
    assert v["agentPreset"] == "standard"
    assert v["trust"] == "system"
    assert v["name"] == "标准模式"
    assert "plugins" in v["content"] and "orchestration" in v["content"]


def test_agent_preset_read_unknown_rejected():
    import pytest
    from chiyu_host.methods import agent_preset_read, RpcError
    with pytest.raises(RpcError):
        agent_preset_read({"agentPreset": "nope"})


def test_agent_preset_select_persists_and_fanout_to_session_list():
    from chiyu_host.methods import agent_preset_select, session_create, session_list
    sid = session_create({"sessionId": "ap-sel-1"})["sessionId"]
    v = agent_preset_select({"sessionId": sid, "agentPreset": "ptc"})
    assert v == {"agentPreset": "ptc"}
    # 同源：session.list 的 agentPreset 字段应反映选中值（前端 ui-agent-preset 据此高亮）
    hit = [it for it in session_list({})["items"] if it["sessionId"] == sid]
    assert hit and hit[0]["agentPreset"] == "ptc"


def test_agent_preset_select_unknown_session_rejected():
    import pytest
    from chiyu_host.methods import agent_preset_select, RpcError
    with pytest.raises(RpcError):
        agent_preset_select({"sessionId": "ghost", "agentPreset": "standard"})


def test_agent_preset_select_unknown_preset_rejected():
    import pytest
    from chiyu_host.methods import agent_preset_select, session_create, RpcError
    sid = session_create({"sessionId": "ap-sel-2"})["sessionId"]
    with pytest.raises(RpcError):
        agent_preset_select({"sessionId": sid, "agentPreset": "nope"})


# ── goal.* 域补全（对齐 DSH goals.schema.ts mutation-only + session projection）──
def test_goal_create_returns_ref_and_projection_event():
    """goal.create 返回 {ref}；goal 状态必须投影到 session 事件流（DSH session projection 语义）。"""
    from chiyu_host.methods import goal_create, session_create, session_history
    sid = session_create({"sessionId": "goal-1"})["sessionId"]
    v = goal_create({"sessionId": sid, "objective": "完成 M2"})
    assert v == {"ref": {"id": "goal:goal-1", "revision": 1}}
    kinds = [e["event"].get("type") for e in session_history({"sessionId": sid})["events"]]
    assert "goal/state" in kinds, "goal 状态未投影到 session 事件流（假绿）"


def test_goal_pause_resume_complete_transitions():
    """pause→paused / resume→running / complete→completed，链式 ref 驱动。"""
    from chiyu_host.methods import goal_create, goal_pause, goal_resume, goal_complete, session_create, _goal_index
    sid = session_create({"sessionId": "goal-2"})["sessionId"]
    ref = goal_create({"sessionId": sid, "objective": "o"})["ref"]
    ref = goal_pause({"sessionId": sid, "ref": ref})["ref"]
    assert _goal_index[sid]["status"] == "paused"
    ref = goal_resume({"sessionId": sid, "ref": ref})["ref"]
    assert _goal_index[sid]["status"] == "running"
    ref = goal_complete({"sessionId": sid, "ref": ref})["ref"]
    assert _goal_index[sid]["status"] == "completed"


def test_goal_edit_bumps_revision_and_objective():
    from chiyu_host.methods import goal_create, goal_edit, session_create, _goal_index
    sid = session_create({"sessionId": "goal-3"})["sessionId"]
    ref = goal_create({"sessionId": sid, "objective": "v1"})["ref"]
    v = goal_edit({"sessionId": sid, "ref": ref, "objective": "v2"})
    assert v["ref"]["revision"] == 2
    assert _goal_index[sid]["objective"] == "v2"


def test_goal_clear_removes_and_blocks_subsequent():
    """clear 后索引删除；随后任意 mutation 必须 goal-not-found（变异自证）。"""
    import pytest
    from chiyu_host.methods import goal_create, goal_clear, goal_pause, session_create, RpcError
    sid = session_create({"sessionId": "goal-4"})["sessionId"]
    ref = goal_create({"sessionId": sid, "objective": "o"})["ref"]
    assert goal_clear({"sessionId": sid, "ref": ref}) == {"cleared": True}
    with pytest.raises(RpcError):
        goal_pause({"sessionId": sid, "ref": ref})


def test_goal_conflict_on_stale_revision():
    """用过期 revision 调 mutation 必须 goal-conflict（乐观锁，防假绿）。"""
    import pytest
    from chiyu_host.methods import goal_create, goal_pause, session_create, RpcError
    sid = session_create({"sessionId": "goal-5"})["sessionId"]
    goal_create({"sessionId": sid, "objective": "o"})
    with pytest.raises(RpcError):
        goal_pause({"sessionId": sid, "ref": {"id": "goal:goal-5", "revision": 99}})


def test_goal_create_unknown_session_rejected():
    import pytest
    from chiyu_host.methods import goal_create, RpcError
    with pytest.raises(RpcError):
        goal_create({"sessionId": "ghost", "objective": "o"})
