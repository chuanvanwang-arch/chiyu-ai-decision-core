"""事件总线（SKILL #8 的机制层）—— ★ 内核新建，demo 无此目录。

⛔ 与 `event` 表的关系
──────────────────────
`bj.event` 是**持久化事实源**（append-only）；本模块是**进程内分发**。
    bus.publish() → ① 落 event 表（持久，不可丢）→ ② 通知订阅者（可丢，可重放）
⛔ 顺序不可颠倒：先落库后分发。反了会出现"订阅者处理了但事件没留下"，
   回放时状态对不上（本项目已撞过同族缺陷：中间态静默）。

⛔ 订阅者异常不得中断发布（否则一个坏的订阅者让全系统的事件都发不出去），
   但必须**计数并留痕** —— 静默吞异常会让"事件发了但没人处理"永远不被发现。

⛔ Batch-2a（GAP-1）：必填面（id/event_type）改由 `contract/event.py` 的
   `EVENT_REQUIRED_FIELDS` 单一事实源驱动 —— 契约声明与总线执行同一份闭集。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping, Tuple

from chiyu_kernel.contract.event import (
    EVENT_ID_FIELD,
    EVENT_REQUIRED_FIELDS,
    EVENT_TYPE_FIELD,
)

Subscriber = Callable[[Mapping], None]


@dataclass
class PublishReport:
    event_id: str
    delivered: int = 0
    failed: Tuple[str, ...] = ()

    @property
    def healthy(self) -> bool:
        return not self.failed


class EventBus:
    def __init__(self) -> None:
        self._subs: Dict[str, List[Tuple[str, Subscriber]]] = {}

    def subscribe(self, event_type: str, name: str, fn: Subscriber) -> None:
        if not callable(fn):
            raise TypeError(f"订阅者必须可调用：{name}")
        self._subs.setdefault(event_type, []).append((name, fn))

    def subscribers(self, event_type: str) -> Tuple[str, ...]:
        return tuple(n for n, _ in self._subs.get(event_type, []))

    def publish(self, event: Mapping, persist: Callable[[Mapping], None]) -> PublishReport:
        """persist 先执行（持久化），再分发。"""
        missing = [f for f in EVENT_REQUIRED_FIELDS
                   if not str(event.get(f) or "").strip()]
        if missing:
            raise ValueError(
                f"事件缺必填字段 {missing}（合法面 {EVENT_REQUIRED_FIELDS}）"
                f"：拒收（无 id 无法回放去重、无 event_type 无人可收）")
        eid = str(event.get(EVENT_ID_FIELD))
        persist(event)                                  # ① 先落库
        delivered = 0
        failed: List[str] = []
        for name, fn in self._subs.get(str(event.get(EVENT_TYPE_FIELD)), []):
            try:
                fn(event)                               # ② 再分发
                delivered += 1
            except Exception:                           # noqa: BLE001
                failed.append(name)                     # 计数留痕，不静默
        return PublishReport(event_id=eid, delivered=delivered, failed=tuple(failed))


__all__ = ["EventBus", "PublishReport", "Subscriber"]
