"""scenario 子包 —— 可运行场景包（模型 / 存储 / MCP 工具面）。

⛔ 门面纪律：本 `__all__` 必须与 `chiyu_kernel.api` 同步（守卫
`test_api_facade_covers_all_layers.py` 逐层比对，scenario 已入 LAYERS）。
"""
from .model import (
    KNOWLEDGE_LAYERS,
    LEVEL_IDS,
    ScenarioPack,
    ScenarioPackError,
    ScenarioStep,
    from_dict,
)
from .store import ScenarioPackStore
from .mcp import ScenarioPackLockDenied, build_in_memory_server
from .registry import (
    ScenarioRegistryError,
    DecisionScenarioProfile,
    register_scenario,
    get_scenario,
    require_scenario,
    list_scenarios,
    is_registered,
    clear_registry,
)

__all__ = [
    "LEVEL_IDS",
    "KNOWLEDGE_LAYERS",
    "ScenarioPackError",
    "ScenarioStep",
    "ScenarioPack",
    "from_dict",
    "ScenarioPackStore",
    "ScenarioPackLockDenied",
    "build_in_memory_server",
    # 决策场景注册表（WS5：单一事实源，根治 CRM 三态键分裂）
    "ScenarioRegistryError",
    "DecisionScenarioProfile",
    "register_scenario",
    "get_scenario",
    "require_scenario",
    "list_scenarios",
    "is_registered",
    "clear_registry",
]
