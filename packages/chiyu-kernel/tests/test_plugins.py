"""Phase A 插件化 + 工作模式契约测试。

⛔ 全确定性、零 IO、不接 LLM（守本仓运行时纪律）。
覆盖：注册表注册/审计、模式解析（含回落与 warning）、模式引用的插件均已在 registry。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.plugins import (
    BUILTIN_PLUGINS,
    DEFAULT_MODE_ID,
    MODE_PRESETS,
    PluginRegistry,
    PluginSpec,
    WorkMode,
    active_plugins,
    disabled_plugins,
    mode_ids,
    register_builtins,
    resolve_work_mode,
)


@pytest.fixture
def registry() -> PluginRegistry:
    reg = PluginRegistry()
    register_builtins(reg)
    return reg


def test_six_builtin_plugins(registry):
    assert registry.names() == (
        "loop", "subagent", "team", "terminal", "voice", "web_search"
    )


def test_duplicate_register_rejected():
    reg = PluginRegistry()
    reg.register(PluginSpec(name="terminal", capability="x"))
    with pytest.raises(ValueError):
        reg.register(PluginSpec(name="terminal", capability="y"))


def test_audit_clean_for_builtins(registry):
    errs, warns = registry.audit()
    assert errs == [], errs
    # voice/web_search 在 Phase A 仅声明槽位，但仍声明了 input_adapters/tools，故无空插件告警
    assert warns == [], warns


def test_four_modes_present():
    assert set(mode_ids()) == {"standard", "ptc", "minimal", "creative"}
    assert MODE_PRESETS[DEFAULT_MODE_ID].default is True


def test_resolve_default_fallback_for_none(registry):
    mode, enabled, disabled, warns = resolve_work_mode(None, registry)
    assert mode.id == DEFAULT_MODE_ID
    assert warns == []


def test_resolve_unknown_falls_back_with_warning(registry):
    mode, enabled, disabled, warns = resolve_work_mode("bogus", registry)
    assert mode.id == DEFAULT_MODE_ID
    assert any("未知工作模式" in w for w in warns)


def test_resolve_never_raises(registry):
    # 即使 registry 不含任何插件，也应回落而非抛
    empty = PluginRegistry()
    mode, enabled, disabled, warns = resolve_work_mode("creative", empty)
    assert mode.id == "creative"
    assert enabled == ()          # 引用插件全未注册 ⇒ 静默剔除
    assert any("未注册插件" in w for w in warns)


def test_mode_plugins_all_registered(registry):
    """每个模式引用的插件都必须真实存在于 registry（否则解析会告警）。"""
    for mid in mode_ids():
        mode = MODE_PRESETS[mid]
        missing = [p for p in mode.plugins if not registry.has(p)]
        assert missing == [], f"模式 {mid} 引用未注册插件 {missing}"


def test_active_and_disabled_partition(registry):
    mode = MODE_PRESETS["minimal"]
    enabled = active_plugins(mode, registry)
    disabled = disabled_plugins(mode, registry)
    assert enabled == ("terminal",)
    assert set(enabled) | set(disabled) == set(registry.names())
    assert "terminal" not in disabled


def test_ptc_opens_script_plan_slot():
    assert MODE_PRESETS["ptc"].orchestration.get("script_plan_slot") is True


def test_minimal_hides_portal():
    assert MODE_PRESETS["minimal"].orchestration.get("portal_hidden") is True


def test_phase_b_backend_declared_for_llm_modes():
    # 标准/PTC/创造 在 Phase B 接 DeepSeek；极简无需 LLM
    assert MODE_PRESETS["standard"].phase_b_backend == "deepseek-ai/DeepSeek-V4-Flash"
    assert MODE_PRESETS["creative"].phase_b_backend == "deepseek-ai/DeepSeek-V4-Flash"
    assert MODE_PRESETS["minimal"].phase_b_backend is None
    # Phase A 生效后端一律确定性
    for m in MODE_PRESETS.values():
        assert m.llm_backend == "deterministic"
