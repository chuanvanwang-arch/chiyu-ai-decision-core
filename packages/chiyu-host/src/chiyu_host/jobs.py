"""JobRegistry：任务登记 + session/jobs 帧推送（M2-T1）。

DSH 契约（实测 `apiproxy/src/api/events.ts:98`）：**jobs 无独立 RPC 方法**，
`JobView{id,kind,label,status:running|stopping|completed|killed|failed,detail?,startedAt,finishedAt?}`
经 `session/jobs` 帧随事件流推送，前端 `ui-jobs` 面板据此渲染。

本实现把 chiyu-host 内的长任务（subagent 委派、workflow 运行等）登记为 JobView，
每次 add / set_status 推一条 `{type:'session/jobs', sessionId, jobs: JobView[]}` 帧。
字段名严格对齐 DSH schema（防假绿）。
"""
from __future__ import annotations

import time
import uuid
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

# JobView.status 合法枚举（对齐 events.ts JobViewStatus）
JOB_STATUS_ACTIVE = frozenset({"running", "stopping"})
JOB_STATUS_TERMINAL = frozenset({"completed", "killed", "failed"})
JOB_STATUSES = JOB_STATUS_ACTIVE | JOB_STATUS_TERMINAL

# kind 扩展点（对齐本平台能力域；消费方可扩展）
JOB_KINDS = frozenset({"bash", "pwsh", "subagent", "workflow"})


class JobRegistry:
    """进程内任务登记表（不连 pg，对齐 M0/M1 内存态策略）。

    - 每会话维护自己的 job 序列（id 前缀 `kind-N`）；跨会话隔离。
    - 每次 add / set_status 都触发_推帧回调（由构造方注入 publisher）。
    - 终态写入 finishedAt；stopping 为中间态（可转任意终态）。
    - 保留最近 _MAX_JOBS_PER_SESSION 条（防无限增长；前端通常只看活动+近期）。
    """

    def __init__(self, publisher: Optional[Callable[[str, List[Dict[str, Any]]], None]] = None) -> None:
        self._publisher: Optional[Callable[[str, List[Dict[str, Any]]], None]] = publisher
        self._jobs: Dict[str, Deque[Dict[str, Any]]] = {}
        self._counters: Dict[str, int] = {}
        self._MAX_JOBS_PER_SESSION = 200

    # ── 登记 / 状态 ──────────────────────────────────────────────────────
    def add(self, session_id: str, kind: str, label: str, detail: Optional[str] = None) -> Dict[str, Any]:
        if kind not in JOB_KINDS:
            raise ValueError(f"未知 job kind：{kind}；须 ∈ {sorted(JOB_KINDS)}")
        if not label:
            raise ValueError("job label 不能为空")
        seq = self._counters.get(session_id, 0) + 1
        self._counters[session_id] = seq
        job: Dict[str, Any] = {
            "id": f"{kind}-{seq}",
            "kind": kind,
            "label": label,
            "status": "running",
            "startedAt": time.time(),
        }
        if detail is not None:
            job["detail"] = detail
        self._jobs.setdefault(session_id, deque()).append(job)
        self._trim(session_id)
        self._publish(session_id)
        return job

    def set_status(self, session_id: str, job_id: str, status: str,
                   detail: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if status not in JOB_STATUSES:
            raise ValueError(f"未知 job status：{status}；须 ∈ {sorted(JOB_STATUSES)}")
        job = self.get(session_id, job_id)
        if job is None:
            return None
        job["status"] = status
        if detail is not None:
            job["detail"] = detail
        if status in JOB_STATUS_TERMINAL:
            job["finishedAt"] = time.time()
        self._publish(session_id)
        return job

    # ── 读取 ─────────────────────────────────────────────────────────────
    def get(self, session_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        for j in self._jobs.get(session_id, ()):
            if j["id"] == job_id:
                return j
        return None

    def list(self, session_id: str) -> List[Dict[str, Any]]:
        return [dict(j) for j in self._jobs.get(session_id, ())]

    def active(self, session_id: str, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        return [j for j in self._jobs.get(session_id, ())
                if j["status"] in JOB_STATUS_ACTIVE and (kind is None or j["kind"] == kind)]

    # ── 内部 ─────────────────────────────────────────────────────────────
    def _trim(self, session_id: str) -> None:
        q = self._jobs.get(session_id)
        while q and len(q) > self._MAX_JOBS_PER_SESSION:
            q.popleft()

    def _publish(self, session_id: str) -> None:
        if self._publisher is not None:
            self._publisher(session_id, self.list(session_id))


def make_publisher(bus: Any, noop_persist: Callable[[Dict[str, Any]], None]) -> Callable[[str, List[Dict[str, Any]]], None]:
    """构造 JobRegistry 的推送回调：把 jobs 列表包成 session/jobs 帧发到总线。

    bus.publish 的事件 envelope 沿用 chiyu-host 现有 `session/event` 通道，
    但 event 对象带 `_frame_type` 标记，供 MuxBroadcaster 识别为 session/jobs 帧
    （见 bridge.MuxBroadcaster 的多帧型扩展示例）。实际实现见 events.py 的
    `publish_mux_frame`：它直接发独立 event_type，MuxBroadcaster 订阅之。
    """

    def publisher(session_id: str, jobs: List[Dict[str, Any]]) -> None:
        bus.publish(
            {"id": str(uuid.uuid4()), "event_type": "session/jobs",
             "sessionId": session_id, "jobs": jobs},
            persist=noop_persist,
        )

    return publisher
