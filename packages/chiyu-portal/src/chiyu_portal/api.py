"""chiyu-portal 唯一公开门面（T5 收口 · 完整导出）。

三段式：NL → 受控 Schema → 运行时渲染器。渲染器是唯一渲染出口，Schema 是唯一输入。
"""
from __future__ import annotations

from .schema import (
    SCHEMA_VERSION, PAGE_TYPES, COMPONENT_KINDS, THEMES, FILTER_OPS,
    AGG_FUNCS, DEFAULT_ALLOWED_ACTIONS, ValidationError, validate_page_schema,
)
from .guardrails import GuardResult, guard_nl_input
from .nl_parser import ParseResult, parse_nl_to_schema
from .renderer import RenderResult, render_page, render_conversation
from .page_store import CreateResult, PageDraft, PageStore
from .onboarding import (
    OnboardingResult, mode_cards, level_cards, workflow_cards,
    direction_cards, onboarding_steps, render_onboarding,
)

__all__ = [
    "SCHEMA_VERSION", "PAGE_TYPES", "COMPONENT_KINDS", "THEMES", "FILTER_OPS",
    "AGG_FUNCS", "DEFAULT_ALLOWED_ACTIONS",
    "GuardResult", "guard_nl_input",
    "ParseResult", "parse_nl_to_schema",
    "RenderResult", "render_page", "render_conversation",
    "ValidationError", "validate_page_schema",
    "CreateResult", "PageDraft", "PageStore",
    "onboarding_steps", "mode_cards", "level_cards", "workflow_cards",
    "direction_cards", "render_onboarding", "OnboardingResult",
]
