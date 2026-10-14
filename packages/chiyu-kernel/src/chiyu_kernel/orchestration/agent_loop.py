"""Agent-loop 轮次流（吸收 dsh `core/agent-loop`）：turn = 0..n step；
每 step = 一次模型请求 + 工具调用。pre-step 可改写/拒绝（dsh `agent/pre-step`）。
"""
from __future__ import annotations

import concurrent.futures
from typing import Any, List, Mapping, Optional

from chiyu_kernel.session import SessionManager


class AgentLoop:
    def __init__(self, *, llm, tools, sessions: SessionManager,
                 live_agents, redline_guard=None, loop_guard=None,
                 hook_bus=None, dispatch: str = "sequential") -> None:
        if dispatch not in ("sequential", "parallel"):
            raise ValueError(f"dispatch 非法：{dispatch}（仅 sequential/parallel）")
        self.llm = llm
        self.tools = tools
        self.sessions = sessions
        self.live_agents = live_agents
        self.redline_guard = redline_guard
        self.loop_guard = loop_guard
        self.hook_bus = hook_bus
        self.dispatch = dispatch

    def run_turn(self, agent_key: str, user_input: str) -> Mapping[str, Any]:
        agent = self.live_agents.get(agent_key)
        if agent is None:
            raise KeyError(f"未知 agent：{agent_key}")
        log = self.sessions.get_or_create(agent_key)
        log.append("user/message", {"content": user_input})

        messages = log.derive_messages()
        if agent.pre_step is not None:
            decided = agent.pre_step(messages)
            if decided is None:
                log.append("agent/pre-step", {"decision": "reject"})
                return {"rejected": True, "steps": 0,
                        "messages": log.derive_messages()}
            messages = decided
            log.append("agent/pre-step", {"decision": "enter"})

        steps = 0
        while True:
            resp = self.llm.stream_chat(messages)
            log.append("assistant/message", {"content": resp.content})
            messages.append({"role": "assistant", "content": resp.content})
            steps += 1
            calls = list(resp.tool_calls or [])
            if not calls:
                break
            # guard 环路卫生：重复提醒 + 预算终止
            if self.loop_guard is not None:
                verdict = self.loop_guard.on_step(step_no=steps, tool_calls=calls)
                if verdict is not None:
                    if verdict.reminder:
                        log.append("system/reminder", {"content": verdict.reminder})
                        messages.append({"role": "system", "content": verdict.reminder})
                    if verdict.terminate:
                        log.append("loop/terminated", {"reason": verdict.terminate})
                        break
            if self.dispatch == "parallel" and len(calls) > 1:
                with concurrent.futures.ThreadPoolExecutor(
                        max_workers=len(calls)) as pool:
                    futures = {pool.submit(self._exec_one, tc, agent, log, messages): tc
                               for tc in calls}
                    for f in concurrent.futures.as_completed(futures):
                        f.result()  # 异常不吞（fail-loud）
            else:
                for tc in calls:
                    self._exec_one(tc, agent, log, messages)
        if self.hook_bus is not None:
            self.hook_bus.run("Stop", agent_key, {"steps": steps})
        log.append("turn/end", {"steps": steps})
        return {"rejected": False, "steps": steps,
                "messages": log.derive_messages()}

    def _exec_one(self, tc, agent, log, messages) -> None:
        """执行单个工具调用（sequential/parallel 共享）；Parallel 时线程内调用。"""
        log.append("tool/call", {"name": tc.name, "args": tc.args})
        # PreToolUse 钩子可否决
        if self.hook_bus is not None:
            pre = self.hook_bus.run("PreToolUse", tc.name,
                                    {"args": tc.args})
            if any(r.decision in ("deny", "block") for r in pre):
                decision = pre[-1].decision
                log.append("tool/denied-by-hook",
                           {"name": tc.name, "decision": decision})
                messages.append({"role": "tool", "name": tc.name,
                                 "content": f"[denied by hook: {decision}]"})
                return
        result = self.tools.execute(
            tc.name, tc.args, scope=agent.tools_scope,
            redline_guard=self.redline_guard)
        log.append("tool/result", {"name": tc.name, "result": result})
        if self.hook_bus is not None:
            self.hook_bus.run("PostToolUse", tc.name,
                              {"result": str(result)})
        messages.append({"role": "tool", "name": tc.name,
                         "content": str(result)})


__all__ = ["AgentLoop"]
