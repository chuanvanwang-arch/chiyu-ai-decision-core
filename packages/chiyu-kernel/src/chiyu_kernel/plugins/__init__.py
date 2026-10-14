"""chiyu_kernel.plugins —— Phase A「Everything is a Plugin」内核能力注册表。

⛔ 本包是 L1 基础设施（与 orchestration/actions 同级），消费方经 `chiyu_kernel.api`
   门面访问（不 import 本内部路径）。本包零领域字面量、零 IO。
"""
from __future__ import annotations

from .contract import PluginRegistry, PluginSpec
from .builtins import BUILTIN_PLUGINS, register_builtins
from .modes import (
    DEFAULT_MODE_ID,
    MODE_PRESETS,
    WorkMode,
    active_plugins,
    disabled_plugins,
    mode_ids,
    resolve_work_mode,
)

__all__ = [
    # contract
    "PluginSpec", "PluginRegistry",
    # builtins
    "BUILTIN_PLUGINS", "register_builtins",
    # modes
    "WorkMode", "MODE_PRESETS", "DEFAULT_MODE_ID",
    "mode_ids", "active_plugins", "disabled_plugins", "resolve_work_mode",
]
