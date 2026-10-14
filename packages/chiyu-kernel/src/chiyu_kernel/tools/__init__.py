"""工具注册与守卫管线（吸收 dsh `core/tools`）：作用域注册 + pre/post-execute 守卫。

⛔ 与 `actions` 的关系：`actions` 是消费方 Action 表面（R1–R6，机制），
   本模块是**模型面工具**注册表（智能体可调用的能力），二者正交、不混。
⛔ 作用域隔离：scope="" 为全局；agent 只调得到自己 scope 或全局工具（越权即拒）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class ToolSpec:
    name: str
    description: str
    scope: str = ""            # "" = 全局可见
    high_risk: bool = False


class ToolNotFound(LookupError):
    pass


class ScopeDenied(PermissionError):
    pass


class GuardDenied(PermissionError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, ToolSpec] = {}
        self._impls: Dict[str, Callable] = {}

    def register(self, spec: ToolSpec, impl: Callable) -> None:
        if spec.name in self._specs:
            raise ValueError(f"重复注册 tool：{spec.name}")
        self._specs[spec.name] = spec
        self._impls[spec.name] = impl

    def spec(self, name: str) -> Optional[ToolSpec]:
        return self._specs.get(name)

    def get(self, name: str) -> Optional[Callable]:
        return self._impls.get(name)

    def unregister(self, name: str) -> None:
        self._specs.pop(name, None)
        self._impls.pop(name, None)

    def names(self, scope: str = "") -> Tuple[str, ...]:
        return tuple(
            n for n, s in self._specs.items() if s.scope in ("", scope)
        )

    def scoped(self, scope: str) -> "ToolRegistry":
        sub = ToolRegistry()
        for n, s in self._specs.items():
            if s.scope in ("", scope):
                sub._specs[n] = s
                sub._impls[n] = self._impls[n]
        return sub

    def execute(
        self, name: str, args: Any, *, scope: str = "", redline_guard=None
    ) -> Any:
        spec = self._specs.get(name)
        if spec is None:
            raise ToolNotFound(name)
        if spec.scope not in ("", scope):           # 越权拒绝
            raise ScopeDenied(f"tool {name} scope={spec.scope!r} 不可被 scope={scope!r} 调用")
        if redline_guard is not None:               # 红线硬闸门
            verdict = redline_guard(name, args)
            if verdict is not None:
                raise GuardDenied(f"tool {name} 被红线拦截：{verdict}")
        impl = self._impls[name]
        return impl(args)                            # post-execute 可在此扩展钩子


__all__ = [
    "ToolSpec", "ToolRegistry", "ToolNotFound", "ScopeDenied", "GuardDenied",
]
