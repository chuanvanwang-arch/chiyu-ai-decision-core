# -*- coding: utf-8 -*-
"""图写 MCP 端点接线 E2E（补 T48 §2.1 纸面缺口：write_controlled_edges 经 McpServer.expose(risk="write") 暴露为可调用端点）。

判据（与 T48 §2.1 / A9 契约对齐）：
1. list_tools 含 write_controlled_edges 且 risk="write"；
2. 零信任默认拒绝：auth 未注入 ⇒ 调用返回 AuthDenied（错误码 -32000）；
3. 写类两阶段：首次调用 ⇒ confirmation_required + confirm_token（不执行）；
4. 带 token 真正落库（FakeStore 记录 graph_edge INSERT），written=1；
5. 闭集经 MCP 通道仍生效：edge_source="consumer" ⇒ 失败且 0 落库；
6. 令牌绑定三元组：参数变更 ⇒ 令牌失效（ConfirmTokenInvalid）。

⛔ 两阶段调用姿势（与 WS7 既有测试同构）：确认令牌须放 `params.confirm_token`
经 `handle_request` 传入；`McpServer.call()` 不转发令牌，仅用于"首次取令牌"。
"""
from typing import Any, Mapping, Optional, Tuple

from chiyu_kernel.contract.particle import PredicateSet
from chiyu_kernel.graph.mcp import WRITE_CONTROLLED_EDGES_TOOL, build_graph_write_server


class _Profile:
    predicates = PredicateSet()


class FakeStore:
    def __init__(self, existing: Tuple[str, ...] = ()) -> None:
        self.schema = "public"
        self.existing = set(existing)
        self.executes: list = []

    def execute(self, sql: str, params: Any = None) -> None:
        self.executes.append((sql, params))

    def execute_fetch(self, sql: str, params: Any = None, **kw) -> list:
        ids = params[0]
        return [{"particle_id": pid} for pid in ids if pid in self.existing]


def _profile() -> _Profile:
    return _Profile()


def _args(**over) -> dict:
    a = {"edges": [{"from_id": "dec-1", "to_id": "dec-2", "predicate": "OVERRIDES",
                    "edge_source": "rule",
                    "valid_from": "2026-10-10T00:00:00+08:00"}]}
    if over:
        a["edges"][0].update(over)
    return a


def _call_tool(srv: Any, args: Mapping[str, Any], ctx: Optional[Mapping[str, Any]],
               token: Optional[str] = None) -> dict:
    """MCP tools/call 调用（令牌走 params.confirm_token，与 WS7 同构）。"""
    params: dict = {"name": WRITE_CONTROLLED_EDGES_TOOL, "arguments": args}
    if token is not None:
        params["confirm_token"] = token
    return srv.handle_request(
        {"id": 1, "method": "tools/call", "params": params}, ctx=ctx)


def test_tool_listed_as_write():
    srv = build_graph_write_server(FakeStore(existing=("dec-1", "dec-2")), profile=_profile())
    tools = {t.name: t for t in srv.list_tools()}
    assert WRITE_CONTROLLED_EDGES_TOOL in tools
    assert tools[WRITE_CONTROLLED_EDGES_TOOL].risk == "write"


def test_zero_trust_deny_without_auth():
    srv = build_graph_write_server(FakeStore(existing=("dec-1", "dec-2")), profile=_profile())
    res = srv.call(WRITE_CONTROLLED_EDGES_TOOL, _args(), ctx={"principal": "crm"})
    assert res["error"]["code"] == -32000
    assert "鉴权" in res["error"]["message"]


def test_two_phase_then_actual_write():
    store = FakeStore(existing=("dec-1", "dec-2"))
    srv = build_graph_write_server(
        store, profile=_profile(), auth=lambda ctx: True, secret="s")
    r1 = _call_tool(srv, _args(), {"principal": "crm"})
    assert r1["result"]["status"] == "confirmation_required"
    token = r1["result"]["confirm_token"]
    r2 = _call_tool(srv, _args(), {"principal": "crm"}, token=token)
    assert r2["result"]["written"] == 1
    assert any("INSERT INTO" in sql and "graph_edge" in sql
               for sql, _ in store.executes), "两阶段确认后必须真实落库"


def test_closed_set_via_mcp_rejects_bad_source():
    store = FakeStore(existing=("dec-1", "dec-2"))
    srv = build_graph_write_server(
        store, profile=_profile(), auth=lambda ctx: True, secret="s")
    args = _args(edge_source="consumer")
    r1 = _call_tool(srv, args, {"principal": "crm"})
    token = r1["result"]["confirm_token"]
    r2 = _call_tool(srv, args, {"principal": "crm"}, token=token)
    assert r2["error"]["code"] == -32000
    assert "edge_source" in r2["error"]["message"]
    assert store.executes == [], "闭集拒绝必须零落库"


def test_token_binding_invalidated_on_arg_change():
    store = FakeStore(existing=("dec-1", "dec-2"))
    srv = build_graph_write_server(
        store, profile=_profile(), auth=lambda ctx: True, secret="s")
    r1 = _call_tool(srv, _args(), {"principal": "crm"})
    token = r1["result"]["confirm_token"]
    bad = _args(to_id="dec-3")
    r2 = _call_tool(srv, bad, {"principal": "crm"}, token=token)
    assert r2["error"]["code"] == -32000
    assert "确认令牌无效" in r2["error"]["message"]
