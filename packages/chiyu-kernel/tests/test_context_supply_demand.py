"""T4·δ2 守卫：context L1–L4 供需校验——缺口**结构化**返回、可失败判据。

上游依据：计划 Step 4（context/assembly 供需校验）与 SKILL #4 §5.2。
⛔ 判别力：缺供给 ≠ 低分。若实现把「层无供给」吞成 relevance 低分（demo
「评分被降级为叙述留痕」同族缺陷），以下用例必须红。

⛔ 零领域词：用例只用中性文本（case/entity 等），不引入单域字面量。
"""
from __future__ import annotations

from chiyu_kernel.context.assembly import (
    CONTEXT_LAYERS,
    KnowledgeNeed,
    assemble,
)
from chiyu_kernel.context.knowledge_needs import (
    GAP_INSUFFICIENT_EXPERIENCE,
    GAP_LOW_COVERAGE,
    GAP_MISSING_GATE,
    GAP_MISSING_HITL,
    build_knowledge_needs,
    check_supply_demand,
)
from chiyu_kernel.context.retrieval import degraded_recall, to_supply_layer


def _needs_l1_l2():
    return (
        KnowledgeNeed("L1", dims=("semantics",), key="entity"),
        KnowledgeNeed("L2", dims=("precedent",), key="case"),
    )


# ── 1. 缺口结构化返回（不吞）──────────────────────────────────────────
def test_assemble_reports_missing_structurally():
    """L1 完全无供给 ⇒ missing 非空 + degraded 标记，而不是「低分吞掉」。"""
    needs = _needs_l1_l2()
    provided = {"L2": [{"dim": "precedent", "key": "case", "value": 0.81}]}
    res = assemble(needs, provided)
    assert res.supply_report.consistent is False
    assert ("L1", "entity") in res.supply_report.missing
    assert "L1" in res.supply_report.degraded_layers
    m = res.supply_report.as_metrics()
    assert m["context_supply_rate"] == 0.5
    assert m["context_missing"] == 1.0
    assert m["context_degraded_layers"] == 1.0


def test_assemble_full_supply_is_consistent():
    needs = _needs_l1_l2()
    provided = {
        "L1": [{"dim": "semantics", "key": "entity", "value": {"name": "x"}}],
        "L2": [{"dim": "precedent", "key": "case", "value": 0.81}],
    }
    res = assemble(needs, provided)
    assert res.supply_report.consistent is True
    assert res.supply_report.missing == ()
    assert res.supply_report.as_metrics()["context_supply_rate"] == 1.0
    assert res.facts["L1"] == [{"name": "x"}]
    assert res.facts["L2"] == [0.81]


def test_missing_layer_is_degraded_not_merely_low_score():
    """判别力：只有 L1 供给，L2 有需求 ⇒ 显式 missing（不得降级为低分叙述）。"""
    needs = (KnowledgeNeed("L2", dims=("precedent",), key="case"),)
    res = assemble(needs, {"L1": [{"dim": "semantics", "key": "entity", "value": 1}]})
    assert res.supply_report.consistent is False
    assert ("L2", "case") in res.supply_report.missing
    assert res.supply_report.degraded_layers == ("L2",)


# ── 2. 四层常量与校验 ────────────────────────────────────────────────
def test_layer_constants_and_validation():
    assert CONTEXT_LAYERS == ("L1", "L2", "L3", "L4")
    try:
        KnowledgeNeed("L5")
    except ValueError:
        pass
    else:
        raise AssertionError("L5 不在四层内，应被拒绝")


# ── 3. to_assembly_needs 接线（KnowledgeNeeds → assemble 消费）────────
def test_to_assembly_needs_wires_level_to_layers():
    needs = build_knowledge_needs("t", knowledge_level=2)
    kn = needs.to_assembly_needs()
    assert tuple(n.layer for n in kn) == ("L1", "L2")
    provided = {
        "L1": [{"dim": "semantics", "key": "", "value": "base"}],
        "L2": [{"dim": "precedent", "key": "", "value": 0.9}],
    }
    res = assemble(kn, provided)
    assert res.supply_report.consistent is True


# ── 4. retrieval → supply 接线（to_supply_layer 供 assemble 消费）──────
def test_to_supply_layer_feeds_assemble():
    pool = [
        {"key": "c1", "text": "precedent document alpha", "vector": [0.5, 0.5]},
        {"key": "c2", "text": "precedent document beta", "vector": [0.9, 0.1]},
    ]
    r = degraded_recall(["precedent"], pool, query_vector=[1.0, 0.0], top_k=2)
    provided = to_supply_layer(r, layer="L2", dim="precedent")
    res = assemble((KnowledgeNeed("L2", dims=("precedent",)),), provided)
    assert res.supply_report.consistent is True
    assert len(res.facts["L2"]) == 2


# ── 5. check_supply_demand：缺键 ⇒ 显式缺口（可失败判据）────────────────
def test_check_supply_demand_reports_gap_explicitly():
    # level=4 ⇒ L1–L4 全激活；提供实体/数据源使各层判据有输入
    needs = build_knowledge_needs(
        "t", knowledge_level=4, entities=("e1", "e2"), data_sources=("ds1",))
    gaps = check_supply_demand(
        needs,
        supply={
            "entity_links": {},
            "historical_cases": 0,
            "embedding_coverage": 0.5,
            "hitl_checkpoints": [],
            "gates": {},
        },
    )
    codes = [g.code for g in gaps]
    assert GAP_INSUFFICIENT_EXPERIENCE in codes
    assert GAP_LOW_COVERAGE in codes
    assert GAP_MISSING_HITL in codes
    assert GAP_MISSING_GATE in codes
