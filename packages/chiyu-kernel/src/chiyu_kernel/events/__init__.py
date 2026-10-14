"""事件子系统 —— 进程内总线（SKILL #8 机制层；★ 内核新建，demo 无此目录）。

Batch-2a（GAP-1）：契约面 `contract/event.py`（必填面 / 载荷三层词汇 /
不变式）+ 载荷三层校验机制 `payload.py`（APS event_payload 机制上迁，
域契约留消费方登记）。
"""
from .bus import EventBus, PublishReport, Subscriber
from .payload import (
    clear_schemas,
    coerce_payload,
    has_schema,
    payload_schema,
    register_schema,
    validate_payload,
)
from .subscribers import counting_subscriber, log_subscriber

__all__ = ["EventBus", "PublishReport", "Subscriber",
           "counting_subscriber", "log_subscriber",
           # payload（GAP-1：载荷三层结构校验机制）
           "register_schema", "has_schema", "payload_schema", "clear_schemas",
           "validate_payload", "coerce_payload"]
