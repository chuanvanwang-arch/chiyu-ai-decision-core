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
