"""scenario MCP 工具面 —— 客户端经 MCP 文件调用写包/列包/锁定。

设计约束（docs/2026-09-26-scenario-pack-design.md §3）：
- 客户端路径 = `McpBridge(InMemoryMcpServer(build_in_memory_server(store)))` →
  `bridge.call_tool("scenario-pack-write", ...)` → **同一 from_dict 校验闸** → store 落盘。
  真桥路径，不是旁路函数；真实 stdio/HTTP transport 留 Phase 后（与 mcp/ 子包现状一致）。
- 工具面收敛为 3 个动作（write/list/lock），防 CRUD 爆炸（ai-native-action-design 判据）。
- `scenario-pack-lock` 为写操作：args 缺 `confirm: true` 拒绝（HITL 闸）。
"""
from __future__ import annotations

from typing import Any, Mapping, Tuple

from chiyu_kernel.mcp import InMemoryMcpServer

from .store import ScenarioPackStore

__all__ = ["build_in_memory_server"]


def build_in_memory_server(store: ScenarioPackStore) -> InMemoryMcpServer:
    """构造 scenario MCP server 替身：3 工具，全部走 store 的唯一写闸。"""

    def _write(args: Mapping[str, Any]) -> Any:
        from .model import from_dict  # 局部 import 避免环（model 不依赖本模块）

        pack = from_dict(args.get("pack") or {})
        path = store.save(pack)
        return {"ok": True, "id": pack.id, "path": str(path)}

    def _list(args: Mapping[str, Any]) -> Any:
        return {"packs": store.list()}

    def _lock(args: Mapping[str, Any]) -> Any:
        if args.get("confirm") is not True:
            raise ScenarioPackLockDenied(
                "scenario-pack-lock 为写操作：args 必须携带 confirm=true（HITL 闸）")
        pack = store.lock(args.get("id") or "", args.get("holder") or "mcp-client")
        return {"ok": True, "id": pack.id, "locked_by": pack.locked_by}

    tools: dict[str, Tuple[str, Any]] = {
        "scenario-pack-write": (
            "Write a scenario pack (validate + persist). Args: {pack: {...}}",
            _write,
        ),
        "scenario-pack-list": (
            "List scenario packs with lock/selected state.",
            _list,
        ),
        "scenario-pack-lock": (
            "Lock a scenario pack (write op; requires confirm=true). Args: {id, holder, confirm}",
            _lock,
        ),
    }
    return InMemoryMcpServer(tools)


class ScenarioPackLockDenied(Exception):
    """锁定缺 confirm 时的显式拒绝（web 层转 400）。"""
