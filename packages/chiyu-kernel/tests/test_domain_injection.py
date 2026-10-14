"""WS6 领域注入 SDK 测试 + 反假绿探针。

收口标准（蓝图 §3 成熟度闸 #1）：每个「测试绿」之外须过可证伪探针——
真缺陷时必 FAIL、修复后必 PASS。「字段非空 / count>0 / 无报错」恒绿禁止作唯一判据。
本文件刻意包含「注入闸捕获错误输入」的探针：删掉对应闸 ⇒ 测试转红（变异自证）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.api import (
    DomainBundle,
    DomainInjectionError,
    inject_domain,
    profile_from_dict,
)
from chiyu_kernel.scenario.model import ScenarioPack, from_dict


# ── 合法基准数据（机制非清单：具体取值仅用于测试，不进内核契约）─────────────
PROFILE = {
    "domain": "demo-crm",
    "particle_types": {
        "names": [
            "unstructured_asset", "entity", "decision", "memory", "knowledge",
            "lead", "opportunity",
        ],
    },
    "predicates": {
        "knowledge": [
            {"predicate": "RELATES_TO", "from_type": "lead",
             "to_type": "opportunity", "layer": "K", "source": "rule"},
        ],
    },
    "autonomous_threshold": 0.8,
}

ACTIONS = [
    {"name": "submit_lead", "capability": "lead_submit", "mutating": True},
    {"name": "query_lead", "capability": "lead_query"},
    {"name": "approve_plan", "capability": "plan_approve",
     "high_risk": True, "has_force": True},
    {"name": "sync_record", "capability": "record_sync", "mutating": True},
    {"name": "export_report", "capability": "report_export"},
]

SCENARIO = {
    "id": "onboard",
    "name": "Onboard",
    "level": "single",
    "direction": "inbound",
    "mode": "standard",
    "workflow": {"steps": [{"name": "s1", "prompt": "do"}]},
    "controlled_edges": [
        {"predicate": "RELATES_TO", "from_type": "lead", "to_type": "opportunity"},
    ],
}


def test_profile_from_dict_basic() -> None:
    tp = profile_from_dict(PROFILE)
    assert tp.domain == "demo-crm"
    assert tp.particle_types.covers("lead")
    assert "RELATES_TO" in tp.predicates.names()
    # memory 默认用内核常量（7 记忆谓词）未丢失
    assert "DECIDED_ON" in tp.predicates.names()


def test_inject_domain_happy_path() -> None:
    bundle = inject_domain(profile=PROFILE, actions=ACTIONS, scenarios=[SCENARIO])
    assert isinstance(bundle, DomainBundle)
    assert set(bundle.actions.names()) == {
        "submit_lead", "query_lead", "approve_plan", "sync_record", "export_report",
    }
    assert len(bundle.scenarios) == 1
    assert bundle.scenarios[0].id == "onboard"
    assert bundle.scenarios[0].controlled_edges[0]["predicate"] == "RELATES_TO"


def test_scenario_pack_accepts_controlled_edges() -> None:
    pack = from_dict(SCENARIO)
    assert pack.controlled_edges[0]["from_type"] == "lead"
    assert pack.to_dict()["controlled_edges"][0]["predicate"] == "RELATES_TO"


# ── 反假绿探针：以下每项断言「注入闸确实捕获错误」，删闸即转红 ───────────────

def test_probe_profile_missing_core_role() -> None:
    bad = dict(PROFILE)
    bad["particle_types"] = {"names": ["entity", "decision", "memory", "knowledge"]}
    with pytest.raises(DomainInjectionError) as exc:
        inject_domain(profile=bad, actions=ACTIONS, scenarios=[SCENARIO])
    assert any("核心语义角色" in e for e in exc.value.errors)


def test_probe_action_r5_capability_conflict() -> None:
    conflict = [
        {"name": "submit_lead", "capability": "lead_submit"},
        {"name": "submit_lead_v2", "capability": "lead_submit"},  # 同 capability ⇒ R5
    ]
    with pytest.raises(DomainInjectionError) as exc:
        inject_domain(profile=PROFILE, actions=conflict, scenarios=[SCENARIO])
    assert any("R5" in e for e in exc.value.errors)


def test_probe_edge_predicate_not_in_profile() -> None:
    bad_scenario = dict(SCENARIO)
    bad_scenario["controlled_edges"] = [
        {"predicate": "UNDECLARED_EDGE", "from_type": "lead", "to_type": "opportunity"},
    ]
    with pytest.raises(DomainInjectionError) as exc:
        inject_domain(profile=PROFILE, actions=ACTIONS, scenarios=[bad_scenario])
    assert any("不在 profile 谓词集" in e for e in exc.value.errors)


def test_probe_edge_type_not_in_particle_types() -> None:
    bad_scenario = dict(SCENARIO)
    bad_scenario["controlled_edges"] = [
        {"predicate": "RELATES_TO", "from_type": "phantom_type", "to_type": "opportunity"},
    ]
    with pytest.raises(DomainInjectionError) as exc:
        inject_domain(profile=PROFILE, actions=ACTIONS, scenarios=[bad_scenario])
    assert any("不在 particle_types" in e for e in exc.value.errors)
