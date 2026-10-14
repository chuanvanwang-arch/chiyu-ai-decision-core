"""处方状态机 —— 自变动作落盘的**唯一**路径。

⛔ 为什么应用必须事务原子
────────────────────────
配置写入与处方状态迁移若分两步，任一中间失败都留下「配置已改、处方仍待批」的
半应用态：运行态被污染，且**无法自动收敛**——状态机不知道该往前还是往后。
故本模块把两步绑在一起，任一步抛错即逆写回滚。

⛔ 为什么 verdict 默认保守
────────────────────────
纯方法论执行默认不抛异常，用"没抛错"判成功是假阳性。故落盘必须带机器可读的
verdict，且**字段默认值为 reject**：没写结论的处方一律挂起。

⚠️ G1 的落点在 `knob.is_forbidden_change`，**不在本模块**
────────────────────────────────────────────────────────────
本模块只检查 `direction == widen` 这一**结果**（调用方须先经 knob 判定）。
两处都判会形成第二份判据表，迟早口径分叉。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

from chiyu_kernel.contract import (
    DIR_WIDEN,
    FAIL_SAFE_VERDICT,
    PRESCRIPTION_STATES,
    PRESCRIPTION_TRANSITIONS,
    VERDICT_PASS,
)


class PrescriptionError(KernelError):
    code = "CONTRACT_VIOLATION"
    """处方契约违规（非法转换 / 事务半应用 / 回滚失败）⇒ 抛，不静默。"""


@dataclass(frozen=True)
class Prescription:
    prescription_id: str
    knob: str
    old_value: Any
    new_value: Any
    direction: str
    tier: str
    state: str = "pending"
    verdict: str = FAIL_SAFE_VERDICT          # ⛔ 默认保守：没写结论 = 拒绝
    replay_ref: Optional[str] = None
    audit_ref: Optional[str] = None
    reason: str = ""

    def __post_init__(self) -> None:
        if self.state not in PRESCRIPTION_STATES:
            raise PrescriptionError(
                f"未知处方状态：{self.state!r}（合法集 {PRESCRIPTION_STATES}）")
        if not self.prescription_id:
            raise PrescriptionError("prescription_id 必填（回滚要靠它定位）")

    def with_state(self, state: str, reason: Optional[str] = None) -> "Prescription":
        """返回迁至 `state` 的新处方（frozen ⇒ 不就地改）。

        ⚠️ 形参刻意**不用 `**overrides`**：`tools/check_cython_friendly.py` 的
           C2 禁 `**kwargs` 动态派发（可编译友好是内核的硬约束）。
        """
        data = dict(self.__dict__)
        data["state"] = state
        if reason is not None:
            data["reason"] = reason
        return Prescription(**data)


def assert_prescription_transition(frm: str, to: str) -> None:
    if frm not in PRESCRIPTION_STATES:
        raise PrescriptionError(f"未知源状态：{frm!r}")
    if to not in PRESCRIPTION_STATES:
        raise PrescriptionError(f"未知目标状态：{to!r}")
    if to not in PRESCRIPTION_TRANSITIONS[frm]:
        raise PrescriptionError(
            f"非法处方转换：{frm} → {to}"
            f"（允许 {sorted(PRESCRIPTION_TRANSITIONS[frm])}）")


def begin_replay(rx: Prescription, *, on_state=None) -> Prescription:
    """进入重放态（pending → replaying）。

    ⛔ 为什么必须由调用方显式走这一步
       转换表规定 `auto_applied` 只能从 `replaying` 到达。若允许 `pending` 直接应用，
       影子重放闸就被"忘记调用"绕过了——而忘记调用不会报错，只是少一行代码。
       把顺序写进状态表，跳过即抛。
    """
    assert_prescription_transition(rx.state, "replaying")
    if on_state is not None:
        on_state(rx.prescription_id, "replaying")
    return rx.with_state("replaying")


def apply_atomic(
    rx: Prescription,
    *,
    writer: Callable[[str, Any], None],
    on_state: Callable[[str, str], None],
    rollback_writer: Optional[Callable[[str, Any], None]] = None,
    redline_hit: bool = False,
) -> Tuple[Prescription, str]:
    """事务原子应用。返回 (新处方, 出口)：`auto_applied` 或 `suspended`。

    `redline_hit=True` ⇒ 挂起（G2）。该判据刻意放在**被调用方**：放在调用方时，
    "忘了查"就等价于绕过，且不产生任何报错。

    ⛔ 前置：处方须已在 `replaying` 态（先经 `begin_replay`）。
       `pending` 直接调用会被转换表拒绝——把「应用前必须重放」写进状态表，
       而不是写成一句注释。

    ⛔ 挂起路径**一行配置都不写** —— 一旦"先改了再说"，回滚就依赖事后人工发现。

    ⚠️ 约定：`writer` / `on_state` 不得吞异常。吞掉异常会让本函数"看上去成功"，
       于是半应用态以"已应用"的形态落库——比抛错难查得多。
    """
    if rx.verdict != VERDICT_PASS:
        return _suspend(rx, on_state,
                        reason=f"verdict={rx.verdict!r} ⇒ 挂起（fail-safe 默认保守）")
    if rx.direction == DIR_WIDEN:
        return _suspend(rx, on_state, reason="放宽自主权 ⇒ 永不在夜间自动应用（护栏）")

    # ⛔ G2 写进应用路径本身（2026-09-22 跨闸集成实测补上的接缝）
    #    此前 G2 只存在于 `guard.g2_suspend_on_redline`，由调用方自觉调用；
    #    夜批一旦忘了查，红线处方会被**静默自动应用** —— 不报错、不留痕。
    #    判据写在被调用方，忘记调用才不会等于绕过。
    if redline_hit:
        return _suspend(rx, on_state, reason="红线命中 ⇒ 挂起（G2，异步人工处置）")

    if rx.state == "pending":
        raise PrescriptionError(
            f"处方 {rx.prescription_id!r} 仍在 pending ⇒ 须先 begin_replay "
            "（应用前必须过影子重放，跳过该步即 blind patch）")
    assert_prescription_transition(rx.state, "auto_applied")
    try:
        writer(rx.knob, rx.new_value)                  # ① 写配置
        on_state(rx.prescription_id, "auto_applied")   # ② 迁状态（同一事务）
    except Exception as exc:
        if rollback_writer is None:
            raise PrescriptionError(
                f"应用失败且未提供逆写通道 ⇒ 半应用态需人工介入：{exc}") from exc
        try:
            rollback_writer(rx.knob, rx.old_value)
        except Exception as rb:
            raise PrescriptionError(
                f"应用失败且回滚失败（**需人工介入**）：{exc} / {rb}") from rb
        raise PrescriptionError(f"应用失败已回滚：{exc}") from exc
    return rx.with_state("auto_applied"), "auto_applied"


def roll_back(
    rx: Prescription,
    *,
    writer: Callable[[str, Any], None],
    on_state: Callable[[str, str], None],
) -> Prescription:
    """一键回滚 = 逆动作，**同样留痕**（回滚本身也是一次自变）。"""
    assert_prescription_transition(rx.state, "rolled_back")
    writer(rx.knob, rx.old_value)
    on_state(rx.prescription_id, "rolled_back")
    return rx.with_state("rolled_back")


def _suspend(rx: Prescription, on_state, *, reason: str) -> Tuple[Prescription, str]:
    assert_prescription_transition(rx.state, "suspended")
    on_state(rx.prescription_id, "suspended")
    return rx.with_state("suspended", reason=reason), "suspended"


__all__ = ["PrescriptionError", "Prescription", "assert_prescription_transition",
           "begin_replay", "apply_atomic", "roll_back"]
