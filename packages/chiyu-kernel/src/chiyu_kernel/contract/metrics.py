"""有效性度量契约 —— 跨仓统计口径统一的最小面（D5，三支柱批次二）。

⛔ L0 纪律：零第三方依赖（除 dataclasses）、零 IO、零领域字面量。

设计来源（三仓回执 P1 一致，详见 docs/plans/2026-10-13-foundation三大支柱详细设计.md D5）：
  - enterprise Q1.3 P1「canonical schema 毕业：record_kind + rubric_scores + elements」；
  - CRM Q1.3 P1「可插拔评分器 + 诚实降级聚合（未评不掩盖为绿）」；
  - APS #5 P1「跨仓统一口径：命中率/逆转率/校准曲线对账最小面」。

⛔ 诚实降级铁律（金律：可证伪）：无样本 / 未评 ⇒ 输出**空或显式 degraded 标记**，
   不得缺省为零、不得缺省为满、不得把「未评」渲染成「合格」——对齐 CRM
   aggregateAuditability「未评不掩盖」与基座「诚实降级，不造假」纪律。

⛔ 域特有留消费方：各仓评分器实现、域 KPI 语义（排产 makespan/tardy、销售命中率）、
   评分尺子（RUBRIC_KEYS 的**取值**由消费方域注入；本契约只收 schema 形状）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Tuple

# ══ ScoreCard schema（单决策度量卡；可插拔评分器输出收敛为一张卡）════════
# 顺序参与 canonical 序列化，不可重排。前三键 = enterprise Q1.3 毕业三键；
# metrics 为域命名空间注入口（键须带域前缀，如 "crm.4q" / "aps.sla"）。
SCORECARD_FIELDS: Tuple[str, ...] = (
    "decision_id",    # 关联决策（与 OUTCOME_REQUIRED_FIELDS.decision_id 同锚，闭环对齐）
    "rubric_scores",  # 九尺子得分（键 ⊆ RUBRIC_KEYS；取值由消费方评分器产出）
    "elements",       # 八要素声明（键 ⊆ EIGHT_ELEMENTS；值为 bool）
    "metrics",        # 域评分器注入（Mapping[str, object]，键为域命名空间）
)

# ══ MetricSummary schema（窗口聚合输出）══════════════════════════════════
METRIC_SUMMARY_FIELDS: Tuple[str, ...] = (
    "window",          # 聚合窗口标识（ISO-8601 区间或窗口 id，消费方定义格式）
    "sample_count",    # 样本数（0 = 无样本，触发诚实降级而非伪造汇总）
    "metrics",         # 聚合指标（键 ⊆ AGGREGATE_METRIC_KEYS ∪ 域命名空间键）
    "degraded",        # 诚实降级标记（True = 样本不足/未评，metrics 可为空映射）
    "degraded_reason", # 降级原因（degraded=True 时必填非空；False 时空串）
)

# 基座聚合指标闭集（对账最小面；域 KPI 走 metrics 的域命名空间键，不入此闭集）
AGGREGATE_METRIC_KEYS: Tuple[str, ...] = (
    "auditability_pct",  # 可审计性百分比（四问可回答的决策占比）
    "full",              # 全要素齐备占比
    "hit_rate",          # 命中率
    "reversal_rate",     # 逆转率
)

# ══ 诚实降级不变量键（升格为基座默认；实现期由内核聚合器断言）════════════
# 变异自证：删「degraded⇒reason 非空」分支 → 构造空样本无 reason 汇总 → 须红。
HONEST_DEGRADATION_INVARIANTS: Tuple[str, ...] = (
    "no_sample_no_fake_summary",        # 无样本不伪造汇总（sample_count=0 ⇒ degraded=True）
    "degraded_requires_reason",         # 降级必带原因（degraded ⇒ degraded_reason 非空）
    "unrated_not_masked_green",         # 未评不掩盖为绿（缺评分 ≠ 满分/合格）
)


@dataclass(frozen=True)
class ScoreCard:
    """单决策度量卡（canonical 形状；域评分器输出收敛为此形状后可跨仓对账）。"""

    decision_id: str
    rubric_scores: Mapping[str, float] = field(default_factory=dict)
    elements: Mapping[str, bool] = field(default_factory=dict)
    metrics: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("ScoreCard.decision_id 必填（决策锚点，闭环对齐）")


@dataclass(frozen=True)
class MetricSummary:
    """窗口聚合输出（诚实降级语义由 __post_init__ 结构保证）。"""

    window: str
    sample_count: int
    metrics: Mapping[str, object] = field(default_factory=dict)
    degraded: bool = False
    degraded_reason: str = ""

    def __post_init__(self) -> None:
        if not self.window:
            raise ValueError("MetricSummary.window 必填（聚合窗口标识）")
        if self.sample_count < 0:
            raise ValueError("MetricSummary.sample_count 不可为负")
        # 诚实降级不变量（结构保证，非文档纪律）：
        #   no_sample_no_fake_summary：无样本 ⇒ degraded 且不给伪造汇总值
        if self.sample_count == 0:
            if not self.degraded:
                raise ValueError("无样本（sample_count=0）必须 degraded=True（不伪造汇总）")
            if self.metrics:
                raise ValueError("无样本不得携带聚合指标值（不伪造汇总）")
        #   degraded_requires_reason：降级必带原因
        if self.degraded and not self.degraded_reason:
            raise ValueError("degraded=True 必须给 degraded_reason（未评不掩盖）")
        if not self.degraded and self.degraded_reason:
            raise ValueError("degraded=False 不得携带 degraded_reason（状态互斥）")


__all__ = [
    "SCORECARD_FIELDS", "METRIC_SUMMARY_FIELDS", "AGGREGATE_METRIC_KEYS",
    "HONEST_DEGRADATION_INVARIANTS", "ScoreCard", "MetricSummary",
]
