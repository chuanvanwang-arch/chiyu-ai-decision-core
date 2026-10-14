"""NL 解析层：自然语言 → 受控 Schema。⛔ 绝不产出 HTML（守卫 + 测试双重锁死）。

确定性规则映射（无 LLM 直出）。实体→粒子经注入 ``entity_map``；未识别实体 → 低置信 +
``needsClarification``。三段式中本层只产出 Schema，渲染器的 HTML 是另一层的事。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .schema import SCHEMA_VERSION

# 意图词 → 页面类型（缺省 dashboard）。顺序即优先级。
_TYPE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("工作台", "协作", "workspace"), "workspace"),
    (("审批", "审核", "approval"), "approval"),
    (("表单", "录入", "编辑", "form"), "form"),
    (("详情", "明细", "detail"), "detail"),
    (("表", "列表", "清单", "table"), "table"),
    (("看板", "dashboard", "指标", "总览", "概览"), "dashboard"),
)


@dataclass
class ParseResult:
    """解析结果：结构化 Schema（绝不 HTML）+ 置信度 + 是否需澄清。"""

    schema: dict[str, Any]
    confidence: float
    needs_clarification: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "confidence": self.confidence,
            "needsClarification": self.needs_clarification,
            "notes": self.notes,
        }


def parse_nl_to_schema(
    text: str,
    *,
    entity_map: dict[str, str] | None = None,
    title: str | None = None,
) -> ParseResult:
    """将自然语言描述解析为受控 Schema（绝不直出 HTML）。

    ``entity_map``：NL 实体词 → 粒子类型（消费方注入）。未命中 → 降置信 + needsClarification。
    """
    entity_map = entity_map or {}
    notes: list[str] = []

    schema_type = "dashboard"
    for keywords, t in _TYPE_RULES:
        if any(k in text for k in keywords):
            schema_type = t
            break

    particle_type: str | None = None
    for token, pt in entity_map.items():
        if token and token in text:
            particle_type = pt
            break

    confidence = 0.9
    needs = False
    if particle_type is None:
        confidence = 0.3
        needs = True
        notes.append("未识别实体，无法确定粒子类型")

    highlight = _detect_threshold(text)

    components: list[dict[str, Any]] = []
    if particle_type is not None:
        metric: dict[str, Any] = {
            "field": "value", "agg": "count", "label": "计数",
        }
        comp: dict[str, Any] = {
            "kind": "metric-card",
            "title": title or f"{schema_type} 视图",
            "dataBinding": {
                "source": "particle",
                "particleType": particle_type,
                "metrics": [metric],
            },
        }
        if highlight is not None:
            comp["style"] = {"highlight": highlight}
        components.append(comp)

    schema: dict[str, Any] = {
        "version": SCHEMA_VERSION,
        "type": schema_type,
        "title": title or f"{schema_type} 视图",
        "layout": {"columns": 2, "theme": "light"},
        "components": components,
    }
    return ParseResult(
        schema=schema, confidence=confidence,
        needs_clarification=needs, notes=notes,
    )


def _detect_threshold(text: str) -> dict[str, Any] | None:
    """阈值高亮：低于|小于|少于 X% → lt；高于|超过|大于|多于 X% → gt（红色）。"""
    m = re.search(r"(低于|小于|少于)\s*(\d+(?:\.\d+)?)\s*%?", text)
    if m:
        return {"field": "value", "op": "lt", "value": float(m.group(2)) / 100.0, "color": "red"}
    m = re.search(r"(高于|超过|大于|多于)\s*(\d+(?:\.\d+)?)\s*%?", text)
    if m:
        return {"field": "value", "op": "gt", "value": float(m.group(2)) / 100.0, "color": "red"}
    return None


__all__ = ["ParseResult", "parse_nl_to_schema"]
