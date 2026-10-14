"""任务状态机守卫 —— 四条**不可回退**的约定必须是可执行判据，不是注释。

⛔ 本文件只测 `chiyu_kernel.orchestration.state_machine` 的**纯逻辑**（状态集 / 转换表 /
   校验 / 投影）。持久化层（`store.TaskStore`）与派发器**未迁移进内核** ⇒ 不在此伪造
   与之相关的绿（"给未实现的代码写测试 = 假绿"，本项目已记录该族缺陷）。

四条约定（`state_machine.py` docstring）逐条对应下方用例：
    ① 审批闸门 ≠ 故障      → test_approval_gate_is_not_a_failure
    ② 无决策不写            → test_no_decision_no_write
    ③ 禁静默中间态          → test_no_silent_intermediate_state
    ④ 熔断计数只在成功/复位清零 → test_retry_path_keeps_counter_semantics
"""
from __future__ import annotations

import pytest

from chiyu_kernel.orchestration import state_machine as sm


# ── 状态集与转换表（最小完备集，不增不改）────────────────────────────────
def test_state_set_is_minimal_complete():
    assert sm.TASK_STATES == (
        "ready", "running", "done", "failed", "reviewing", "blocked", "zombie",
    )
    assert sm.TERMINAL_STATES == ("done", "failed")
    for s in sm.TERMINAL_STATES:
        assert s in sm.TASK_STATES


def test_transition_table_is_exact():
    """转换表逐项相等 —— 增删任何一条边都必须让本用例红。"""
    assert {k: set(v) for k, v in sm.ALLOWED_TRANSITIONS.items()} == {
        "ready": {"running", "blocked"},
        "running": {"done", "failed", "blocked", "zombie"},
        "done": {"reviewing", "ready"},
        "failed": {"ready", "blocked"},
        "reviewing": {"ready", "blocked"},
        "blocked": {"ready"},
        "zombie": {"ready"},
    }
    assert set(sm.ALLOWED_TRANSITIONS) == set(sm.TASK_STATES)


@pytest.mark.parametrize("frm,to", [
    ("ready", "done"), ("done", "running"), ("blocked", "done"),
    ("zombie", "running"), ("reviewing", "done"), ("failed", "done"),
])
def test_illegal_transition_rejected(frm, to):
    with pytest.raises(sm.TaskStateError, match="非法转换"):
        sm.assert_transition(frm, to)


def test_unknown_state_is_rejected():
    with pytest.raises(sm.TaskStateError, match="未知"):
        sm.assert_state("finished")


def test_negative_control_permissive_table_turns_red(monkeypatch):
    """判别力自证：把表放宽一步，守卫**必须**失去拦截力（否则它没在读表）。"""
    relaxed = dict(sm.ALLOWED_TRANSITIONS)
    relaxed["ready"] = frozenset({"running", "blocked", "done"})
    monkeypatch.setattr(sm, "ALLOWED_TRANSITIONS", relaxed)
    sm.assert_transition("ready", "done")          # 放宽后合法 ⇒ 不抛
    with pytest.raises(sm.TaskStateError):
        sm.assert_transition("done", "running")    # 未放宽的边仍须红


def test_blocked_requires_block_kind():
    with pytest.raises(sm.TaskStateError, match="block_kind"):
        sm.assert_transition("running", "blocked")
    assert sm.assert_block_kind("approval") == "approval"
    with pytest.raises(sm.TaskStateError, match="未知 block_kind"):
        sm.assert_block_kind("paused")


def test_non_blocked_state_must_not_carry_block_kind():
    with pytest.raises(sm.TaskStateError, match="非 blocked 状态"):
        sm.assert_transition("ready", "running", block_kind="approval")


# ── 约定 ①：审批闸门 ≠ 故障 ─────────────────────────────────────────────
def test_approval_gate_is_not_a_failure():
    """`blocked(approval)` 可达、且**不是终态**；三分类必须把审批与熔断分开。"""
    sm.assert_transition("running", "blocked", block_kind="approval")
    assert sm.BLOCK_KINDS == ("approval", "circuit_break", "manual")
    assert "blocked" not in sm.TERMINAL_STATES
    # 审批等待可解除（blocked→ready），无需计入熔断
    sm.assert_transition("blocked", "ready")


# ── 约定 ②：无决策不写 ──────────────────────────────────────────────────
def test_no_decision_no_write():
    with pytest.raises(sm.TaskStateError, match="缺决策锚"):
        sm.assert_anchor("", kind="analysis")
    with pytest.raises(sm.TaskStateError, match="缺决策锚"):
        sm.assert_anchor(None, kind="retro")


