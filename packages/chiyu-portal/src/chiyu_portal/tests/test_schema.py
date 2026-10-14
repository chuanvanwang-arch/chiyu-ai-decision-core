"""T1 Schema 协议常量 + validate_page_schema 校验器（TDD）。"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.particle import CORE_ROLES, ParticleTypeSet

from chiyu_portal.schema import (
    AGG_FUNCS, COMPONENT_KINDS, FILTER_OPS, PAGE_TYPES, SCHEMA_VERSION,
    THEMES, ValidationError, validate_page_schema,
)

# 测试用受控粒子集：CORE_ROLES + 一个中性通用类型（非领域字面量）
TEST_PARTICLES = ParticleTypeSet(names=(*CORE_ROLES, "metric"))


def _valid_schema() -> dict:
    return {
        "version": SCHEMA_VERSION,
        "type": "dashboard",
        "title": "测试看板",
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


def _err_paths(errors) -> set[str]:
    return {e.path for e in errors}


def test_protocol_constants_coverage():
    assert set(PAGE_TYPES) >= {"dashboard", "table", "form", "detail", "workspace", "approval"}
    assert "metric-card" in COMPONENT_KINDS
    assert set(THEMES) == {"light", "dark"}
    assert set(FILTER_OPS) >= {"eq", "lt", "gt", "lte", "gte", "ne", "in"}
    assert set(AGG_FUNCS) >= {"count", "sum", "avg", "min", "max", "latest"}


def test_valid_schema_passes():
    errs = validate_page_schema(_valid_schema(), particle_types=TEST_PARTICLES)
    assert errs == ()


def test_unknown_particle_type_rejected():
    s = _valid_schema()
    s["components"][0]["dataBinding"]["particleType"] = "PURCHASE_ORDER"  # 旧/未知粒子
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES)
    assert any("particleType" in p for p in _err_paths(errs))


def test_unknown_page_type_rejected():
    s = _valid_schema()
    s["type"] = "slideshow"
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES)
    assert any(p == "type" for p in _err_paths(errs))


def test_unknown_component_kind_rejected():
    s = _valid_schema()
    s["components"][0]["kind"] = "pie-chart"
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES)
    assert any("kind" in p for p in _err_paths(errs))


def test_non_whitelist_action_rejected():
    s = _valid_schema()
    s["components"][0]["actions"][0]["action"] = "domain-approve"  # 未注入白名单
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES)
    assert any("action" in p for p in _err_paths(errs))


def test_illegal_filter_op_rejected():
    s = _valid_schema()
    s["components"][0]["dataBinding"]["filters"] = [{"field": "stage", "op": "between", "value": [1, 2]}]
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES)
    assert any("filters" in p and "op" in p for p in _err_paths(errs))


def test_illegal_agg_rejected():
    s = _valid_schema()
    s["components"][0]["dataBinding"]["metrics"][0]["agg"] = "median"
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES)
    assert any("metrics" in p and "agg" in p for p in _err_paths(errs))


def test_status_field_only_eq():
    s = _valid_schema()
    s["components"][0]["dataBinding"]["filters"] = [{"field": "stage", "op": "lt", "value": "done"}]
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES, status_fields=("stage",))
    assert any("stage" in e.message for e in errs)


def test_status_field_not_aggregated():
    s = _valid_schema()
    s["components"][0]["dataBinding"]["metrics"][0]["field"] = "stage"
    s["components"][0]["dataBinding"]["metrics"][0]["agg"] = "count"
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES, status_fields=("stage",))
    assert any("stage" in e.message for e in errs)


def test_snapshot_field_only_latest():
    s = _valid_schema()
    s["components"][0]["dataBinding"]["metrics"][0]["field"] = "qty"
    s["components"][0]["dataBinding"]["metrics"][0]["agg"] = "sum"
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES, snapshot_fields=("qty",))
    assert any("qty" in e.message for e in errs)


def test_unknown_theme_rejected():
    s = _valid_schema()
    s["layout"]["theme"] = "neon"
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES)
    assert any(p == "layout.theme" for p in _err_paths(errs))


def test_unsupported_version_rejected():
    s = _valid_schema()
    s["version"] = "9.9"
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES)
    assert any(p == "version" for p in _err_paths(errs))


def test_non_particle_source_rejected():
    s = _valid_schema()
    s["components"][0]["dataBinding"]["source"] = "sql"
    errs = validate_page_schema(s, particle_types=TEST_PARTICLES)
    assert any("source" in p for p in _err_paths(errs))


