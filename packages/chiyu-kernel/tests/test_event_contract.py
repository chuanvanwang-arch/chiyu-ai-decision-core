"""GAP-1 事件契约 + 载荷三层机制守卫（Batch-2a，2026-10-14）。

判据面：
  · 契约与门面同一对象（再导出无漂移）；
  · 必填面闭集 + bus 拒收（缺 id / 缺 event_type 都拒）；
  · 载荷注册表 fail-open / 已登记拒缺字段 / 未知层拒 / 层名闭集；
  · coerce 域键由调用方注入（内核零域键清单）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.api import (
    EVENT_REQUIRED_FIELDS,
    PAYLOAD_LAYERS,
    PUBLISH_INVARIANTS,
    EventBus,
    clear_schemas,
    coerce_payload,
    has_schema,
    payload_schema,
    register_schema,
    validate_payload,
)
from chiyu_kernel.contract import event as event_contract


def test_contract_and_facade_same_object():
    assert EVENT_REQUIRED_FIELDS is event_contract.EVENT_REQUIRED_FIELDS
    assert PAYLOAD_LAYERS is event_contract.PAYLOAD_LAYERS
    assert PUBLISH_INVARIANTS is event_contract.PUBLISH_INVARIANTS


def test_event_required_fields_closed():
    assert set(EVENT_REQUIRED_FIELDS) == {"id", "event_type"}
    assert "persist_before_dispatch" in PUBLISH_INVARIANTS
    assert "subscriber_failure_counted_not_silent" in PUBLISH_INVARIANTS


def test_bus_rejects_missing_required_fields():
    bus = EventBus()
    with pytest.raises(ValueError, match="event_type"):
        bus.publish({"id": "e1"}, persist=lambda e: None)      # 缺 event_type
    with pytest.raises(ValueError, match="id"):
        bus.publish({"event_type": "t"}, persist=lambda e: None)  # 缺 id


def test_payload_registry_fail_open_unregistered():
    clear_schemas()
    assert has_schema("whatever.type") is False
    assert payload_schema("whatever.type") is None
    # 未登记 ⇒ 不臆断结构，直接放行
    assert validate_payload("whatever.type", {"metadata": {"x": 1}}) == []


def test_payload_registered_missing_required_rejected():
    clear_schemas()
    register_schema("demo.emitted", {
        "metadata": {"required": ["emitted_at"], "types": {"emitted_at": "number"}},
    })
    assert has_schema("demo.emitted") is True
    assert payload_schema("demo.emitted")["metadata"]["required"] == ["emitted_at"]
    # 类型不符 ⇒ 问题列表非空
    issues = validate_payload("demo.emitted", {"metadata": {"emitted_at": "soon"}})
    assert any("类型应为 number" in i for i in issues)
    # 合规 ⇒ 空
    assert validate_payload("demo.emitted", {"metadata": {"emitted_at": 1.0}}) == []


def test_payload_unknown_layer_rejected():
    clear_schemas()
    register_schema("demo.typed", {"metadata": {"required": [], "types": {}}})
    issues = validate_payload("demo.typed", {"bogus": {}})
    assert any("未知层" in i for i in issues)


def test_payload_register_rejects_unknown_layer():
    with pytest.raises(ValueError, match="非法载荷层"):
        register_schema("demo.bad", {"nope": {}})


def test_coerce_payload_context_keys_injected_by_caller():
    out = coerce_payload({"a": 1, "case_id": "c1"}, context_keys=("case_id",))
    assert out["context"] == {"case_id": "c1"}
    assert out["metadata"] == {"a": 1}
    assert out["impact_domain"] == {}
    # 不传 context_keys ⇒ 全进 metadata（内核不持域键清单）
    out2 = coerce_payload({"case_id": "c1"})
    assert out2["metadata"] == {"case_id": "c1"}
    assert out2["context"] == {}
