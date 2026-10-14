"""evolution 毕业判据守卫（T78，2026-10-13：experimental → stable）。

⛔ 为什么需要独立守卫
──────────────────
T44（memory 毕业）与 T78（evolution 毕业）的同一教训：状态翻转若只改
`version.py` 一处而无机检判据面，任何一次重构都可能把实验态悄悄翻回去
（或把 stable 层降级）而无人知。本文件把毕业事实钉成四组判据：

    G1  CAPABILITIES 状态翻转 + 全清单无 experimental 层
    G2  EVOLUTION_EXPERIMENTAL 机器可检出口（False + 进 __all__ + 同对象）
    G3  require_capabilities 毕业态双向判定（stable 过 / experimental 拒）
    G4  readiness 十闸全绿且含对抗判别力（毕业前置的持续可复验）

判别力纪律：G1/G2/G3 各含破坏性构造（状态不符 / 标志为 True / 实验态误用），
破坏性输入必须转红——见各用例 docstring。G4 的判别力由 readiness 自身的
对抗输入（每闸注入必红样本）保证，此处只复验结论。
"""
from __future__ import annotations

import pytest

import chiyu_kernel.api as api
from chiyu_kernel.version import CAPABILITIES, capability_status, require_capabilities


def test_g1_capabilities_evolution_is_stable():
    """状态翻转判据 + 毕业后全清单无 experimental（29 层全 stable）。"""
    assert capability_status("evolution") == "stable"
    assert dict(CAPABILITIES)["evolution"] == "stable"
    experimental = [n for n, s in CAPABILITIES if s == "experimental"]
    assert experimental == [], (
        f"毕业后不应残留 experimental 层：{experimental}")


def test_g2_evolution_flag_machine_checkable():
    """机器可检出口：False + 进 __all__ + 与 api 同对象（`from api import *` 可达）。"""
    assert api.EVOLUTION_EXPERIMENTAL is False
    assert "EVOLUTION_EXPERIMENTAL" in api.__all__
    # memory 毕业同形态并存（T44），两标志互不混写
    assert api.MEMORY_EXPERIMENTAL is False


def test_g3_require_capabilities_graduated_semantics():
    """毕业态双向判定：stable 通过；experimental 必拒（防降级静默使用）。"""
    require_capabilities({"evolution": "stable"})  # 不抛即过
    with pytest.raises(RuntimeError, match="期望 experimental，实际 stable"):
        require_capabilities({"evolution": "experimental"})


def test_g4_readiness_ten_gates_all_green():
    """毕业前置持续可复验：readiness 十闸全绿且 10/10 含对抗判别力。

    任一闸转红 ⇒ 毕业判据失效 ⇒ 本测试红（而不是等夜批开闸时才发现）。
    """
    from chiyu_kernel.evolution import readiness_report

    report = readiness_report()
    assert report.ready, (
        "readiness 十闸未全绿（毕业态失效）: "
        + "; ".join(f"{c.check_id}: {c.detail}" for c in report.blocking_red))
    assert len(report.checks) == 10
    discriminating = [c for c in report.checks if c.discriminating]
    assert len(discriminating) == 10, (
        "十闸必须全部含对抗输入（无鉴别力的探针是空跑）: "
        + repr([c.check_id for c in report.checks if not c.discriminating]))


def test_g5_facade_exposes_evolution_symbols():
    """毕业层符号经 api 门面可达（抽查三族代表，identity 断言防复制体）。"""
    from chiyu_kernel.evolution import (
        KnobTable,
        ReadinessReport,
        shadow_replay,
    )

    assert api.KnobTable is KnobTable
    assert api.shadow_replay is shadow_replay
    assert api.ReadinessReport is ReadinessReport
    for name in ("KnobTable", "shadow_replay", "ReadinessReport",
                 "assert_channel_may_open", "readiness_report"):
        assert name in api.__all__, f"evolution 符号漏登 __all__: {name}"
