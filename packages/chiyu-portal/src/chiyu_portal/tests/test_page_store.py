"""T5 页面生命周期（三段式全链路编排）。"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.particle import CORE_ROLES, ParticleTypeSet

from chiyu_portal.page_store import CreateResult, PageDraft, PageStore

TEST_PARTICLES = ParticleTypeSet(names=(*CORE_ROLES, "metric"))
ENTITY_MAP = {"供应商": "entity"}


def test_create_from_nl_valid_produces_draft():
    store = PageStore()
    r: CreateResult = store.create_page_from_nl(
        "展示供应商绩效", particle_types=TEST_PARTICLES, entity_map=ENTITY_MAP,
    )
    assert r.ok
    assert isinstance(r.draft, PageDraft)
    assert r.draft.confidence == 0.9
    assert not r.draft.published


def test_create_rejects_injection():
    store = PageStore()
    r = store.create_page_from_nl(
        "<script>alert(1)</script> 看板", particle_types=TEST_PARTICLES, entity_map=ENTITY_MAP,
    )
    assert not r.ok
    assert r.guard_reason != ""
    assert r.draft is None


def test_create_rejects_invalid_schema_no_draft():
    store = PageStore()
    # 实体未知 → 解析出无粒子类型 schema → 校验拒（未知粒子）
    r = store.create_page_from_nl(
        "展示神秘对象分布", particle_types=TEST_PARTICLES, entity_map=ENTITY_MAP,
    )
    assert not r.ok
    assert r.draft is None  # 未创建草稿
    assert r.errors  # 字段级校验错误


def test_publish_and_render():
    store = PageStore()
    r = store.create_page_from_nl(
        "展示供应商绩效", particle_types=TEST_PARTICLES, entity_map=ENTITY_MAP,
    )
    assert store.publish_page(r.draft.draft_id)
    rendered = store.render(r.draft.draft_id, particle_types=TEST_PARTICLES)
    assert rendered.ok
    assert "<!DOCTYPE html>" in rendered.html


def test_render_unknown_draft_fails():
    store = PageStore()
    rendered = store.render("nope", particle_types=TEST_PARTICLES)
    assert not rendered.ok


def test_draft_default_unpublished():
    store = PageStore()
    r = store.create_page_from_nl(
        "供应商看板", particle_types=TEST_PARTICLES, entity_map=ENTITY_MAP,
    )
    assert r.draft.published is False
    # 未发布不应影响渲染（渲染只依赖 schema）
    assert store.render(r.draft.draft_id, particle_types=TEST_PARTICLES).ok
