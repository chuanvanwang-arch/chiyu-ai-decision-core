"""CLI 侧的插件/模式辅助（薄封装，避免各命令重复装配 registry）。

⛔ 只从 `chiyu_kernel.api`/公开门面取插件能力，不 import 内核内部路径。
"""
from __future__ import annotations

# ⛔ 走门面而非内部路径（`chiyu_kernel.plugins`）：sanctioned import 面见
#    docs/sanctioned-import-surface.md，由 tools/check_import_surface.py 机械校验。
from chiyu_kernel.api import (
    MODE_PRESETS,
    PluginRegistry,
    register_builtins,
    resolve_work_mode,
)


def build_registry() -> PluginRegistry:
    """装配含 6 个内置插件的 registry。"""
    reg = PluginRegistry()
    register_builtins(reg)
    return reg


def resolve(mode_id: str | None):
    """解析工作模式，返回 (WorkMode, enabled, disabled, warnings)。永不抛。"""
    return resolve_work_mode(mode_id, build_registry())


def mode_summary_lines() -> list[str]:
    """给 `chiyu modes` 用的多行摘要。"""
    reg = build_registry()
    lines: list[str] = []
    for mid in sorted(MODE_PRESETS):
        mode = MODE_PRESETS[mid]
        _, enabled, disabled, _ = resolve(mid)
        flag = "（默认）" if mode.default else ""
        lines.append(f"● {mode.id}{flag} —— {mode.label}")
        lines.append(f"    {mode.description}")
        lines.append(f"    启用插件：{', '.join(enabled) or '（无）'}")
        if disabled:
            lines.append(f"    惰性关闭：{', '.join(disabled)}")
        if mode.phase_b_backend:
            lines.append(f"    Phase B 后端：{mode.phase_b_backend}")
    return lines
