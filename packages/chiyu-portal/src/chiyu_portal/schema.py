"""chiyu-portal 受控页面 Schema 协议（零领域字面量）。

三段式：NL → 受控 Schema → 运行时渲染器。本模块是 **Schema 层**（结构化中间表示），
定义协议常量与校验器。渲染器（`renderer.py`）是唯一渲染出口，且渲染前会再次调用
`validate_page_schema` —— 非法 Schema 必须被拒（不是「尽力渲染」）。

⛔ 粒子类型 / 动作经**注入**，框架层零硬编码业务字面量。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from chiyu_kernel.contract.particle import ParticleTypeSet

# ── 协议常量（形态，无业务取值）────────────────────────────────────────
PAGE_TYPES: tuple[str, ...] = (
    "dashboard", "table", "form", "detail", "workspace", "approval",
    "conversation",
)
COMPONENT_KINDS: tuple[str, ...] = (
    "metric-card", "table", "form", "detail",
    "reasoning-trace", "approval-queue", "conflict-marker",
    "goal-form", "interaction-panel", "acceptance-checklist",
    "chat-log", "composer", "goal-bar",
)
THEMES: tuple[str, ...] = ("light", "dark")
FILTER_OPS: tuple[str, ...] = ("eq", "ne", "lt", "gt", "lte", "gte", "in")
AGG_FUNCS: tuple[str, ...] = ("count", "sum", "avg", "min", "max", "latest")

# 框架级默认动作白名单（消费方注入其完整 ActionRegistry 覆盖）
DEFAULT_ALLOWED_ACTIONS: tuple[str, ...] = (
    "data-particle-read", "data-particle-write", "page-reload", "aiattr-generate",
)

SCHEMA_VERSION = "0.2"


@dataclass(frozen=True)
class ValidationError:
    """字段级校验错误（路径定位，便于前端逐字段回显）。"""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def validate_page_schema(
    schema: dict[str, Any],
    *,
    particle_types: ParticleTypeSet,
    allowed_actions: Iterable[str] | None = None,
    status_fields: Iterable[str] = (),
    snapshot_fields: Iterable[str] = (),
) -> tuple[ValidationError, ...]:
    """校验受控页面 Schema。返回字段级错误元组（空 = 通过）。

    ⛔ 判别力自证要点（均须被拒，非静默映射）：
      - 未知 particleType / 页面类型 / 组件类型
      - 非白名单 action
      - 非法过滤算子 / 聚合函数
      - 状态字段非 eq 或聚合
      - 快照字段非 latest
    """
    if not isinstance(schema, dict):
        return (ValidationError("schema", "Schema 必须是对象"),)

    errors: list[ValidationError] = []

    version = schema.get("version")
    if version is not None and version != SCHEMA_VERSION:
        errors.append(ValidationError("version", f"不支持的 version: {version!r}"))

    ptype = schema.get("type")
    if ptype is not None and ptype not in PAGE_TYPES:
        errors.append(ValidationError("type", f"未知页面类型: {ptype!r}"))

    layout = schema.get("layout")
    if isinstance(layout, dict):
        theme = layout.get("theme")
        if theme is not None and theme not in THEMES:
            errors.append(ValidationError("layout.theme", f"未知主题: {theme!r}"))

    actions = set(allowed_actions) if allowed_actions is not None else set(DEFAULT_ALLOWED_ACTIONS)
    status_set = set(status_fields)
    snapshot_set = set(snapshot_fields)

    for i, comp in enumerate(_iter_components(schema)):
        cpath = f"components[{i}]"
        kind = comp.get("kind")
        if kind is not None and kind not in COMPONENT_KINDS:
            errors.append(ValidationError(f"{cpath}.kind", f"未知组件类型: {kind!r}"))

        binding = comp.get("dataBinding")
        if isinstance(binding, dict):
            _validate_binding(
                binding, f"{cpath}.dataBinding", errors,
                particle_types, status_set, snapshot_set,
            )

        for j, act in enumerate(comp.get("actions", []) or []):
            apath = f"{cpath}.actions[{j}]"
            aname = act.get("action") if isinstance(act, dict) else None
            if aname is not None and aname not in actions:
                errors.append(ValidationError(f"{apath}.action", f"非白名单动作: {aname!r}"))

    return tuple(errors)


def _iter_components(schema: dict[str, Any]) -> list[dict]:
    comps = schema.get("components")
    return comps if isinstance(comps, list) else []


def _validate_binding(
    binding: dict[str, Any], path: str, errors: list[ValidationError],
    particle_types: ParticleTypeSet, status_set: set[str], snapshot_set: set[str],
) -> None:
    src = binding.get("source")
    if src is not None and src != "particle":
        errors.append(ValidationError(f"{path}.source", f"仅支持 particle 数据源: {src!r}"))

    pt = binding.get("particleType")
    if pt is not None and pt not in particle_types.names:
        errors.append(ValidationError(f"{path}.particleType", f"未知粒子类型: {pt!r}（受控枚举）"))

    for fi, f in enumerate(binding.get("filters", []) or []):
        if not isinstance(f, dict):
            continue
        fpath = f"{path}.filters[{fi}]"
        op = f.get("op")
        field_name = f.get("field")
        if op is not None and op not in FILTER_OPS:
            errors.append(ValidationError(f"{fpath}.op", f"非法过滤算子: {op!r}"))
        if field_name in status_set and op is not None and op != "eq":
            errors.append(ValidationError(f"{fpath}.op", f"状态字段仅支持 eq: {field_name!r}"))

    for mi, m in enumerate(binding.get("metrics", []) or []):
        if not isinstance(m, dict):
            continue
        mpath = f"{path}.metrics[{mi}]"
        agg = m.get("agg")
        field_name = m.get("field")
        if agg is not None and agg not in AGG_FUNCS:
            errors.append(ValidationError(f"{mpath}.agg", f"非法聚合函数: {agg!r}"))
        if field_name in status_set and agg is not None:
            errors.append(ValidationError(f"{mpath}.agg", f"状态字段不可聚合: {field_name!r}"))
        if field_name in snapshot_set and agg is not None and agg != "latest":
            errors.append(ValidationError(f"{mpath}.agg", f"快照字段仅支持 latest: {field_name!r}"))


__all__ = [
    "PAGE_TYPES", "COMPONENT_KINDS", "THEMES", "FILTER_OPS", "AGG_FUNCS",
    "DEFAULT_ALLOWED_ACTIONS", "SCHEMA_VERSION", "ValidationError", "validate_page_schema",
]
