"""M2 全量域测试：JobRegistry + session/jobs 帧 + session/projection 帧 + workflow→jobs。

判别项（防假绿）：
- JobRegistry.add → running；set_status(completed) → finishedAt 出现；终态/中间态枚举合法
- session/jobs 帧：总线订阅者可收到 {event_type:'session/jobs', sessionId, jobs[]}
- session/projection 帧：goal 每次状态变更投 key='goal'、seq=revision 的投影帧（DSH events.ts:107）
- subagent 委派接线为 job：parent 会话出现 kind='subagent' 的 job，终态为 completed
- MuxBroadcaster 多帧型：同一连接可依次收到 jobs 帧与 projection 帧
"""
from __future__ import annotations

from chiyu_host.bridge import MuxBroadcaster, MUX_FRAME_TYPES
from chiyu_host.jobs import JobRegistry, JOB_KINDS, JOB_STATUSES
from chiyu_host.methods import (
    _job_registry, session_create, goal_create, goal_pause, subagent_prompt,
    _SUBAGENT_LABELS, _bus,
)

from chiyu_kernel.events import EventBus


# ── JobRegistry 直测 ──────────────────────────────────────────────────────
def test_job_registry_add_running_and_terminal():
    reg = JobRegistry()
    j = reg.add("s1", "bash", "安装依赖")
    assert j["status"] == "running"
    assert "startedAt" in j and "finishedAt" not in j
    assert j["id"] == "bash-1", "首个 job id 须 <kind>-1（判别项）"
    done = reg.set_status("s1", j["id"], "completed")
    assert done["status"] == "completed"
    assert "finishedAt" in done, "终态必须写 finishedAt（假绿防护）"


def test_job_registry_kind_and_status_validation():
    import pytest
    reg = JobRegistry()
    with pytest.raises(ValueError):
        reg.add("s1", "nope", "x")          # 非法 kind
    with pytest.raises(ValueError):
        reg.add("s1", "bash", "")           # 空 label
    j = reg.add("s1", "workflow", "wf")
    with pytest.raises(ValueError):
        reg.set_status("s1", j["id"], "running-wrong")  # 非法 status


def test_job_registry_scope_isolated_per_session():
    reg = JobRegistry()
    reg.add("sA", "subagent", "a")
    reg.add("sB", "bash", "b")
    assert len(reg.list("sA")) == 1
    assert len(reg.list("sB")) == 1
    assert reg.list("sA")[0]["kind"] == "subagent"
    assert reg.list("sB")[0]["kind"] == "bash"


def test_job_registry_active_filter():
    reg = JobRegistry()
    a = reg.add("s1", "bash", "a")
    b = reg.add("s1", "workflow", "b")
    reg.set_status("s1", a["id"], "completed")
    active = reg.active("s1")
    assert [j["id"] for j in active] == ["workflow-2"]
    active_flow = reg.active("s1", kind="workflow")
    assert [j["id"] for j in active_flow] == ["workflow-2"]
    assert reg.active("s1", kind="bash") == []


# ── session/jobs 帧：总线订阅者可收到 ─────────────────────────────────────
def test_session_jobs_frame_published_on_registry_change():
    """job add/set_status 必须把 jobs 列表投为 session/jobs 帧（DSH events.ts:98）。"""
    received = []
    _bus.subscribe("session/jobs", "test-collect", lambda ev: received.append(ev))
    try:
        reg = JobRegistry(publisher=lambda sid, jobs: _bus.publish(
            {"id": "job-frame-1", "event_type": "session/jobs", "sessionId": sid, "jobs": jobs},
            persist=lambda ev: None))
        reg.add("sx", "bash", "x")
        assert received, "session/jobs 帧未发出（假绿）"
        frame = received[-1]
        assert frame["event_type"] == "session/jobs"
        assert frame["sessionId"] == "sx"
        assert frame["jobs"][0]["id"] == "bash-1"
        assert frame["jobs"][0]["status"] == "running"
    finally:
        _bus._subs.pop("session/jobs", None)


# ── session/projection 帧：goal 状态变更投影 ──────────────────────────────
def test_goal_projects_session_projection_frame():
    """goal.create/pause 必须投 session/projection 帧（key='goal', seq=revision）。"""
    received = []
    _bus.subscribe("session/projection", "test-collect2", lambda ev: received.append(ev))
    try:
        sid = session_create({"sessionId": "m2-goal-proj"})["sessionId"]
        ref = goal_create({"sessionId": sid, "objective": "o"})["ref"]
        # create 后 revision=1 → seq=1
        proj = [f for f in received if f["key"] == "goal"]
        assert proj, "goal 未投 session/projection 帧（假绿）"
        assert proj[0]["seq"] == 1 and proj[0]["value"]["revision"] == 1
        assert proj[0]["value"]["status"] == "running"
        goal_pause({"sessionId": sid, "ref": ref})
        proj2 = [f for f in received if f["key"] == "goal"]
        assert proj2[-1]["seq"] == 2, "pause 后 revision 应 ++（2）"
        assert proj2[-1]["value"]["status"] == "paused"
    finally:
        _bus._subs.pop("session/projection", None)


# ── subagent 委派接线为 job ───────────────────────────────────────────────
def test_subagent_prompt_records_job_in_parent():
    """subagent.prompt 必须在 parent 会话登记 kind='subagent' job，终态 completed。"""
    child = f"sub:{next(iter(_SUBAGENT_LABELS))}"
    parent = "m2-je-1"
    session_create({"sessionId": parent})
    session_create({"sessionId": child})
    jobs_before = _job_registry.list(parent)
    subagent_prompt({"parentSessionId": parent, "childSessionId": child,
                     "content": [{"type": "text", "text": "M2 job 接线"}]})
    jobs_after = _job_registry.list(parent)
    assert len(jobs_after) == len(jobs_before) + 1, "委派须新增 job（假绿）"
    job = jobs_after[-1]
    assert job["kind"] == "subagent"
    assert job["status"] == "completed"
    assert "finishedAt" in job


# ── MuxBroadcaster 多帧型 ─────────────────────────────────────────────────
def test_mux_broadcaster_supports_multi_frame_types():
    """MUX_FRAME_TYPES 须含三帧型；attach 订阅全部（多帧型广播判别）。"""
    assert set(MUX_FRAME_TYPES) == {"session/event", "session/jobs", "session/projection"}
    bus = EventBus()
    mux = MuxBroadcaster()
    mux.attach(bus)
    # 三个帧型都有订阅者
    for etype in MUX_FRAME_TYPES:
        assert bus.subscribers(etype), f"{etype} 未订阅（多帧广播缺失）"
    # 连接收到 session/jobs 帧（ServerRequest 全形）
    import json as _json
    got = []
    mux.add_connection(got.append)
    bus.publish({"id": "f1", "event_type": "session/jobs", "sessionId": "s",
                 "jobs": [{"id": "bash-1", "status": "running"}]}, persist=lambda e: None)
    parsed = _json.loads(got[0])
    assert parsed.get("type") == "server-request", "下行须为 ServerRequest 全形"
    payload = parsed.get("payload", {})
    assert payload.get("type") == "session/jobs"
    assert payload.get("sessionId") == "s"
