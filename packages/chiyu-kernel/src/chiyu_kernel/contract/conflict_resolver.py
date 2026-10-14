"""冲突仲裁契约（Batch-1b-3 conflict_resolver；上迁自 CRM decision/conflict.js G4）。

⛔ L0 纪律：零第三方依赖、零 IO、零领域字面量。

多源事实断言（assertion）并存时，不同来源对同一属性给出不同值 ⇒ **全部保留**
（keep disagreement），置待裁决；裁决只做**标记**（权威 valid=true，其余 valid=false），
物理不删——与审计轨零 DELETE 同律。人工裁决必须挂真实决策行（第 0 闸产物），
禁无决策依据的静默改值。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Tuple

# 裁决策略闭集（CRM G4 测试计划 §5.3 五策略原样上收；命中即止、未知即抛）
CONFLICT_STRATEGIES: Tuple[str, ...] = (
    "timestamp",            # 最新者胜（created_at 比较，由调用方保证同型可比）
    "source_priority",      # 源优先级表注入，缺省优先级 0；平局先到者胜
    "confidence_weighted",  # 源可信度最高者胜（缺省 0.5）
    "merge",                # 合并多值（保留全部，needs_review 解除）
    "human_arbitration",    # 人工裁决：必须携带第 0 闸产出的 decision_ref
)

CONFLICT_INVARIANTS: Tuple[str, ...] = (
    "keep_disagreement_no_delete",   # 保留分歧不物理删（裁决=标记，非删除）
    "unknown_strategy_raises",       # 未知策略 ⇒ 抛错（禁静默回落默认策略）
    "human_arbitration_requires_decision_ref",  # 人工裁决必须挂第 0 闸决策行
    "adoption_is_marking_not_deletion",         # 采用=权威标记 + 其余 valid=False，物理保留
    "tie_keeps_first",               # 平局保持先到者（与 CRM reduce 同序，禁 ties 翻转）
)


class ConflictStrategyError(KernelError):
    code = "CONTRACT_VIOLATION"
    """冲突裁决非法（未知策略 / human_arbitration 缺 decision_ref）。"""


__all__ = [
    "CONFLICT_STRATEGIES", "CONFLICT_INVARIANTS", "ConflictStrategyError",
]
