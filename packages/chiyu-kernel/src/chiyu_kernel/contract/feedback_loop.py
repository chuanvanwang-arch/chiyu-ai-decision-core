"""反馈闭环契约 —— L0 单一事实源（零第三方依赖、零 IO、零领域字面量）。

上迁源（GAP-6，Batch-2b，2026-10-14）：APS ``platform/feedback_loop.py``
（design #9 ai-feedback-loop 补强层，回流边 ⑤⑥⑦⑧）。

**机制上迁、域值留消费方**（APS 盘点 §〇 裁决书口径）：
    · 上迁：指标模板要素面 / 双口径观测 / 三档加权评估 / 拒绝出方守卫 / HITL 校准闸
      —— 与 APS 排程域无关的机制与不变式；
    · 留 APS：``aps.*`` 事件名 / ``metric_template``·``calibration_candidate`` DDL /
      ``bus.emit``·``store.append_timeseries`` 耦合 / 钢卷实测等域指标名。

⛔ 本层只有**词汇与不变式**，没有 IO：落库、事件发射、表装配一律在消费方；
   内核提供的对应机制（``chiyu_kernel.feedback``）全部为纯函数。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Tuple

__all__ = [
    "METRIC_TEMPLATE_FIELDS", "METRIC_TEMPLATE_REQUIRED",
    "METRIC_SCOPES", "RUNTIME_SCOPE", "SEED_SCOPE",
    "EVAL_VERDICT_KINDS", "EVAL_VERDICT_PASS", "EVAL_VERDICT_REVIEW",
    "EVAL_VERDICT_REJECT", "EVAL_VERDICT_UNDECIDABLE",
    "CALIBRATION_STATUSES", "CALIBRATION_PENDING", "CALIBRATION_APPROVED",
    "CALIBRATION_BLOCKED",
    "CALIBRATION_MIN_SAMPLE", "CALIBRATION_MIN_COVERAGE",
    "DEFAULT_AUTO_PASS", "DEFAULT_HUMAN_REVIEW",
    "FEEDBACK_INVARIANTS",
    "FeedbackTemplateError", "CalibrationStateError", "ExpressionError",
]

# ── 指标模板字段面（design §3.2 七要素 + 归属/技能/调整动作）─────────────
#: 模板全字段面（落库/传输用）。
METRIC_TEMPLATE_FIELDS: Tuple[str, ...] = (
    "metric_template_id", "loop", "name", "type", "direction", "formula",
    "target", "alert", "sources", "owner_agent", "evaluator_skill",
    "adjust_actions",
)
#: 必填面（B1 资格断言）：缺一即拒登记——"先判能不能判"再出结论。
METRIC_TEMPLATE_REQUIRED: Tuple[str, ...] = (
    "name", "loop", "type", "direction", "formula", "target", "alert",
    "sources", "owner_agent", "evaluator_skill", "adjust_actions",
)

# ── 双口径观测（B5）───────────────────────────────────────────────────
#: 指标口径闭集：runtime=运行真值（唯一可判绿口径）；seed=种子/演示（禁混入）。
METRIC_SCOPES: Tuple[str, ...] = ("runtime", "seed")
RUNTIME_SCOPE: str = "runtime"
SEED_SCOPE: str = "seed"

# ── 评估结论闭集（B2 三档 + B7 不可判三态）────────────────────────────
#: ``undecidable`` 是独立第三态，**绝不并入通过**——资格缺失时诚实标注"不可判"。
EVAL_VERDICT_KINDS: Tuple[str, ...] = ("pass", "review", "reject", "undecidable")
EVAL_VERDICT_PASS: str = "pass"
EVAL_VERDICT_REVIEW: str = "review"
EVAL_VERDICT_REJECT: str = "reject"
EVAL_VERDICT_UNDECIDABLE: str = "undecidable"

# ── 校准候选状态（B3/B4）────────────────────────────────────────────
#: pending=待 HITL 裁决；approved=已批准（**生效属治理动作，另行执行**）；
#: blocked=拒绝出方守卫拦截（样本/覆盖率不足，不发射事件）；rejected=被拒。
CALIBRATION_STATUSES: Tuple[str, ...] = (
    "pending", "approved", "rejected", "blocked",
)
CALIBRATION_PENDING: str = "pending"
CALIBRATION_APPROVED: str = "approved"
CALIBRATION_BLOCKED: str = "blocked"

# ── 拒绝出方守卫默认门槛（B4：先判"能不能出"，再判"出什么"）────────────
# ⛔ 命名带 CALIBRATION_ 前缀：门面已有 vector 层 DEFAULT_MIN_COVERAGE（=0.80，
#   嵌入覆盖率口径），裸名重名即语义静默冲突（同名不同值）。
CALIBRATION_MIN_SAMPLE: int = 30
CALIBRATION_MIN_COVERAGE: float = 0.6

# ── 评估三档默认阈值（B2）──────────────────────────────────────────
DEFAULT_AUTO_PASS: int = 90    # ≥ 此值 ⇒ pass
DEFAULT_HUMAN_REVIEW: int = 70  # ≥ 此值 ⇒ review；否则 reject

# ── 不变式（每条均有守卫测试，不是注释）─────────────────────────────
FEEDBACK_INVARIANTS: Tuple[str, ...] = (
    "template_incomplete_rejected",  # B1：要素缺一即拒登记（资格断言）
    "scope_dual_counting",           # B5：运行指标只认 runtime 口径，禁混 seed
    "undecidable_never_pass",        # B7：变量缺失 ⇒ undecidable，绝不并入通过
    "blocked_never_emits",           # B4：守卫拦截的候选不发射治理事件
    "hitl_only_to_approved",         # B3：校准只到 approved，绝不自动生效
    "repeat_adjudication_rejected",  # 已裁决候选不得重复裁决
)


class FeedbackTemplateError(KernelError):
    code = "CONTRACT_VIOLATION"
    """指标模板必填要素缺失（B1 资格断言失败）——拒登记，不静默放行。"""


class CalibrationStateError(KernelError):
    code = "CONTRACT_VIOLATION"
    """校准候选状态跃迁非法（如对非 pending 候选重复裁决）。"""


class ExpressionError(KernelError):
    code = "CONTRACT_VIOLATION"
    """评估表达式非法或不在安全子集内（禁任意代码执行）。"""
