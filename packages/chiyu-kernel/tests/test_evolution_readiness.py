"""开闸前置认证器测试（§12.3 七闸 + §12.4 G1/G2/G3 的强制前置）。

⛔ 判别力自证是核心：除了「全绿」，本文件还把某个底层机制 monkeypatch 成失效，
确认 `assert_channel_may_open()` 必须转红——否则认证器是「永远绿」的假绿。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract import FAIL_SAFE_VERDICT, VERDICT_PASS
from chiyu_kernel.evolution import (
    ChannelNotReadyError,
    CheckResult,
    ReadinessReport,
    assert_channel_may_open,
    readiness_report,
)
from chiyu_kernel.evolution import readiness as readiness_mod
from chiyu_kernel.evolution.replay import ReplayVerdict


def test_readiness_report_all_green() -> None:
    report = readiness_report()
    assert isinstance(report, ReadinessReport)
    assert report.ready is True, report.summary()
    assert report.blocking_red == [], [c.check_id for c in report.blocking_red]
    # 10 项：七闸 + G1/G2/G3
    assert len(report.checks) == 10, [c.check_id for c in report.checks]
    # 每个判据都是 green 且带判别力标记
    for c in report.checks:
        assert c.status == "green", f"{c.check_id}: {c.detail}"
        assert c.discriminating is True


def test_assert_channel_may_open_returns_report_when_ready() -> None:
    inited = assert_channel_may_open()
    assert inited.ready is True
    assert isinstance(inited, ReadinessReport)


def test_assert_channel_may_open_raises_when_gate_red(monkeypatch) -> None:
    """判别力自证①：把影子重放机制改成「永远 pass」⇒ G1 判红 ⇒ 认证器转红。"""
    def fake_replay(samples, formula, new_params, *, min_samples=1):  # noqa: ANN001
        return ReplayVerdict(VERDICT_PASS, checked=len(samples))
    monkeypatch.setattr(readiness_mod, "shadow_replay", fake_replay)
    report = readiness_report()
    bad = [c for c in report.checks if c.check_id == "G1-shadow-replay"]
    assert bad and bad[0].status == "red", "影子重放失效应判红"
    assert report.ready is False
    with pytest.raises(ChannelNotReadyError) as exc:
        assert_channel_may_open()
    assert "G1-shadow-replay" in str(exc.value)


def test_assert_channel_may_open_raises_when_guard_red(monkeypatch) -> None:
    """判别力自证②：把 G1 放宽判据改成「永远允许」⇒ 护栏失效 ⇒ 认证器转红。"""
    def fake_forbidden(spec, direction, *, redline_hit=False):  # noqa: ANN001
        return False
    monkeypatch.setattr(readiness_mod, "is_forbidden_change", fake_forbidden)
    report = readiness_report()
    bad = [c for c in report.checks if c.check_id == "GUARD-G1-widen-never-auto"]
    assert bad and bad[0].status == "red", "G1 护栏失效应判红"
    with pytest.raises(ChannelNotReadyError):
        assert_channel_may_open()


def test_channel_not_ready_error_carries_report() -> None:
    report = readiness_report()
    err = ChannelNotReadyError(report)
    assert err.report is report
    assert "未达开闸条件" in str(err)


def test_probes_coverage_maps_to_seven_gates_plus_guardrails() -> None:
    expected_ids = {
        "G1-shadow-replay", "G2-guard-before-rule", "G3-transactional-atomic",
        "G4-budget-circuit-cooldown", "G5-audit-chain-rollback",
        "G6-verdict-readable", "G7-idempotency-anchor",
        "GUARD-G1-widen-never-auto", "GUARD-G2-redline-suspend",
        "GUARD-G3-readonly-baseline",
    }
    got = {c.check_id for c in readiness_report().checks}
    assert got == expected_ids, got.symmetric_difference(expected_ids)
