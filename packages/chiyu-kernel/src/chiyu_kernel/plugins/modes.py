"""四种工作模式（对标 DeepSeek Harness 桌面版）—— Phase A 声明式预设。

深源四模式：标准 / PTC(Plan-Then-Code) / 极简 / 创造。
本仓落点：每个模式 = **插件组合 + 编排开关**的声明，存于 `MODE_PRESETS`；
CLI/Portal 从 registry 读菜单与引导式 nav。

⛔ Phase A 边界（已与用户确认）：本仓当前为**确定性运行时**
   （`chiyu-cli` 决策走确定性分支、不接真 LLM；`chiyu-decision.run_spine` 亦确定性）。
   故四模式在 A 阶段先以「编排契约 + 双端入口 + 确定性桩」落地；真正需要 LLM
   驱动的行为（PTC 先写小程序、创造写插件）在 `phase_b_backend` 字段留接口，
   等 Phase B 接 `deepseek-ai/DeepSeek-V4-Flash`（llm/tier.py 已预留云端端点）激活。

`llm_backend`：Phase A 生效值，全为 "deterministic"（零 IO、不接真模型）。
`phase_b_backend`：Phase B 目标后端；None 表示无需 LLM（极简模式永远确定性）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class WorkMode:
    """一个工作模式 = 启用的插件 + 编排开关 + LLM 后端声明。"""

    id: str                              # standard / ptc / minimal / creative
    label: str
    description: str
    plugins: Tuple[str, ...] = field(default_factory=tuple)
    orchestration: Dict[str, object] = field(default_factory=dict)
    llm_backend: str = "deterministic"   # Phase A 生效值
    phase_b_backend: Optional[str] = None  # Phase B 目标（None=无需 LLM）
    default: bool = False


# ── 出厂预设（单一事实源）────────────────────────────────────────────────────
MODE_PRESETS: Dict[str, WorkMode] = {
    "standard": WorkMode(
        id="standard",
        label="标准模式",
        description="全能力默认编排：6 插件全开 + 确定性决策脊柱；Phase B 接 DeepSeek 走 auto 路径。",
        plugins=("terminal", "loop", "subagent", "web_search", "team"),
        orchestration={"portal": True, "nav": True, "script_plan_slot": False},
        llm_backend="deterministic",
        phase_b_backend="deepseek-ai/DeepSeek-V4-Flash",
        default=True,
    ),
    "ptc": WorkMode(
        id="ptc",
        label="PTC 模式",
        description="先写「小程序/编排脚本」再批量调工具：开启脚本规划槽位，Agent 先生成幂等计划再批量 dispatch。",
        plugins=("terminal", "loop", "web_search"),
        orchestration={"portal": True, "nav": True, "script_plan_slot": True},
        llm_backend="deterministic",
        phase_b_backend="deepseek-ai/DeepSeek-V4-Flash",
    ),
    "minimal": WorkMode(
        id="minimal",
        label="极简模式",
        description="仅终端：隐藏门户与导航，只剩 chiyu shell + 受限对话环；最快上手、最小心智负担。",
        plugins=("terminal",),
        orchestration={"portal": False, "nav": False, "portal_hidden": True},
        llm_backend="deterministic",
        phase_b_backend=None,
    ),
    "creative": WorkMode(
        id="creative",
        label="创造模式",
        description="Everything is a Plugin：全插件 + voice + 自定义 hook，开放插件注册与模式声明框架。",
        plugins=("terminal", "loop", "subagent", "web_search", "team", "voice"),
        orchestration={"portal": True, "nav": True, "custom_plugin_registry": True,
                       "custom_mode_def": True},
        llm_backend="deterministic",
        phase_b_backend="deepseek-ai/DeepSeek-V4-Flash",
    ),
}

DEFAULT_MODE_ID = "standard"


def mode_ids() -> Tuple[str, ...]:
    return tuple(sorted(MODE_PRESETS))


def active_plugins(mode: WorkMode, registry: object = None) -> Tuple[str, ...]:
    """模式启用的插件中、确实存在于 registry 的子集（注册表未知项被静默剔除，不崩）。"""
    if registry is None:
        return mode.plugins
    known = getattr(registry, "has", None)
    if known is None:
        return mode.plugins
    return tuple(p for p in mode.plugins if known(p))


def disabled_plugins(mode: WorkMode, registry: object = None) -> Tuple[str, ...]:
    """被本模式惰性关闭的插件（registry 全集 − 启用集）。"""
    if registry is None:
        return ()
    names = getattr(registry, "names", None)
    if names is None:
        return ()
    enabled = set(mode.plugins)
    return tuple(p for p in names() if p not in enabled)


def resolve_work_mode(mode_id: Optional[str], registry: object = None
                      ) -> Tuple[WorkMode, Tuple[str, ...], Tuple[str, ...], List[str]]:
    """解析工作模式。**永不抛异常**（顶层防御，对齐 dispatch_cfg 范式）。

    返回 `(mode, enabled_plugins, disabled_plugins, warnings)`。
    `mode_id` 为 None/空 ⇒ 回落 DEFAULT_MODE_ID；未知 id ⇒ 回落默认并记 warning。
    """
    warnings: List[str] = []
    mid = (mode_id or "").strip().lower()
    if not mid:
        mid = DEFAULT_MODE_ID
    mode = MODE_PRESETS.get(mid)
    if mode is None:
        warnings.append(
            f"未知工作模式 {mid!r} ⇒ 回落默认 {DEFAULT_MODE_ID!r}")
        mode = MODE_PRESETS[DEFAULT_MODE_ID]
    enabled = active_plugins(mode, registry)
    missing = tuple(p for p in mode.plugins if p not in enabled)
    if missing:
        warnings.append(
            f"模式 {mode.id} 引用了未注册插件 {missing}（已被静默剔除）")
    return mode, enabled, disabled_plugins(mode, registry), warnings


__all__ = ["WorkMode", "MODE_PRESETS", "DEFAULT_MODE_ID",
           "mode_ids", "active_plugins", "disabled_plugins", "resolve_work_mode"]
