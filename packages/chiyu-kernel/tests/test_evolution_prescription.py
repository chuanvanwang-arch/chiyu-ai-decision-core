"""T4 守卫：处方状态机 —— 事务原子 + 挂起 + 回滚（判别力自证）。

⛔ 最关键的反向用例是「状态迁移失败 ⇒ 配置必须逆写回去」：
   若只回滚状态不回滚配置，就留下「配置已改、处方仍待批」的半应用态，
   运行态被污染且无法自动收敛。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.evolution.prescription import (
    Prescription,
    PrescriptionError,
    apply_atomic,
    assert_prescription_transition,
    begin_replay,
    roll_back,
)


def _rx(**over) -> Prescription:
    base = dict(prescription_id="rx-1", knob="gate", old_value=0.79, new_value=0.72,
                direction="tighten", tier="auto", verdict="pass")
    base.update(over)
    return Prescription(**base)


def _ready(**over) -> Prescription:
    """已过 begin_replay 的处方（应用前必须处在该态）。"""
    return begin_replay(_rx(**over))


class _Sink:
    """记录写入与状态迁移顺序，用于验证事务原子性。"""

    def __init__(self, fail_on_state=False):
        self.cfg = {"gate": 0.79}
        self.states = []
        self.fail_on_state = fail_on_state

    def writer(self, knob, value):
        self.cfg[knob] = value

    def on_state(self, pid, state):
        if self.fail_on_state:
            raise RuntimeError("状态表写入失败")
        self.states.append((pid, state))

    def rollback_writer(self, knob, value):
        self.cfg[knob] = value


# ── 构造期校验 ────────────────────────────────────────────────────────
def test_unknown_state_is_rejected():
    with pytest.raises(PrescriptionError, match="未知处方状态"):
        _rx(state="applied_maybe")


def test_missing_id_is_rejected():
    with pytest.raises(PrescriptionError, match="prescription_id"):
        _rx(prescription_id="")


def test_verdict_defaults_to_reject():
    """没写结论的处方不得被当成通过（fail-safe 默认保守）。"""
    rx = Prescription(prescription_id="rx", knob="gate", old_value=1,
                      new_value=2, direction="flat", tier="auto")
    assert rx.verdict == "reject"


# ── 转换表 ────────────────────────────────────────────────────────────
def test_pending_apply_is_rejected():
    """跳过影子重放 ⇒ 被拒。把「应用前必须重放」写进状态表，而非写成注释。"""
    with pytest.raises(PrescriptionError, match="begin_replay"):
        apply_atomic(_rx(), writer=lambda *a: None, on_state=lambda *a: None)


def test_illegal_transition_is_rejected():
    with pytest.raises(PrescriptionError, match="非法处方转换"):
        assert_prescription_transition("rolled_back", "auto_applied")


def test_legal_transitions_pass():
    assert_prescription_transition("pending", "replaying")
    assert_prescription_transition("replaying", "auto_applied")
    assert_prescription_transition("auto_applied", "rolled_back")


# ── 正常应用 ──────────────────────────────────────────────────────────
def test_apply_writes_config_then_state():
    s = _Sink()
    rx, exit_ = apply_atomic(_ready(), writer=s.writer, on_state=s.on_state)
    assert exit_ == "auto_applied"
    assert s.cfg["gate"] == 0.72
    assert s.states == [("rx-1", "auto_applied")]
    assert rx.state == "auto_applied"


# ── 挂起：一行配置都不写 ──────────────────────────────────────────────
def test_widen_is_suspended_without_writing_config():
    s = _Sink()
    rx, exit_ = apply_atomic(_rx(direction="widen", new_value=0.5),
                             writer=s.writer, on_state=s.on_state)
    assert exit_ == "suspended"
    assert s.cfg["gate"] == 0.79, "放宽被挂起 ⇒ 不得写入配置"
    assert s.states == [("rx-1", "suspended")]


def test_non_pass_verdict_is_suspended_without_writing_config():
    s = _Sink()
    rx, exit_ = apply_atomic(_rx(verdict="reject"),
                             writer=s.writer, on_state=s.on_state)
    assert exit_ == "suspended"
    assert s.cfg["gate"] == 0.79


# ── 事务原子：状态迁移失败 ⇒ 配置逆写 ─────────────────────────────────
def test_state_failure_rolls_back_config():
    s = _Sink(fail_on_state=True)
    with pytest.raises(PrescriptionError, match="应用失败已回滚"):
        apply_atomic(_ready(), writer=s.writer, on_state=s.on_state,
                     rollback_writer=s.rollback_writer)
    assert s.cfg["gate"] == 0.79, "状态未迁成功 ⇒ 配置必须逆写回原值"
    assert s.states == []


def test_state_failure_without_rollback_channel_raises_loudly():
    """没有逆写通道时不得假装成功 —— 必须把半应用态暴露成异常。"""
    s = _Sink(fail_on_state=True)
    with pytest.raises(PrescriptionError, match="人工介入"):
        apply_atomic(_ready(), writer=s.writer, on_state=s.on_state)
    assert s.cfg["gate"] == 0.72, "配置已被写脏 ⇒ 必须由人工处理"


def test_writer_failure_is_propagated():
    def boom(knob, value):
        raise RuntimeError("配置存储不可用")

    s = _Sink()
    with pytest.raises(PrescriptionError, match="应用失败已回滚"):
        apply_atomic(_ready(), writer=boom, on_state=s.on_state,
                     rollback_writer=s.rollback_writer)
    assert s.states == [], "配置没写成 ⇒ 状态不得迁移"


# ── 一键回滚 ──────────────────────────────────────────────────────────
def test_roll_back_restores_old_value_and_leaves_trace():
    s = _Sink()
    applied, _ = apply_atomic(_ready(), writer=s.writer, on_state=s.on_state)
    rx = roll_back(applied, writer=s.writer, on_state=s.on_state)
    assert rx.state == "rolled_back"
    assert s.cfg["gate"] == 0.79
    assert ("rx-1", "rolled_back") in s.states   # 回滚本身也留痕


def test_roll_back_from_pending_is_rejected():
    with pytest.raises(PrescriptionError, match="非法处方转换"):
        roll_back(_rx(), writer=lambda *a: None, on_state=lambda *a: None)
