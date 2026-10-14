"""MCP 工具桥（吸收 dsh `mcp/mcp-client`）：连接外部 MCP server，将其工具注册进本仓
`ToolRegistry`，命名归一为 `mcp__<serverName>__<rawName>`，并预留 serverName 命名空间。

网络型 transport（stdio / Streamable HTTP）不在本阶段——`McpTransport` 为协议，真实 transport
可后续实现；测试用 `InMemoryMcpServer` 替身。

> 与 dsh 一致：每个 bridge 实例连一个 server；命名空间重复为配置错误（显式报错，不静默覆盖）。
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from chiyu_kernel.tools import ToolNotFound, ToolRegistry, ToolSpec


@dataclass
class McpToolDef:
    raw_name: str
    description: str


class McpTransport:
    """MCP 传输协议（抽象）。真实实现可接 stdio / HTTP。"""
    def connect(self) -> None:  # pragma: no cover - 接口
        raise NotImplementedError
    def list_tools(self) -> List[McpToolDef]:  # pragma: no cover
        raise NotImplementedError
    def call_tool(self, raw_name: str, args: Mapping[str, Any]) -> Any:  # pragma: no cover
        raise NotImplementedError
    def disconnect(self) -> None:  # pragma: no cover
        raise NotImplementedError


class InMemoryMcpServer(McpTransport):
    """测试替身：在内存里实现一个 MCP server（raw_name -> (description, impl)）。"""
    def __init__(self, tools: Mapping[str, Tuple[str, Callable]]) -> None:
        self._tools = dict(tools)
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def list_tools(self) -> List[McpToolDef]:
        return [McpToolDef(raw_name=n, description=d) for n, (d, _) in self._tools.items()]

    def call_tool(self, raw_name: str, args: Mapping[str, Any]) -> Any:
        if raw_name not in self._tools:
            raise KeyError(raw_name)
        return self._tools[raw_name][1](args)


_SERVER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_MAX_PUBLIC_NAME_LENGTH = 64
_HASH_LENGTH = 12

# serverName 命名空间预留（跨活实例唯一）。进程级集合，模拟 dsh 的 WeakMap<ctx,Set>。
_RESERVED: set = set()


def normalize_mcp_name(server_name: str, raw_name: str) -> str:
    """派生模型面公开名：干净情形 `mcp__<server>__<raw>`；字符替换/截断到 64 时追加 12 位
    SHA-256 哈希后缀，避免不同 MCP 身份塌缩为同一公开名（与 dsh 一致）。"""
    base = f"mcp__{server_name}__{raw_name}"
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", base)
    if len(cleaned) <= _MAX_PUBLIC_NAME_LENGTH:
        return cleaned
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:_HASH_LENGTH]
    return cleaned[: _MAX_PUBLIC_NAME_LENGTH - _HASH_LENGTH - 2] + "__" + digest


class McpBridge:
    def __init__(self, transport: McpTransport, server_name: str) -> None:
        if not _SERVER_NAME_PATTERN.match(server_name):
            raise ValueError(f"serverName 须匹配 [A-Za-z0-9_-]{{1,32}}：{server_name!r}")
        self._transport = transport
        self._server = server_name
        self._public: Dict[str, str] = {}      # public name -> raw name
        self._registered: List[str] = []

    @property
    def server_name(self) -> str:
        return self._server

    def connect(self, registry: ToolRegistry) -> List[str]:
        if self._server in _RESERVED:
            raise ValueError(f"serverName 已被占用：{self._server}")
        _RESERVED.add(self._server)
        self._transport.connect()
        for td in self._transport.list_tools():
            pub = normalize_mcp_name(self._server, td.raw_name)
            raw = td.raw_name

            def _impl(args: Any, _raw: str = raw) -> Any:
                return self._transport.call_tool(_raw, args)

            registry.register(
                ToolSpec(name=pub, description=td.description, scope="", high_risk=False),
                _impl,
            )
            self._public[pub] = raw
            self._registered.append(pub)
        return list(self._registered)

    def call_tool(self, public_name: str, args: Mapping[str, Any]) -> Any:
        raw = self._public.get(public_name)
        if raw is None:
            raise ToolNotFound(public_name)
        return self._transport.call_tool(raw, args)

    def disconnect(self, registry: ToolRegistry) -> None:
        for pub in self._registered:
            registry.unregister(pub)
        self._registered = []
        self._public = {}
        _RESERVED.discard(self._server)
        self._transport.disconnect()


__all__ = [
    "McpToolDef", "McpTransport", "InMemoryMcpServer", "McpBridge", "normalize_mcp_name",
]
