"""编排层 —— 任务状态机 + 派发参数 + 智能体注册闸（SKILL #6 机制层，demo 搬迁）。"""
from .agent_registry import (
    MIN_SUCCESS_LEN,
    AgentRegistry,
    AgentRegistryError,
    AgentSpec,
)
from .idem import IDEM_PREFIX, derive_idem_key, nightly_idem_key
from .dispatch_cfg import (
    DISPATCH_CFG_DEFAULTS,
    DISPATCH_CFG_SECTION,
    dispatch_cfg_report,
    read_dispatch_cfg,
)
from .state_machine import (
    ALLOWED_TRANSITIONS,
    BLOCK_KINDS,
    FAILURE_LIMIT,
    MAX_REDO,
    SYSTEM_ANCHOR_PREFIX,
    SYSTEM_TASK_KINDS,
    TASK_KINDS,
    TASK_STATES,
    TERMINAL_STATES,
    TaskStateError,
    ZOMBIE_STALE_SECONDS,
    assert_anchor,
    assert_block_kind,
    assert_reset,
    assert_result_ref,
    assert_state,
    assert_transition,
    fold_history,
    is_stuck,
    is_terminal,
    summarize,
    system_anchor,
)
from .subagent import SubagentDescriptor, SubagentPool
from .agent_loop import AgentLoop
from .loop_guard import LoopGuard, StepVerdict

__all__ = [
    "MIN_SUCCESS_LEN", "AgentRegistry", "AgentRegistryError", "AgentSpec",
    "IDEM_PREFIX", "derive_idem_key", "nightly_idem_key",
    "DISPATCH_CFG_DEFAULTS", "DISPATCH_CFG_SECTION",
    "dispatch_cfg_report", "read_dispatch_cfg",
    "ALLOWED_TRANSITIONS", "BLOCK_KINDS", "FAILURE_LIMIT", "MAX_REDO",
    "SYSTEM_ANCHOR_PREFIX", "SYSTEM_TASK_KINDS", "TASK_KINDS", "TASK_STATES",
    "TERMINAL_STATES", "TaskStateError", "ZOMBIE_STALE_SECONDS",
    "assert_anchor", "assert_block_kind", "assert_reset", "assert_result_ref",
    "assert_state", "assert_transition", "fold_history", "is_stuck",
    "is_terminal", "summarize", "system_anchor",
    "SubagentDescriptor", "SubagentPool", "AgentLoop", "LoopGuard", "StepVerdict",
]
