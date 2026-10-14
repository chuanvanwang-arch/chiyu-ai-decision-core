"""WS7 MCP 服务端骨架 —— 测试 + 反假绿探针。

覆盖：注册守卫（重名禁覆盖 / 名式 / risk 枚举）/ 零信任默认拒绝 / 可插拔鉴权 /
两阶段确认（token 绑定 工具名+参数+主体）/ 未暴露工具不可调用 / stdio 传输对拍。

⛔ 反假绿：每个判据都有探针；变异自证见文件末尾说明。
"""
from __future__ import annotations

import io
import json

import pytest

from chiyu_kernel.mcpserver import (
    RISKS, AuthDenied, ConfirmRequired, ConfirmTokenInvalid, McpServer,
    StdioTransport, ToolNotExposed, allow_principals, canonical_args,
    issue_confirm_token, verify_confirm_token,
)

SECRET = "s3cret"
ALICE = {"principal": "alice"}


def _server(*, auth=None) -> McpServer:
    s = McpServer(auth=auth, secret=SECRET)
    s.expose("read_thing", lambda args, ctx=None: {"ok": True, "args": args},
             description="读", risk="read")
    s.expose("write_thing", lambda args, ctx=None: {"written": args},
             description="写", risk="write")
    return s


# ── 注册守卫 ────────────────────────────────────────────────────────────────
def test_duplicate_name_is_rejected() -> None:
    s = _server()
    with pytest.raises(ValueError, match="已被占用"):
        s.expose("read_thing", lambda args, ctx=None: None)


def test_probe_duplicate_guard_discriminates() -> None:
    """探针：重名必须抛，且**原处理器不被替换**（否则调用方会打到错的处理器）。"""
    s = McpServer(auth=lambda ctx: True, secret=SECRET)
    s.expose("dup", lambda args, ctx=None: {"who": "original"}, risk="read")
    try:
        s.expose("dup", lambda args, ctx=None: {"who": "evil"}, risk="read")
    except ValueError:
        pass
    else:
        pytest.fail("重名未抛 ⇒ 静默覆盖（调用方会打到错的处理器）")
    # 关键：原处理器仍生效（若被覆盖，这里会返回 evil）
    assert s.call("dup", {}, ctx=ALICE)["result"] == {"who": "original"}


def test_bad_name_and_risk_rejected() -> None:
    s = McpServer(auth=lambda ctx: True, secret=SECRET)
    for bad in ("", "Bad", "1bad", "bad-name", "x" * 65):
        with pytest.raises(ValueError, match="工具名"):
            s.expose(bad, lambda args, ctx=None: None)
    with pytest.raises(ValueError, match="risk"):
        s.expose("t", lambda args, ctx=None: None, risk="admin")
    with pytest.raises(ValueError, match="handler"):
        s.expose("t2", "not-callable")  # type: ignore[arg-type]


def test_list_tools() -> None:
    s = _server()
    names = [t.name for t in s.list_tools()]
    assert names == ["read_thing", "write_thing"]
    assert RISKS == ("read", "write")


# ── 零信任：默认拒绝 ────────────────────────────────────────────────────────
def test_no_auth_means_deny() -> None:
    """未注入 auth ⇒ 全部拒绝（不是"先放行再说"）。"""
    s = McpServer(secret=SECRET)          # auth=None
    s.expose("t", lambda args, ctx=None: "leaked", risk="read")
    res = s.call("t", {}, ctx=ALICE)
    assert "error" in res
    assert res["error"]["code"] == -32000


def test_probe_default_deny_discriminates() -> None:
    """探针：若默认放行，读工具会返回值 ⇒ 泄密。"""
    s = McpServer(secret=SECRET)
    s.expose("t", lambda args, ctx=None: "leaked", risk="read")
    res = s.call("t", {}, ctx=ALICE)
    assert res.get("result") is None, "未注入 auth 却返回了结果 ⇒ 默认放行（泄密）"


def test_pluggable_auth_allow_deny() -> None:
    s = _server(auth=allow_principals("alice"))
    assert "result" in s.call("read_thing", {}, ctx=ALICE)
    assert "error" in s.call("read_thing", {}, ctx={"principal": "bob"})


# ── 未暴露工具不可调用 ──────────────────────────────────────────────────────
def test_unexposed_tool_not_callable() -> None:
    s = _server(auth=lambda ctx: True)
    res = s.call("ghost_tool", {}, ctx=ALICE)
    assert "error" in res
    with pytest.raises(ToolNotExposed):
        s._call({"name": "ghost_tool", "arguments": {}}, ALICE)


# ── 两阶段确认（写操作）────────────────────────────────────────────────────
def test_write_requires_two_phase_confirm() -> None:
    s = _server(auth=lambda ctx: True)
    args = {"amount": 100}
    first = s.call("write_thing", args, ctx=ALICE)
    assert first["result"]["status"] == "confirmation_required"
    token = first["result"]["confirm_token"]
    assert token
    # 第二阶段：带 token 才真正执行
    second = s.handle_request(
        {"id": 7, "method": "tools/call",
         "params": {"name": "write_thing", "arguments": args,
                    "confirm_token": token}},
        ctx=ALICE)
    assert second["result"] == {"written": args}


