"""参数健康诊断契约（Batch-1b-4 param_health_check；上迁自 CRM monitor/diagnosis.js recommend 判据）。

⛔ L0 纪律：零第三方依赖、零 IO、零领域字面量。
红线前缀清单（如 CRM routing 系 knob 名）由消费方注入（域值留消费方）；
判据算法与阈值常量在基座（推荐口径永不漂移）。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Tuple

# ── 处方风险档（消费方风险评级闭集；基座不评级只按档判）────────────────────
PARAM_RISK_LEVELS: Tuple[str, ...] = ("LOW", "MEDIUM", "HIGH")

# ── 推荐结论闭集 ────────────────────────────────────────────────────────
RECOMMEND_OUTCOMES: Tuple[str, ...] = ("approve", "reject")

#: HIGH 风险放行门槛：场景失败率 > 此值才 approve（其余一律 reject）。
HIGH_RISK_FAIL_RATE = 0.3

RECOMMEND_INVARIANTS: Tuple[str, ...] = (
    "high_risk_needs_substantial_fail_rate",  # HIGH + fail>0.3 ⇒ approve；否则 reject
    "medium_risk_needs_any_fail",             # MEDIUM + fail>0 ⇒ approve；否则 reject
    "low_risk_never_auto_approve",            # LOW 一律 reject（无自动放行通道）
    "red_line_knobs_display_only",            # 红线系 knob 只展示不产处方（过滤后仍可见、标 red_line）
    "red_line_prefixes_consumer_injected",    # 红线前缀清单由消费方注入（域值不入基座）
)


class ParamHealthError(KernelError):
    code = "CONTRACT_VIOLATION"
    """参数健康判据输入非法（未知风险档 / 非法失败率形态）。"""


__all__ = [
    "PARAM_RISK_LEVELS", "RECOMMEND_OUTCOMES", "HIGH_RISK_FAIL_RATE",
    "RECOMMEND_INVARIANTS", "ParamHealthError",
]
