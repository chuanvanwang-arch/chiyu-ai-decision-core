"""分级判定 + 生产调用点计数（纯函数）。

上迁源：APS ``platform/capability_audit.py`` 的 ``_grade`` / ``_count_production_calls``
（A6 修复顺序：零命中最优先；零外部入口假绿形态）。

★ 判定次序即不变式（``zero_hit_first_missing`` / ``zero_entry_is_partial``）：
    ① ``hit_count == 0`` 最优先 —— 零命中即 missing，任何硬编码分支都不得遮蔽；
    ② 符号存在但生产路径零调用方 ⇒ partial + 显式标注「零外部入口」；
    ③ 其余才允许 landed。
"""
from __future__ import annotations

from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

from chiyu_kernel.contract.capability_audit import (
    NON_CALL_LINE_PREFIXES,
    VERDICT_LANDED,
    VERDICT_MISSING,
    VERDICT_PARTIAL,
)

__all__ = ["is_call_line", "count_production_calls", "grade_capability"]

#: three_check 命中元组：(relpath, lineno, line)
Hit = Tuple[str, int, str]


def is_call_line(line: str) -> bool:
    """该行是否算「生产调用点」——定义/枚举/注释行不算（``definition_is_not_call``）。"""
    stripped = line.lstrip()
    return not stripped.startswith(NON_CALL_LINE_PREFIXES)


def count_production_calls(hits: Iterable[Hit]) -> int:
    """数三查命中中的**调用点**行数（过滤 def/class/__all__/注释/文档串）。"""
    return sum(1 for _path, _lineno, line in hits if is_call_line(line))


def grade_capability(
    *, hit_count: int, production_calls: int,
) -> Tuple[str, Optional[str], str]:
    """据三查命中数 + 生产调用点数给分级结论（verdict, priority, note）。

    纯函数、无消费方特例：APS 的 cap4/cap9 等领域性说明由消费方在
    本函数输出之上追加（特例逻辑留域，判定次序上收）。
    """
    if hit_count == 0:
        return (VERDICT_MISSING, "P0",
                "三查法零命中：预期符号/文件不存在 → 判未落地。")
    if production_calls == 0:
        return (VERDICT_PARTIAL, "P0",
                "链内自洽但零外部入口：三查（符号/文件）命中，但生产路径零调用方"
                "（仅测试与演示脚本引用）→ 闭环不成立，判部分落地并显式标注零入口。"
                "⚠ 不得据此判 landed（函数存在 ≠ 已落地）。")
    return (VERDICT_LANDED, None,
            f"三查法命中预期符号，且生产路径存在真实调用点（{production_calls} 处）。")
