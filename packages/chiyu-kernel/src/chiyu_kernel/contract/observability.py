"""observability 契约（L0：零依赖 / 零 IO / 零领域字面量）。

Batch-4a 监控底座判据词汇。上收自 CRM 监控页纯函数判据核
（monitorStore.js / signalMetrics.js / enrichmentMetrics.js / edgeSource.js / busFailures.js），
域值（闸门名/渠道名/租户名）由消费方注入，本契约只收结构与机制口径。

防假绿不变量（OBSERVABILITY_INVARIANTS，全部为判据语义登记，违者即假绿）：
  O1 无投递尝试时 success_rate=null，禁报 100%（signalMetrics.js:31）。
  O2 富集命中率分母恒真实：calls=0 → rate=0 且不虚造（enrichmentMetrics.js:7-11）。
  O3 配置读取失败 ≠ 配置缺失：两者分别留痕，绝不回退默认全开（signalMetrics.js:107-115）。
  O4 边来源 NULL 不计入真实供给（edgeSource.js:17）；演示边只分类不物理删（零 DELETE）。
  O5 真静默（delivery_silent）才参与出口闸；有归因未送达（delivery_undelivered）刻意
     不参与——把配置未齐判成出口不健康会让闸门变噪音被绕过（signalMetrics.js:131-139）。
  O6 失败计数单一实现：record/get/reset 同一计数器，bus 与监控 re-export 同源防判据分裂
     （busFailures.js 注释 §G4）。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError
from typing import Tuple

# ── 归因四类交叉（monitorStore.js:88-97 classifyAttribution 交叉矩阵）──────────
#   ⚠ 与 attribution 契约的 ATTRIBUTION_CATEGORIES（rootCauseClassifier 11 态）不同源：
#   本组是「拦截即时判定」四类交叉（CRM 设计 §1/§3 术语：交叉矩阵），故带 CROSS 前缀。
#   inference_bias       必填齐 + 不准（输入对了还错 → 调 agent 而非补数据）
#   input_error          必填缺 + 不准（缺/错导致判错）
#   input_missing        必填缺 + 准/待定（必填未齐）
#   context_insufficient 必填齐 + level='warn'（上下文不足，非阻断）
ATTRIBUTION_CROSS_CATEGORIES: Tuple[str, ...] = (
    "inference_bias", "input_error", "input_missing", "context_insufficient",
)

# 良性判定返回 None（不计入错误类）——哨兵名登记，机制返回值用 None 本体
ATTRIBUTION_BENIGN = None

# ── 准确率三态桶（monitorStore.js:138-143）───────────────────────────────────
#   CONFIRMED/APPROVED → accurate；OVERRIDDEN/CORRECTED → inaccurate；其余（含空）→ pending
ACCURACY_BUCKETS: Tuple[str, ...] = ("accurate", "inaccurate", "pending")
ACCURACY_ACCURATE_FROM: Tuple[str, ...] = ("CONFIRMED", "APPROVED")
ACCURACY_INACCURATE_FROM: Tuple[str, ...] = ("OVERRIDDEN", "CORRECTED")

# ── 闸门指标聚合状态映射（monitorStore.js:49-55）─────────────────────────────
#   state → metric 桶；未列出状态不计入任何桶（total 仍累计）
GATE_METRIC_STATES: Tuple[Tuple[str, str], ...] = (
    ("AUTONOMOUS", "autonomous"),
    ("HUMAN", "human"),
    ("REQUIRED", "escalated"),
    ("ESCALATED", "escalated"),
)

# ── 负向判据类型闭集（signalMetrics.js）──────────────────────────────────────
#   delivery_silent       渠道启用且窗口内零行（attempted=0，真静默）——参与出口闸可阻断
#   delivery_undelivered  有尝试但零 sent（有归因未送达，附首位原因）——不参与出口闸
#   gen_silent            event-trigger 命中（fired>0）而内部信号零生成（landed=0）
NEGATIVE_PREDICATE_TYPES: Tuple[str, ...] = (
    "delivery_silent", "delivery_undelivered", "gen_silent",
)
#: O5 语义登记：只有 delivery_silent 参与出口闸（exportGate）
EXPORT_GATE_BLOCKING_TYPES: Tuple[str, ...] = ("delivery_silent",)

# ── 边来源双口径（edgeSource.js）─────────────────────────────────────────────
# 演示/种子边来源标记闭集（默认含 seed-script；消费方可扩展注入）
DEMO_EDGE_SOURCES_DEFAULT: Tuple[str, ...] = ("seed-script",)
#: 双口径拆分输出键
EDGE_CALIBER_KEYS: Tuple[str, ...] = ("runtime", "demo")

# ── 富集命中率字段（enrichmentMetrics.js）────────────────────────────────────
ENRICHMENT_FIELDS: Tuple[str, ...] = ("calls", "hits", "rate", "total_cost")

# ── 失败计数器口径（busFailures.js）──────────────────────────────────────────
#: 记录返回键；get 聚合为 {kind: count} 字典
FAILURE_COUNTER_RETURN_KEYS: Tuple[str, ...] = ("kind", "count")

# ── 判据自检（机器可读，gen_capability_manifest VERIFY 语义）─────────────────
OBSERVABILITY_INVARIANTS: Tuple[str, ...] = (
    "O1_no_attempt_null_rate",        # 无尝试→null 禁报 100%
    "O2_real_denominator",            # 分母恒真实，空记录不虚造命中率
    "O3_read_fail_not_missing",       # 读失败≠配置缺失，分别留痕不回退全开
    "O4_null_source_not_runtime",     # NULL 来源不计入真实供给；演示边零 DELETE
    "O5_only_true_silence_blocks",    # 只有真静默参与出口闸
    "O6_single_failure_counter",      # 失败计数单一实现防判据分裂
)


class ObservabilityError(KernelError):
    code = "CONTRACT_VIOLATION"
    """observability 判据核参数错误（未知判据类型/非法桶名等）。fail-closed。"""


__all__ = [
    "ATTRIBUTION_CROSS_CATEGORIES", "ATTRIBUTION_BENIGN",
    "ACCURACY_BUCKETS", "ACCURACY_ACCURATE_FROM", "ACCURACY_INACCURATE_FROM",
    "GATE_METRIC_STATES",
    "NEGATIVE_PREDICATE_TYPES", "EXPORT_GATE_BLOCKING_TYPES",
    "DEMO_EDGE_SOURCES_DEFAULT", "EDGE_CALIBER_KEYS",
    "ENRICHMENT_FIELDS", "FAILURE_COUNTER_RETURN_KEYS",
    "OBSERVABILITY_INVARIANTS", "ObservabilityError",
]