def test_anchor_provenance_must_match_task_kind():
    """业务任务不得冒用系统锚；系统任务必须点名 scope（只查"非空"会放过这种坏形状）。"""
    with pytest.raises(sm.TaskStateError, match="不得使用系统锚"):
        sm.assert_anchor("sys-nightly", kind="analysis")
    with pytest.raises(sm.TaskStateError, match="必须用系统锚"):
        sm.assert_anchor("dec-001", kind="retro")
    with pytest.raises(sm.TaskStateError, match="必须用系统锚"):
        sm.assert_anchor("sys-", kind="retro")
    assert sm.assert_anchor("dec-001", kind="analysis") == "dec-001"
    assert sm.assert_anchor("sys-nightly", kind="retro") == "sys-nightly"


def test_system_anchor_constructor_rejects_blank_scope():
    assert sm.system_anchor("nightly") == "sys-nightly"
    with pytest.raises(sm.TaskStateError, match="scope 非法"):
        sm.system_anchor("  ")
    with pytest.raises(sm.TaskStateError, match="scope 非法"):
        sm.system_anchor("a b")


# ── 约定 ③：禁静默中间态 ────────────────────────────────────────────────
def test_no_silent_intermediate_state():
    """`reviewing` 必须能走出去：重跑（→ready）或升级人工（→blocked/manual）。"""
    sm.assert_transition("reviewing", "ready")
    sm.assert_transition("reviewing", "blocked", block_kind="manual")
    assert sm.MAX_REDO >= 1
    assert sm.is_stuck("reviewing", redo_count=sm.MAX_REDO) is True
    assert sm.is_stuck("reviewing", redo_count=sm.MAX_REDO - 1) is False


# ── 约定 ④：重试不清熔断计数（在纯逻辑层可验证的部分）──────────────────
def test_retry_path_keeps_counter_semantics():
    """`failed→ready` 是**重试**路径（表内合法），与 `reset`（任何态→ready）不同语义。

    ⚠ 诚实边界：计数器本身在 `store.py`（未迁移内核）⇒ 本用例只锁"重试路径存在且
    `failed` 不是卡住态（等待重试而非被误判为僵尸）"这两条可判据。
    """
    sm.assert_transition("failed", "ready")
    sm.assert_reset("failed")                       # 显式复位同样可达
    assert sm.is_terminal("failed") is True
    assert sm.is_stuck("failed") is False
    assert sm.FAILURE_LIMIT == 2


# ── 结果引用 / 投影 / 参数自述 ──────────────────────────────────────────
def test_assert_result_ref_requires_non_empty():
    with pytest.raises(sm.TaskStateError, match="result_ref"):
        sm.assert_result_ref("")
    with pytest.raises(sm.TaskStateError, match="result_ref"):
        sm.assert_result_ref(None)
    assert sm.assert_result_ref(" evt-1 ") == "evt-1"


def test_fold_history_is_independent_projection():
    """从转换日志独立重算当前态 —— 给守卫一条与状态表**相互独立**的读路径。"""
    rows = [
        {"to_state": "running", "block_kind": None},
        {"to_state": "failed", "block_kind": None},
        {"to_state": "ready", "block_kind": None},
        {"to_state": "running", "block_kind": None},
    ]
    got = sm.fold_history(rows)
    assert got["state"] == "running" and got["transitions"] == 4
    # ⛔ `terminal_state` 语义 = **曾到过**终态（刻意不随重试清除）。这与 `state`
    #   是两条独立信息：一个 `failed→ready` 重试中的任务，当前态是 running，
    #   但它"曾经终结过"这一事实必须留在投影里（否则外部无法发现"重试掩盖了失败"）。
    assert got["terminal_state"] == "failed"
    term = sm.fold_history(rows + [{"to_state": "done", "block_kind": None}])
    assert term["state"] == "done" and term["terminal_state"] == "done"
    assert sm.fold_history([])["state"] is None
    assert sm.fold_history([])["terminal_state"] is None


def test_is_stuck_semantics():
    assert sm.is_stuck("running", age_seconds=sm.ZOMBIE_STALE_SECONDS + 1) is True
    assert sm.is_stuck("running", age_seconds=1) is False
    assert sm.is_stuck("running") is False            # 无心跳时长 ⇒ 不判卡（不得默认卡）
    assert sm.is_stuck("ready") is False
    assert sm.is_stuck("done", age_seconds=10 ** 6) is False


def test_summarize_is_single_source():
    s = sm.summarize()
    assert s["states"] == list(sm.TASK_STATES)
    assert s["block_kinds"] == list(sm.BLOCK_KINDS)
    assert s["failure_limit"] == sm.FAILURE_LIMIT
    assert s["max_redo"] == sm.MAX_REDO
    assert s["transitions"]["ready"] == sorted(sm.ALLOWED_TRANSITIONS["ready"])
