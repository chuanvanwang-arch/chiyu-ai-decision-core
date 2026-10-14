"""G5 启动期能力自检 `require_capabilities` 守卫。

enterprise 第二轮 G5 诉求：推荐断言语态与必检键清单的**机检落地**。
⛔ 判别力：未登记键 / 状态不符 / 多 mismatch 聚合，各自破坏性构造必须转红。
"""
from __future__ import annotations

import pytest

import chiyu_kernel.api as api
from chiyu_kernel.version import require_capabilities


def test_gate_passes_on_stable_capabilities():
    # 接决策脊柱消费方的推荐必检集（见 docs/versioning-and-deprecation.md §启动期能力自检）
    require_capabilities({
        "decision": "stable", "persist": "stable", "approval": "stable",
        "store": "stable", "contract": "stable", "canary": "stable",
    })


def test_gate_rejects_unregistered_capability():
    with pytest.raises(RuntimeError, match="能力未登记"):
        require_capabilities({"no-such-capability": "stable"})


def test_gate_rejects_status_mismatch():
    with pytest.raises(RuntimeError, match="期望 deprecated，实际 stable"):
        require_capabilities({"persist": "deprecated"})


def test_gate_pins_memory_stable():
    """哨兵随毕业翻转（T44，2026-10-10）：memory 已 stable（T40–T44 验收）。
    原哨兵钉 experimental；毕业验收时按其自述"须随验收同步更新"翻转为钉 stable。"""
    require_capabilities({"memory": "stable"})  # 不抛即过
    with pytest.raises(RuntimeError, match="期望 experimental，实际 stable"):
        require_capabilities({"memory": "experimental"})


def test_gate_pins_evolution_stable():
    """哨兵随毕业翻转（T78，2026-10-13）：evolution 已 stable（readiness 十闸验收）。

    原哨兵形态同 memory（T44）：钉 stable + 拒 experimental——消费方把
    evolution 当 experimental 用（`require_capabilities({"evolution": "experimental"})`）
    必须**报错**，防止毕业态被降级使用而无人知（capability_status 可机检，
    靠 hasattr/注释推断实验态的同族事故不再可能静默发生）。
    """
    require_capabilities({"evolution": "stable"})  # 不抛即过
    with pytest.raises(RuntimeError, match="期望 experimental，实际 stable"):
        require_capabilities({"evolution": "experimental"})


def test_gate_aggregates_all_mismatches_in_one_error():
    with pytest.raises(RuntimeError) as ei:
        require_capabilities({"ghost": "stable", "persist": "experimental"})
    msg = str(ei.value)
    assert "ghost" in msg and "persist" in msg, "多 mismatch 必须一次性列全（fail-fast 不逐个炸）"


def test_gate_exported_via_facade():
    assert "require_capabilities" in api.__all__
    assert api.require_capabilities is require_capabilities
