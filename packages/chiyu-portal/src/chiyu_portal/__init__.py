"""chiyu-portal —— 免代码门户（NL→受控 Schema→渲染器，#7）。

三段式：NL → 受控 Schema → 运行时渲染器。渲染器是唯一渲染出口，Schema 是唯一输入。
本模块是唯一公开门面，全部公共符号经 ``api`` 重导出。
"""
from __future__ import annotations

from .api import (
    SCHEMA_VERSION, PAGE_TYPES, COMPONENT_KINDS, THEMES, FILTER_OPS,
    AGG_FUNCS, DEFAULT_ALLOWED_ACTIONS, GuardResult, guard_nl_input,
    ParseResult, parse_nl_to_schema, RenderResult, render_page,
    ValidationError, validate_page_schema, CreateResult, PageDraft, PageStore,
    onboarding_steps, mode_cards, level_cards, workflow_cards,
    direction_cards, render_onboarding, OnboardingResult,
)

__all__ = [
    "SCHEMA_VERSION", "PAGE_TYPES", "COMPONENT_KINDS", "THEMES", "FILTER_OPS",
    "AGG_FUNCS", "DEFAULT_ALLOWED_ACTIONS", "GuardResult", "guard_nl_input",
    "ParseResult", "parse_nl_to_schema", "RenderResult", "render_page",
    "ValidationError", "validate_page_schema", "CreateResult", "PageDraft", "PageStore",
    "onboarding_steps", "mode_cards", "level_cards", "workflow_cards",
    "direction_cards", "render_onboarding", "OnboardingResult",
]
