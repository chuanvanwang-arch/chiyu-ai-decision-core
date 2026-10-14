"""子智能体委派 —— dsh `subagent` 能力吸收（L2）+ 治理三缰绳。

忠实吸收 dsh subagent 的**委派语义**：一个子 agent 拥有 role / instruction / tools_scope，
被父 agent 委派一个任务后，经阶段一已落地的 `AgentLoop` 跑一轮到完成，返回结果。

治理扩展（2026-09-26 编排设计 §阶段1）：depth_limit / max_concurrent / tier 分层 LLM
/ configure 运行时调整——三缰绳由 SubagentPool 强制，防失控递归与并发打爆；tier
映射可把「lead 类任务」路由到更强的 LLM（provider_switch 的 openai_compat 接续点）。

⛔ 不引入 dsh 的 out-of-process / ACP / continuation 机制——本仓已有 `AgentLoop` 与
`LiveAgentRegistry`，委派即「构造一个 live agent 并跑一轮」，避免平行 driver 框架（R2）。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from chiyu_kernel.orchestration.agent_loop import AgentLoop
from chiyu_kernel.orchestration.agent_runtime import Agent, LiveAgentRegistry
from chiyu_kernel.llm.client import LlmProvider
from chiyu_kernel.session import SessionManager
from chiyu_kernel.tools import ToolRegistry


@dataclass
class SubagentDescriptor:
    """子智能体描述（dsh `descriptor` 的内存简化版 + 治理三缰绳）。"""

    key: str
    role: str
    instruction: str
    tools_scope: str = ""
    tier: str = "default"
    depth_limit: int = 2        # 递归层级缰绳：后代派发深度上限
    max_concurrent: int = 1     # 并发缰绳：同 key 在途委派上限
    pre_step: Optional[Callable[[Mapping[str, Any]], Optional[Mapping[str, Any]]]] = None

    def live_key(self) -> str:
        """在 live registry 中的唯一 agent key（避免与父 agent 撞名）。"""
        return f"sub:{self.key}"


class SubagentPool:
    """子智能体委派池：register 描述 → delegate 跑一轮（深度/并发缰绳 + tier 分层 LLM）。

    复用阶段一的 `AgentLoop` / `LiveAgentRegistry`，不在本模块重建运行时。
    """

    def __init__(
        self,
        *,
        llm: LlmProvider,
        tools: ToolRegistry,
        sessions: SessionManager,
        redline_guard=None,
        llm_by_tier: Optional[Mapping[str, LlmProvider]] = None,
    ) -> None:
        self._llm = llm
        self._llm_by_tier: dict[str, LlmProvider] = dict(llm_by_tier or {})
        self._tools = tools
        self._sessions = sessions
        self._redline_guard = redline_guard
        self._descs: dict[str, SubagentDescriptor] = {}
        self._live = LiveAgentRegistry()
        self._depth: dict[str, int] = {}      # live_key → 已处深度
        self._inflight: dict[str, int] = {}   # key → 在途委派数
        self._lock = threading.Lock()

    def register(self, desc: SubagentDescriptor) -> None:
        if not isinstance(desc, SubagentDescriptor):
            raise TypeError("desc 须为 SubagentDescriptor")
        self._descs[desc.key] = desc
        self._live.register(Agent(
            key=desc.live_key(),
            system_prompt=desc.instruction,
            tools_scope=desc.tools_scope,
            pre_step=desc.pre_step,
        ))

    def configure(self, key: str, *, depth_limit: Optional[int] = None,
                  max_concurrent: Optional[int] = None,
                  tier: Optional[str] = None) -> None:
        """运行时调整治理缰绳（dsh subagent.config.set 的内核承接点）。"""
        desc = self._descs.get(key)
        if desc is None:
            raise KeyError(key)
        if depth_limit is not None:
            if not isinstance(depth_limit, int) or depth_limit < 1:
                raise ValueError(f"depth_limit 须为 >=1 整数：{depth_limit}")
            desc.depth_limit = depth_limit
        if max_concurrent is not None:
            if not isinstance(max_concurrent, int) or max_concurrent < 1:
                raise ValueError(f"max_concurrent 须为 >=1 整数：{max_concurrent}")
            desc.max_concurrent = max_concurrent
        if tier is not None:
            desc.tier = tier

    def describe_all(self) -> list[dict[str, Any]]:
        """全量描述快照（subagent.config.get 数据源）。"""
        return [{"key": d.key, "role": d.role, "tier": d.tier,
                 "depth_limit": d.depth_limit,
                 "max_concurrent": d.max_concurrent,
                 "tools_scope": d.tools_scope}
                for d in self._descs.values()]

    def depth_of(self, live_key: str) -> int:
        return self._depth.get(live_key, 0)

    def _llm_for(self, desc: SubagentDescriptor) -> LlmProvider:
        return self._llm_by_tier.get(desc.tier, self._llm)

    def delegate(self, task: str, *, subagent_key: str,
                 parent_session_id: Optional[str] = None) -> Mapping[str, Any]:
        if subagent_key not in self._descs:
            raise KeyError(subagent_key)
        desc = self._descs[subagent_key]
        # 深度缰绳：parent 是某子会话（sub:*）→ child 深度 = parent 深度 + 1
        child_depth = 0
        if parent_session_id and str(parent_session_id).startswith("sub:"):
            child_depth = self._depth.get(str(parent_session_id), 0) + 1
            if child_depth >= desc.depth_limit:
                raise RuntimeError(
                    f"subagent depth_limit exceeded: {subagent_key} "
                    f"depth={child_depth} >= limit={desc.depth_limit}")
        # 并发缰绳：同 key 在途数达上限 → 拒绝（不静默排队）
        with self._lock:
            if self._inflight.get(subagent_key, 0) >= desc.max_concurrent:
                raise RuntimeError(
                    f"subagent max_concurrent exceeded: {subagent_key} "
                    f"inflight={self._inflight.get(subagent_key, 0)} "
                    f">= limit={desc.max_concurrent}")
            self._inflight[subagent_key] = self._inflight.get(subagent_key, 0) + 1
        try:
            loop = AgentLoop(
                llm=self._llm_for(desc),
                tools=self._tools,
                sessions=self._sessions,
                live_agents=self._live,
                redline_guard=self._redline_guard,
            )
            if parent_session_id:
                self._depth[desc.live_key()] = child_depth
            return loop.run_turn(desc.live_key(), task)
        finally:
            with self._lock:
                self._inflight[subagent_key] = max(
                    0, self._inflight.get(subagent_key, 0) - 1)


__all__ = ["SubagentDescriptor", "SubagentPool"]
