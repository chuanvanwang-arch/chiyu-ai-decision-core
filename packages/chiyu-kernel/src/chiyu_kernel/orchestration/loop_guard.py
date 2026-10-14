"""guard 环路卫生（吸收 dsh `guard/repeat-tool-reminder` + `guard/timeout-policy`）。

两段职责：
1. **重复调用提醒**（repeat-tool-reminder，建议性）：连续相同 (工具名, 规范参数) 调用达阈值
   [3,5,8] 时，向会话日志注入一条 `system/reminder`（下一轮模型请求会携带）；不否决、不改写调用。
2. **轮次预算**（timeout-policy 的合作式终止等价物）：step 数达 `max_steps` 即终止本轮，
   防失控环路。同步实现（Python 无协作式 signal 中断），以预算为硬边界。

> 与 dsh 一致：提醒为建议性（无否决）；预算终止为卫生安全网。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Sequence, Tuple


@dataclass
class StepVerdict:
    """一轮 step 后 guard 的判定。"""
    terminate: Optional[str] = None   # 非 None = 终止原因
    reminder: Optional[str] = None     # 非 None = 注入提醒文本


def _canonical(name: str, args: Any) -> str:
    """规范键：工具名 + 参数深度排序后的 JSON（顺序无关一致）。"""
    try:
        norm = json.dumps(args, sort_keys=True, ensure_ascii=False)
    except TypeError:
        norm = repr(args)
    return f"{name}\u0000{norm}"


_GENTLE = (
    "You are repeating the exact same tool call with identical arguments. "
    "Carefully analyze the previous result before calling again: if the task is "
    "not complete, try a different approach or different arguments instead of "
    "repeating the call."
)


def _detailed(tool_name: str, count: int, canonical: str) -> str:
    preview = canonical[:500]
    return (
        "Repeated tool call detected:\n"
        f"- tool: {tool_name}\n"
        f"- consecutive_calls: {count}\n"
        f"- arguments: {preview}\n"
        "The repeated calls are not making progress. Do not call this tool with "
        "these exact arguments again. Inspect the latest result and choose a "
        "different action, different arguments, or finish the task if enough "
        "evidence has been gathered."
    )


class LoopGuard:
    def __init__(self, *, thresholds: Sequence[int] = (3, 5, 8),
                 max_steps: int = 25) -> None:
        if not thresholds:
            raise ValueError("thresholds 不可为空")
        for t in thresholds:
            if not isinstance(t, int) or t < 2:
                raise ValueError(f"阈值须为 >=2 整数：{t}")
        self.thresholds = tuple(thresholds)
        self.max_steps = int(max_steps)
        self._last_key: Optional[str] = None
        self._run_len = 0

    def on_step(self, *, step_no: int,
                tool_calls: Sequence[Any]) -> Optional[StepVerdict]:
        reminder: Optional[str] = None
        if tool_calls:
            first = tool_calls[0]
            name = getattr(first, "name", None) or (
                first.get("name") if isinstance(first, Mapping) else None)
            args = getattr(first, "args", None)
            if isinstance(first, Mapping):
                args = first.get("args")
            key = _canonical(name, args)
            if key == self._last_key:
                self._run_len += 1
            else:
                self._last_key = key
                self._run_len = 1
            if self._run_len in self.thresholds:
                reminder = (_GENTLE if self._run_len == self.thresholds[0]
                            else _detailed(name, self._run_len, key))
        terminate: Optional[str] = None
        if step_no >= self.max_steps:
            terminate = f"max_steps exceeded ({self.max_steps})"
        if terminate is None and reminder is None:
            return None
        return StepVerdict(terminate=terminate, reminder=reminder)


__all__ = ["LoopGuard", "StepVerdict"]
