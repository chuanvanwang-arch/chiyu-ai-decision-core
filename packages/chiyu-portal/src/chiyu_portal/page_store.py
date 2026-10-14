"""页面生命周期：护栏 → 解析 → 校验 → 落库 draft → 发布。

无 PG 可全绿（内存存储，便于测试；消费方可替换为真实存储）。
三段式全链路在此编排：``guard_nl_input`` → ``parse_nl_to_schema`` → ``validate_page_schema``。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from .guardrails import GuardResult, guard_nl_input
from .nl_parser import ParseResult, parse_nl_to_schema
from .renderer import RenderResult, render_page
from .schema import ValidationError, validate_page_schema


@dataclass
class PageDraft:
    """页面草稿（未发布）。"""

    draft_id: str
    schema: dict[str, Any]
    confidence: float
    needs_clarification: bool
    notes: list[str] = field(default_factory=list)
    published: bool = False


@dataclass
class CreateResult:
    """创建结果。``ok=False`` 时携带护栏原因或字段级校验错误。"""

    ok: bool
    draft: PageDraft | None = None
    errors: tuple[ValidationError, ...] = ()
    guard_reason: str = ""

    def __bool__(self) -> bool:
        return self.ok


class PageStore:
    """内存页面存储（无 PG 依赖）。消费方应替换为真实持久层。"""

    def __init__(self) -> None:
        self._drafts: dict[str, PageDraft] = {}

    def create_page_from_nl(
        self,
        text: str,
        *,
        particle_types: Any,
        entity_map: dict[str, str] | None = None,
        allowed_actions=None,
        status_fields: Any = (),
        snapshot_fields: Any = (),
    ) -> CreateResult:
        guard: GuardResult = guard_nl_input(text)
        if not guard:
            return CreateResult(False, guard_reason=guard.reason)

        parsed: ParseResult = parse_nl_to_schema(text, entity_map=entity_map)
        # 实体未识别（低置信 / needsClarification）→ 无粒子绑定，不应落草稿
        if parsed.needs_clarification:
            return CreateResult(
                False, errors=(ValidationError("nl", "实体未识别，需澄清后再生成页面"),),
            )
        errors = validate_page_schema(
            parsed.schema, particle_types=particle_types,
            allowed_actions=allowed_actions, status_fields=status_fields,
            snapshot_fields=snapshot_fields,
        )
        if errors:
            return CreateResult(False, errors=errors)

        draft = PageDraft(
            draft_id=uuid.uuid4().hex,
            schema=parsed.schema,
            confidence=parsed.confidence,
            needs_clarification=parsed.needs_clarification,
            notes=parsed.notes,
        )
        self._drafts[draft.draft_id] = draft
        return CreateResult(True, draft=draft)

    def publish_page(self, draft_id: str) -> bool:
        draft = self._drafts.get(draft_id)
        if draft is None:
            return False
        draft.published = True
        return True

    def render(self, draft_id: str, **kwargs: Any) -> RenderResult:
        draft = self._drafts.get(draft_id)
        if draft is None:
            return RenderResult(False, errors=(ValidationError("draft", "草稿不存在"),))
        return render_page(draft.schema, **kwargs)


__all__ = ["PageDraft", "CreateResult", "PageStore"]
