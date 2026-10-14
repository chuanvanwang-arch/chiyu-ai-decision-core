"""行动面注册表（R1–R6 基数的可执行形式）—— ★ 新建，demo 未收敛。

⛔ 内容为**机制**（判定规则），非具体 Action 清单（那是 L4 消费方域内容）。
"""
from .registry import (ActionRegistry, ActionSpec, ACTION_MAX, ACTION_MIN)

__all__ = ["ActionSpec", "ActionRegistry", "ACTION_MIN", "ACTION_MAX"]
