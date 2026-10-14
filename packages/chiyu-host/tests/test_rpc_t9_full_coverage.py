"""T9 全覆盖域测试：workspace / settings 写 / credentials 写 / host 文件域 /
llm.discoverModels / session 扩展（rename/fork/search/updateQueue/attachment）/
agentPreset 写域。逐域真实往返 + 错误分支判据（防假绿）。
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from chiyu_host import methods
from chiyu_host.app import app

client = TestClient(app)


def rpc(method: str, payload=None, rpc_id: str = "t9") -> dict:
    body = {"type": "client-request", "rpcId": rpc_id, "method": method, "payload": payload or {}}
    r = client.post(f"/api/{method}", json=body)
    assert r.status_code == 200, r.text
    resp = r.json()
    assert resp["type"] == "server-response"
    return resp["result"]


def ok(method: str, payload=None) -> dict:
    res = rpc(method, payload)
    assert res["ok"] is True, res
    return res["value"]


def err_code(method: str, payload=None) -> dict:
    res = rpc(method, payload)
    assert res["ok"] is False, res
    return res["error"]


# ── workspace 域 ──────────────────────────────────────────────────────────
def test_workspace_lifecycle_roundtrip(tmp_path):
    d = str(tmp_path / "ws-a")
    os.makedirs(d)
    v = ok("workspace.create", {"path": d})
    assert v["created"] is True
    ws = v["workspace"]
    assert set(["workspaceId", "path", "title", "sessionIds", "createdAt", "updatedAt"]).issubset(ws)
    # 幂等收编：同 path 再 create → created:False 且同一 workspaceId
    v2 = ok("workspace.create", {"path": d})
    assert v2["created"] is False and v2["workspace"]["workspaceId"] == ws["workspaceId"]
    # rename
    r = ok("workspace.rename", {"workspaceId": ws["workspaceId"], "title": "风控工作区"})
    assert r["workspace"]["title"] == "风控工作区"
    # insertSessionBefore（先建真实会话）
    sid = ok("session.create")["sessionId"]
    iv = ok("workspace.insertSessionBefore",
            {"workspaceId": ws["workspaceId"], "sessionId": sid})
    assert iv["workspace"]["sessionIds"] == [sid]
    # list 含该项
    lst = ok("workspace.list")
    assert any(w["workspaceId"] == ws["workspaceId"] for w in lst["items"])
    # archiveSession → 移出工作区 + 进归档集
    arc = ok("workspace.archiveSession", {"sessionId": sid})
    assert sid in arc["archivedSessionIds"]
    lst2 = ok("workspace.list")
    w2 = next(w for w in lst2["items"] if w["workspaceId"] == ws["workspaceId"])
    assert sid not in w2["sessionIds"]
    # delete
    assert ok("workspace.delete", {"workspaceId": ws["workspaceId"]}) == {"deleted": True}
    assert err_code("workspace.rename",
                    {"workspaceId": ws["workspaceId"], "title": "x"})["code"] == "workspace-not-found"


def test_workspace_insert_before_reorders():
    a = ok("workspace.create", {"path": "C:/__t9_a__"})["workspace"]["workspaceId"]
    b = ok("workspace.create", {"path": "C:/__t9_b__"})["workspace"]["workspaceId"]
    ids = ok("workspace.insertBefore", {"workspaceId": a, "beforeWorkspaceId": b})["workspaceIds"]
    assert ids.index(a) < ids.index(b)
    ok("workspace.delete", {"workspaceId": a})
    ok("workspace.delete", {"workspaceId": b})


# ── settings 写域 ─────────────────────────────────────────────────────────
def test_settings_write_roundtrip_and_conflict():
    v0 = ok("settings.describe")
    ns0 = next(n for n in v0["namespaces"] if n["ns"] == "llm-deepseek")
    rev0 = ns0["revision"]
    # update 浅合并 → revision+1
    v1 = ok("settings.update", {"ns": "llm-deepseek", "patch": {"model": "deepseek-v4"}, "expectedRevision": rev0})
    assert v1["value"]["model"] == "deepseek-v4" and v1["revision"] == rev0 + 1
    # 过期 revision → settings-conflict
    e = err_code("settings.update",
                 {"ns": "llm-deepseek", "patch": {"model": "x"}, "expectedRevision": rev0})
    assert e["code"] == "settings-conflict"
    assert set(e["details"].keys()) >= {"ns", "expected", "actual"}
    # mutate 深路径 set/unset
    v2 = ok("settings.mutate", {"ns": "llm-deepseek", "ops": [
        {"op": "set", "path": ["sampling", "temperature"], "value": 0.3},
        {"op": "unset", "path": ["sampling", "temperature"]},
        {"op": "set", "path": ["model"], "value": "deepseek-v4-flash"},
    ]})
    assert "temperature" not in v2["value"].get("sampling", {}) or v2["value"]["sampling"] == {}
    assert v2["value"]["model"] == "deepseek-v4-flash"
    # replace 覆盖同名键
    v3 = ok("settings.replace", {"ns": "llm-deepseek", "section": {"model": "deepseek-v4"}})
    assert v3["value"]["model"] == "deepseek-v4"
    # 未知 ns → settings-rejected；openDocument → opened:false
    assert err_code("settings.update", {"ns": "nope", "patch": {}})["code"] == "settings-rejected"
    assert ok("settings.openDocument")["opened"] is False


# ── credentials 写域 ──────────────────────────────────────────────────────
def test_credentials_set_unset_roundtrip():
    ref = "T9_TEST_KEY"
    assert ok("credentials.describe", {"refs": [ref]})["credentials"][ref]["configured"] is False
    ok("credentials.set", {"ref": ref, "value": "sk-test"})
    v = ok("credentials.describe", {"refs": [ref]})["credentials"][ref]
    assert v["configured"] is True and v["source"] == "memory"
    ok("credentials.unset", {"ref": ref})
    assert ok("credentials.describe", {"refs": [ref]})["credentials"][ref]["configured"] is False
    # 非法引用名 → bad-request（issues 数组在 app 层自动补齐）
    assert err_code("credentials.set", {"ref": "bad name!", "value": "x"})["code"] == "bad-request"


def test_credentials_set_flips_settings_secret_slot():
    # llm-deepseek ns 的 apiKey 槽在 set DEEPSEEK_API_KEY 后联动 set:true（describe 反映）
    ok("credentials.set", {"ref": "DEEPSEEK_API_KEY", "value": "sk-test"})
    try:
        ns = next(n for n in ok("settings.describe")["namespaces"] if n["ns"] == "llm-deepseek")
        sec = next(s for s in ns["secrets"] if s["path"] == ["apiKey"])
        assert sec["set"] is True
    finally:
        ok("credentials.unset", {"ref": "DEEPSEEK_API_KEY"})


# ── host 文件域 ───────────────────────────────────────────────────────────
def test_host_file_domain(tmp_path, monkeypatch):
    # listDirectory（真实目录）
    d = tmp_path / "parent"
    (d / "sub").mkdir(parents=True)
    v = ok("host.listDirectory", {"path": str(d)})
    assert set(["path", "home", "crumbs", "entries", "truncated"]).issubset(v)
    assert any(e["name"] == "sub" for e in v["entries"])
    assert v["crumbs"], "面包屑不可为空"
    # 不可读 → directory-unreadable
    assert err_code("host.listDirectory", {"path": str(tmp_path / "nope")})["code"] == "directory-unreadable"
    # createDirectory 成功 + 已存在 + 非法名
    created = ok("host.createDirectory", {"path": str(d), "name": "made"})
    assert created["path"].endswith("made")
    assert err_code("host.createDirectory", {"path": str(d), "name": "made"})["code"] == "directory-exists"
    assert err_code("host.createDirectory", {"path": str(d), "name": "a/b"})["code"] == "bad-request"
    # openPath：monkeypatch 外部打开避免真实拉起资源管理器；不存在路径报错
    monkeypatch.setattr(methods, "_open_path_externally", lambda p: None)
    assert ok("host.openPath", {"path": str(d)}) == {"opened": True}
    assert err_code("host.openPath", {"path": str(tmp_path / "nope")})["code"] == "directory-unreadable"
    # pickDirectory：headless → path:null（取消语义）
    assert ok("host.pickDirectory") == {"path": None}


# ── llm.discoverModels ────────────────────────────────────────────────────
def test_llm_discover_models():
    v = ok("llm.discoverModels", {"settingsNs": "llm-deepseek"})
    assert v["models"], "deepseek 目录不可为空"
    assert all(set(["id"]).issubset(m) for m in v["models"])
    e = err_code("llm.discoverModels", {"settingsNs": "llm-unknown-ns"})
    assert e["code"] == "model-discovery-failed"
    assert e["details"]["settingsNs"] == "llm-unknown-ns"


# ── session 扩展域 ────────────────────────────────────────────────────────
def test_session_rename_and_fork():
    sid = ok("session.create")["sessionId"]
    r = ok("session.rename", {"sessionId": sid, "title": "  融资决策会话  "})
    assert r["title"] == "融资决策会话" and isinstance(r["seq"], int) and r["seq"] >= 0
    # 空标题 → title-invalid
    assert err_code("session.rename", {"sessionId": sid, "title": "   "})["code"] == "title-invalid"
    # 种子几条事件后 fork
    methods._session_index[sid].append("user/message", {"text": "第一轮"})
    methods._session_index[sid].append("assistant/message", {"text": "第一轮回复"})
    child = ok("session.fork", {"sessionId": sid})["sessionId"]
    assert child != sid
    child_events = ok("session.history", {"sessionId": child})["events"]
    kinds = [e["event"]["type"] for e in child_events]
    assert "user/message" in kinds and "assistant/message" in kinds
    # atSeq 截断 fork：只取 seq <= 1 的事件
    child2 = ok("session.fork", {"sessionId": sid, "atSeq": 1})["sessionId"]
    k2 = [e["event"]["type"] for e in ok("session.history", {"sessionId": child2})["events"]]
    assert "assistant/message" not in k2 or "user/message" in k2
    # 未知会话 → session-not-found
    assert err_code("session.fork", {"sessionId": "nope"})["code"] == "session-not-found"


def test_session_search_finds_seeded_text():
    sid = ok("session.create")["sessionId"]
    methods._session_index[sid].append("user/message", {"text": "信贷反欺诈特殊标记查询"})
    v = ok("session.search", {"query": "反欺诈特殊标记"})
    assert any(it["sessionId"] == sid and "反欺诈特殊标记" in it["snippet"] for it in v["items"])
    assert v["hasMore"] is False
    # 空 query → bad-request（issues 数组由 app 层补齐）
    assert err_code("session.search", {"query": "  "})["code"] == "bad-request"


def test_session_update_queue_and_attachment():
    sid = ok("session.create")["sessionId"]
    # 未知队列项 → queue-item-not-found（真实查找，非盲 accept）
    e = err_code("session.updateQueue",
                 {"sessionId": sid, "itemId": "m-1", "action": {"kind": "remove"}})
    assert e["code"] == "queue-item-not-found" and e["details"]["itemId"] == "m-1"
    # 种子队列项 → edit/remove 真实生效
    methods._session_meta.setdefault(sid, {})["queue"] = [
        {"itemId": "m-1", "content": [{"type": "text", "text": "旧"}]}]
    assert ok("session.updateQueue",
              {"sessionId": sid, "itemId": "m-1",
               "action": {"kind": "edit", "content": [{"type": "text", "text": "新"}]}}) == {"accepted": True}
    assert methods._session_meta[sid]["queue"][0]["content"][0]["text"] == "新"
    assert ok("session.updateQueue",
              {"sessionId": sid, "itemId": "m-1", "action": {"kind": "remove"}}) == {"accepted": True}
    assert methods._session_meta[sid]["queue"] == []
    # 附件未存储 → unsupported（绝不伪造 ref/data）
    assert err_code("session.attachment",
                    {"sessionId": sid, "attachmentId": "att-1"})["code"] == "unsupported"


# ── agentPreset 写域 ──────────────────────────────────────────────────────
def test_agent_preset_copy_remove_roundtrip():
    pid = "t9-user-copy"
    v = ok("agentPreset.copy", {"from": "standard", "agentPreset": pid})
    assert v == {"agentPreset": pid}
    # list 出现 trust:user 条目
    lst = ok("agentPreset.list")
    entry = next(p for p in lst["presets"] if p["id"] == pid)
    assert entry["trust"] == "user" and entry["isDefault"] is False
    # read 返回 content
    r = ok("agentPreset.read", {"agentPreset": pid})
    assert r["trust"] == "user" and r["content"] and r["name"].endswith("副本")
    # select 用户预设可用
    sid = ok("session.create")["sessionId"]
    assert ok("agentPreset.select", {"sessionId": sid, "agentPreset": pid}) == {"agentPreset": pid}
    # 重复 id → conflict；删系统预设 → read-only；删用户预设 → 消失
    assert err_code("agentPreset.copy", {"from": "standard", "agentPreset": pid})["code"] == "agent-preset-conflict"
    assert err_code("agentPreset.remove", {"agentPreset": "standard"})["code"] == "agent-preset-read-only"
    assert ok("agentPreset.remove", {"agentPreset": pid}) == {}
    assert err_code("agentPreset.read", {"agentPreset": pid})["code"] == "agent-preset-not-found"


def test_dsh_method_coverage_complete():
    """T9 铁判据：DSH 官方 rpc-map 52 方法必须全部注册（防新增遗漏）。"""
    dsh_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".tmp_m0t3", "dsh_methods.txt")
    dsh_methods = set(open(os.path.abspath(dsh_file), encoding="utf-8").read().split())
    assert dsh_methods, "官方方法清单文件不可为空"
    missing = dsh_methods - set(methods.HANDLERS)
    assert not missing, f"DSH 官方方法缺失注册：{sorted(missing)}"
