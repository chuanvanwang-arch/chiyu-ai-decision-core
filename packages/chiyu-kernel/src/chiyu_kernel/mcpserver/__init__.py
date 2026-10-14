"""MCP **服务端**骨架（WS7）—— 把底座能力**稳定地输出**出去。

⛔ 与 `chiyu_kernel.mcp` 的分工（别混）
──────────────────────────────────
- `chiyu_kernel.mcp`      = **客户端桥**：连外部 MCP server，把对方工具注册进 `ToolRegistry`。
- `chiyu_kernel.mcpserver` = **服务端**：把本仓能力暴露给外部调用方（本包）。

⛔ 零信任（默认拒绝，非默认放行）
──────────────────────────────
`auth` 未注入 ⇒ **一律拒绝**（`AuthDenied`），不是"先放行再说"。
鉴权是可插拔函数 `auth(ctx) -> bool`，由消费方注入；内核不发明账号体系。

⛔ 两阶段确认（写操作）
──────────────────────────────
写类工具首次调用**不执行**，返回 `confirmation_required` + `confirm_token`；
第二次带上该 token 才真正执行。token **绑定 (工具名, 参数, 调用主体)** 三者：
改任一 ⇒ token 失效（防"拿到 token 再改参数"的重放攻击）。

⛔ 传输层（诚实边界）
──────────────────────────────
`handle_request()` 是**与传输无关**的 JSON-RPC 风格派发器（任何 http 框架都能直接调）。
`StdioTransport` 已实现（行分隔 JSON，可测：用文本流对拍）。
**HTTP 适配器不在内核**：需真实端口即可测性下降，且各消费方框架不同；
消费方把 http body 喂给 `handle_request()` 即可，无需内核适配器。
"""
from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Tuple

# ── 常量 ────────────────────────────────────────────────────────────────────
RISKS: Tuple[str, ...] = ("read", "write")
_TOOL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
JSONRPC = "2.0"


# ── 异常（机器可路由）───────────────────────────────────────────────────────
class McpServerError(Exception):
    """MCP 服务端错误基类。"""


class ToolNotExposed(McpServerError):
    """调用了未暴露的工具（未注册即不可调用，不静默放行）。"""


class AuthDenied(McpServerError):
    """鉴权被拒（含"未注入 auth"的默认拒绝）。"""


class ConfirmRequired(McpServerError):
    """写操作需两阶段确认；携带 `token`。"""

    def __init__(self, token: str, summary: str = "") -> None:
        super().__init__("confirmation required")
        self.token = token
        self.summary = summary


class ConfirmTokenInvalid(McpServerError):
    """确认令牌无效/被篡改/主体不符。"""


@dataclass(frozen=True)
class ExposedTool:
    """已暴露工具（只读投影）。"""

    name: str
    description: str
    risk: str
    scope: str


# ── 确认令牌（Batch-1b-1 two_phase_token：机制已提升至 chiyu_kernel.iam.two_phase，
#    本包**委托同一实现**——禁双源。签名/语义不变，既有消费方 import 面零破坏）────
from chiyu_kernel.iam.two_phase import (  # noqa: F401
    canonical_args, issue_confirm_token, verify_confirm_token,
)


