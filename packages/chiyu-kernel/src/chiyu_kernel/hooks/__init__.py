"""钩子总线（吸收 dsh `hooks/hook-protocol`）：matcher（match-all/literal/regex）+ 生命周期点。

`HookBus` 在 AgentLoop 生命周期点触发：
- `PreToolUse`：工具调用前；任一钩子 decision 为 `deny`/`block` → 跳过该工具调用。
- `PostToolUse`：工具调用后（观察）。
- `Stop`：本轮结束（观察）。

matcher 语义与 dsh 一致：缺省/空/`*` = 全匹配；claude-code 模式下纯 `[A-Za-z0-9_|]` 为字面量
（按 `|` 拆分精确匹配），其余按未锚定正则；无效正则按非匹配处理（不抛）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

HookFn = Callable[[Mapping[str, Any]], str]


@dataclass
class HookResult:
    point: str
    handler_id: str
    decision: str
    output: Optional[str] = None
    duration_ms: int = 0


_CLAUDE_LITERAL = re.compile(r"^[A-Za-z0-9_|]+$")
_VALID_DECISIONS = ("pass", "deny", "block")


def matches(matcher: Optional[str], query: str, mode: str = "claude-code") -> bool:
    """matcher 是否选中 query（与 dsh `matchesMatcher` 一致）。"""
    if matcher is None or matcher == "" or matcher == "*":
        return True
    if mode == "claude-code" and _CLAUDE_LITERAL.match(matcher):
        return query in matcher.split("|")
    try:
        return re.search(matcher, query) is not None
    except re.error:
        return False


class HookBus:
    def __init__(self) -> None:
        # point -> [(handler_id, matcher, fn)]
        self._hooks: Dict[str, List[Tuple[str, Optional[str], HookFn]]] = {}

    def register(self, point: str, handler_id: str, fn: HookFn,
                 matcher: Optional[str] = None) -> None:
        self._hooks.setdefault(point, []).append((handler_id, matcher, fn))

    def run(self, point: str, query: str,
            payload: Optional[Mapping[str, Any]] = None) -> List[HookResult]:
        results: List[HookResult] = []
        for hid, matcher, fn in self._hooks.get(point, []):
            if not matches(matcher, query):
                continue
            out = fn(payload or {})
            decision = out if isinstance(out, str) else str(out)
            if decision not in _VALID_DECISIONS:
                decision = "pass"
            results.append(HookResult(point=point, handler_id=hid, decision=decision))
        return results


__all__ = ["HookBus", "HookResult", "matches"]
