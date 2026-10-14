"""事件总线守卫 —— 顺序、容错、留痕三条判据。

⛔ 顺序不可颠倒：**先落库后分发**。反了会出现"订阅者处理了但事件没留下"，回放时
   状态对不上（本项目已撞过同族缺陷：中间态静默）。
⛔ 订阅者异常不得中断发布（一个坏订阅者不能让全系统的事件都发不出去），但必须
   **计数并留痕** —— 静默吞异常会让"事件发了但没人处理"永远不被发现。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.events.bus import EventBus
from chiyu_kernel.events.subscribers import counting_subscriber, log_subscriber


def _boom(_e):
    raise RuntimeError("subscriber down")


def test_persist_precedes_dispatch():
    order: list[str] = []
    bus = EventBus()
    bus.subscribe("t", "s1", lambda e: order.append("dispatch"))
    bus.publish({"id": "e1", "event_type": "t"},
                persist=lambda e: order.append("persist"))
    assert order == ["persist", "dispatch"]


def test_persist_failure_propagates_and_does_not_dispatch():
    """⛔ 落库失败必须**上抛**（事件没留下 ⇒ 不得假装已分发）。"""
    seen: list[str] = []
    bus = EventBus()
    bus.subscribe("t", "s1", lambda e: seen.append("dispatch"))

    def _fail_persist(_e):
        raise RuntimeError("db down")

    with pytest.raises(RuntimeError, match="db down"):
        bus.publish({"id": "e1", "event_type": "t"}, persist=_fail_persist)
    assert seen == []


def test_subscriber_exception_does_not_block_others():
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("t", "bad", _boom)
    bus.subscribe("t", "good", lambda e: seen.append("ok"))
    rep = bus.publish({"id": "e1", "event_type": "t"}, persist=lambda e: None)
    assert seen == ["ok"]
    assert rep.delivered == 1
    assert rep.failed == ("bad",)          # 计数留痕，不静默
    assert rep.healthy is False
    assert rep.event_id == "e1"


def test_healthy_when_no_subscriber_fails():
    bus = EventBus()
    bus.subscribe("t", "ok", lambda e: None)
    rep = bus.publish({"id": "e1", "event_type": "t"}, persist=lambda e: None)
    assert rep.healthy is True and rep.failed == ()


def test_missing_event_id_is_rejected():
    bus = EventBus()
    # Batch-2a（GAP-1）：拒收文案改由 contract/event.py 必填面闭集驱动
    with pytest.raises(ValueError, match=r"缺必填字段 \['id'\]"):
        bus.publish({"event_type": "t"}, persist=lambda e: None)


def test_non_callable_subscriber_is_rejected():
    bus = EventBus()
    with pytest.raises(TypeError, match="可调用"):
        bus.subscribe("t", "oops", None)          # type: ignore[arg-type]


def test_dispatch_is_scoped_by_event_type():
    """订阅面按类型隔离：别的类型的事件不得被投递（否则订阅者要自己做类型判断）。"""
    bus = EventBus()
    got: list[str] = []
    bus.subscribe("a", "on_a", lambda e: got.append(str(e.get("id"))))
    bus.publish({"id": "e1", "event_type": "b"}, persist=lambda e: None)
    assert got == []
    bus.publish({"id": "e2", "event_type": "a"}, persist=lambda e: None)
    assert got == ["e2"]


def test_subscribers_listing_is_stable_and_ordered():
    bus = EventBus()
    bus.subscribe("t", "first", lambda e: None)
    bus.subscribe("t", "second", lambda e: None)
    assert bus.subscribers("t") == ("first", "second")
    assert bus.subscribers("nope") == ()


def test_unknown_event_type_with_no_subscribers_is_not_a_failure():
    bus = EventBus()
    rep = bus.publish({"id": "e1", "event_type": "untouched"}, persist=lambda e: None)
    assert rep.delivered == 0 and rep.failed == () and rep.healthy is True


def test_example_subscribers_are_deterministic_and_replayable():
    counter: dict = {}
    log: list = []
    bus = EventBus()
    bus.subscribe("t", "count", counting_subscriber(counter))
    bus.subscribe("t", "log", log_subscriber(log, prefix="#"))
    for i in range(3):
        bus.publish({"id": f"e{i}", "event_type": "t"}, persist=lambda e: None)
    assert counter == {"t": 3}
    assert log == ["#e0", "#e1", "#e2"]        # 可重放：顺序确定
