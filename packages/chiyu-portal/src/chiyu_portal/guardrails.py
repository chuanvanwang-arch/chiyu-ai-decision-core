"""输入层护栏：拦截 NL 中的脚本/注入，从源头杜绝「NL 直出 HTML」。

纵深防御第一层（输入层）。第二层结构层 `validate_page_schema`，第三层渲染层 `render_page`。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# 注入模式（IGNORECASE）：脚本 / 伪协议 / 事件属性 / 动态求值 / 嵌入对象
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"<\s*iframe", re.IGNORECASE),
    re.compile(r"<\s*object", re.IGNORECASE),
    re.compile(r"<\s*embed", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"eval\s*\("),
)


@dataclass(frozen=True)
class GuardResult:
    """输入护栏结果。``ok`` 决定可否进入解析层。"""

    ok: bool
    reason: str = ""

    def __bool__(self) -> bool:
        return self.ok


def guard_nl_input(text: str) -> GuardResult:
    """拦截脚本注入。命中任一模式即拒绝，返回字段级原因。"""
    if not isinstance(text, str):
        return GuardResult(False, "输入必须是字符串")
    for pat in _INJECTION_PATTERNS:
        m = pat.search(text)
        if m:
            return GuardResult(False, f"检测到注入模式: {m.group(0)!r}")
    return GuardResult(True)


__all__ = ["GuardResult", "guard_nl_input"]
