"""插件契约与注册表 —— Phase A「Everything is a Plugin」的内核落点（方案 1）。

深源：DeepSeek Harness 桌面版的「6 个内置插件 + 插件化架构」工程思路。
本仓映射：参照 CRM 的 `seedActions()` 注册表（动作注册 + 元数据）与 kernel 既有
`ActionRegistry` 范式，把「插件」正式化为内核一级能力注册表。

⛔ 本模块零领域字面量：插件只声明**能力槽位**（架构概念），具体能力清单是 L4
   （消费方域内容）。内置插件的名字（terminal/loop/subagent/web_search/team/voice）
   全是**架构能力标识**，不是业务域词，故不触发 domain-literal 守卫。
⛔ 插件绝不硬编码领域词、绝不反向 import 消费方；只通过 `TenantProfile`（L4）注入
   领域内容，守内核「零领域字面量」铁律。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class PluginSpec:
    """一个插件 = 一组**能力槽位**声明（不承载行为，行为由对应内核模块实现）。

    槽位设计对齐本仓既有分层：
        particle_types       → contract/particle（粒子类型集）
        actions              → actions/registry（R1–R6 动作表面）
        page_types           → chiyu_portal（可渲染页面类型）
        tools                → 工具名（终端/web_search 等）
        orchestration_hooks  → orchestration（agent 循环 / subagent / 团队）
        input_adapters       → 输入模态（text / voice）
    """

    name: str
    capability: str                       # 人类可读的能力族（架构概念）
    description: str = ""
    author: str = "builtin"
    particle_types: Tuple[str, ...] = field(default_factory=tuple)
    actions: Tuple[str, ...] = field(default_factory=tuple)
    page_types: Tuple[str, ...] = field(default_factory=tuple)
    tools: Tuple[str, ...] = field(default_factory=tuple)
    orchestration_hooks: Tuple[str, ...] = field(default_factory=tuple)
    input_adapters: Tuple[str, ...] = field(default_factory=tuple)

    def slots(self) -> Dict[str, Tuple[str, ...]]:
        """能力槽位总览（供菜单/观测面使用）。"""
        return {
            "particle_types": self.particle_types,
            "actions": self.actions,
            "page_types": self.page_types,
            "tools": self.tools,
            "orchestration_hooks": self.orchestration_hooks,
            "input_adapters": self.input_adapters,
        }


class PluginRegistry:
    """插件注册 / 发现 / 校验的**单一事实源**。

    范式对齐 `actions/registry.ActionRegistry`：注册期即拒绝重复，审计返回
    (errors, warnings)，errors 非空 ⇒ 不得发布。
    """

    def __init__(self) -> None:
        self._by_name: Dict[str, PluginSpec] = {}

    def register(self, spec: PluginSpec) -> None:
        if spec.name in self._by_name:
            raise ValueError(f"重复注册插件：{spec.name}")
        self._by_name[spec.name] = spec

    def get(self, name: str) -> Optional[PluginSpec]:
        return self._by_name.get(name)

    def names(self) -> Tuple[str, ...]:
        return tuple(sorted(self._by_name))

    def has(self, name: str) -> bool:
        return name in self._by_name

    def audit(self) -> Tuple[List[str], List[str]]:
        """返回 (errors, warnings)。errors 非空 ⇒ 表面不合规。"""
        errors: List[str] = []
        warnings: List[str] = []
        for name, spec in self._by_name.items():
            if not name.replace("_", "").isalnum():
                errors.append(f"插件名须为字母数字/下划线：{name}")
            if not spec.capability:
                errors.append(f"插件 {name} 缺 capability 声明")
            slots = spec.slots()
            if not any(slots.values()):
                warnings.append(
                    f"插件 {name} 未声明任何能力槽位（空插件？）")
        return errors, warnings

    def capabilities_of(self, name: str) -> Dict[str, Tuple[str, ...]]:
        spec = self._by_name.get(name)
        return spec.slots() if spec else {}


__all__ = ["PluginSpec", "PluginRegistry"]
