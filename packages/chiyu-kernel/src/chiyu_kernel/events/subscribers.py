"""事件订阅者集合（SKILL #8 机制层的**示例接线**，可随时替换）。

内核只提供**机制**（bus.py）；具体订阅逻辑由消费方注入。
本模块给出一个**确定性示例**（零领域词）：计数订阅者，供测试与演示装配。
"""
from __future__ import annotations

from typing import Callable, Mapping

from .bus import Subscriber


def counting_subscriber(counter: dict) -> Subscriber:
    """返回一个事件计数订阅者（幂等、可重放；每收到一次事件就计一次数）。"""
    def _on(event: Mapping) -> None:
        key = str(event.get("event_type") or "?")
        counter[key] = counter.get(key, 0) + 1
    return _on


def log_subscriber(log: list, *, prefix: str = "") -> Subscriber:
    """把事件追加到给定 list（作留痕；供测试断言事件序）。"""
    def _on(event: Mapping) -> None:
        log.append(f"{prefix}{event.get('id')}")
    return _on


__all__ = ["counting_subscriber", "log_subscriber"]
