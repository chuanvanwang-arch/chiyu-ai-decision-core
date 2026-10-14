"""事件载荷三层结构校验（GAP-1 机制上迁，Batch-2a，2026-10-14）。

上迁源：APS `platform/event_payload.py`（P1-2，借 6.1.2「事件标准载荷
JSON Schema 三层 + Schema Registry 强校验」）。**只上迁机制，不搬域值**：
APS 预置的域事件契约（unit.published/run.done…）与 coerce 的域键清单
（case_id/unit_key/order_no…）一律剥离 —— 域契约由消费方自行
`register_schema` 登记（零领域字面量铁律）。

三层有穷枚举与不变式在 `contract/event.py`（词汇单一事实源）；
本模块是机制层：结构契约注册表 + 强校验 + 平面载荷分层搬迁。

设计要点（从 APS 逐条继承并有守卫）：
  · 未登记事件类型 **fail-open**（不臆断结构；诚实优于强校验的幻觉）；
  · 已登记类型缺必填字段 / 未知层 ⇒ 拒（`validate_payload` 返回问题列表，
    由发射方显式处理，不静默发射）；
  · 部分层传允许（存量升级路径，不强制补全）。
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from chiyu_kernel.contract.event import (
    EVENT_PAYLOAD_TYPES,
    PAYLOAD_LAYERS,
)

#: 结构契约注册表：{etype: {layer: {"required": [...], "types": {...}}}}
#: 只登记**语义明确**的事件类型；未登记 → fail-open。
_SCHEMAS: Dict[str, Dict[str, Dict[str, Any]]] = {}


def register_schema(etype: str, schema: Mapping[str, Mapping[str, Any]]) -> None:
    """登记某事件类型的结构契约。形如::

        {
          "metadata": {"required": ["emitted_at"], "types": {"emitted_at": "number"}},
          "context":  {"required": ["unit_key"], "types": {"unit_key": "string"}},
          "impact_domain": {"required": [], "types": {}},
        }

    层名必须 ∈ `PAYLOAD_LAYERS`（契约闭集）；只注册语义明确的契约，
    不确定结构的事件**不要登记**（fail-open 更诚实）。
    """
    for layer in schema:
        if layer not in PAYLOAD_LAYERS:
            raise ValueError(f"非法载荷层 {layer!r}（合法值 {PAYLOAD_LAYERS}）")
    _SCHEMAS[str(etype)] = {str(layer): dict(schema[layer]) for layer in schema}


def has_schema(etype: str) -> bool:
    return str(etype) in _SCHEMAS


def payload_schema(etype: str) -> Optional[Dict[str, Dict[str, Any]]]:
    return _SCHEMAS.get(str(etype))


def clear_schemas() -> None:
    """清空注册表（仅供测试/消费方重建隔离用；运行期不应调用）。"""
    _SCHEMAS.clear()


def _type_matches(value: Any, expected: str) -> bool:
    if expected not in EVENT_PAYLOAD_TYPES:
        return True  # 未知期望类型不臆断
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "list":
        return isinstance(value, (list, tuple))
    if expected == "dict":
        return isinstance(value, dict)
    return value is not None  # "any"


def validate_payload(etype: str, payload: Mapping[str, Any]) -> List[str]:
    """强校验：已登记 etype 的载荷是否符合结构契约。返回问题列表。

    - 未登记 etype → `[]`（fail-open，**不臆断结构**）；
    - 已登记：未知层 / required 缺失 / 类型不匹配 ⇒ 逐条列出；
    - 已传的层不强制补全（调用方传了部分层也放行，不破坏存量）。
    """
    schema = _SCHEMAS.get(str(etype))
    if schema is None:
        return []  # fail-open

    issues: List[str] = []
    for layer in PAYLOAD_LAYERS:
        spec = schema.get(layer, {})
        layer_payload = payload.get(layer)
        if layer_payload is None:
            continue  # 未传该层，不强制
        if not isinstance(layer_payload, Mapping):
            issues.append(f"{etype}.{layer} 必须是 dict，"
                          f"实际 {type(layer_payload).__name__}")
            continue
        for req in spec.get("required", ()):
            if layer_payload.get(req) in (None, ""):
                issues.append(f"{etype}.{layer}.{req} 缺失（required）")
        for fname, exp in (spec.get("types") or {}).items():
            if fname in layer_payload and not _type_matches(layer_payload[fname], exp):
                issues.append(
                    f"{etype}.{layer}.{fname} 类型应为 {exp}，"
                    f"实际 {type(layer_payload[fname]).__name__}")
    for k in payload:
        if k not in PAYLOAD_LAYERS:
            issues.append(f"{etype} 含未知层 {k!r}（合法层 {PAYLOAD_LAYERS}）")
    return issues


def coerce_payload(payload: Mapping[str, Any], *,
                   context_keys: Iterable[str] = ()) -> Dict[str, Any]:
    """把平面载荷自动包成三层（升级路径，老调用方不需逐个改）。

    `context_keys`（消费方注入的域键清单）里的键进 `context`，其余进
    `metadata`；`impact_domain` 恒为 `{}`（调用方显式填才非空）。
    ⛔ 本函数**只做分层搬迁，不校验** —— 校验交给 `validate_payload`（显式）；
    ⛔ 域键由调用方声明（默认空 ⇒ 全进 metadata），内核不持域键清单。
    """
    ctx_keys = {str(k) for k in context_keys}
    out: Dict[str, Any] = {"metadata": {}, "context": {}, "impact_domain": {}}
    for k, v in payload.items():
        if str(k) in ctx_keys:
            out["context"][k] = v
        else:
            out["metadata"][k] = v
    return out


__all__ = [
    "register_schema", "has_schema", "payload_schema", "clear_schemas",
    "validate_payload", "coerce_payload",
]
