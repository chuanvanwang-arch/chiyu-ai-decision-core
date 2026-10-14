"""自主通道开闸前置认证器（§12.3 七闸 + §12.4 G1/G2/G3）。

⛔ 本模块只「认证」、不「开闸」
────────────────────────────
§12.3：七条正确性闸全部必须先于自主通道上线，任一缺失 ⇒ 自主通道不得开闸。
本模块是**开闸前的强制前置检查**——夜批调度器（下一轮）必须先 `assert_channel_may_open()`
通过才能跑。它不串联七闸（那是调度器职责），只回答「现在能不能开闸」。

⛔ 每个判据都有判别力（anti-fake-green）
────────────────────────────────────
只查「模块存在」的探针是空跑。本模块每个闸都注入一个「必红」的对抗输入：若该机制对
坏输入仍判绿，或探查本身证明该机制无鉴别力，则该闸判 RED（判据失效），认证器不会假绿。

⛔ 不新增第二份判据表
──────────────────
本模块只**引用**已落地的原语（`shadow_replay` / `KnobTable` / `apply_atomic` / `audit.chain` /
`derive_idem_key` 等），不重写其判据——双份清单是本项目同族事故源。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from chiyu_kernel.audit import build_chain, verify_chain
from chiyu_kernel.contract import (
    DIR_TIGHTEN,
    DIR_WIDEN,
    FAIL_SAFE_VERDICT,
    TIER_AUTO,
    VERDICT_PASS,
)
from chiyu_kernel.evolution.guard import (
    GuardViolation,
    assert_not_baseline_skill,
    assert_writable,
    g2_suspend_on_redline,
)
from chiyu_kernel.evolution.knob import (
    KnobSpec,
    KnobTable,
    classify_change,
    is_forbidden_change,
)
from chiyu_kernel.evolution.prescription import (
    Prescription,
    PrescriptionError,
    apply_atomic,
    begin_replay,
    roll_back,
)
from chiyu_kernel.evolution.replay import ReplayVerdict, shadow_replay
from chiyu_kernel.orchestration.idem import derive_idem_key, nightly_idem_key
from chiyu_kernel.orchestration.state_machine import (
    BLOCK_KINDS,
    FAILURE_LIMIT,
    TaskStateError,
    system_anchor,
)


# ── 状态常量 ────────────────────────────────────────────────────────────
GATE_GREEN = "green"
GATE_RED = "red"
CHECK_NOTE = "note"  # 非阻塞：调度器/消费方接线项，不阻止开闸但须留痕


@dataclass(frozen=True)
class CheckResult:
    """单条判据结果。``discriminating`` 标记该判据是否含对抗输入（有鉴别力）。"""

    check_id: str
    title: str
    status: str            # GATE_GREEN / GATE_RED / CHECK_NOTE
    detail: str = ""
    discriminating: bool = False


@dataclass
class ReadinessReport:
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        """全部阻断闸绿 ⇒ 可开闸。"""
        return all(c.status != GATE_RED for c in self.checks)

    @property
    def blocking_red(self) -> List[CheckResult]:
        return [c for c in self.checks if c.status == GATE_RED]

    def summary(self) -> str:
        n_green = sum(1 for c in self.checks if c.status == GATE_GREEN)
        n_note = sum(1 for c in self.checks if c.status == CHECK_NOTE)
        return (f"ready={self.ready} checks={len(self.checks)} "
                f"green={n_green} red={len(self.blocking_red)} note={n_note}")


class ChannelNotReadyError(RuntimeError):
    """七闸未全绿 ⇒ 自主通道不得开闸（§12.3 / §12.7 失效条件）。"""

    def __init__(self, report: ReadinessReport) -> None:
        self.report = report
        reds = "; ".join(f"{c.check_id}: {c.detail}" for c in report.blocking_red)
        super().__init__(f"自主通道未达开闸条件：{reds}")


# ── 内部辅助 ────────────────────────────────────────────────────────────
def _green_prescription(knob: str = "probe_knob", old_value: float = 1.0,
                       new_value: float = 2.0) -> Prescription:
    """构造一个「已进 replaying 态、verdict=pass、收紧方向」的处方（应用路径的正常前置）。

    ⚠ 参数刻意显式列出（禁 `**kwargs`）：`tools/check_cython_friendly.py` 的 C2
       禁动态关键字派发（可编译友好是内核硬约束）。
    """
    rx = Prescription(
        prescription_id="rx-probe",
        knob=knob,
        old_value=old_value,
        new_value=new_value,
        direction=DIR_TIGHTEN,
        tier=TIER_AUTO,
        verdict=VERDICT_PASS,
    )
    return begin_replay(rx)


# ── 判据 1：影子重放（§12.3-1）─────────────────────────────────────────
def _probe_shadow_replay() -> CheckResult:
    fid = "G1-shadow-replay"
    formula = lambda p: p.get("x", 0.0) + p.get("delta", 0.0)
    # 对抗：空样本必须判拒（盲改红线，无重放即 blind patch）
    empty = shadow_replay([], formula, {})
    if empty.verdict != FAIL_SAFE_VERDICT or empty.ok:
        return CheckResult(
            fid, "影子重放·空样本即拒", GATE_RED,
            f"空样本未判拒（blind patch 红线失效）: {empty!r}", discriminating=True)
    # 正常：带基线样本应可过
    sample = {"x": 1.0, "delta": 1.0, "__expected": 2.0}
    ok = shadow_replay([sample], formula, {})
    if not ok.ok:
        return CheckResult(fid, "影子重放·正常可过", GATE_RED, f"正常样本判拒: {ok!r}")
    return CheckResult(
        fid, "影子重放", GATE_GREEN,
        "空样本判拒（盲改红线）+ 正常样本可过", discriminating=True)


# ── 判据 2：拒绝出方守卫优先（§12.3-2）────────────────────────────────
def _probe_guard_before_rule() -> CheckResult:
    fid = "G2-guard-before-rule"
    table = KnobTable([KnobSpec(name="ok", tier=TIER_AUTO)])
    out, rejected = table.read({"ok": 1.0, "evil": 9.0})  # evil 非白名单
    if "evil" in out:
        return CheckResult(
            fid, "拒绝出方守卫·外键不入生效集", GATE_RED,
            "非白名单键被写入生效集（守卫被绕过）", discriminating=True)
    if not any("evil" in r for r in rejected):
        return CheckResult(
            fid, "拒绝出方守卫·外键留痕", GATE_RED,
            "非白名单键未被留痕 rejected（脏配置静默）")
    return CheckResult(
        fid, "拒绝出方守卫优先", GATE_GREEN,
        "非白名单键被拒且留痕 rejected（不出任何处方）", discriminating=True)


# ── 判据 3：处方应用事务原子（§12.3-3）────────────────────────────────
def _probe_atomic_apply() -> CheckResult:
    fid = "G3-transactional-atomic"
    written: List[Tuple[str, float]] = []
    rolled: List[Tuple[str, float]] = []

    def writer(k: str, v: float) -> None:
        written.append((k, v))

    def on_state(_id: str, st: str) -> None:
        if st == "auto_applied":
            raise RuntimeError("状态落库失败（模拟）")

    def rollback(k: str, v: float) -> None:
        rolled.append((k, v))

    rx = _green_prescription(knob="probe_knob", old_value=1.0, new_value=2.0)
    try:
        apply_atomic(rx, writer=writer, on_state=on_state, rollback_writer=rollback)
    except PrescriptionError:
        # 期望：状态落库失败 ⇒ 逆写回滚已发生（无半应用态）
        if rolled:
            return CheckResult(
                fid, "事务原子·失败逆写回滚", GATE_GREEN,
                "状态落库失败时触发逆写回滚（无半应用态）", discriminating=True)
        return CheckResult(
            fid, "事务原子·失败逆写回滚", GATE_RED,
            f"失败但回滚未触发（半应用态风险）: written={written} rolled={rolled}",
            discriminating=True)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            fid, "事务原子", GATE_RED, f"未以 PrescriptionError 暴露: {type(exc).__name__}: {exc}")
    return CheckResult(
        fid, "事务原子", GATE_RED, "状态落库失败却未抛错（半应用态静默）")


# ── 判据 4：预算 + 熔断 + 冷却（§12.3-4）─────────────────────────────
def _probe_budget_circuit_cooldown() -> CheckResult:
    fid = "G4-budget-circuit-cooldown"
    # 熔断机制：FAILURE_LIMIT>0 + block_kind 含 circuit_break
    if not (isinstance(FAILURE_LIMIT, int) and FAILURE_LIMIT > 0):
        return CheckResult(
            fid, "熔断参数", GATE_RED, f"FAILURE_LIMIT 非法: {FAILURE_LIMIT!r}")
    if "circuit_break" not in BLOCK_KINDS:
        return CheckResult(
            fid, "熔断分类", GATE_RED, "block_kind 缺 circuit_break（熔断不可达）")
    # 冷却方向语义：值变小 = 收紧（discriminating：方向不可由内核推断）
    cooldown = KnobSpec(name="cooldown", tier=TIER_AUTO, widen_direction="down")
    if classify_change(cooldown, 3.0, 1.0) != DIR_WIDEN:
        return CheckResult(
            fid, "冷却方向语义", GATE_RED,
            "冷却变小未判为 widen（方向推断错误 ⇒ R1 风险）", discriminating=True)
    note = "budget_deadline 由夜批调度器注入并强制；内核提供熔断机制（非内核原语）"
    return CheckResult(
        fid, "预算+熔断+冷却", GATE_GREEN,
        f"熔断(FAILURE_LIMIT={FAILURE_LIMIT})+冷却方向语义正确；{note}", discriminating=True)


# ── 判据 5：全链审计 + 一键回滚（§12.3-5）────────────────────────────
def _probe_audit_rollback() -> CheckResult:
    fid = "G5-audit-chain-rollback"
    rec = {
        "audit_id": "a1", "ts": "t", "domain": "x", "action": "tune",
        "subject_id": "s", "decision_id": "d", "prescription_id": "p",
        "from_value": 1, "to_value": 2, "verdict": "pass",
    }
    chain = build_chain([rec])
    if not verify_chain([rec], chain).ok:
        return CheckResult(
            fid, "审计链可验", GATE_RED, "构建后即验证失败（审计链失效）")
    # 对抗：篡改记录 ⇒ 验证失败（防伪改）
    tampered = [dict(rec, to_value=999)]
    if verify_chain(tampered, chain).ok:
        return CheckResult(
            fid, "审计链防篡改", GATE_RED,
            "篡改记录仍验证通过（审计无鉴别力）", discriminating=True)
    # 一键回滚：从 auto_applied 出发应可达 rolled_back
    applied = _green_prescription(knob="probe_knob", old_value=1.0, new_value=2.0)
    applied = applied.with_state("auto_applied")
    try:
        roll_back(
            applied,
            writer=lambda _k, _v: None,
            on_state=lambda _i, _s: None,
        )
    except PrescriptionError:
        return CheckResult(
            fid, "回滚路径", GATE_RED, "auto_applied 回滚被拒（回滚不可达）")
    return CheckResult(
        fid, "全链审计+一键回滚", GATE_GREEN,
        "构建/验证一致 + 篡改即失配 + 回滚可达", discriminating=True)


# ── 判据 6：verdict 机器可读（§12.3-6）───────────────────────────────
def _probe_verdict_machine_readable() -> CheckResult:
    fid = "G6-verdict-readable"
    # fail-safe：verdict=reject 的处方不得写出任何配置
    written: List[Tuple[str, float]] = []
    rx = Prescription(
        prescription_id="rx-rej", knob="probe_knob", old_value=1.0, new_value=2.0,
        direction=DIR_TIGHTEN, tier=TIER_AUTO, verdict=FAIL_SAFE_VERDICT,
    )
    rx = begin_replay(rx)
    res, _ = apply_atomic(
        rx, writer=lambda k, v: written.append((k, v)), on_state=lambda _i, _s: None)
    if written:
        return CheckResult(
            fid, "verdict 默认保守", GATE_RED,
            "verdict=reject 却写入了配置（fail-safe 失效）", discriminating=True)
    if res.state != "suspended":
        return CheckResult(
            fid, "verdict 默认保守", GATE_RED, f"未挂起: {res.state}")
    return CheckResult(
        fid, "verdict 机器可读", GATE_GREEN,
        "verdict=reject 一律挂起且零写入（fail-safe）", discriminating=True)


# ── 判据 7：幂等 + 系统锚（§12.3-7）─────────────────────────────────
def _probe_idempotency_anchor() -> CheckResult:
    fid = "G7-idempotency-anchor"
    same_a = derive_idem_key("nightly", [{"x": 1}])
    same_b = derive_idem_key("nightly", [{"x": 1}])
    if same_a != same_b:
        return CheckResult(
            fid, "幂等键稳定", GATE_RED, "同内容两次键不同（幂等失效）")
    diff = nightly_idem_key("retro", window="2026-09-23", parts=[{"x": 1}])
    diff2 = nightly_idem_key("retro", window="2026-09-24", parts=[{"x": 1}])
    if diff == diff2:
        return CheckResult(
            fid, "幂等键换天换键", GATE_RED, "换 window 键未变（跨天撞键）")
    # 对抗：空 scope 必须拒（撞键风险）
    try:
        derive_idem_key("", [{"x": 1}])
        return CheckResult(
            fid, "幂等键空 scope 拒", GATE_RED, "空 scope 未拒（撞键风险）", discriminating=True)
    except ValueError:
        pass
    # 系统锚可达
    try:
        system_anchor("nightly")
    except TaskStateError:
        return CheckResult(fid, "系统锚", GATE_RED, "system_anchor 不可用")
    return CheckResult(
        fid, "幂等+系统锚", GATE_GREEN,
        "同内容键稳定 + 换天换键 + 空 scope 拒 + 系统锚可用", discriminating=True)


# ── 护栏 G1：阈值放宽永不自动（§12.4-G1）────────────────────────────
def _probe_g1_widen_never_auto() -> CheckResult:
    fid = "GUARD-G1-widen-never-auto"
    spec = KnobSpec(
        name="autonomous_threshold", tier=TIER_AUTO, widen_direction="down",
        autonomy_related=True)
    if not is_forbidden_change(spec, DIR_WIDEN):
        return CheckResult(
            fid, "G1·放宽永不自动", GATE_RED,
            "自主权放宽未判为 forbidden（R1 自我扩权风险）", discriminating=True)
    if is_forbidden_change(spec, DIR_TIGHTEN):
        return CheckResult(
            fid, "G1·收紧可自动", GATE_RED, "收紧被误判 forbidden（自主权被架空）")
    return CheckResult(
        fid, "G1·阈值放宽永不自动", GATE_GREEN,
        "放宽=forbidden，收紧=允许", discriminating=True)


# ── 护栏 G2：红线命中挂起（§12.4-G2）────────────────────────────────
def _probe_g2_redline_suspend() -> CheckResult:
    fid = "GUARD-G2-redline-suspend"
    if not g2_suspend_on_redline(True):
        return CheckResult(
            fid, "G2·红线挂起", GATE_RED,
            "红线命中未触发挂起（R3 风险）", discriminating=True)
    if g2_suspend_on_redline(False):
        return CheckResult(
            fid, "G2·无红线不挂起", GATE_RED, "无红线却挂起（误伤正常处方）")
    # 应用路径内置：redline_hit=True ⇒ 不写配置
    written: List[Tuple[str, float]] = []
    rx = _green_prescription(knob="probe_knob", old_value=1.0, new_value=2.0)
    res, _ = apply_atomic(
        rx, writer=lambda k, v: written.append((k, v)),
        on_state=lambda _i, _s: None, redline_hit=True)
    if written:
        return CheckResult(
            fid, "G2·应用路径红线不写", GATE_RED,
            "红线命中仍写入（静默自动应用）", discriminating=True)
    return CheckResult(
        fid, "G2·红线命中挂起", GATE_GREEN,
        "命中即挂起 + 应用路径不写配置（异步人工处置）", discriminating=True)


# ── 护栏 G3：基线 / L0 物理只读（§12.4-G3）──────────────────────────
def _probe_g3_readonly_baseline() -> CheckResult:
    fid = "GUARD-G3-readonly-baseline"
    try:
        assert_writable("chiyu_kernel.contract.evolution")
        return CheckResult(
            fid, "G3·L0 契约只读", GATE_RED,
            "L0 契约路径可写（R2 风险）", discriminating=True)
    except GuardViolation:
        pass
    try:
        assert_not_baseline_skill("ai-memory-lifecycle")
        return CheckResult(
            fid, "G3·基线命名空间只读", GATE_RED,
            "基线命名空间可写（10 大能力被改）", discriminating=True)
    except GuardViolation:
        pass
    # 正常路径应放行（防止误伤消费方合法写入）
    try:
        assert_writable("tenant/acme/foo")
    except GuardViolation:
        return CheckResult(
            fid, "G3·正常路径", GATE_RED, "正常租户路径被误拒")
    return CheckResult(
        fid, "G3·基线/L0 物理只读", GATE_GREEN,
        "L0 契约 + ai-* 基线均拒写，正常路径放行", discriminating=True)


# ── 判据注册表（顺序即报告顺序）──────────────────────────────────────
_PROBES: Tuple[Callable[[], CheckResult], ...] = (
    _probe_shadow_replay,
    _probe_guard_before_rule,
    _probe_atomic_apply,
    _probe_budget_circuit_cooldown,
    _probe_audit_rollback,
    _probe_verdict_machine_readable,
    _probe_idempotency_anchor,
    _probe_g1_widen_never_auto,
    _probe_g2_redline_suspend,
    _probe_g3_readonly_baseline,
)


def readiness_report() -> ReadinessReport:
    """跑全部判据，返回结构化报告。覆盖 §12.3 七闸 + §12.4 G1/G2/G3。"""
    report = ReadinessReport()
    for probe in _PROBES:
        try:
            report.checks.append(probe())
        except Exception as exc:  # noqa: BLE001
            # 探查本身抛错 ⇒ 判据不可达 ⇒ 该闸判红（绝不静默绿）
            report.checks.append(CheckResult(
                getattr(probe, "__name__", "probe"), "探查异常", GATE_RED,
                f"{type(exc).__name__}: {exc}", discriminating=True))
    return report


def assert_channel_may_open() -> ReadinessReport:
    """开闸前置强制检查。任一阻断闸 RED ⇒ 抛 `ChannelNotReadyError`。

    夜批调度器（下一轮）必须在跑七闸之前调用本函数；通过后才允许串联七闸。
    """
    report = readiness_report()
    if not report.ready:
        raise ChannelNotReadyError(report)
    return report


__all__ = [
    "GATE_GREEN", "GATE_RED", "CHECK_NOTE",
    "CheckResult", "ReadinessReport", "ChannelNotReadyError",
    "readiness_report", "assert_channel_may_open",
]
