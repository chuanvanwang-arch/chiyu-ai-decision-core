"""WS5 决策场景注册表 —— 单一事实源 + 变异自证。

核心断言（CRM F-05 / enterprise #6）：
- 未注册键在首调 `require_scenario` 时**抛 ValueError**（fail-fast，非运行期静默）。
- 键格式强制 kebab-case。
- 重复登记 ⇒ 抛 `ScenarioRegistryError`（单一注册，根治三态键分裂）。

判别力自证：本文件刻意断言「未注册键必须红」，若有人删掉
`require_scenario` 的未注册分支使其静默返回，本测试立即转红。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.api import (
    DecisionScenarioProfile,
    ScenarioRegistryError,
    clear_registry,
    is_registered,
    list_scenarios,
    register_scenario,
    require_scenario,
)
from chiyu_kernel.scenario.registry import _REGISTRY


@pytest.fixture(autouse=True)
def _isolate():
    clear_registry()
    yield
    clear_registry()


def test_register_then_list_is_single_source():
    p = register_scenario("config-change", title="配置变更决策")
    assert p.key == "config-change"
    assert is_registered("config-change")
    assert [s.key for s in list_scenarios()] == ["config-change"]


def test_duplicate_registration_is_rejected():
    register_scenario("config-change", title="配置变更决策")
    with pytest.raises(ScenarioRegistryError):
        register_scenario("config-change", title="再次登记同一键")


def test_kebab_key_format_enforced():
    # 下划线 / 大写 / 空 均非法（CRM 三态键分裂的根因之一）
    for bad in ("config_change", "Config-Change", "", "llm_config_change"):
        with pytest.raises(ScenarioRegistryError):
            register_scenario(bad, title="x")


def test_require_unregistered_key_raises_valueerror():
    """变异自证：未注册键首调必须抛 ValueError（非静默崩溃）。"""
    with pytest.raises(ValueError):
        require_scenario("config-change")


def test_require_registered_key_returns_profile():
    register_scenario(
        "config-change", title="配置变更决策",
        description="d", version="1.0.0", rubric="r", redline="g",
    )
    p = require_scenario("config-change")
    assert isinstance(p, DecisionScenarioProfile)
    assert p.title == "配置变更决策"
    assert p.version == "1.0.0"


def test_title_must_be_nonempty():
    with pytest.raises(ScenarioRegistryError):
        register_scenario("config-change", title="   ")


def test_registry_is_process_global_and_mutable():
    register_scenario("a-change", title="A")
    register_scenario("b-change", title="B")
    assert set(_REGISTRY) == {"a-change", "b-change"}


def test_key_format_switch_offs_kebab_and_accepts_upper_snake():
    """R3 自证（2026-10-09 CRM 回信）：键格式闸可插拨。

    CRM 销售域 22 键为 UPPER_SNAKE，且 `config_change`（治理留痕）与
    `config-change`（配置中心键写入）语义不同必须共存 ⇒ 禁止按字符串规范化判重。
    本测试：`set_key_format('none')` 后登记上划线/大写键合法，**且同键判重仍生效**。
    """
    from chiyu_kernel.api import key_format, set_key_format

    assert key_format() == "kebab"  # 默认历史行为不变
    set_key_format("none")
    try:
        p = register_scenario("LEAD_FOLLOW_UP", title="线索跟进")
        assert p.key == "LEAD_FOLLOW_UP"
        # none 模式下重复登记仍判重（单一事实源不因放宽格式而失守）
        with pytest.raises(ScenarioRegistryError):
            register_scenario("LEAD_FOLLOW_UP", title="重复")
        # 两个语义不同的键可共存（config_change ≢ config-change）
        register_scenario("config_change", title="治理留痕")
        register_scenario("config-change", title="配置中心键写入")
        assert is_registered("config_change")
        assert is_registered("config-change")
    finally:
        set_key_format("kebab")


def test_key_format_invalid_mode_rejected():
    """R3：非法模式必须抛（判别力：模式开关不是橡皮图章）。"""
    from chiyu_kernel.api import set_key_format

    with pytest.raises(ScenarioRegistryError):
        set_key_format("upper_snake")
