"""T10 跨闸集成 —— 单闸全绿 ≠ 串起来对。

⛔ 为什么必须单独建这个文件
   前七个测试文件各自只验一个模块。但 B 档的风险恰恰出在**闸与闸的接缝**：
   例如 `prescription` 自己保证"挂起不写配置"，可若调用方忘了先过 `guard`，
   挂起路径根本不会被走到。本文件把整条链跑一遍，并**逐个证明反向**。

覆盖的接缝（每一条都是"漏了不会报错、只会静默失效"）：
   ① knob → replay → prescription      全链路放行
   ② 放宽方向 ⇒ 挂起**且 writer 零调用**（不是"挂起了但配置已改"）
   ③ 红线 ⇒ 挂起**且 writer 零调用**
   ④ G3 只读路径 ⇒ 在 writer 之前被拦
   ⑤ 元红线 ⇒ 次日报告能检出「给自己扩权」这个动作本身
   ⑥ 半应用 ⇒ 逆写回滚且抛（配置与状态不得各走一半）
   ⑦ 幂等键 ⇒ 同窗口重跑被判重（这是回滚链不断裂的唯一保证）
"""
from __future__ import annotations

import pytest

from chiyu_kernel.evolution.guard import (
    GuardViolation,
    assert_writable,
    g2_suspend_on_redline,
    meta_redline_hits,
)
from chiyu_kernel.evolution.knob import (
    KnobSpec,
    KnobTable,
    classify_change,
    is_forbidden_change,
)
from chiyu_kernel.evolution.prescription import (
    PrescriptionError,
    Prescription,
    apply_atomic,
    begin_replay,
)
from chiyu_kernel.evolution.replay import shadow_replay
from chiyu_kernel.orchestration.idem import nightly_idem_key

# 收紧自主权 = 提高阈值（放行门槛变高）
TIGHTEN_SPEC = KnobSpec(
    name="autonomous_threshold",
    tier="guarded",
    min_value=0.5,
    max_value=1.0,
    default=0.79,
    widen_direction="down",     # 阈值变小 ⇒ 更容易自主放行 ⇒ 放宽
    autonomy_related=True,
)


class _Sink:
    """记录 writer / on_state 的调用，用于证明「挂起 ⇒ 一行都没写」。"""

    def __init__(self) -> None:
        self.cfg: dict = {}
        self.states: list = []
        self.writes = 0

    def writer(self, k, v):
        self.writes += 1
        self.cfg[k] = v

    def on_state(self, pid, st):
        self.states.append((pid, st))

    def rollback(self, k, v):
        self.cfg[k] = v


def _rx(**over) -> Prescription:
    base = dict(
        prescription_id="rx-chain-1",
        knob="autonomous_threshold",
        old_value=0.79,
        new_value=0.85,
        direction="tighten",
        tier="guarded",
    )
    base.update(over)
    return Prescription(**base)


def _pass_samples():
    """新阈值 0.85 下，0.9 应放行、0.6 应拦截 —— 与基线一致 ⇒ pass。"""
    return [
        {"confidence": 0.9, "__expected": True},
        {"confidence": 0.6, "__expected": False},
    ]


def test_chain_happy_path_applies_once():
    sink = _Sink()
    tbl = KnobTable([TIGHTEN_SPEC])
    _, rejected = tbl.read({"autonomous_threshold": 0.79})
    assert rejected == []

    direction = classify_change(TIGHTEN_SPEC, 0.79, 0.85)
    assert direction == "tighten"
    assert is_forbidden_change(TIGHTEN_SPEC, direction) is False

    def formula(payload):
        # ⛔ shadow_replay 的 formula 是**单参**：样本去掉 `__expected` 后
        #    再并入 new_params，合成一个 payload 传入。
        return payload["confidence"] >= payload["autonomous_threshold"]

    v = shadow_replay(_pass_samples(), formula, {"autonomous_threshold": 0.85})
    assert v.verdict == "pass"

    rx = begin_replay(_rx(verdict=v.verdict, replay_ref="rp-1"))
    out, exit_kind = apply_atomic(
        rx, writer=sink.writer, on_state=sink.on_state,
        rollback_writer=sink.rollback,
    )
    assert exit_kind == "auto_applied" and out.state == "auto_applied"
    assert sink.cfg["autonomous_threshold"] == 0.85
    assert sink.writes == 1, "正常路径只应写一次"
    assert ("rx-chain-1", "auto_applied") in sink.states


