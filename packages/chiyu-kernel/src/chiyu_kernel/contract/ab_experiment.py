"""A/B 实验收口契约（Batch-1b-4 ab_experiment；上迁自 CRM decision/routingReview.js + context/routingExperiment.js）。

⛔ L0 纪律：零第三方依赖、零 IO、零领域字面量（场景/轨道/黑名单 ⇒ 消费方）。

三取二判据（CRM routingReview §7.1）：ΔQ 质量 / ΔO 业务结果 / ΔR 人机覆写率
至少两项显著且符号一致才出结论；样本不足 ⇒ 显式 insufficient_evidence **不硬凑**。
⛔ 收口只产 PENDING 处方、绝不自动写配置（CRM 红线：人工批准 + 第 0 闸后才 apply）。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Tuple

# ── 实验臂闭集（on=注入候选 / off=对照原样）────────────────────────────
AB_ARMS: Tuple[str, ...] = ("on", "off")

# ── 判决闭集（方向以 ΔQ 为准；oSig 同号条件保证符号一致）────────────────
AB_VERDICTS: Tuple[str, ...] = ("prefer_on", "prefer_off", "insufficient")

# ── 判据阈值出厂默认（CRM DEFAULT_JUDGE_CFG 逐值同源；config 覆盖留消费方）──
#: 质量分显著阈值：|ΔQ| ≥ q_eps 记显著。
AB_Q_EPS_DEFAULT = 0.05
#: 业务结果显著阈值：|ΔO| ≥ o_eps 且与 ΔQ 同号记显著。
AB_O_EPS_DEFAULT = 0.10
#: 覆写率改善阈值：ΔR ≤ -r_eps（下降才有利）记显著。
AB_R_EPS_DEFAULT = 0.05
#: 单臂最小样本：任一臂 n < min_arm_sample ⇒ insufficient_evidence（不硬凑）。
AB_MIN_ARM_SAMPLE_DEFAULT = 20

AB_INVARIANTS: Tuple[str, ...] = (
    "insufficient_evidence_no_conclusion",   # 样本不足显式判 insufficient，禁硬凑结论
    "three_of_two_significant_and_consistent",  # ≥2 项显著且符号一致才出方向结论
    "override_drop_only_positive",           # ΔR 只认下降为有利（上升再大也不是显著）
    "close_produces_pending_only",           # 收口只产 PENDING 处方，绝不自动写配置
    "preferred_equals_baseline_no_patch",    # 偏好臂==配置原值 ⇒ 维持现状不出处方
    "next_arm_appends_not_deletes",          # 证据不足排反向臂补对照：append-only 新开一期，禁删原行
    "apply_arm_fail_open_identity",          # 实验信息非法 ⇒ 轨道原样返回（装配不因实验读失败而炸）
)


class AbExperimentError(KernelError):
    code = "CONTRACT_VIOLATION"
    """A/B 判据输入非法（未知臂 / 非法阈值形态）。"""


__all__ = [
    "AB_ARMS", "AB_VERDICTS",
    "AB_Q_EPS_DEFAULT", "AB_O_EPS_DEFAULT", "AB_R_EPS_DEFAULT",
    "AB_MIN_ARM_SAMPLE_DEFAULT", "AB_INVARIANTS", "AbExperimentError",
]
