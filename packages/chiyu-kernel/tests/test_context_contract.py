"""GAP-2 上下文契约 + impl 对拍守卫（Batch-2a，2026-10-14）。

判据面：
  · impl 与契约**同一对象**（单一事实源落地，不是抄了一份）；
  · 四层/七维/缺口类型/降级档位闭集完整；
  · assemble 供需缺口结构化返回（不静默吞）；
  · 七维齐全轴列出缺失维度。
"""
from __future__ import annotations

from chiyu_kernel.contract import context as ctx_contract
from chiyu_kernel.context import assembly, knowledge_needs, retrieval


def test_impl_sources_from_contract_same_object():
    assert assembly.CONTEXT_LAYERS is ctx_contract.CONTEXT_LAYERS
    assert assembly.LAYER_LABELS_ZH is ctx_contract.CONTEXT_LAYER_LABELS_ZH
    assert knowledge_needs.LAYER_NAMES is ctx_contract.CONTEXT_LAYER_LABELS_ZH
    assert knowledge_needs.KNOWLEDGE_LAYERS is ctx_contract.KNOWLEDGE_LAYERS
    assert knowledge_needs.CONTEXT_DIMENSIONS is ctx_contract.CONTEXT_DIMENSIONS
    assert knowledge_needs.MIN_PRECEDENTS is ctx_contract.MIN_PRECEDENTS
    assert retrieval.VTIER_ORDER is ctx_contract.VTIER_ORDER
    assert retrieval.TIER_FTS_VECTOR is ctx_contract.VTIER_FTS_VECTOR


def test_context_layers_closed_and_labels_complete():
    assert set(ctx_contract.CONTEXT_LAYERS) == {"L1", "L2", "L3", "L4"}
    assert set(ctx_contract.CONTEXT_LAYER_LABELS_ZH) == set(ctx_contract.CONTEXT_LAYERS)


def test_context_dimensions_seven():
    assert set(ctx_contract.CONTEXT_DIMENSIONS) == {
        "identity", "structure", "semantics", "time_config",
        "decision_history", "operational_state", "governance"}


def test_gap_kinds_closed():
    assert len(ctx_contract.GAP_KINDS) == 6
    assert len(set(ctx_contract.GAP_KINDS)) == 6


def test_vtier_order_is_degradation_chain():
    assert ctx_contract.VTIER_ORDER[0] == "fts+vector"
    assert ctx_contract.VTIER_ORDER[-1] == "none"
    # 弃用别名与主名同一对象（deprecation 政策：别名在册，不悄悄改值）
    assert ctx_contract.TIER_ORDER is ctx_contract.VTIER_ORDER
    assert ctx_contract.TIER_FTS is ctx_contract.VTIER_FTS


def test_assemble_reports_gaps_structurally():
    needs = (assembly.KnowledgeNeed(layer="L2", key="p1"),)
    result = assembly.assemble(needs, {})
    rep = result.supply_report
    assert rep.missing == (("L2", "p1"),)
    assert rep.degraded_layers == ("L2",)
    assert rep.consistent is False
    assert rep.as_metrics()["context_supply_rate"] == 0.0


def test_missing_context_dimensions_lists_absent():
    full = {d: 1 for d in ctx_contract.CONTEXT_DIMENSIONS}
    assert knowledge_needs.missing_context_dimensions(full) == []
    absent = knowledge_needs.missing_context_dimensions({"identity": 1})
    assert "structure" in absent and "identity" not in absent
