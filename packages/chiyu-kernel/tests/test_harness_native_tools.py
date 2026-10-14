import pytest

from chiyu_kernel.contract import TenantProfile
from chiyu_kernel.contract.particle import ParticleTypeSet
from chiyu_kernel.tools import ToolRegistry, GuardDenied
from chiyu_kernel.harness_native_tools import register_native_tools, native_redline_guard


def _profile():
    return TenantProfile(
        domain="demo",
        particle_types=ParticleTypeSet(
            ("unstructured_asset", "entity", "decision", "memory", "knowledge")),
    )


def test_native_context_assemble_registered():
    reg = ToolRegistry()
    register_native_tools(reg, profile=_profile())
    assert "native-context-assemble" in reg.names()
    out = reg.execute("native-context-assemble", {
        "needs": [{"layer": "L1", "dims": ("semantics",)}],
        "provided": {"L1": [{"dim": "semantics", "key": "k", "value": "v"}]},
    })
    assert out["facts"]["L1"] == ["v"]


def test_native_redline_check_reports_hits():
    reg = ToolRegistry()
    register_native_tools(reg, profile=_profile())
    hit = reg.execute("native-redline-check", {"actions": ["baseline_write"]})
    assert hit["redline_hit"] is True and "baseline_write" in hit["hits"]
    clean = reg.execute("native-redline-check", {"actions": ["do_something_safe"]})
    assert clean["redline_hit"] is False


def test_redline_guard_blocks_meta_redline_action():
    reg = ToolRegistry()
    register_native_tools(reg, profile=_profile())
    guard = native_redline_guard(profile=_profile())
    # 携带元红线动作的工具调用 ⇒ 被 guard 拦截（GuardDenied）
    with pytest.raises(GuardDenied):
        reg.execute("native-redline-check", {"actions": ["baseline_write"]},
                    redline_guard=guard)
    # 无红线动作 ⇒ 不拦截
    reg.execute("native-redline-check", {"actions": ["do_something_safe"]},
                redline_guard=guard)
