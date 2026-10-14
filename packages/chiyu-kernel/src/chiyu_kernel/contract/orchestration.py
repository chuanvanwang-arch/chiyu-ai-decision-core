"""编排契约 —— L0 词汇与不变式（GAP-5，Batch-2a，2026-10-14）。

定位：多智能体编排（`chiyu_kernel/orchestration/`）的**词汇单一事实源**：
任务状态集 / 转换表 / 阻塞三分类 / 任务种类 / 熔断与重试参数 / 系统锚前缀 /
Agent 契约字段面。此前 orchestration 只有 impl 无 sanctioned contract，
消费方（APS `aps/agents/*`+`orchestrator.py`，enterprise `scenario/*`）
被迫 import 内部路径（APS 盘点 §四 GAP-5）。

⛔ 本层零第三方依赖、零 IO、零领域字面量。impl（state_machine/agent_registry）
   改为从本模块导入这些闭集 —— 同名符号是**同一对象**，不存在双份漂移；
   校验逻辑（assert_transition/assert_anchor/…）仍留 impl（机制层）。

状态集（最小完备集 + 质量闸门；与 SKILL #6 第 2 轮判据逐项对应）：

    ready → running → done ─(评估 reject)→ reviewing → ready(带评估意见) → running
                    │  └→ failed ─(重试)→ ready
                    │        └→ (连续失败 ≥ FAILURE_LIMIT) → blocked(circuit_break)
                    └→ (进程死) → zombie → reset → ready
    blocked(block_kind) → ready   # approval=等人批 / circuit_break=熔断 / manual=人工挂起
"""
from __future__ import annotations

from typing import Tuple

# ── 状态集（最小完备集 + 质量闸门）────────────────────────────────────
TASK_STATES: Tuple[str, ...] = (
    "ready",      # 可派发，等待 worker
    "running",    # worker 执行中
    "done",       # 完成（终态；质量闸门下为「待评估」）
    "failed",     # 失败可重试（终态）
    "reviewing",  # 质量闸门：评估 reject → 带反馈重跑
    "blocked",    # 阻塞（block_kind 区分审批等待 / 熔断 / 人工）
    "zombie",     # running 但 worker 已死
)
TERMINAL_STATES: Tuple[str, ...] = ("done", "failed")

# block_kind 三分类：**审批等待不是系统故障**，故必须与 circuit_break 分开。
BLOCK_KINDS: Tuple[str, ...] = ("approval", "circuit_break", "manual")

# 任务种类（机制级闭集；系统任务用系统锚，业务任务必须锚真实决策）。
TASK_KINDS: Tuple[str, ...] = (
    "analysis", "retro", "sweep", "approval", "governance")
SYSTEM_TASK_KINDS: Tuple[str, ...] = ("retro", "sweep")

# ── 参数（SKILL #6 默认值，写死可复核）────────────────────────────────
FAILURE_LIMIT = 2            # 连续失败 ≥ 2 即熔断（实践心得 1）
MAX_REDO = 3                 # 质量闸门重跑 ≥ 3 次升级人工（防死循环）
ZOMBIE_STALE_SECONDS = 300   # running 心跳超过 5 min 且进程不可判活 ⇒ zombie
SYSTEM_ANCHOR_PREFIX = "sys-"  # 系统锚前缀（显式标记「非业务决策」）

# ── 转换表（唯一事实源；`reset` 不在表内，走 assert_reset）────────────
ALLOWED_TRANSITIONS = {
    "ready":     frozenset({"running", "blocked"}),
    "running":   frozenset({"done", "failed", "blocked", "zombie"}),
    "done":      frozenset({"reviewing", "ready"}),   # 评估 reject → 回滚
    "failed":    frozenset({"ready", "blocked"}),     # 重试 / 熔断
    "reviewing": frozenset({"ready", "blocked"}),     # 重跑 / redo 超限升级人工
    "blocked":   frozenset({"ready"}),                # unblock（不改状态集）
    "zombie":    frozenset({"ready"}),                # reset
}

# ── Agent 契约字段面（agent_registry.AgentSpec；注册期拒绝的判据源）────
AGENT_SPEC_FIELDS: Tuple[str, ...] = (
    "key", "contract_task_id", "skills", "memory", "knowledge_scope", "success")
#: 必填字段（缺一即拒绝注册：无成功标准的 agent 跑完了也无法判定成败）。
AGENT_SPEC_REQUIRED: Tuple[str, ...] = (
    "key", "contract_task_id", "skills", "memory", "success")
#: success 判定式最短长度（短于它视为形容词而非判据，audit 告警）。
MIN_SUCCESS_LEN = 8

# ── 不变式（有守卫测试，不是注释）────────────────────────────────────
ORCHESTRATION_INVARIANTS: Tuple[str, ...] = (
    "blocked_requires_block_kind",     # 进 blocked 必须说为什么（不可排查=拒）
    "decision_anchor_required",        # 无决策不写：状态转换必须带非空 decision_id
    "system_anchor_kind_consistent",   # 系统任务用 sys- 锚、业务任务禁 sys- 锚
    "terminal_requires_result_ref",    # 终态必须带结果引用（只写状态不算落盘）
    "approval_block_not_failure",      # blocked(approval) 不计 failed、不进熔断
    "circuit_count_kept_on_retry",     # 重试保留熔断计数，仅成功/显式复位清零
)

__all__ = [
    "TASK_STATES", "TERMINAL_STATES", "BLOCK_KINDS",
    "TASK_KINDS", "SYSTEM_TASK_KINDS",
    "FAILURE_LIMIT", "MAX_REDO", "ZOMBIE_STALE_SECONDS", "SYSTEM_ANCHOR_PREFIX",
    "ALLOWED_TRANSITIONS",
    "AGENT_SPEC_FIELDS", "AGENT_SPEC_REQUIRED", "MIN_SUCCESS_LEN",
    "ORCHESTRATION_INVARIANTS",
]
