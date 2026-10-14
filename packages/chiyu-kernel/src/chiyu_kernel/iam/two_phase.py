"""两阶段确认令牌（Batch-1b-1 two_phase_token）—— 纯函数，零 IO、零网络。

由 `chiyu_kernel.mcpserver` **原样提升**（2026-10-14）：签发/验签是域无关安全原语，
不该绑定在 MCP 服务端；mcpserver 改为委托本模块（同一实现，禁双源）。
消费方自建网关（HTTP/消息队列等）也可直接复用，无需经 McpServer。

绑定规则（TWO_PHASE_INVARIANTS 的机制投影）：
  token = HMAC-SHA256(secret, name | canonical_args | principal)
  ⛔ 三重绑定：改工具名 / 改参数 / 换主体 ⇒ 验签失败（防"拿到 token 再改参数"重放）。
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

__all__ = ["canonical_args", "issue_confirm_token", "verify_confirm_token"]


def canonical_args(args: Any) -> str:
    """参数规范化串（键排序 + 紧凑分隔）⇒ 同一语义的参数必得同一串。"""
    return json.dumps(args if args is not None else {}, sort_keys=True,
                      ensure_ascii=False, separators=(",", ":"))


def issue_confirm_token(secret: str, name: str, args: Any,
                        principal: str = "") -> str:
    """签发确认令牌：HMAC-SHA256(secret, name|args|principal)。

    ⛔ 绑定三者：改工具名 / 改参数 / 换主体 ⇒ 验签失败。
    """
    msg = f"{name}|{canonical_args(args)}|{principal}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def verify_confirm_token(secret: str, name: str, args: Any, principal: str,
                         token: str) -> bool:
    """恒定时间比较（防计时侧信道）。"""
    expected = issue_confirm_token(secret, name, args, principal)
    return hmac.compare_digest(expected, token or "")
