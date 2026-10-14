"""审批闸门（吸收 dsh `interaction/permission-presets` + 用户审批）：高风险动作 HITL。

`ApprovalGate` 接进 `ToolRegistry` 的红线位（`redline_guard`）：当模型请求调用**高危险**
工具（`ToolSpec.high_risk`）且尚未批准时，自动建待批请求并拦截（`GuardDenied`）；人工
`approve` 后放行，`deny` 保持拒绝。`safe` 工具不经此闸门。

> 与 dsh 一致：审批是人工决策点；本实现为同步 HITL（夜间无人时由上游档位决定是否自动批准）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from chiyu_kernel.tools import GuardDenied, ToolRegistry


@dataclass
class ApprovalRequest:
    id: str
    action: str
    summary: str
    status: str = "pending"   # pending | approved | denied


class ApprovalGate:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._pending: Dict[str, ApprovalRequest] = {}
        self._open: Dict[str, str] = {}        # action -> pending id（去重）
        self._approved: set = set()            # 已批准 action
        self._seq = 0

    def request(self, action: str, summary: str = "") -> str:
        self._seq += 1
        aid = f"apr-{self._seq}"
        self._pending[aid] = ApprovalRequest(id=aid, action=action, summary=summary)
        self._open[action] = aid
        return aid

    def approve(self, approval_id: str) -> None:
        req = self._pending.get(approval_id)
        if req is None:
            raise KeyError(approval_id)
        req.status = "approved"
        self._approved.add(req.action)
        self._open.pop(req.action, None)

    def deny(self, approval_id: str) -> None:
        req = self._pending.get(approval_id)
        if req is None:
            raise KeyError(approval_id)
        req.status = "denied"
        self._open.pop(req.action, None)

    def pending(self) -> List[str]:
        return [aid for aid, r in self._pending.items() if r.status == "pending"]

    def guard(self, name: str, args: Any) -> Optional[str]:
        """供 `ToolRegistry.redline_guard` 使用：高危险未批 → 拦截 verdict。"""
        spec = self._registry.spec(name)
        if spec is None or not spec.high_risk:
            return None
        if name in self._approved:
            return None
        if name in self._open:               # 已有待批，复用
            return f"needs-approval:{self._open[name]}"
        aid = self.request(name, summary=str(args))
        return f"needs-approval:{aid}"


__all__ = ["ApprovalGate", "ApprovalRequest"]