def test_probe_write_does_not_execute_on_first_call() -> None:
    """探针：第一阶段若偷偷执行了 ⇒ 两阶段形同虚设。"""
    s = _server(auth=lambda ctx: True)
    calls: list = []
    s.expose("w2", lambda args, ctx=None: calls.append(args), risk="write")
    res = s.call("w2", {"a": 1}, ctx=ALICE)
    assert res["result"]["status"] == "confirmation_required"
    assert calls == [], "第一阶段就执行了 ⇒ 两阶段确认被绕过"


def test_token_bound_to_args() -> None:
    """改参数 ⇒ token 失效（防"拿 token 再改参数"重放）。"""
    s = _server(auth=lambda ctx: True)
    first = s.call("write_thing", {"amount": 100}, ctx=ALICE)
    token = first["result"]["confirm_token"]
    res = s.handle_request(
        {"id": 1, "method": "tools/call",
         "params": {"name": "write_thing", "arguments": {"amount": 999999},
                    "confirm_token": token}},
        ctx=ALICE)
    assert "error" in res, "改了参数却仍通过 ⇒ token 未绑定参数"


def test_token_bound_to_principal() -> None:
    """换主体 ⇒ token 失效（防 A 签发 B 使用）。"""
    s = _server(auth=lambda ctx: True)
    token = s.call("write_thing", {"a": 1}, ctx=ALICE)["result"]["confirm_token"]
    res = s.handle_request(
        {"id": 1, "method": "tools/call",
         "params": {"name": "write_thing", "arguments": {"a": 1},
                    "confirm_token": token}},
        ctx={"principal": "bob"})
    assert "error" in res, "换主体却仍通过 ⇒ token 未绑定主体"


def test_token_bound_to_tool_name() -> None:
    """换工具名 ⇒ token 失效。"""
    s = _server(auth=lambda ctx: True)
    s.expose("w3", lambda args, ctx=None: "w3", risk="write")
    token = s.call("write_thing", {"a": 1}, ctx=ALICE)["result"]["confirm_token"]
    res = s.handle_request(
        {"id": 1, "method": "tools/call",
         "params": {"name": "w3", "arguments": {"a": 1},
                    "confirm_token": token}},
        ctx=ALICE)
    assert "error" in res, "换工具名却仍通过 ⇒ token 未绑定工具名"


def test_read_tool_needs_no_confirm() -> None:
    """读类工具不该被两阶段拦（否则可用性归零）。"""
    s = _server(auth=lambda ctx: True)
    assert s.call("read_thing", {"q": 1}, ctx=ALICE)["result"]["ok"] is True


def test_token_helpers() -> None:
    assert canonical_args({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    t = issue_confirm_token(SECRET, "n", {"a": 1}, "alice")
    assert verify_confirm_token(SECRET, "n", {"a": 1}, "alice", t)
    assert not verify_confirm_token(SECRET, "n", {"a": 2}, "alice", t)
    with pytest.raises(ConfirmTokenInvalid):
        raise ConfirmTokenInvalid("bad")


def test_confirm_required_exception_shape() -> None:
    e = ConfirmRequired("tok", summary="s")
    assert e.token == "tok" and e.summary == "s"


# ── stdio 传输（行分隔 JSON，文本流对拍）────────────────────────────────────
def test_stdio_roundtrip() -> None:
    s = _server(auth=lambda ctx: True)
    t = StdioTransport(s, ctx=ALICE)
    out = t.handle_line(json.dumps({"id": 1, "method": "tools/list"}))
    payload = json.loads(out)
    assert payload["id"] == 1
    assert [x["name"] for x in payload["result"]["tools"]] == \
        ["read_thing", "write_thing"]


def test_stdio_serve_multiple_lines() -> None:
    s = _server(auth=lambda ctx: True)
    t = StdioTransport(s, ctx=ALICE)
    reader = io.StringIO(
        json.dumps({"id": 1, "method": "tools/list"}) + "\n\n" +
        json.dumps({"id": 2, "method": "tools/call",
                    "params": {"name": "read_thing", "arguments": {}}}) + "\n")
    writer = io.StringIO()
    assert t.serve(reader, writer) == 2
    lines = [json.loads(x) for x in writer.getvalue().strip().split("\n")]
    assert [x["id"] for x in lines] == [1, 2]


def test_stdio_malformed_json() -> None:
    s = _server(auth=lambda ctx: True)
    out = json.loads(StdioTransport(s, ctx=ALICE).handle_line("{not json"))
    assert out["error"]["code"] == -32700


def test_unknown_method() -> None:
    s = _server(auth=lambda ctx: True)
    res = s.handle_request({"id": 1, "method": "nope"}, ctx=ALICE)
    assert res["error"]["code"] == -32601


# ── 变异自证（2026-10-09 实测）──────────────────────────────────────────────
# ① 把 `if self._auth is None or not self._auth(ctx)` 改成 `if False`
#    → test_no_auth_means_deny / test_probe_default_deny_discriminates 转红（泄密）。
# ② 把写类两阶段分支 `if tool["risk"] == "write"` 改成 `if False`
#    → test_write_requires_two_phase_confirm 与 test_probe_write_does_not_execute_on_first_call
#      转红（写操作无确认即执行）。
# ③ 把 `issue_confirm_token` 的消息体去掉参数部分（只绑 name）
#    → test_token_bound_to_args 转红（改参数仍通过）。
# 三者均已实测转红后还原，证明探针非恒绿。