def test_widen_suspends_and_writes_nothing():
    """护栏 G1 的接缝：判据在 knob，但若处方不查它，配置照样被改。"""
    sink = _Sink()
    direction = classify_change(TIGHTEN_SPEC, 0.79, 0.70)
    assert direction == "widen"
    assert is_forbidden_change(TIGHTEN_SPEC, direction) is True

    rx = begin_replay(_rx(new_value=0.70, direction=direction, verdict="pass"))
    out, exit_kind = apply_atomic(
        rx, writer=sink.writer, on_state=sink.on_state,
        rollback_writer=sink.rollback,
    )
    assert exit_kind == "suspended" and out.state == "suspended"
    assert sink.writes == 0, "⛔ 挂起路径写配置 ⇒ 回滚链已断，只是没人发现"
    assert sink.cfg == {}


def test_redline_suspends_and_writes_nothing():
    """护栏 G2：红线命中 ⇒ 挂起**且一行配置都不写**。

    ⛔ 本用例在 2026-09-22 首次跑红，暴露一个真接缝：G2 原先只存在于
       `guard.g2_suspend_on_redline`，由调用方自觉调用；`apply_atomic` 对红线
       一无所知 ⇒ 夜批忘了查就会静默自动应用。现已把 `redline_hit` 写进
       `apply_atomic` 的判定路径 —— 判据在被调用方，"忘记调用"才不等于绕过。
    """
    sink = _Sink()
    assert g2_suspend_on_redline(True) is True

    rx = begin_replay(_rx(verdict="pass"))
    out, exit_kind = apply_atomic(
        rx, writer=sink.writer, on_state=sink.on_state,
        rollback_writer=sink.rollback,
        redline_hit=g2_suspend_on_redline(True),
    )
    assert exit_kind == "suspended" and out.state == "suspended"
    assert sink.writes == 0, "⛔ 红线处方被自动应用 ⇒ 人工处置被架空"


def test_g3_blocks_before_writer():
    """护栏 G3：只读路径在写入前被拒 —— 不是写完再回滚。"""
    sink = _Sink()
    with pytest.raises(GuardViolation, match="只读路径"):
        assert_writable("chiyu_kernel.contract.decision.SPINE_ORDER")
    assert sink.writes == 0
    # 非只读路径正常放行（判据不能一刀切）
    assert assert_writable("config/tenant/acme/knobs.json").endswith("knobs.json")


def test_meta_redline_is_detectable_next_day():
    """元红线：『放宽阈值』这个动作本身必须被次日报告点名，否则逐步架空。"""
    hits = meta_redline_hits(["threshold_widen", "tune:cooldown_days"])
    assert hits, "给自己扩权的动作未被检出 ⇒ 可逐步下调阈值架空人工"
    assert meta_redline_hits(["tune:cooldown_days"]) == []


def test_half_application_rolls_back():
    """配置写成功、状态迁移失败 ⇒ 必须逆写回滚，而不是留下半应用态。"""
    sink = _Sink()

    def boom(pid, st):
        raise RuntimeError("状态库不可写")

    rx = begin_replay(_rx(verdict="pass"))
    with pytest.raises(PrescriptionError, match="回滚"):
        apply_atomic(rx, writer=sink.writer, on_state=boom,
                     rollback_writer=sink.rollback)
    assert sink.cfg["autonomous_threshold"] == 0.79, "未逆写 ⇒ 配置已改、状态仍待批"


def test_idem_key_makes_rerun_detectable():
    """同窗口同内容重跑 ⇒ 同一个键。据此判重，避免第二次覆盖 old_value。"""
    parts = [{"knob": "autonomous_threshold", "to": 0.85}]
    k1 = nightly_idem_key("tune", window="2026-09-22", parts=parts)
    k2 = nightly_idem_key("tune", window="2026-09-22", parts=parts)
    assert k1 == k2

    seen = {k1}
    k3 = nightly_idem_key("tune", window="2026-09-22", parts=parts)
    assert k3 in seen, "重跑未被判重 ⇒ 会二次应用 ⇒ old_value 被覆盖 ⇒ 回滚链断"

    k4 = nightly_idem_key("tune", window="2026-09-23", parts=parts)
    assert k4 not in seen, "换天必须是新键（否则永远只跑第一天）"
