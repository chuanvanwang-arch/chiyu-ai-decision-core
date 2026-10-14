"""mux WebSocket 契约测试：session.prompt 经事件总线下发 session/event 帧。

帧形态（实测 DSH）= ServerRequest 全形 {type, rpcId, method:'events.mux', payload: MuxFrame}，
MuxFrame 为 {type:'session/event', sessionId, event}（对齐 events.schema muxFrameSchema）。
"""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from chiyu_host.app import app


def test_mux_receives_session_event_frame():
    client = TestClient(app)
    with client.websocket_connect("/api/events.mux") as ws:
        create = client.post("/api/session.create",
                             json={"type": "client-request", "rpcId": "r1",
                                   "method": "session.create", "payload": {}})
        sid = create.json()["result"]["value"]["sessionId"]
        client.post("/api/session.prompt",
                    json={"type": "client-request", "rpcId": "r2",
                          "method": "session.prompt",
                          "payload": {"sessionId": sid, "mode": "queue",
                                      "content": [{"type": "text", "text": "hello"}]}})
        frame = ws.receive_text()
        msg = json.loads(frame)
        assert msg["type"] == "server-request"
        assert msg["method"] == "events.mux"
        assert "rpcId" in msg
        payload = msg["payload"]
        assert payload["type"] == "session/event"
        assert payload["sessionId"] == sid
        assert payload["event"]["type"] == "user/message"
        assert payload["event"]["data"]["content"] == "hello"
