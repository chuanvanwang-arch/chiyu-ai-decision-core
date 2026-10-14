"""Agent 接口与 live 注册表（吸收 dsh `core/agent`）。
⛔ 与 `agent_registry.py` 的区别：后者是**契约注册表**（key/contract_task_id/success，
守 brainstorming 生命契约）；本模块是**运行时** Agent（系统提示 / 工具作用域 / pre-step 钩子）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class Agent:
    key: str
    system_prompt: str = ""
    tools_scope: str = ""
    pre_step: Optional[Callable] = None   # (messages)->messages|None（改写/拒绝）


class LiveAgentRegistry:
    def __init__(self) -> None:
        self._by_key: Dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._by_key[agent.key] = agent

    def get(self, key: str) -> Optional[Agent]:
        return self._by_key.get(key)

    def keys(self) -> List[str]:
        return sorted(self._by_key)


__all__ = ["Agent", "LiveAgentRegistry"]
