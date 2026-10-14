"""GAP-5 编排契约 + 状态机完整性守卫（Batch-2a，2026-10-14）。

判据面：
  · impl 与契约**同一对象**（单一事实源落地）；
  · 转换表覆盖全部状态、目标不越界（删状态/加非法边即红）；
  · 禁静默中间态：任一状态沿转换表可达终态；
  · blocked 必须带 block_kind / 非 blocked 禁带（行为判据）；
  · 决策锚与任务种类一致性（业务禁 sys- 锚、系统必须 sys- 锚）；
  · AgentSpec 字段面与契约一致。
"""
from __future__ import annotations

import pytest
from dataclasses import fields

from chiyu_kernel.contract import orchestration as orch_contract
from chiyu_kernel.contract.orchestration import (
    ALLOWED_TRANSITIONS,
    BLOCK_KINDS,
    SYSTEM_ANCHOR_PREFIX,
    SYSTEM_TASK_KINDS,
    TASK_KINDS,
    TASK_STATES,
    TERMINAL_STATES,
)
from chiyu_kernel.orchestration import agent_registry, state_machine
from chiyu_kernel.orchestration.agent_registry import AgentSpec


def test_impl_sources_from_contract_same_object():
    assert state_machine.TASK_STATES is TASK_STATES
    assert state_machine.TERMINAL_STATES is TERMINAL_STATES
    assert state_machine.ALLOWED_TRANSITIONS is ALLOWED_TRANSITIONS
    assert state_machine.SYSTEM_TASK_KINDS is SYSTEM_TASK_KINDS
    assert state_machine.FAILURE_LIMIT is orch_contract.FAILURE_LIMIT
    assert agent_registry.MIN_SUCCESS_LEN is orch_contract.MIN_SUCCESS_LEN


def test_transition_table_covers_every_state():
    assert set(ALLOWED_TRANSITIONS) == set(TASK_STATES)
    for frm, tos in ALLOWED_TRANSITIONS.items():
        assert tos <= set(TASK_STATES), f"{frm} 的转换目标越界：{tos - set(TASK_STATES)}"


def test_every_non_terminal_state_can_reach_terminal():
    # 禁静默中间态（反模式 15）：任一状态必须能走到终态
    for start in TASK_STATES:
        seen: set = set()
        stack = [start]
        while stack:
            cur = stack.pop()
            for nxt in ALLOWED_TRANSITIONS.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        assert seen & set(TERMINAL_STATES), f"{start} 无法到达终态"


def test_block_kinds_closed_and_system_kinds_subset():
    assert set(BLOCK_KINDS) == {"approval", "circuit_break", "manual"}
    assert set(SYSTEM_TASK_KINDS) <= set(TASK_KINDS)


def test_blocked_requires_block_kind():
    with pytest.raises(state_machine.TaskStateError, match="block_kind"):
        state_machine.assert_transition("ready", "blocked")          # 缺 kind ⇒ 拒
    state_machine.assert_transition("ready", "blocked", block_kind="approval")
    with pytest.raises(state_machine.TaskStateError):
        state_machine.assert_transition("running", "done", block_kind="approval")


def test_assert_anchor_enforces_kind_consistency():
    with pytest.raises(state_machine.TaskStateError):
        state_machine.assert_anchor(None, kind="analysis")
    with pytest.raises(state_machine.TaskStateError):
        state_machine.assert_anchor(f"{SYSTEM_ANCHOR_PREFIX}x", kind="analysis")
    with pytest.raises(state_machine.TaskStateError):
        state_machine.assert_anchor("d-1", kind="retro")
    assert state_machine.assert_anchor(
        f"{SYSTEM_ANCHOR_PREFIX}retro", kind="retro") == f"{SYSTEM_ANCHOR_PREFIX}retro"


def test_agent_spec_fields_match_registry_dataclass():
    assert {f.name for f in fields(AgentSpec)} == set(orch_contract.AGENT_SPEC_FIELDS)
    assert set(orch_contract.AGENT_SPEC_REQUIRED) == {
        "key", "contract_task_id", "skills", "memory", "success"}
