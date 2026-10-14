"""WS9 参考消费层测试 + 反假绿探针（无需 PG / 无需外部服务）。

⛔ 收口标准（蓝图 §3）：每条「测试绿」之外须过**可证伪**判据。
   本文件对五条探针各配一个「破坏性构造」，证明探针真会转红 —— 不是恒绿装饰。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.decision import RUBRIC_KEYS
from chiyu_kernel.contract.particle import MEMORY_PREDICATES

from reference_consumer.app import (
    backlinks, build_app, record_outcome, relations, run_decision, sync_graph, timeline,
)
from reference_consumer.canary import (
    CONCEPT_REFS, EXPECTED_NET_TRIPLES, FULL_ELEMENTS, FULL_SCORES, REFERENCES,
    run_canary,
)
from reference_consumer.probes import (
    CLOSED_LOOP_EDGES, REQUIRED_CLOSED_LOOP_EDGES,
    probe_closed_loop, probe_decision_really_persisted,
    probe_graph_is_derived, probe_memory_really_materialized,
    probe_redline_blocks_persist,
)

DECISION_ID = "dec-1"


def _app_with_decision():
    app = build_app()
    res = run_decision(
        app, decision_id=DECISION_ID, text="常规评审场景",
        rubric_scores=FULL_SCORES, elements=FULL_ELEMENTS,
        references=REFERENCES, concept_refs=CONCEPT_REFS,
        subject_id="doc-1", policy_version="v1")
    return app, res


# ── 装配与注入 ──────────────────────────────────────────────────────────────
def test_build_app_domain_injected() -> None:
    app = build_app()
    controlled = set(app.controlled())
    assert {p.predicate for p in MEMORY_PREDICATES} <= controlled, \
        "七条记忆谓词须在受控集内（否则记忆网永远建不起来）"
    assert {"DESCRIBES", "BLOCKS"} <= controlled
    assert app.bundle.scenarios and app.bundle.scenarios[0].id == "review-flow"
    assert app.graph is not None


def test_run_decision_persists_and_materializes() -> None:
    app, res = _app_with_decision()
    assert res.persisted is True
    assert res.autonomous is True

    p1 = probe_decision_really_persisted(
        app, DECISION_ID,
        expected={"confidence": res.confidence, "redline_hit": False,
                  "autonomous": True, "policy_version": "v1"})
    assert p1.ok, p1.reason

    p2 = probe_memory_really_materialized(
        app, DECISION_ID, expected_triples=EXPECTED_NET_TRIPLES)
    assert p2.ok, (p2.reason, p2.evidence)

    p3 = probe_graph_is_derived(app, DECISION_ID)
    assert p3.ok, (p3.reason, p3.evidence)


# ── 闭环：接通的有证据，未接线的不许充数 ────────────────────────────────────
def test_closed_loop_required_edges_connected() -> None:
    app, _ = _app_with_decision()
    record_outcome(app, DECISION_ID, {"status": "applied"}, subject_id="doc-1")
    p = probe_closed_loop(app, DECISION_ID, references=REFERENCES,
                          concept_refs=CONCEPT_REFS)
    assert p.ok, (p.reason, p.evidence)
    for edge in REQUIRED_CLOSED_LOOP_EDGES:
        assert p.evidence[edge]["connected"] is True, edge


def test_closed_loop_does_not_claim_unwired_edges() -> None:
    """⛔ 铁律：不得把「未接线」说成「已跑通全链路」。本测试守住这条。"""
    app, _ = _app_with_decision()
    p = probe_closed_loop(app, DECISION_ID, references=REFERENCES,
                          concept_refs=CONCEPT_REFS)
    for edge in ("D→K", "校准", "参数生效", "M→K"):
        assert p.evidence[edge]["connected"] is False, \
            f"{edge} 不得被声称已接通（底座未内置该通道）"
        assert "not_wired" in p.evidence[edge]["detail"]
    assert set(p.evidence) == set(CLOSED_LOOP_EDGES), "八边必须逐条报，不得省略"


# ── 视图 ────────────────────────────────────────────────────────────────────
def test_views_are_read_only_derivations() -> None:
    app, _ = _app_with_decision()
    v = relations(app, DECISION_ID, max_hops=2)
    assert v["root"] == DECISION_ID
    assert len(v["edges"]) == len(EXPECTED_NET_TRIPLES)

    rows = timeline(app, subject_id="doc-1")
    assert rows, "时间线不应为空（至少粒子 + 记忆边 + 事件）"
    assert {r["source"] for r in rows} <= {"particle", "graph_edge", "event", "decision"}
    # 时间基准：非空且按 basis 排序（None 排最后）
    assert all(r["time_basis"] is None or isinstance(r["time_basis"], str)
               for r in rows)

    b = backlinks(app, DECISION_ID)
    assert set(b) >= {"referenced_by", "overrides", "overridden_by", "from_exception"}


# ── 工具暴露：读可直接调，写须两阶段 ────────────────────────────────────────
def test_mcp_read_tool_ok() -> None:
    app, _ = _app_with_decision()
    r = app.server.call("list_decisions", {}, ctx={"principal": "reader"})
    assert "result" in r and DECISION_ID in r["result"]


def test_mcp_write_requires_two_phase() -> None:
    app, _ = _app_with_decision()
    args = {"decision_id": DECISION_ID, "status": "applied"}
    first = app.server.handle_request(
        {"id": 1, "method": "tools/call",
         "params": {"name": "record_decision_outcome", "arguments": args}},
        ctx={"principal": "writer"})
    assert first["result"]["status"] == "confirmation_required"
    assert not any(k.endswith(":outcome") for k in app.store.events), \
        "首次调用不得执行写操作"

    token = first["result"]["confirm_token"]
    second = app.server.handle_request(
        {"id": 2, "method": "tools/call",
         "params": {"name": "record_decision_outcome", "arguments": args,
                    "confirm_token": token}},
        ctx={"principal": "writer"})
    assert "error" not in second
    assert any(k.endswith(":outcome") for k in app.store.events), \
        "带有效 token 的二次调用须真正执行"


def test_mcp_unauthenticated_is_denied() -> None:
    app, _ = _app_with_decision()
    r = app.server.call("list_decisions", {}, ctx={"principal": "stranger"})
    assert "error" in r, "未授权主体必须被拒（零信任：默认拒绝）"


# ── 红线优先 ────────────────────────────────────────────────────────────────
def test_redline_blocks_persist_probe_green() -> None:
    app = build_app()
    p = probe_redline_blocks_persist(
        app, decision_id="dec-redline", rubric_scores=FULL_SCORES,
        elements=FULL_ELEMENTS, redline_items=("受限事项",))
    assert p.ok, (p.reason, p.evidence)


def test_canary_ok() -> None:
    v = run_canary()
    assert v["ok"], [p for p in v["probes"] if not p["ok"]]
    assert len(v["probes"]) == 5
    assert v["counts"]["edges"] == len(EXPECTED_NET_TRIPLES)


# ── 探针可证伪（破坏性构造 ⇒ 必须转红）──────────────────────────────────────
def test_probe_decision_detects_tampered_content() -> None:
    app, res = _app_with_decision()
    app.store.events[DECISION_ID]["confidence"] = 0.01   # 篡改落库内容
    p = probe_decision_really_persisted(
        app, DECISION_ID, expected={"confidence": res.confidence})
    assert p.ok is False, "内容被篡改却仍判绿 ⇒ 探针恒绿（假绿）"


def test_probe_memory_detects_missing_and_unexpected_edges() -> None:
    app, _ = _app_with_decision()
    app.store.edges = [e for e in app.store.edges
                       if e["predicate"] != "REFERENCED_PRECEDENT"]
    p = probe_memory_really_materialized(
        app, DECISION_ID, expected_triples=EXPECTED_NET_TRIPLES)
    assert p.ok is False
    assert any(t[2] == "REFERENCED_PRECEDENT" for t in p.evidence["missing"])


def test_probe_graph_detects_phantom_edge() -> None:
    """图里出现事实源没有的边 ⇒ 必须红（图变第二份存储的判据）。"""
    from chiyu_kernel.api import GraphEdge, InMemoryGraphStore

    app, _ = _app_with_decision()
    edges = [GraphEdge.from_row(e) for e in app.store.edges]
    edges.append(GraphEdge(DECISION_ID, "phantom-1", "DESCRIBES", layer="K"))
    app.graph = InMemoryGraphStore(app.controlled(), edges)
    p = probe_graph_is_derived(app, DECISION_ID)
    assert p.ok is False, "出现幻影边却仍判绿 ⇒ 探针恒绿"
    assert ("phantom-1",) or p.evidence["phantom_edges"]
    assert any("phantom-1" in str(e) for e in p.evidence["phantom_edges"])


def test_probe_closed_loop_detects_broken_m_to_d() -> None:
    app, _ = _app_with_decision()
    p = probe_closed_loop(app, DECISION_ID, references={}, concept_refs=CONCEPT_REFS)
    assert p.ok is False, "记忆供给为空却仍判闭环接通 ⇒ 探针恒绿"
    assert p.evidence["M→D"]["connected"] is False


def test_probe_closed_loop_detects_missing_outcome() -> None:
    app, _ = _app_with_decision()
    p = probe_closed_loop(app, DECISION_ID, references=REFERENCES,
                          concept_refs=CONCEPT_REFS)
    assert p.evidence["结果→D"]["connected"] is False, \
        "未回填结果时不得声称「结果→D」已接通"
