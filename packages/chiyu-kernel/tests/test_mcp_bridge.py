"""T2 — MCP 工具桥（吸收 dsh `mcp/mcp-client`）：命名归一 + namespace 预留。

TDD：先红（chiyu_kernel.mcp 尚不存在）→ 绿。
"""
import pytest
import re

from chiyu_kernel.mcp import (
    InMemoryMcpServer, McpBridge, McpToolDef, normalize_mcp_name,
)
from chiyu_kernel.tools import ToolRegistry, ToolNotFound


@pytest.fixture(autouse=True)
def _clear_reserved():
    from chiyu_kernel.mcp import _RESERVED
    _RESERVED.clear()
    yield
    _RESERVED.clear()


def _server():
    return InMemoryMcpServer({
        "search": ("搜索", lambda args: f"found:{args.get('q')}"),
        "bad name!": ("带非法字符", lambda args: "ok"),
    })


def test_connect_registers_normalized_tools():
    reg = ToolRegistry()
    bridge = McpBridge(_server(), server_name="srv1")
    names = bridge.connect(reg)
    assert "mcp__srv1__search" in names
    # 非法字符归一
    assert any(n == "mcp__srv1__bad_name_" for n in names), names
    # 注册进 registry，scope=mcp
    assert "mcp__srv1__search" in reg.names(scope="mcp")


def test_call_forwards_to_server():
    reg = ToolRegistry()
    bridge = McpBridge(_server(), server_name="srv1")
    bridge.connect(reg)
    # 经 bridge.call_tool
    assert bridge.call_tool("mcp__srv1__search", {"q": "x"}) == "found:x"
    # 经 registry.execute（impl 内部转发到 transport）
    assert reg.execute("mcp__srv1__search", {"q": "y"}) == "found:y"


def test_duplicate_server_name_rejected():
    reg = ToolRegistry()
    b1 = McpBridge(_server(), server_name="dup")
    b1.connect(reg)
    b2 = McpBridge(_server(), server_name="dup")
    try:
        raised = False
        try:
            b2.connect(reg)
        except ValueError:
            raised = True
        assert raised, "重复 serverName 未报错"
    finally:
        b1.disconnect(reg)


def test_disconnect_unregisters():
    reg = ToolRegistry()
    bridge = McpBridge(_server(), server_name="srv1")
    bridge.connect(reg)
    assert "mcp__srv1__search" in reg.names(scope="mcp")
    bridge.disconnect(reg)
    assert "mcp__srv1__search" not in reg.names(scope="mcp")
    # namespace 释放后可复用
    b2 = McpBridge(_server(), server_name="srv1")
    b2.connect(reg)
    b2.disconnect(reg)


def test_normalize_length_cap_and_hash():
    long_raw = "x" * 80
    name = normalize_mcp_name("srv", long_raw)
    assert len(name) <= 64
    assert name.startswith("mcp__srv__")
    # 稳定：同输入同输出
    assert normalize_mcp_name("srv", long_raw) == name
