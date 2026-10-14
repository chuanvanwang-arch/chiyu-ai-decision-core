"""nightly_report 契约（L0：零依赖 / 零 IO / 零领域字面量）。

Batch-5 零 LLM 夜报判据词汇。上收自 CRM report/nightlyReport.js
（collectSegments / extractRetroMetrics / renderNightlyMarkdown）。
报告标题/日期口径/落盘路径由消费方注入；三段产出的业务语义由消费方采集。

不变量（REPORT_INVARIANTS）：
  R1 零额外 LLM：渲染仅聚合三段既有结果，不二次调用模型（nightlyReport.js:2 铁律；
     复盘段归因由消费方 LLM 产出属既有行为，不在本核内）。
  R2 段 null 容错：任一段缺省给空结构，防渲染崩（:26 注释）。
  R3 双形态兼容：实时形态与落库回读持久化形态统一提取，summary.* 为权威聚合、
     clusters 为明细、任一缺失回退顶层字段——避免落库回读计数恒 0（:53-56 注释）。
  R4 漂移口径诚实：drift>0 但无自动建议值时必须显示「需人工研判」，
     禁误显示「全部健康」（:122-128 修复语义）。
  R5 失败原因过滤阈值独立注入：缺省 0.7（CRM 语境，与 D3 裁定同源——
     禁与基座 0.79 自主放行阈值静默互替）。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError
from typing import Tuple

# ── 三段闭集（nightlyReport.js collectSegments；段名是结构词汇非域值）──────────
REPORT_SEGMENTS: Tuple[str, ...] = ("retro", "routing", "param")

# ── 复盘段统一指标字段（extractRetroMetrics :57-77 输出面）────────────────────
RETRO_METRIC_FIELDS: Tuple[str, ...] = (
    "total", "ok", "drift", "draft_count", "llm_enabled", "llm_effective",
    "fail_reasons", "by_root_cause", "scanned",
)

# ── 失败原因过滤阈值（R5；D3 同源：0.7=CRM 语境缺省，可注入）──────────────────
FAIL_CONFIDENCE_THRESHOLD_DEFAULT = 0.7

# ── 参数快照过滤前缀（九尺子扩展；rubric 是基座概念词汇非域值）──────────────────
RUBRIC_ITEM_PREFIX = "rubric"

# ── 判据自检 ─────────────────────────────────────────────────────────────────
REPORT_INVARIANTS: Tuple[str, ...] = (
    "R1_no_extra_llm",            # 渲染零额外 LLM
    "R2_null_segment_tolerant",   # 段 null 容错不崩
    "R3_summary_authoritative",   # 双形态 summary.* 权威，回读不归零
    "R4_drift_honest",            # drift>0 无建议禁报全部健康
    "R5_threshold_injectable",    # 失败阈值独立注入禁与 0.79 互替
)


class NightlyReportError(KernelError):
    code = "CONTRACT_VIOLATION"
    """nightly_report 判据核参数错误。fail-closed。"""


__all__ = [
    "REPORT_SEGMENTS", "RETRO_METRIC_FIELDS", "FAIL_CONFIDENCE_THRESHOLD_DEFAULT",
    "RUBRIC_ITEM_PREFIX", "REPORT_INVARIANTS", "NightlyReportError",
]