# ── 服务端 ──────────────────────────────────────────────────────────────────
class McpServer:
    """MCP 服务端骨架：注册守卫 + 可插拔鉴权 + 两阶段确认 + 传输无关派发。

    参数：
        auth    `auth(ctx) -> bool`；**未注入 ⇒ 全部拒绝**（零信任）
        secret  令牌密钥；未注入 ⇒ 进程内随机（重启即失效，不跨进程重放）
    """

    def __init__(self, *, auth: Optional[Callable[[Mapping[str, Any]], bool]] = None,
                 secret: Optional[str] = None) -> None:
        self._auth = auth
        self._secret = secret or secrets.token_hex(32)
        self._tools: dict = {}

    # ── 注册守卫 ────────────────────────────────────────────────────
    def expose(self, name: str, handler: Callable[..., Any], *,
               description: str = "", risk: str = "read",
               scope: str = "") -> ExposedTool:
        """暴露一个工具。⛔ 同名重复 ⇒ 抛（静默覆盖会让调用方打到错的处理器）。"""
        if not _TOOL_NAME_PATTERN.match(name or ""):
            raise ValueError(
                f"工具名须匹配 ^[a-z][a-z0-9_]{{0,63}}$：{name!r}")
        if risk not in RISKS:
            raise ValueError(f"risk 须 ∈ {RISKS}：{risk!r}")
        if not callable(handler):
            raise ValueError(f"handler 须可调用：{handler!r}")
        if name in self._tools:
            raise ValueError(f"工具名已被占用（禁静默覆盖）：{name!r}")
        self._tools[name] = {
            "handler": handler, "description": description,
            "risk": risk, "scope": scope,
        }
        return ExposedTool(name, description, risk, scope)

    def list_tools(self) -> Tuple[ExposedTool, ...]:
        return tuple(ExposedTool(n, d["description"], d["risk"], d["scope"])
                     for n, d in sorted(self._tools.items()))

    # ── 派发（传输无关）─────────────────────────────────────────────
    def handle_request(self, req: Mapping[str, Any],
                       ctx: Optional[Mapping[str, Any]] = None) -> dict:
        """JSON-RPC 风格派发：http / stdio / 进程内 都能直接喂进来。"""
        ctx = dict(ctx or {})
        rid = req.get("id")
        method = req.get("method")
        params = dict(req.get("params") or {})
        try:
            if method == "tools/list":
                result: Any = {"tools": [
                    {"name": t.name, "description": t.description,
                     "risk": t.risk, "scope": t.scope}
                    for t in self.list_tools()]}
            elif method == "tools/call":
                result = self._call(params, ctx)
            else:
                return _error(rid, -32601, f"未知 method：{method!r}")
        except ConfirmRequired as e:
            # 两阶段第一阶段：不是错误，是"待确认"结果（带 token）
            return _ok(rid, {"status": "confirmation_required",
                             "confirm_token": e.token,
                             "summary": e.summary})
        except McpServerError as e:
            return _error(rid, -32000, str(e))
        return _ok(rid, result)

    def _call(self, params: Mapping[str, Any], ctx: Mapping[str, Any]) -> Any:
        name = params.get("name")
        args = params.get("arguments")
        if name not in self._tools:
            raise ToolNotExposed(f"未暴露的工具：{name!r}（已暴露：{sorted(self._tools)}）")
        # 1. 鉴权（未注入 auth ⇒ 默认拒绝）
        if self._auth is None or not self._auth(ctx):
            raise AuthDenied("鉴权被拒（auth 未注入时默认拒绝一切）")
        tool = self._tools[name]
        principal = str(ctx.get("principal") or "")
        # 2. 两阶段确认（仅写类）
        if tool["risk"] == "write":
            token = params.get("confirm_token")
            if not token:
                raise ConfirmRequired(
                    issue_confirm_token(self._secret, name, args, principal),
                    summary=f"写操作 {name} 需确认")
            if not verify_confirm_token(self._secret, name, args, principal, token):
                raise ConfirmTokenInvalid(
                    "确认令牌无效：工具名/参数/主体任一变更都会使其失效")
        return tool["handler"](args, ctx=ctx)

    # ── 便捷：直调（供进程内消费方 / 测试）──────────────────────────
    def call(self, name: str, args: Any = None, *,
             ctx: Optional[Mapping[str, Any]] = None) -> Any:
        return self.handle_request(
            {"id": 1, "method": "tools/call",
             "params": {"name": name, "arguments": args}}, ctx=ctx)


def _ok(rid: Any, result: Any) -> dict:
    return {"jsonrpc": JSONRPC, "id": rid, "result": result}


def _error(rid: Any, code: int, message: str) -> dict:
    return {"jsonrpc": JSONRPC, "id": rid,
            "error": {"code": code, "message": message}}


# ── 传输：stdio（行分隔 JSON；可测，用文本流对拍）───────────────────────────
class StdioTransport:
    """行分隔 JSON 的 stdio 传输：读入一行请求 → 写回一行响应。

    构造参数是**类文件对象**（任何有 readline/write 的对象），故无需真实端口即可测。
    """

    def __init__(self, server: McpServer, *,
                 ctx: Optional[Mapping[str, Any]] = None) -> None:
        self.server = server
        self.ctx = dict(ctx or {})

    def handle_line(self, line: str) -> str:
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            return json.dumps(_error(None, -32700, f"解析失败：{e}"),
                              ensure_ascii=False)
        return json.dumps(self.server.handle_request(req, ctx=self.ctx),
                          ensure_ascii=False)

    def serve(self, reader, writer) -> int:
        """循环处理至 EOF，返回处理条数。"""
        n = 0
        for line in reader:
            if not line.strip():
                continue
            writer.write(self.handle_line(line) + "\n")
            n += 1
        return n


# ── 鉴权助手（可插拔；内核不发明账号体系）───────────────────────────────────
def allow_principals(*names: str) -> Callable[[Mapping[str, Any]], bool]:
    """白名单鉴权：ctx['principal'] 命中才放行。"""
    allowed = set(names)

    def _auth(ctx: Mapping[str, Any]) -> bool:
        return str(ctx.get("principal") or "") in allowed

    return _auth


__all__ = [
    "RISKS", "McpServerError", "ToolNotExposed", "AuthDenied",
    "ConfirmRequired", "ConfirmTokenInvalid", "ExposedTool",
    "canonical_args", "issue_confirm_token", "verify_confirm_token",
    "McpServer", "StdioTransport", "allow_principals",
]
