"""T3 NL 解析层（绝不直出 HTML）。"""
from __future__ import annotations

import pytest

from chiyu_portal.nl_parser import ParseResult, parse_nl_to_schema

# 中性实体→粒子映射（非领域字面量，仅用于验证解析链路）
ENTITY_MAP = {"供应商": "entity", "单据": "knowledge"}


def test_dashboard_keyword_maps_to_dashboard():
    r = parse_nl_to_schema("给我一个看板展示合格率", entity_map=ENTITY_MAP)
    assert r.schema["type"] == "dashboard"


def test_table_keyword_maps_to_table():
    r = parse_nl_to_schema("列出所有采购单表格", entity_map=ENTITY_MAP)
    assert r.schema["type"] == "table"


def test_approval_keyword_maps_to_approval():
    r = parse_nl_to_schema("生成一个审批中心页面", entity_map=ENTITY_MAP)
    assert r.schema["type"] == "approval"


def test_known_entity_sets_particle_type():
    r = parse_nl_to_schema("展示供应商绩效", entity_map=ENTITY_MAP)
    assert r.schema["components"][0]["dataBinding"]["particleType"] == "entity"
    assert r.confidence == 0.9
    assert not r.needs_clarification


def test_unknown_entity_low_confidence_and_needs_clarification():
    r = parse_nl_to_schema("展示神秘对象分布", entity_map=ENTITY_MAP)
    assert r.needs_clarification is True
    assert r.confidence == 0.3
    # 未识别实体 → 无组件（schema 不含粒子绑定）
    assert r.schema["components"] == []


def test_threshold_below_becomes_lt_highlight():
    r = parse_nl_to_schema("展示供应商合格率，低于 90% 的标红", entity_map=ENTITY_MAP)
    comp = r.schema["components"][0]
    hl = comp["style"]["highlight"]
    assert hl["op"] == "lt"
    assert hl["value"] == pytest.approx(0.9)
    assert hl["color"] == "red"


def test_threshold_above_becomes_gt_highlight():
    r = parse_nl_to_schema("展示供应商中超过 95 分的标红", entity_map=ENTITY_MAP)
    hl = r.schema["components"][0]["style"]["highlight"]
    assert hl["op"] == "gt"
    assert hl["value"] == pytest.approx(0.95)


def test_parse_result_has_no_html_marker():
    """C-P1 锁死：NL 层绝不产出 HTML。"""
    for text in ["看板展示合格率", "列出单据", "<script>alert(1)</script> 看板", "表单录入"]:
        r = parse_nl_to_schema(text, entity_map=ENTITY_MAP)
        blob = str(r.schema)
        assert "<html" not in blob
        assert "<script" not in blob
        assert "onclick" not in blob
        assert isinstance(r, ParseResult)


def test_to_dict_roundtrip():
    r = parse_nl_to_schema("供应商看板", entity_map=ENTITY_MAP)
    d = r.to_dict()
    assert d["confidence"] == 0.9
    assert d["needsClarification"] is False
    assert d["schema"]["type"] == "dashboard"
