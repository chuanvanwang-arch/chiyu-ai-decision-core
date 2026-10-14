"""渲染层：受控 Schema → HTML。⛔ 唯一渲染出口；渲染前再校验；动态值全转义；
交互仅 data-action 声明式；输出强制无 <script> / on*=。纵深防御第三层。

⛔ 判别力：非法 Schema 直接拒绝（返回字段级错误），绝不尽力渲染。
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any, Iterable

from .schema import SCHEMA_VERSION, ValidationError, validate_page_schema

_SCRIPT_RE = re.compile(r"<\s*script", re.IGNORECASE)
_ONATTR_RE = re.compile(r"\son\w+\s*=", re.IGNORECASE)


@dataclass
class RenderResult:
    """渲染结果。``ok=False`` 时携带字段级错误（非法 Schema 被拒）。"""

    ok: bool
    html: str = ""
    errors: tuple[ValidationError, ...] = ()

    def __bool__(self) -> bool:
        return self.ok


def render_page(
    schema: dict[str, Any],
    *,
    particle_types: Any,
    allowed_actions: Iterable[str] | None = None,
    status_fields: Iterable[str] = (),
    snapshot_fields: Iterable[str] = (),
) -> RenderResult:
    """渲染受控 Schema 为 HTML。非法 Schema 拒绝（字段级错误），绝不尽力渲染。"""
    errors = validate_page_schema(
        schema, particle_types=particle_types,
        allowed_actions=allowed_actions, status_fields=status_fields,
        snapshot_fields=snapshot_fields,
    )
    if errors:
        return RenderResult(False, errors=errors)

    out: list[str] = []
    out.append("<!DOCTYPE html>")
    out.append('<html lang="zh"><head><meta charset="utf-8">')
    out.append("<title>" + html.escape(str(schema.get("title", ""))) + "</title>")
    out.append('<link rel="stylesheet" href="/portal/page.css">')
    out.append("</head><body>")
    out.append('<main class="portal-page">')
    out.append('<h1 class="page-title">' + html.escape(str(schema.get("title", ""))) + "</h1>")
    for comp in schema.get("components", []) or []:
        out.append(_render_component(comp))
    out.append("</main></body></html>")

    rendered = "".join(out)
    # 渲染层硬闸门：不得出现 script / 内联事件属性
    if _SCRIPT_RE.search(rendered) or _ONATTR_RE.search(rendered):
        return RenderResult(False, errors=(ValidationError("render", "渲染产物含禁用标记"),))
    return RenderResult(True, html=rendered)


def _render_component(comp: dict[str, Any]) -> str:
    kind = html.escape(str(comp.get("kind", "")))
    title = html.escape(str(comp.get("title", "")))
    parts: list[str] = [f'<section class="component component-{kind}">']
    parts.append(f'<h2 class="component-title">{title}</h2>')
    binding = comp.get("dataBinding")
    if isinstance(binding, dict):
        pt = html.escape(str(binding.get("particleType", "")))
        parts.append(f'<div class="binding" data-particle-type="{pt}">')
        for m in binding.get("metrics", []) or []:
            if not isinstance(m, dict):
                continue
            label = html.escape(str(m.get("label", "")))
            field = html.escape(str(m.get("field", "")))
            parts.append(f'<span class="metric" data-field="{field}">{label}</span>')
        parts.append("</div>")
    for act in comp.get("actions", []) or []:
        if not isinstance(act, dict):
            continue
        label = html.escape(str(act.get("label", "")))
        action = html.escape(str(act.get("action", "")))
        # 交互仅声明式 data-action，无 onclick / 内联 JS
        parts.append(f'<button class="action-btn" data-action="{action}">{label}</button>')
    parts.append("</section>")
    return "".join(parts)


def render_conversation(
    *,
    events: Any = None,
    composer_action: str = "send_message",
    goal: str = "",
) -> "RenderResult":
    """渲染 dsh 式对话页：session 日志 + 目标栏 + composer。

    声明式 ``data-action``，无内联 JS；复用渲染层硬闸门（无 <script> / on*=）。
    ``events`` 形如 ``[{"role": "user"|"assistant", "content": ...}]`` 或
    ``[{"kind": "user/message"|"assistant/message", "payload": {"content": ...}}]``
    （兼容 SessionEvent 形态，零领域字面量）。
    """
    out: list[str] = []
    out.append("<!DOCTYPE html>")
    out.append('<html lang="zh"><head><meta charset="utf-8">'
               '<title>对话</title><link rel="stylesheet" href="/portal/page.css"></head><body>')
    out.append('<main class="portal-page conversation-page">')
    if goal:
        out.append(f'<div class="goal-bar">{html.escape(goal)}</div>')
    out.append('<section class="component component-chat-log">'
               '<h2 class="component-title">对话</h2><div class="chat-log">')
    for ev in events or []:
        role = html.escape(str(ev.get("role", ev.get("kind", ""))))
        payload = ev.get("payload") or {}
        content = html.escape(str(ev.get("content", payload.get("content", ""))))
        out.append(f'<div class="msg msg-{role}">'
                   f'<span class="role">{role}</span>'
                   f'<span class="text">{content}</span></div>')
    out.append('</div></section>')
    out.append(f'<form class="composer" data-action="{html.escape(composer_action)}">'
               '<input name="message" class="composer-input" placeholder="输入消息…" '
               'autocomplete="off">'
               '<button type="submit" class="action-btn">发送</button></form>')
    out.append('</main></body></html>')

    rendered = "".join(out)
    if _SCRIPT_RE.search(rendered) or _ONATTR_RE.search(rendered):
        return RenderResult(False, errors=(ValidationError("render", "渲染产物含禁用标记"),))
    return RenderResult(True, html=rendered)


__all__ = ["RenderResult", "render_page", "render_conversation"]
