"""RPC 方法响应形状对照 DSH apiproxy/*.schema.ts 的契约测试（防假绿）。

逐字段断言：每个返回 value 的顶层键、关键嵌套键必须与 schema 严格一致。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chiyu_host.app import app

client = TestClient(app)


def rpc_call(method: str, payload=None, rpc_id: str = "rpc-test-1") -> dict:
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


def test_session_list_shape():
    v = get_value("session.list")
    assert "items" in v and isinstance(v["items"], list)


def test_session_summary_fields():
    # 先确保至少一个会话存在，避免空 items 使字段断言假绿
    get_value("session.create")
    v = get_value("session.list")
    assert v["items"], "session.list 必须至少返回一个会话"
    for it in v["items"]:
        assert set(["sessionId", "updatedAt", "running", "blank"]).issubset(it.keys())


def test_session_create_and_history_event_envelope():
    create = rpc_call("session.create", {})
    sid = create["result"]["value"]["sessionId"]
    rpc_call("session.prompt", {"sessionId": sid, "mode": "queue",
                                "content": [{"type": "text", "text": "hi"}]})
    h = get_value("session.history", {"sessionId": sid})
    assert "events" in h and h["events"]
    # SessionEvent 线格式信封：type/seq/time/data（对齐 sessions.schema sessionEventSchema）
    env = h["events"][0]["event"]
    assert env["type"] == "user/message"
    assert set(["type", "seq", "time", "data"]).issubset(env.keys())


def test_session_models_and_select_roundtrip():
    sid = get_value("session.create")["sessionId"]
    m = get_value("session.models", {"sessionId": sid})
    assert set(["current", "routable", "groups", "failures"]).issubset(m.keys())
    sel = get_value("session.selectModel",
                    {"sessionId": sid, "provider": "deepseek", "model": "deepseek-v4-flash"})
    assert sel["selected"]["model"] == "deepseek-v4-flash"
    m2 = get_value("session.models", {"sessionId": sid})
    assert m2["current"]["model"] == "deepseek-v4-flash"


def test_session_cancel_shape():
    sid = get_value("session.create")["sessionId"]
    v = get_value("session.cancel", {"sessionId": sid})
    assert v == {"accepted": True}


def test_llm_providers_models_fields():
    p = get_value("llm.providers")
    assert set(["providers"]).issubset(p.keys())
    prov = p["providers"][0]
    assert set(["provider", "displayName", "settingsNs", "settingsPath", "active"]).issubset(prov.keys())
    m = get_value("llm.models")
    assert set(["groups", "failures"]).issubset(m.keys())
    g = m["groups"][0]
    assert set(["id", "name", "models"]).issubset(g.keys())
    assert set(["id", "name"]).issubset(g["models"][0].keys())


def test_settings_describe_shape_and_ns_crossref():
    # 对齐 DSH settingsDescribeValueSchema：writable/hasDocument/namespaces 必备
    v = get_value("settings.describe")
    assert set(["writable", "hasDocument", "namespaces"]).issubset(v.keys())
    assert isinstance(v["namespaces"], list) and v["namespaces"]
    ns = v["namespaces"][0]
    # settingsNamespaceViewSchema：ns/schema/value/applies/secrets/revision 必备
    assert set(["ns", "schema", "value", "applies", "secrets", "revision"]).issubset(ns.keys())
    assert ns["applies"] in ("live", "restart")
    assert isinstance(ns["revision"], int)
    # 交叉一致性：llm.providers 的 settingsNs 必须能在 settings.describe namespaces 中找到
    # （DSH client 的 DeepSeekOnboardingDialog 硬编码查 'llm-deepseek'，连字符）
    prov = get_value("llm.providers")["providers"][0]
    ns_names = {n["ns"] for n in v["namespaces"]}
    assert prov["settingsNs"] in ns_names


def test_credentials_describe_roundtrip():
    # 对齐 DSH credentialsDescribeValueSchema：credentials 为 ref→view 记录
    v = get_value("credentials.describe", {"refs": ["DEEPSEEK_API_KEY", "MY_KEY_2"]})
    assert set(v["credentials"].keys()) == {"DEEPSEEK_API_KEY", "MY_KEY_2"}
    for view in v["credentials"].values():
        assert set(["configured", "writable"]).issubset(view.keys())
    # 空 refs → 空 records（不报错）
    v2 = get_value("credentials.describe", {"refs": []})
    assert v2["credentials"] == {}


def test_agent_preset_fields():
    v = get_value("agentPreset.list")
    assert set(["presets", "authorable", "hasDocument"]).issubset(v.keys())
    p = v["presets"][0]
    assert set(["id", "trust", "isDefault"]).issubset(p.keys())
    assert p["trust"] == "system"


def test_skill_list_fields():
    v = get_value("skill.list", {"sessionId": "x"})
    assert "skills" in v
    if v["skills"]:
        s = v["skills"][0]
        assert set(["name", "description", "modelInvocable"]).issubset(s.keys())


def test_subagent_list_fields():
    v = get_value("subagent.list", {"parentSessionId": "x"})
    assert set(["entries", "parentAvailable"]).issubset(v.keys())
    e = v["entries"][0]
    assert set(["kind", "id", "mode", "activity", "hasChildren"]).issubset(e.keys())


def test_host_describe_fields():
    v = get_value("host.describe")
    assert set(["version", "cwd", "provider", "model", "attachedSessions", "canOpenPath"]).issubset(v.keys())


def test_unknown_method_error_branch():
    resp = rpc_call("nope.unknown", {})
    assert resp["result"]["ok"] is False
    err = resp["result"]["error"]
    assert err["code"] == "bad-request"
    # DSH 官方 rpcErrorSchema 对 bad-request 分支强制 details.issues 数组
    # （discriminatedUnion；缺 issues 会使 client 端 union 解析失败、UI 露出原始 zod 报错串）
    assert isinstance(err["details"].get("issues"), list)


def test_rpc_error_bad_request_details_issues_injected():
    # RpcError(code="bad-request") 未带 issues 时，app 层必须自动补 issues:[]
    from chiyu_host import methods

    orig = methods.HANDLERS.get("session.list")

    def _boom(_payload):
        raise methods.RpcError("bad-request", "参数缺失")

    methods.HANDLERS["session.list"] = _boom
    try:
        resp = rpc_call("session.list", {})
    finally:
        methods.HANDLERS["session.list"] = orig
    err = resp["result"]["error"]
    assert err["code"] == "bad-request"
    assert isinstance(err["details"].get("issues"), list)


def test_boot_manifest_endpoint():
    r = client.get("/api/boot", params={"base_url": "http://localhost:8000"})
    assert r.status_code == 200
    m = r.json()
    assert m["apiPath"] == "/api"
    assert m["muxPath"] == "/api/events.mux"
    assert "ui-conversation" in m["modules"]
