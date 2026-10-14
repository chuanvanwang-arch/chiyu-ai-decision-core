"""决策脊柱审批闸（WS3 + B3 三态）—— 硬约束先于置信度（A 红线优先 / 反馈闭环金律26）。

⛔ 与 `chiyu_kernel.interaction.ApprovalGate` 是**两个不同层**，职责不重叠、可组合：
   - 本模块 `DecisionApprovalGate`：决策**落库前**的审批裁定（红线/置信度 ⇒ 自动放行 or 转人工）。
   - `interaction.ApprovalGate`：工具**执行前**的人工确认（高危险工具 HITL）。
   命名加 `Decision` 前缀，避免门面与 interaction 同名符号静默覆盖（同 `vector_*` 前缀纪律）。
   组合方式：本闸 `requires_human=True` ⇒ 消费方再走 `interaction.ApprovalGate` 做真人确认。

⛔ B3 三态（方案 Z，2026-10-09）：裁定从两态升三态。
   此前 `requires_human=True`（等人批）与 `redline`（硬拒）共用 `approved=False`，
   脊柱只能一律记 `approval_rejected` —— 「待人工审批」被记成「已驳回」（错值），
   且消费方无法从结果区分"该去催人"还是"该改方案"。
   兼容性：旧消费方读 `.approved` 仍工作（PENDING/REJECTED 下均为 False）；
   `DecisionPassThroughGate` 默认仍 APPROVED（未注入闸的既有消费方零影响）；
   **红线命中恒 REJECTED，不因 pending 豁免**（A 红线优先）。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, Tuple


class DecisionVerdictState(str, Enum):
    """审批裁定三态（B3 方案 Z）。

    - `APPROVED`：可自动落库（脊柱走 persister）；
    - `REJECTED`：硬拒（红线命中），**不可**转 pending、不可自动豁免；
    - `PENDING`：待人工审批（判据缺失 / 未达自主阈值），不落正向边、审计留 `approval_pending`。
    """

    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


@dataclass(frozen=True)
class DecisionApprovalVerdict:
    """审批裁定（三态）。``approved`` / ``pending`` 为派生属性（旧消费方读 `.approved` 不破）。"""

    state: DecisionVerdictState = DecisionVerdictState.APPROVED
    reason: str = ""
    requires_human: bool = False

    @property
    def approved(self) -> bool:
        """兼容字段：仅 APPROVED 为真（旧两态消费方读此属性不破）。"""
        return self.state is DecisionVerdictState.APPROVED

    @property
    def pending(self) -> bool:
        """兼容字段：PENDING 为真（供消费方区分"待人工"与"已驳回"）。"""
        return self.state is DecisionVerdictState.PENDING

    @property
    def rejected(self) -> bool:
        """兼容字段：REJECTED 为真。"""
        return self.state is DecisionVerdictState.REJECTED


class DecisionApprovalGate(Protocol):
    """决策脊柱 S4→S5 审批闸协议（鸭子类型，消费方可注入自有实现）。"""

    def decide(self, *, decision_id: str, confidence: float, redline_hit: bool,
               redline_reasons: Tuple[str, ...], autonomous: bool,
               rubric_missing: Tuple[str, ...], elements_missing: Tuple[str, ...],
               threshold: float) -> DecisionApprovalVerdict:
        ...


@dataclass
class RedlinePriorityGate:
    """默认审批闸 —— embody A 红线优先 + 硬约束先于置信度（金律26）。

    裁定顺序（不可重排，顺序即语义）：
      1. 红线命中 → **REJECTED**（不因置信度高而豁免，也不得降级为 pending）。
      2. 判据缺失（九尺子/八要素）→ **PENDING**（转人工确认，不自动放行）。
      3. ``autonomous`` 为真 ⇒ APPROVED；否则 PENDING（未达自主阈值，等人批）。
    """

    def decide(self, *, decision_id: str, confidence: float, redline_hit: bool,
               redline_reasons: Tuple[str, ...], autonomous: bool,
               rubric_missing: Tuple[str, ...], elements_missing: Tuple[str, ...],
               threshold: float) -> DecisionApprovalVerdict:
        # 1. 硬约束先于置信度：红线命中立即硬拒，高置信度不豁免（A 红线优先 / 金律26）
        if redline_hit:
            reason = "红线命中（硬约束优先于置信度）"
            if redline_reasons:
                reason += "：" + "；".join(redline_reasons)
            return DecisionApprovalVerdict(
                state=DecisionVerdictState.REJECTED, reason=reason, requires_human=True)
        # 2. 判据缺失 → 待人工确认（B3：等人批 ≠ 已驳回）
        missing = tuple(list(rubric_missing) + list(elements_missing))
        if missing:
            return DecisionApprovalVerdict(
                state=DecisionVerdictState.PENDING,
                reason="判据缺失需人工确认：" + "、".join(missing),
                requires_human=True)
        # 3. autonomous 为真（红线未命中且置信度达门槛）⇒ 自动放行；否则待人工
        if autonomous:
            return DecisionApprovalVerdict(
                state=DecisionVerdictState.APPROVED, reason="置信度达标，自动放行")
        return DecisionApprovalVerdict(
            state=DecisionVerdictState.PENDING,
            reason=f"未达自主放行条件（置信度 {confidence:.3f}），需人工确认",
            requires_human=True)


@dataclass
class DecisionPassThroughGate:
    """审批闸透传（默认）：不拦截，等价于未注入审批闸（保留 run_spine 既有行为）。"""

    def decide(self, *, decision_id: str, confidence: float, redline_hit: bool,
               redline_reasons: Tuple[str, ...], autonomous: bool,
               rubric_missing: Tuple[str, ...], elements_missing: Tuple[str, ...],
               threshold: float) -> DecisionApprovalVerdict:
        return DecisionApprovalVerdict(
            state=DecisionVerdictState.APPROVED, reason="无审批闸（透传）")


# ── HITL 证据 / 状态机断言（三支柱批次二 D3 实现，2026-10-13）──────────────
# 「无 approve 不可生效」的基座结构保证入口（E9 同族：经 approval sanctioned 面
# 可达，消费方免摸内部模块路径）。常量源自 contract（L0 单一事实源）。
from .hitl import (  # noqa: F401
    ApprovalTransitionError, HITLEvidenceError, assert_hitl_evidence,
    assert_transition, missing_hitl_evidence_fields,
)

# ── 审批聚合裁决核（Batch-1b-2 approval_engine；对拍 CRM 会签/或签/链签）────
from .engine import (  # noqa: F401
    aggregate, chain_for_tier, resolve_tier,
)

__all__ = [
    "DecisionVerdictState", "DecisionApprovalVerdict", "DecisionApprovalGate",
    "RedlinePriorityGate", "DecisionPassThroughGate",
    # HITL 证据 / 状态机断言（三支柱批次二 D3 实现）
    "HITLEvidenceError", "ApprovalTransitionError",
    "missing_hitl_evidence_fields", "assert_hitl_evidence", "assert_transition",
    # approval_engine（Batch-1b-2）
    "resolve_tier", "chain_for_tier", "aggregate",
]
