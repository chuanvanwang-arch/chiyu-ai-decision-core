"""6 个内置插件（对标 DeepSeek Harness 桌面版）—— 全部映射到本仓既有内核能力。

映射表（深源 → 本仓落点）：
    terminal     → chiyu-cli 受限命令壳（shell 命令表面）
    loop         → orchestration.state_machine + dispatch_cfg（agent 循环 / 派发）
    subagent     → orchestration.idem + agent_registry（幂等子任务 / 智能体注册）
    web_search   → 外部检索工具（Phase A 仅声明槽位；Phase B 接 DeepSeek 激活）
    team         → orchestration 多智能体协作（agent_team hook）
    voice        → 输入适配器（voice 模态；Phase A 仅声明，Phase B 接 DeepSeek 激活）

⛔ 每个插件只声明能力槽位，行为由对应内核模块实现；插件本身不含业务逻辑、
   不含领域词。Phase B 接真 LLM 后，web_search / voice / loop(在创造模式下) 的
   动态行为才被真正激活。
"""
from __future__ import annotations

from typing import Tuple

from .contract import PluginRegistry, PluginSpec

BUILTIN_PLUGINS: Tuple[PluginSpec, ...] = (
    PluginSpec(
        name="terminal",
        capability="受限命令壳",
        description="终端命令表面：decide / render / readiness / selftest（白名单外一律拒绝）。",
        tools=("shell",),
        input_adapters=("text",),
        actions=("decide", "render_page", "readiness", "selftest"),
        page_types=("terminal",),
    ),
    PluginSpec(
        name="loop",
        capability="智能体循环",
        description="任务状态机驱动的 agent 循环 + 派发参数（并发/退避/锁）。",
        orchestration_hooks=("agent_loop", "dispatch"),
        tools=("dispatch",),
    ),
    PluginSpec(
        name="subagent",
        capability="子智能体",
        description="幂等子任务（idem）+ 智能体注册闸（agent_registry）。",
        orchestration_hooks=("subagent",),
        actions=("spawn_subagent",),
        tools=("idem",),
    ),
    PluginSpec(
        name="web_search",
        capability="网页搜索",
        description="外部检索工具。Phase A 仅声明槽位；Phase B 接 DeepSeek 后激活。",
        tools=("web_search",),
        orchestration_hooks=("web_search",),
    ),
    PluginSpec(
        name="team",
        capability="智能体团队",
        description="多智能体协作（agent_team hook）：派发/汇总/冲突仲裁。",
        orchestration_hooks=("agent_team",),
        actions=("spawn_team",),
    ),
    PluginSpec(
        name="voice",
        capability="语音输入",
        description="语音输入适配器。Phase A 仅声明槽位；Phase B 接 DeepSeek 后激活。",
        input_adapters=("voice", "text"),
    ),
)


def register_builtins(registry: PluginRegistry) -> None:
    """把 6 个内置插件注册进给定 registry（幂等：重复注册抛错由 registry 负责）。"""
    for spec in BUILTIN_PLUGINS:
        registry.register(spec)


__all__ = ["BUILTIN_PLUGINS", "register_builtins"]
