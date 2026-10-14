"""智能体团队（吸收 dsh agent-team 的协作语义，中性化）：lead + 成员 + 共享任务 + 消息。

⛔ 内核层零领域：本模块只有通用协作原语；write_scope/allowlist 的**取值**由消费方
（enterprise 场景包 Action FQN 集）注入。产出纪律（[假设]/[数据] 标注）经
SharedTask.output_contract 透传，不做语义校验（语义在消费方 Output Guard）。
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

TEAM_MEMBER_CAP = 5
TEAM_TASK_STATES = ("pending", "claimed", "running", "done", "failed")
_TASK_TRANSITIONS = {
    ("pending", "claimed"), ("claimed", "running"),
    ("running", "done"), ("running", "failed"),
    ("claimed", "failed"),
}


@dataclass
class TeamMember:
    key: str
    role: str
    model_tier: str = "default"
    permission: str = "readonly"            # readonly | default | full
    action_allowlist: Tuple[str, ...] = ()  # 可调 Action FQN 集（权限天花板判定域）


@dataclass
class SharedTask:
    id: str
    title: str
    write_scope: Tuple[str, ...] = ()       # 本任务允许的 Action FQN 集（⊆ 场景包声明）
    output_contract: str = ""               # 产出纪律文本（含标注要求）
    status: str = "pending"
    owner: Optional[str] = None
    revision: int = 1


@dataclass
class TeamSpec:
    id: str
    name: str
    lead_key: str
    members: Dict[str, TeamMember] = field(default_factory=dict)
    scenario: str = ""                       # 来源场景包名（企业层填）
    lead_allowlist: Tuple[str, ...] = ()     # lead 可调 Action 集（空=不设限）


@dataclass
class TeamMessage:
    seq: int
    from_key: str
    to_key: str
    text: str


class TeamRegistry:
    """团队注册表：建团/成员/任务状态机/消息（纯内存，事件经 subscribe 回调外抛）。"""

    def __init__(self) -> None:
        self._teams: Dict[str, TeamSpec] = {}
        self._tasks: Dict[str, Dict[str, SharedTask]] = {}
        self._messages: Dict[str, List[TeamMessage]] = {}
        self._seq = itertools.count(1)
        self._subs: List[Callable[[str, Dict[str, Any]], None]] = []

    def subscribe(self, cb: Callable[[str, Dict[str, Any]], None]) -> None:
        self._subs.append(cb)

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        for cb in list(self._subs):
            cb(event_type, payload)

    # ── 团队 ──
    def create_team(self, spec: TeamSpec) -> Dict[str, Any]:
        if spec.id in self._teams:
            raise ValueError(f"团队已存在：{spec.id}")
        if len(spec.members) > TEAM_MEMBER_CAP:
            raise ValueError(f"成员数超上限：{len(spec.members)} > {TEAM_MEMBER_CAP}")
        if spec.lead_allowlist:
            for m in spec.members.values():
                over = [a for a in m.action_allowlist if a not in spec.lead_allowlist]
                if over:
                    raise ValueError(
                        f"权限天花板：成员 {m.key} 超出 lead 可调集 {over}")
        self._teams[spec.id] = spec
        self._tasks[spec.id] = {}
        self._messages[spec.id] = []
        self._emit("team/created", {"teamId": spec.id, "lead": spec.lead_key,
                                    "members": sorted(spec.members)})
        return {"teamId": spec.id, "revision": 1}

    def add_member(self, team_id: str, member: TeamMember) -> Dict[str, Any]:
        spec = self._team_or_raise(team_id)
        if len(spec.members) >= TEAM_MEMBER_CAP:
            raise ValueError(f"成员数超上限：{TEAM_MEMBER_CAP}")
        if spec.lead_allowlist:
            over = [a for a in member.action_allowlist if a not in spec.lead_allowlist]
            if over:
                raise ValueError(f"权限天花板：成员 {member.key} 超出 lead 可调集 {over}")
        spec.members[member.key] = member
        self._emit("team/member-added", {"teamId": team_id, "member": member.key})
        return {"teamId": team_id, "members": sorted(spec.members)}

    def remove_member(self, team_id: str, member_key: str) -> Dict[str, Any]:
        spec = self._team_or_raise(team_id)
        if member_key not in spec.members:
            raise KeyError(member_key)
        del spec.members[member_key]
        self._emit("team/member-removed", {"teamId": team_id, "member": member_key})
        return {"teamId": team_id, "members": sorted(spec.members)}

    # ── 任务 ──
    def create_task(self, team_id: str, task: SharedTask) -> Dict[str, Any]:
        self._team_or_raise(team_id)
        tasks = self._tasks[team_id]
        if task.id in tasks:
            raise ValueError(f"任务已存在：{task.id}")
        if task.status != "pending":
            raise ValueError(f"新任务须为 pending：{task.status}")
        tasks[task.id] = task
        self._emit("team/task-created", {"teamId": team_id, "task": task.id})
        return {"ref": {"id": task.id, "revision": task.revision}}

    def claim_task(self, team_id: str, task_id: str, *, member_key: str,
                   revision: int) -> Dict[str, Any]:
        task = self._task_or_raise(team_id, task_id)
        if task.revision != revision:
            raise RuntimeError(
                f"版本冲突：期望 {revision} 实际 {task.revision}")
        if task.status != "pending":
            raise RuntimeError(f"状态机非法：pending→{task.status} 仅可一次认领")
        task.status, task.owner = "claimed", member_key
        task.revision += 1
        self._emit("team/task-updated", {"teamId": team_id, "task": task_id,
                                          "status": task.status})
        return {"ref": {"id": task.id, "revision": task.revision},
                "status": task.status, "owner": task.owner}

    def update_task(self, team_id: str, task_id: str, *, revision: int,
                    status: str) -> Dict[str, Any]:
        task = self._task_or_raise(team_id, task_id)
        if task.revision != revision:
            raise RuntimeError(f"版本冲突：期望 {revision} 实际 {task.revision}")
        if (task.status, status) not in _TASK_TRANSITIONS:
            raise RuntimeError(f"状态机非法：{task.status} → {status}")
        task.status, task.revision = status, task.revision + 1
        self._emit("team/task-updated", {"teamId": team_id, "task": task_id,
                                          "status": task.status})
        return {"ref": {"id": task.id, "revision": task.revision},
                "status": task.status}

    # ── 消息 ──
    def send_message(self, team_id: str, *, from_key: str, to_key: str,
                     text: str) -> Dict[str, Any]:
        self._team_or_raise(team_id)
        msg = TeamMessage(seq=next(self._seq), from_key=from_key,
                          to_key=to_key, text=text)
        self._messages[team_id].append(msg)
        self._emit("team/message", {"teamId": team_id, "seq": msg.seq,
                                     "from": from_key, "to": to_key})
        return {"seq": msg.seq}

    # ── 看板 ──
    def board(self, team_id: str) -> Dict[str, Any]:
        spec = self._team_or_raise(team_id)
        return {
            "teamId": team_id, "name": spec.name, "scenario": spec.scenario,
            "lead": spec.lead_key,
            "members": [{"key": m.key, "role": m.role, "modelTier": m.model_tier,
                          "permission": m.permission}
                         for m in spec.members.values()],
            "tasks": [{"id": t.id, "title": t.title, "status": t.status,
                        "owner": t.owner, "revision": t.revision,
                        "writeScope": list(t.write_scope),
                        "outputContract": t.output_contract}
                       for t in self._tasks[team_id].values()],
            "messages": [{"seq": m.seq, "from": m.from_key, "to": m.to_key,
                           "text": m.text} for m in self._messages[team_id]],
        }

    def list_teams(self) -> List[Dict[str, Any]]:
        return [{"teamId": s.id, "name": s.name, "lead": s.lead_key,
                 "scenario": s.scenario, "memberCount": len(s.members)}
                for s in self._teams.values()]

    # ── 内部 ──
    def _team_or_raise(self, team_id: str) -> TeamSpec:
        spec = self._teams.get(team_id)
        if spec is None:
            raise KeyError(f"未知团队：{team_id}")
        return spec

    def _task_or_raise(self, team_id: str, task_id: str) -> SharedTask:
        self._team_or_raise(team_id)
        task = self._tasks[team_id].get(task_id)
        if task is None:
            raise KeyError(f"未知任务：{task_id}")
        return task


__all__ = ["TeamMember", "SharedTask", "TeamSpec", "TeamRegistry",
           "TEAM_MEMBER_CAP", "TEAM_TASK_STATES"]
