"""记忆契约 —— L0 单一事实源。

⛔ 落点铁律：记忆**不建新表**，落既有粒子 substrate
    particle(type='memory', layer='L2') + particle_attribute 列化 + graph_edge
   （理由：两版设计冲突，晚者胜 —— 见 demo `memory/store.py` 模块 docstring）

写入寻址六元组：缺任一项 ⇒ 记忆**虽落库却永不被命中且不报错**。
故把六项做成**显式参数**，缺项默认拒写（strict）。
"""
from __future__ import annotations

from typing import Tuple

MEMORY_KINDS: Tuple[str, ...] = ("log", "note")

# 写入寻址六元组（缺项拒写）
MEMORY_ADDRESS_KEYS: Tuple[str, ...] = (
    "topic", "layer", "anchor_kind", "anchor_id", "actor", "occurred_at",
)

# 缺项解析来源标记（可见地"没传但结构固定" ≠ 静默兜底）
PROVENANCE_SOURCES: Tuple[str, ...] = ("explicit", "payload", "default", "fallback")

# 结构默认（不算缺项）：layer 由结构恒定固定为 L2
MEMORY_DEFAULTS = {"layer": "L2"}

# 双时钟分离（业务时钟 vs 记录时钟）—— 阈值计算只走业务时钟
BUSINESS_CLOCK_FIELD = "occurred_at"
RECORD_CLOCK_FIELD = "created_at"

__all__ = [
    "MEMORY_KINDS", "MEMORY_ADDRESS_KEYS", "PROVENANCE_SOURCES",
    "MEMORY_DEFAULTS", "BUSINESS_CLOCK_FIELD", "RECORD_CLOCK_FIELD",
]
