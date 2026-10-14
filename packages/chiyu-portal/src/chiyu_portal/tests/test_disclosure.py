"""T5 披露纪律 §13.2 + 三段式无绕过路径扫描。

⛔ 对外面不得出现权属/内部核查要素字样。包源码与渲染产物均须零残留。
"""
from __future__ import annotations

import pathlib
import re

import pytest

from chiyu_kernel.contract.particle import CORE_ROLES, ParticleTypeSet

from chiyu_portal.renderer import render_page
from chiyu_portal.schema import SCHEMA_VERSION

PKG_ROOT = pathlib.Path(__file__).resolve().parent.parent
# §13.2 禁用清单（与项目披露扫描一致，按概念扫描而非按单词）
DENY_RE = re.compile(r"专利|[A-H] ?件|实施例|权 ?[0-9]|7[×xX*]7|九尺子|八要素|七尺子|S1→S5|K-M-D")

TEST_PARTICLES = ParticleTypeSet(names=(*CORE_ROLES, "metric"))


# 已知受控的静态 HTML 产出模块（豁免本守卫）。
# onboarding.py 的引导式导航页是**平台固定的硬编码静态页**，不经 NL→Schema→renderer
# 动态路径，内容为平台自身产出而非用户 NL 输入，故豁免；
# 其余任何模块若新增动态/用户内容驱动的 HTML 产出仍会被本守卫捕获。
_HTML_EMITTER_ALLOWLIST = {"onboarding.py"}


def _prod_modules() -> list[pathlib.Path]:
    """仅扫描生产模块（chiyu_portal/*.py），排除 tests/、渲染层本身、以及受控静态产出模块。"""
    return [f for f in sorted(PKG_ROOT.glob("*.py"))
            if f.name != "renderer.py" and f.name not in _HTML_EMITTER_ALLOWLIST]


def test_no_disclosure_tokens_in_source():
    hits: list[str] = []
    for f in _prod_modules():
        text = f.read_text(encoding="utf-8")
        for m in DENY_RE.finditer(text):
            hits.append(f"{f.name}: {m.group(0)!r}")
    assert not hits, "包源码命中 §13.2 禁用字样: " + "; ".join(hits)


def test_no_html_emitter_outside_renderer():
    """C-P1 锁死：除 renderer 外，guardrails/nl_parser/schema/page_store 不得构造 HTML 输出。"""
    html_marker = re.compile(r"<!DOCTYPE html>|<html|</html>", re.IGNORECASE)
    offenders: list[str] = []
    for f in _prod_modules():
        text = f.read_text(encoding="utf-8")
        if html_marker.search(text):
            offenders.append(f.name)
    assert not offenders, "非渲染层模块构造 HTML 输出: " + ", ".join(offenders)


def test_rendered_output_no_disclosure_tokens():
    schema = {
        "version": SCHEMA_VERSION,
        "type": "dashboard",
        "title": "中性看板",
        "layout": {"columns": 2, "theme": "light"},
        "components": [
            {
                "kind": "metric-card",
                "title": "计数",
                "dataBinding": {
                    "source": "particle", "particleType": "metric",
                    "metrics": [{"field": "value", "agg": "count", "label": "计数"}],
                },
            }
        ],
    }
    r = render_page(schema, particle_types=TEST_PARTICLES)
    assert r.ok
    assert not DENY_RE.search(r.html)
