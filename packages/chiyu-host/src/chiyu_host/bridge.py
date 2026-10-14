"""DSH 线格式映射 + 进程内事件总线 → MuxFrame 桥接。

字段名严格对齐 DSH `packages/host/apiproxy/src/api/*.schema.ts`（防假绿）：
- SessionEvent 信封：{type, seq, time, data}
  （DSH `sessions.schema.ts` sessionEventSchema；chiyu_kernel SessionEvent 是 kind/payload/ts/seq）
- MuxFrame（session/event 支）：{type:'session/event', sessionId, event}
  （DSH `events.schema.ts` muxFrameSchema 联合首支）
- ServerRequest 全形：{type:'server-request', rpcId, method, payload}
  （DSH `rpc.ts` ServerRequest；WebSocket 下行帧形态）
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Dict, List, Optional

from chiyu_kernel.session import SessionEvent


def to_wire_session_event(ev: SessionEvent) -> Dict[str, Any]:
    """chiyu_kernel SessionEvent(kind/payload/ts/seq) → DSH 线格式(type/seq/time/data)。"""
    return {"type": ev.kind, "seq": ev.seq, "time": ev.ts, "data": dict(ev.payload)}


def build_mux_frame(session_id: str, wire_event: Dict[str, Any]) -> Dict[str, Any]:
    """构造 session/event 的 MuxFrame（对齐 events.schema muxFrameSchema 联合首支）。"""
    return {"type": "session/event", "sessionId": session_id, "event": wire_event}


def wrap_server_request(payload: Dict[str, Any], method: str = "events.mux") -> Dict[str, Any]:
    """对齐 rpc.ts ServerRequest 全形：{type, rpcId, method, payload}。"""
    return {"type": "server-request", "rpcId": str(uuid.uuid4()), "method": method, "payload": payload}


def mux_frame_to_wire(session_id: str, wire_event: Dict[str, Any]) -> Dict[str, Any]:
    """MuxFrame → ServerRequest 全形（供 WebSocket 下行）。"""
    return wrap_server_request(build_mux_frame(session_id, wire_event))


# 多帧型广播（M2-T3）：MuxBroadcaster 可订阅并转发的帧 event_type 集。
# 首支 session/event = 会话事件（M0 兼容）；session/jobs = 任务列表；
# session/projection = 状态投影（goal 等）。每个帧型的事件 envelope 均为
# {id, event_type, sessionId, ...}，MuxBroadcaster 把其 payload 包装为
# ServerRequest 全形下发（MuxFrame 契约）。
MUX_FRAME_TYPES = ("session/event", "session/jobs", "session/projection")


class MuxBroadcaster:
    """持有活跃 WS 连接，将总线多帧型事件转为 ServerRequest 全形广播。

    订阅 MUX_FRAME_TYPES 各 event_type，收到后按帧型合成 wire：
    - session/event：{type:'session/event', sessionId, event}（M0 兼容）
    - session/jobs：{type:'session/jobs', sessionId, jobs}（DSH events.ts:98）
    - session/projection：{type:'session/projection', sessionId, key, value, seq}
    """

    def __init__(self) -> None:
        self._connections: List[Callable[[str], None]] = []
        self._types: List[str] = []
        self._subscribed = False

    def attach(self, bus: Any) -> None:
        if self._subscribed:
            return
        for etype in MUX_FRAME_TYPES:
            bus.subscribe(etype, f"chiyu-host-mux:{etype}", self._on_frame)
        self._types = list(MUX_FRAME_TYPES)
        self._subscribed = True

    def _on_frame(self, event: Dict[str, Any]) -> None:
        session_id = event.get("sessionId")
        if session_id is None:
            return
        etype = event.get("event_type")
        if etype == "session/event":
            wire = event.get("event")
            if wire is None:
                return
            frame = mux_frame_to_wire(session_id, wire)  # 已含 ServerRequest 外层
            text = json.dumps(frame, ensure_ascii=False)
        elif etype == "session/jobs":
            mux = {"type": "session/jobs", "sessionId": session_id,
                   "jobs": event.get("jobs") or []}
            text = json.dumps(wrap_server_request(mux), ensure_ascii=False)
        elif etype == "session/projection":
            mux = {"type": "session/projection", "sessionId": session_id,
                   "key": event.get("key"), "value": event.get("value"),
                   "seq": event.get("seq")}
            text = json.dumps(wrap_server_request(mux), ensure_ascii=False)
        else:
            return
        for send in list(self._connections):
            try:
                send(text)
            except Exception:  # noqa: BLE001 — 移除失效连接，不中断广播
                if send in self._connections:
                    self._connections.remove(send)

    def add_connection(self, send: Callable[[str], None]) -> None:
        self._connections.append(send)

    def remove_connection(self, send: Callable[[str], None]) -> None:
        if send in self._connections:
            self._connections.remove(send)
