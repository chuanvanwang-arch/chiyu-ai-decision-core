"""知识升格与回流管道契约 —— L0 单一事实源（零第三方依赖、零 IO、零领域字面量）。

上迁源（GAP-9，Batch-2b，2026-10-14）：APS ``platform/promotion.py``（D→K /
M→K 升格闸门与漂移审计）+ ``platform/reflux.py``（K-M-D 单一回流管道，四通道）。

**机制上迁、域值留消费方**：
    · 上迁：升格三态闸门（白名单→证据数→一致性）/ 产物形态红线
      （PROMOTED 标记 + 恒 PENDING）/ 覆盖守卫（calibrated 不可覆盖）/
      漂移判定（不可比 ⇒ 告警）/ 回流四通道语义 / 未知 kind 拒绝 /
      处方恒 PENDING / 后见之明 AND 条件与窗口判据；
    · 留 APS：``PRESCRIBABLE`` 域键（reschedule.*）/ ``configs/*.json`` 域配置 /
      ``TRUTH_FIELD_BY_KEY`` 域真值表 / ``aps.*`` 事件名 / store·bus 耦合。

⛔ 处方**状态机**的单一事实源在 ``contract/evolution.py``（PRESCRIPTION_*）；
    本层只持回流侧词汇，``PRESCRIPTION_PENDING`` 与之一致性由守卫测试对拍。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Tuple

__all__ = [
    # 升格闸门
    "PROMOTION_STATUSES", "PROMOTED", "BLOCKED", "REJECTED",
    "PROMOTION_STAGE", "PARAMS_SOURCE_PROMOTED", "PROTECTED_STAGES",
    "DEFAULT_MIN_EVIDENCE", "DEFAULT_MIN_CONSISTENCY", "TRUTH_TOLERANCE",
    "PROMOTION_INVARIANTS",
    # 回流管道
    "REFLUX_CHANNELS", "REFLUX_KINDS", "KIND_TO_CHANNEL", "DEFAULT_CHANNEL",
    "PRESCRIPTION_PENDING", "DEFAULT_REFLUX_POLICY",
    "REFLUX_INVARIANTS",
    # 后见之明
    "HINDSIGHT_STATUSES", "WINDOW_STATUSES",
    # 错误
    "RefluxChannelError", "PromotionPolicyError",
]

# ── 升格三态（裁决顺序：白名单 → 证据数 → 一致性）────────────────────
PROMOTION_STATUSES: Tuple[str, ...] = ("promoted", "blocked", "rejected")
PROMOTED: str = "promoted"    # 达标（产物恒 PENDING，第 3 闸 HITL 在外层把守）
BLOCKED: str = "blocked"      # 证据不足/自相矛盾（**不发射事件**：非治理动作）
REJECTED: str = "rejected"    # 白名单外（直接拒绝，不降级为待人工判断）

# ── 升格产物形态红线（绝不写 CALIBRATED）─────────────────────────────
#: ``promoted`` = AI 由证据归纳、尚未标定；``calibrated`` = 已标定（受保护）。
PROMOTION_STAGE: str = "promoted"
#: 升格产物参数来源标记——**唯一合法值**。写成 CALIBRATED 即用 AI 归纳值
#: 冒充已标定规则 = 知识污染且无法事后审计。
PARAMS_SOURCE_PROMOTED: str = "PROMOTED"
#: 升格产物**不得覆盖**的阶段（AI 归纳值覆盖已标定知识不可逆）。
PROTECTED_STAGES: Tuple[str, ...] = ("calibrated",)

# ── 升格默认门槛（消费方可经 policy 覆盖）───────────────────────────
DEFAULT_MIN_EVIDENCE: int = 3        # 最少证据条数（孤证不得上升为知识）
DEFAULT_MIN_CONSISTENCY: float = 0.7  # 众数占比门槛（低于此值 = 证据自相矛盾）
#: 浮点真值比较容差（直接 ``==`` 会因精度误报漂移）。
TRUTH_TOLERANCE: float = 1e-6

# ── 回流四通道（C1/C2/C3/C3′）───────────────────────────────────────
REFLUX_CHANNELS: Tuple[str, ...] = ("c1", "c2", "c3", "c3p")
#: 复盘事实 kind 闭集（未知 kind ⇒ 拒绝，禁静默丢弃）。
#: 【D5 裁定登记·2026-10-14，CRM 为源仓】本闭集是**最小核闭集**；CRM C4
#: （knowledge_particles→KNOWLEDGE 粒子回写，租户级知识）为消费方扩展通道，
#: 留 CRM 自有路由层承载，不入基座；路由键形态差异（CRM 按 payload 字段路由 /
#: 基座按 kind 路由）由消费方适配层承载，四通道语义一一对应已对拍钉死。
REFLUX_KINDS: Tuple[str, ...] = ("fact", "falsified", "config_patch", "hindsight")
#: kind → 通道单一映射。
KIND_TO_CHANNEL: Tuple[Tuple[str, str], ...] = (
    ("fact", "c1"),                # 事实 append-only
    ("falsified", "c2"),           # 反面先例，不覆盖既有先例
    ("config_patch", "c3"),        # 配置处方（白名单 + 恒 PENDING）
    ("hindsight", "c3p"),          # 记忆影响，原记忆不动
)
#: 处方 kind 未登记时的默认通道：**建议通道**（永远不会被自动 apply）。
DEFAULT_CHANNEL: str = "c3p"
#: 处方恒待批（与 contract/evolution.PRESCRIPTION_STATES 的 "pending" 同值）。
PRESCRIPTION_PENDING: str = "pending"
#: 回流策略默认阈值（缺配置/键非法时逐键回落至此）。
DEFAULT_REFLUX_POLICY: Tuple[Tuple[str, float], ...] = (
    ("threshold", 0.3),      # 单决策偏差阈值
    ("rate_alarm", 0.3),     # 窗口偏差率告警线
    ("window_days", 90.0),   # 统计窗口（天）
)

# ── 后见之明状态闭集 ────────────────────────────────────────────────
HINDSIGHT_STATUSES: Tuple[str, ...] = (
    "checked", "no_baseline", "scope_rejected", "below_window_alarm",
)
#: 窗口状态：``no_data`` ≠ healthy（没数据不是运行良好）。
WINDOW_STATUSES: Tuple[str, ...] = ("no_data", "stagnant", "alarm", "healthy")

# ── 不变式（每条均有守卫测试，不是注释）─────────────────────────────
PROMOTION_INVARIANTS: Tuple[str, ...] = (
    "whitelist_outside_rejected",   # 白名单外直接拒绝，不降级待人工
    "insufficient_evidence_blocked",  # 孤证不得上升为知识
    "inconsistent_evidence_blocked",  # 证据矛盾不得上升为知识
    "promoted_always_pending",      # 升格产物恒 PENDING（HITL 在外层）
    "calibrated_never_overwritten",  # 已标定知识不可被 AI 归纳值覆盖
    "drift_incomparable_alerts",    # 真值不可比 ⇒ 告警，不静默吞
)

REFLUX_INVARIANTS: Tuple[str, ...] = (
    "unknown_kind_rejected",        # 未知回流 kind ⇒ 抛错（禁静默丢弃）
    "prescribe_whitelist_only",     # 仅白名单键可出方，集合外直接拒绝
    "prescribe_always_pending",     # 处方恒 PENDING，绝不自动 apply
    "empty_rationale_rejected",     # 无依据不得出方
    "hindsight_and_condition",      # 单条超阈 **且** 窗口告警才出方（AND 非 OR）
    "every_check_recorded",         # 每次校验都留痕（无论是否触发）
    "no_data_is_not_healthy",       # 空窗口 ≠ 健康（防回流指标假绿）
    "stagnant_stops_prescribing",   # 空转（有偏差零批准）时停止堆处方
    "default_channel_is_suggestion",  # 未登记 kind 默认建议通道
)


class RefluxChannelError(KernelError):
    code = "CONTRACT_VIOLATION"
    """未知回流 kind（允许 fact/falsified/config_patch/hindsight）。"""


class PromotionPolicyError(KernelError):
    code = "CONTRACT_VIOLATION"
    """升格/回流策略配置非法（如 promotable_keys 非序列）。"""
