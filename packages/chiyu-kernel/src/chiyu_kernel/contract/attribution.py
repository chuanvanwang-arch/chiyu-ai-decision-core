"""归因规则契约（Batch-1b-3 attribution；上迁自 CRM monitor/attribution.js T29 +
decision/rootCauseClassifier.js R0-R3 分类树）。

⛔ L0 纪律：零第三方依赖、零 IO、零领域字面量。

七态根因词汇（写时占位 + 滞后回写共用；分类树命中即止，优先级不可重排）。
⛔ 域值留消费方：旋钮（knob）映射与中文名是消费方 SKILL 动作词汇（如 CRM
META_ATTR_MAP / SOURCE_REFRESH），基座只收 code/layer/severity/evidence；
边规格（serves_dimension 绑定、E1-E7 边闭集）由消费方注入。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Tuple

# 归因类别闭集（CRM T29 CATEGORY_STATES 11 态原样上收；含旧三态兼容位）
ATTRIBUTION_CATEGORIES: Tuple[str, ...] = (
    "ok", "input_missing", "inference_bias",                    # 旧三态
    "FIELD_MISMATCH", "INFO_INCOMPLETE", "INPUT_STALE",         # 粒子库三检
    "DIM_MISSING", "EDGE_MISSING", "NEED_DIM_ORDER",
    "DATA_QUALITY_PRECEDENT",                                   # M/K 层
    "UNKNOWN",
)

# 根因代码的层归属（code → layer；knob/名称留消费方）
ROOT_CAUSE_LAYERS: Tuple[Tuple[str, str], ...] = (
    ("FIELD_MISMATCH", "particle"),
    ("INFO_INCOMPLETE", "particle_or_knowledge"),
    ("INPUT_STALE", "particle"),
    ("DIM_MISSING", "model_required_dims"),
    ("EDGE_MISSING", "model_edge_bindings"),
    ("NEED_DIM_ORDER", "model_or_knowledge"),
    ("DATA_QUALITY_PRECEDENT", "knowledge"),
    ("UNKNOWN", "unknown"),
)

# 人工处置词汇（滞后回写；推翻=业务不可用且重大偏差走 R0 树，确认=准确）
HUMAN_DISPOSITIONS: Tuple[str, ...] = (
    "OVERRIDDEN", "CORRECTED",   # 推翻（accuracy_signal=inaccurate）
    "CONFIRMED", "APPROVED",     # 确认（accuracy_signal=accurate）
)

ATTRIBUTION_INVARIANTS: Tuple[str, ...] = (
    "no_feedback_is_unknown",                  # 无反馈信号 ⇒ UNKNOWN（进人工归因队列）
    "positive_reinforcement_needs_no_knob",    # 可用且非重大 ⇒ 无根因干预（severity=none）
    "classify_hit_and_stop_priority",          # 命中即止：field > info > stale > dim > edge > major > order
    "e_missing_requires_required_missing",     # E 缺=应连未连显式非空；未查实不判缺（防误判护栏）
    "human_overwrite_preserves_fine_category",  # 已七态判定不被人工推翻重算覆盖
    "all_clear_overturn_is_inference_bias",    # L+E 全齐仍被推翻 ⇒ 推理偏差（兼容旧态）
)


class AttributionError(KernelError):
    code = "CONTRACT_VIOLATION"
    """归因输入非法（非法处置词 / 非法类别）。"""


__all__ = [
    "ATTRIBUTION_CATEGORIES", "ROOT_CAUSE_LAYERS", "HUMAN_DISPOSITIONS",
    "ATTRIBUTION_INVARIANTS", "AttributionError",
]
