"""T4 渲染层（唯一出口·转义·data-action·无 script）。"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.particle import CORE_ROLES, ParticleTypeSet

from chiyu_portal.renderer import RenderResult, render_page
from chiyu_portal.schema import SCHEMA_VERSION

TEST_PARTICLES = ParticleTypeSet(names=(*CORE_ROLES, "metric"))


def _valid_schema() -> dict:
    return {
        "version": SCHEMA_VERSION,
        "type": "dashboard",
        "title": "合格率看板",
        "layout": {"columns": 2, "theme": "light"},
        "components": [
            {
                "kind": "metric-card",
                "title": "计数",
                "dataBinding": {
                    "source": "particle",
                    "particleType": "metric",
                    "metrics": [{"field": "value", "agg": "count", "label": "计数"}],
                },
                "actions": [{"label": "刷新", "action": "data-particle-read"}],
            }
        ],
    }


def test_valid_schema_renders_html():
    r = render_page(_valid_schema(), particle_types=TEST_PARTICLES)
    assert r.ok
    assert isinstance(r.html, str)
    assert "<!DOCTYPE html>" in r.html
    assert "合格率看板" in r.html  # 标题转义后可见


def test_render_escapes_dynamic_values():
    s = _valid_schema()
    s["title"] = "<b>注入</b>"
    s["components"][0]["title"] = "<script>alert(1)</script>"
    r = render_page(s, particle_types=TEST_PARTICLES)
    assert r.ok
    assert "<b>注入</b>" not in r.html
    assert "&lt;b&gt;注入&lt;/b&gt;" in r.html
    assert "<script>alert(1)</script>" not in r.html


def test_render_action_is_declarative_not_onclick():
    r = render_page(_valid_schema(), particle_types=TEST_PARTICLES)
    assert 'data-action="data-particle-read"' in r.html
    assert "onclick" not in r.html


def test_render_output_has_no_script_tag():
    r = render_page(_valid_schema(), particle_types=TEST_PARTICLES)
    assert _no_script(r.html)


def test_invalid_schema_rejected_with_field_errors():
    s = _valid_schema()
    s["components"][0]["dataBinding"]["particleType"] = "UNKNOWN_PARTICLE"
    r = render_page(s, particle_types=TEST_PARTICLES)
    assert not r.ok
    assert r.html == ""
    assert any("particleType" in e.path for e in r.errors)


def test_render_is_only_html_emitter_in_pipeline():
    """C-P1/C-P2 锁死：渲染层是唯一 HTML 出口；非法 Schema 不产生任何 HTML 片段。"""
    r = render_page(_valid_schema(), particle_types=TEST_PARTICLES)
    assert r.ok
    # 渲染产物不含内联事件属性
    assert "onerror" not in r.html
    assert "onload" not in r.html


def _no_script(html_text: str) -> bool:
    return "<script" not in html_text.lower()


def test_render_result_dataclass():
    rr = RenderResult(True, html="<x>")
    assert bool(rr)
    assert not bool(RenderResult(False))
