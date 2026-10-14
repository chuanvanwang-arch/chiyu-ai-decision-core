"""事件契约 —— L0 词汇与不变式（GAP-1，Batch-2a，2026-10-14）。

定位：进程内事件总线（`chiyu_kernel/events/`）与事件载荷三层校验的
**词汇单一事实源**。此前 events 只有 impl 无 sanctioned contract，消费方
（APS `platform/events.py` / enterprise `agent_dispatch`）被迫 import 内部
路径，违反 sanctioned 面纪律（APS 盘点 §四 GAP-1）。

⛔ 本层零第三方依赖、零 IO、零领域字面量：只声明词汇与不变式。
   域事件契约（如某域 `unit.published` 的结构约束）由消费方经
   `chiyu_kernel.events.register_schema` 自行登记，内核不预置任何域契约。

⛔ 顺序铁律（bus.publish 的可执行判据，不是注释）：**先落库后分发**。
   反了会出现"订阅者处理了但事件没留下"，回放时状态对不上。
"""
from __future__ import annotations

from typing import Tuple

# ── 事件必填面（bus.publish 的拒收判据）────────────────────────────────
#: 事件唯一标识字段。缺它 ⇒ 无法回放与去重，bus 拒收。
#: 【G1 语义登记·2026-10-14，CRM 实施报告】两层 id 勿在契约混同：
#: 进程内 bus.emit 可增发单调自增临时 id（evt_N 形态，订阅去重/追踪用）；
#: 持久化事件的**权威 id** 由消费方 DB 唯一收敛点分配（如 CRM recordEvent）。
#: 契约不把两层 id 合一表述——混同即丢失「落库前事件无权威 id」的语义。
EVENT_ID_FIELD = "id"
#: 事件类型字段。订阅者按它路由；缺它 ⇒ 事件发了但无人能收到。
EVENT_TYPE_FIELD = "event_type"
#: 事件必填字段闭集（bus.publish 逐项校验，缺一即拒）。
EVENT_REQUIRED_FIELDS: Tuple[str, ...] = (EVENT_ID_FIELD, EVENT_TYPE_FIELD)

# ── 载荷三层结构（APS event_payload.py 机制上迁的本地方言）─────────────
#: 三层有穷枚举：发射元数据 / 上下文 / 影响域。顺序即结构契约的层序。
PAYLOAD_LAYERS: Tuple[str, ...] = ("metadata", "context", "impact_domain")
#: 结构契约版本（Registry 演进语义；消费方登记契约时声明）。
EVENT_PAYLOAD_SCHEMA_VERSION = "1.0"
#: 结构契约支持的字段类型闭集（未知期望类型不臆断，见 payload 实现）。
EVENT_PAYLOAD_TYPES: Tuple[str, ...] = (
    "number", "string", "boolean", "list", "dict", "any")

# ── 不变式（有守卫测试，不是注释）────────────────────────────────────
#: 发布不变式：持久化先于分发；订阅者异常计数留痕（不静默吞）；必填面齐才发。
PUBLISH_INVARIANTS: Tuple[str, ...] = (
    "persist_before_dispatch",
    "subscriber_failure_counted_not_silent",
    "event_id_required",
    "event_type_required",
)
#: 载荷结构契约不变式：未登记事件类型 fail-open（不臆断结构）；已登记则
#: 缺必填字段/未知层必须拒；部分层传允许（不破坏存量升级路径）。
PAYLOAD_INVARIANTS: Tuple[str, ...] = (
    "unregistered_etype_fail_open",
    "registered_missing_required_rejected",
    "unknown_layer_rejected",
    "partial_layers_allowed",
)

__all__ = [
    "EVENT_ID_FIELD", "EVENT_TYPE_FIELD", "EVENT_REQUIRED_FIELDS",
    "PAYLOAD_LAYERS", "EVENT_PAYLOAD_SCHEMA_VERSION", "EVENT_PAYLOAD_TYPES",
    "PUBLISH_INVARIANTS", "PAYLOAD_INVARIANTS",
]
