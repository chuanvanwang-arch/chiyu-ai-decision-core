"""Batch-1b-3 守卫测试——conflict_resolver + attribution + audit_4q。

对拍锚点（CRM 只读快照，判据逐条对齐）：
  - `src/decision/conflict.js` G4 五策略 + 保留分歧不物理删 + human_arbitration 必挂决策
  - `src/decision/rootCauseClassifier.js` R0-R3 命中即止分类树
  - `src/monitor/attribution.js` T29 applyHumanDisposition / hasRealEdgeMissing 护栏
  - `src/decision/auditability.js` computeAudit4q §7.1 判据（Q1≥5/7、Q2 空链不可自称 OK、
    Q3 零实体扫描=warn、Q4 孤立=warn、聚合空窗口 pct=null）
"""
import pytest

from chiyu_kernel import api
from chiyu_kernel.attribution import (
    apply_human_disposition, apply_outcome, classify_root_cause,
    compute_edge_compliance, required_edges_for_dims,
)
from chiyu_kernel.audit_4q import aggregate_4q, evaluate_4q
from chiyu_kernel.conflict_resolver import (
    adopt_verdict, detect_conflicts, mark_conflict, pick_winner,
    resolve_conflict,
)
from chiyu_kernel.contract import (
    ATTRIBUTION_CATEGORIES, ATTRIBUTION_INVARIANTS, AUDIT4Q_INVARIANTS,
    AUDIT4Q_KEYS, AUDIT4Q_STATUSES, Audit4QError, CONFLICT_INVARIANTS,
    CONFLICT_STRATEGIES, ConflictStrategyError, HUMAN_DISPOSITIONS,
    Q1_MIN_SUPPLIED_DIMS, ROOT_CAUSE_LAYERS,
)


def _assertion(value, source, **kw):
    base = {"value": value, "source_id": source, "valid": True,
            "needs_review": False, "source_credibility": 0.5,
            "created_at": "2026-10-14T00:00:00"}
    base.update(kw)
    return base


# ── conflict_resolver ───────────────────────────────────────────────────────
def test_conflict_detection_and_marking():
    rows = [_assertion("A", "s1"), _assertion("A", "s2")]
    assert detect_conflicts(rows) == {"has_conflict": False, "needs_review": False}
    rows = [_assertion("A", "s1"), _assertion("B", "s2")]
    det = detect_conflicts(rows)
    assert det["has_conflict"] and not det["needs_review"]
    marked = mark_conflict(rows)
    # 整组置 needs_review（CRM recordAssertion 后置步骤同口径）
    assert all(r["needs_review"] for r in marked)
    assert marked[0] is not rows[0]          # 新列表（禁原地改）


def test_pick_winner_five_strategies():
    rows = [_assertion("old", "s1", created_at="2026-10-13T00:00:00", source_credibility=0.9),
            _assertion("new", "s2", created_at="2026-10-14T00:00:00", source_credibility=0.4)]
    # timestamp：最新者胜
    assert pick_winner(rows, "timestamp")["value"] == "new"
    # confidence_weighted：可信度最高（0.9 > 0.4）
    assert pick_winner(rows, "confidence_weighted")["value"] == "old"
    # source_priority：优先级表注入，缺省 0；平局先到者胜（MUTANT：ties 翻转即红）
    srcs = [{"source_id": "s1", "priority": 1}, {"source_id": "s2", "priority": 1}]
    assert pick_winner(rows, "source_priority", sources=srcs)["value"] == "old"
    srcs = [{"source_id": "s2", "priority": 5}]
    assert pick_winner(rows, "source_priority", sources=srcs)["value"] == "new"
    # human_arbitration：与 confidence_weighted 同选
    assert pick_winner(rows, "human_arbitration")["value"] == "old"
    # merge：保留全部值（CRM conflict.js merge 分支 winner={value:[全部值]} 同口径）
    w = pick_winner(rows, "merge")
    assert w["value"] == ["old", "new"]
    # timestamp 平局：先到者胜（CRM reduce 严格 >，MUTANT：改 >= 后到者胜即红）
    tie = [_assertion("first", "s1"), _assertion("second", "s2")]
    assert pick_winner(tie, "timestamp")["value"] == "first"
    assert pick_winner([], "timestamp") is None
    with pytest.raises(ConflictStrategyError):
        pick_winner(rows, "majority")        # 未知策略抛错


def test_adopt_verdict_marks_not_deletes():
    rows = [_assertion("A", "s1"), _assertion("B", "s2", source_credibility=0.4)]
    out = adopt_verdict(rows, "A")
    # 权威标记 + 其余 valid=False；物理保留（行数不减）
    assert len(out) == 2
    assert out[0]["valid"] is True and out[0]["needs_review"] is False
    assert out[1]["valid"] is False
    assert rows[0]["valid"] is True          # 输入未被原地改


def test_resolve_conflict_requires_decision_ref_for_human():
    rows = [_assertion("A", "s1", created_at="2026-10-13T00:00:00"), _assertion("B", "s2")]
    with pytest.raises(ConflictStrategyError):
        resolve_conflict(rows, "human_arbitration")               # 缺 decision_ref 即抛
    out = resolve_conflict(rows, "human_arbitration", decision_ref="dec-001")
    assert out["decision_ref"] == "dec-001"
    assert out["winner"]["value"] == "A"
    # 一步裁决：timestamp（B 更新者胜）+ 采用标记
    out = resolve_conflict(rows, "timestamp")
    assert out["winner"]["value"] == "B"
    assert [r["valid"] for r in out["assertions"]] == [False, True]
    # 空断言组：不抛、winner=None
    out = resolve_conflict([], "timestamp")
    assert out["winner"] is None and out["assertions"] == []
    with pytest.raises(ConflictStrategyError):
        resolve_conflict(rows, "bogus")


# ── attribution：R0-R3 分类树 ───────────────────────────────────────────────
def test_classify_no_feedback_is_unknown():
    out = classify_root_cause()
    assert out["code"] == "UNKNOWN" and out["severity"] == "unknown"


def test_classify_positive_reinforcement():
    out = classify_root_cause(feedback={"usable": True, "major_deviation": False})
    assert out["code"] == "UNKNOWN" and out["severity"] == "none"


def test_classify_hit_and_stop_priority():
    fb = {"usable": False, "major_deviation": True}
    pc = {"field_mismatch": True, "info_incomplete": True, "input_stale": True}
    # 命中即止：field > info > stale（MUTANT：重排优先级即红）
    assert classify_root_cause(feedback=fb, particle_checks=pc)["code"] == "FIELD_MISMATCH"
    assert classify_root_cause(feedback=fb, particle_checks={
        "info_incomplete": True, "input_stale": True})["code"] == "INFO_INCOMPLETE"
    assert classify_root_cause(feedback=fb, particle_checks={
        "input_stale": True})["code"] == "INPUT_STALE"
    # L 维缺 → E 边缺（E 缺只认 required_missing 显式非空）
    assert classify_root_cause(feedback=fb, attribution={
        "required_fill": {"missing": ["identity"]}})["code"] == "DIM_MISSING"
    # 全 missing 投影（未查实）不判 E 缺——防误判护栏
    assert classify_root_cause(feedback=fb, attribution={
        "edge_compliance": {"E1": "missing", "E2": "missing"}})["code"] == "DATA_QUALITY_PRECEDENT"
    assert classify_root_cause(feedback=fb, attribution={
        "edge_compliance": {"required_missing": ["DECIDED_ON"]}})["code"] == "EDGE_MISSING"
    # L+E 全齐 + 重大 ⇒ 先例污染；非重大 ⇒ 优化次序
    assert classify_root_cause(feedback=fb)["code"] == "DATA_QUALITY_PRECEDENT"
    assert classify_root_cause(feedback={"usable": False, "major_deviation": False})[
        "code"] == "NEED_DIM_ORDER"


def test_apply_human_disposition_overturn_and_confirm():
    attr = {"category": "ok", "required_fill": {"missing": []},
            "edge_compliance": {"required_missing": []}}
    # 确认 → ok/accurate
    out = apply_human_disposition(attr, "CONFIRMED")
    assert out["category"] == "ok" and out["accuracy_signal"] == "accurate"
    # 推翻 + 旧三态 → 重推（全齐仍推翻 = 推理偏差，兼容旧态）
    out = apply_human_disposition(attr, "OVERRIDDEN")
    assert out["category"] == "inference_bias"
    assert out["accuracy_signal"] == "inaccurate"
    assert out["root_cause"]["code"] == "DATA_QUALITY_PRECEDENT"
    # 已七态判定：保留不覆盖（MUTANT：重算覆盖即红）
    fine = dict(attr, category="FIELD_MISMATCH")
    out = apply_human_disposition(fine, "CORRECTED")
    assert out["category"] == "FIELD_MISMATCH"
    assert out["accuracy_signal"] == "inaccurate"
    # 非法处置词
    with pytest.raises(Exception):
        apply_human_disposition(attr, "MAYBE")


def test_apply_outcome_and_edge_compliance():
    out = apply_outcome({"category": "ok"}, {"revenue_delta": 100})
    assert out["outcome_verified"] == {"revenue_delta": 100}
    assert apply_outcome({"category": "ok"}, None)["outcome_verified"] is None
    # 边合规：应连边注入；无依据 ⇒ known=False（E 缺不可判）
    ec = compute_edge_compliance(["DECIDED_ON"], required_edges=["DECIDED_ON", "RELATES_TO"])
    assert ec["known"] is True and ec["required_missing"] == ["RELATES_TO"]
    ec = compute_edge_compliance([], required_dims=None)
    assert ec["known"] is False and ec["required_missing"] == []
    # 维度→边推导（规格注入）
    spec = [{"edge_type": "DECIDED_ON", "serves_dimension": ["identity", "structure"]},
            {"edge_type": "EVIDENCES", "serves_dimension": "time_config"}]
    assert required_edges_for_dims(["identity"], spec) == ["DECIDED_ON"]
    assert required_edges_for_dims(None, spec) is None
    assert required_edges_for_dims([], spec) == []


# ── audit_4q：四问评分 ─────────────────────────────────────────────────────
def test_q1_threshold_and_missing_evidence():
    assert Q1_MIN_SUPPLIED_DIMS == 5
    ok = evaluate_4q(supplied_dims=6, chain_status="ok",
                     prov_entries=[{"entry_type": "context_supply"}],
                     entities_scanned=1, downstream_count=2)
    assert ok["health"]["statuses"]["Q1"] == "pass"
    # 无快照 = 无证据 ⇒ warn（不顶替）
    w = evaluate_4q(supplied_dims=None, chain_status="ok",
                    prov_entries=[{"entry_type": "context_supply"}], entities_scanned=1)
    assert w["health"]["statuses"]["Q1"] == "warn"
    # 4/7 未达门槛 ⇒ warn
    w = evaluate_4q(supplied_dims=4, chain_status="ok",
                    prov_entries=[{"entry_type": "context_supply"}], entities_scanned=1)
    assert w["health"]["statuses"]["Q1"] == "warn"


def test_q2_empty_chain_never_ok():
    ent = [{"entry_type": "context_supply"}]
    # 空链：chain ok 但零证据 ⇒ warn（MUTANT：空链放行即红）
    w = evaluate_4q(supplied_dims=6, chain_status="ok", prov_entries=[], entities_scanned=1)
    assert w["health"]["statuses"]["Q2"] == "warn"
    # 有证据但缺 context_supply 覆盖 ⇒ warn
    w = evaluate_4q(supplied_dims=6, chain_status="ok",
                    prov_entries=[{"entry_type": "note"}], entities_scanned=1)
    assert w["health"]["statuses"]["Q2"] == "warn"
    # 齐备 ⇒ pass
    p = evaluate_4q(supplied_dims=6, chain_status="ok", prov_entries=ent, entities_scanned=1)
    assert p["health"]["statuses"]["Q2"] == "pass"
    # 篡改 ⇒ fail
    t = evaluate_4q(supplied_dims=6, chain_status="tampered", prov_entries=ent, entities_scanned=1)
    assert t["health"]["statuses"]["Q2"] == "fail"
    # 事件条目不入证据口径（presence 不改变判定，仅计数分离）
    e = evaluate_4q(supplied_dims=6, chain_status="ok",
                    prov_entries=[{"entry_type": "context_supply"},
                                  {"entry_type": "event:approved"}], entities_scanned=1)
    q2 = e["questions"]["Q2"]
    assert q2["entries"] == 1 and q2["event_entries"] == 1 and q2["status"] == "pass"


def test_q3_q4_and_score():
    # Q3：零实体扫描 = 无证据 ⇒ warn（非 pass）
    r = evaluate_4q(supplied_dims=6, chain_status="ok",
                    prov_entries=[{"entry_type": "context_supply"}],
                    entities_scanned=0, downstream_count=1)
    assert r["health"]["statuses"]["Q3"] == "warn"
    r = evaluate_4q(supplied_dims=6, chain_status="ok",
                    prov_entries=[{"entry_type": "context_supply"}],
                    entities_scanned=3, unresolved_conflicts=2)
    assert r["health"]["statuses"]["Q3"] == "warn"
    assert r["health"]["needs_review_count"] == 2
    # Q4：影响计算失败 ⇒ fail；孤立 ⇒ warn；有下游 ⇒ pass
    r = evaluate_4q(supplied_dims=6, chain_status="ok",
                    prov_entries=[{"entry_type": "context_supply"}],
                    entities_scanned=1, impact_error="timeout")
    assert r["health"]["statuses"]["Q4"] == "fail"
    r = evaluate_4q(supplied_dims=6, chain_status="ok",
                    prov_entries=[{"entry_type": "context_supply"}],
                    entities_scanned=1, downstream_count=0)
    assert r["health"]["statuses"]["Q4"] == "warn"
    # 满分形态
    full = evaluate_4q(supplied_dims=5, chain_status="ok",
                       prov_entries=[{"entry_type": "context_supply"}],
                       entities_scanned=1, downstream_count=1)
    assert full["health"]["score"] == 4 and full["health"]["total"] == 4


def test_aggregate_4q_window_semantics():
    def mk(score, statuses, needs=0, did="d"):
        return {"decision_id": did, "health": {"score": score, "statuses": statuses,
                                               "needs_review_count": needs}}
    good = mk(4, {"Q1": "pass", "Q2": "pass", "Q3": "pass", "Q4": "pass"})
    warn = mk(3, {"Q1": "warn", "Q2": "pass", "Q3": "pass", "Q4": "pass"}, needs=2)
    bad = mk(2, {"Q1": "pass", "Q2": "fail", "Q3": "warn", "Q4": "pass"})
    out = aggregate_4q([good, warn, bad, None])   # None = 超时跳过，不计入
    assert out["scored"] == 3
    assert out["full"] == 1 and out["with_conflict"] == 1 and out["tampered"] == 1
    # pct = (4+3+2)/3/4 = 75%
    assert out["auditability_pct"] == 75
    assert out["per_status"]["Q2"] == {"pass": 2, "warn": 0, "fail": 1}
    # 空窗口：pct=null（不报 0 充数）
    empty = aggregate_4q([])
    assert empty["auditability_pct"] is None and empty["scored"] == 0
    # 非法状态值
    with pytest.raises(Audit4QError):
        aggregate_4q([mk(4, {"Q1": "good", "Q2": "pass", "Q3": "pass", "Q4": "pass"})])


# ── 契约词汇与门面同对象 ────────────────────────────────────────────────────
def test_contract_vocabularies():
    assert set(CONFLICT_STRATEGIES) == {
        "timestamp", "source_priority", "confidence_weighted", "merge",
        "human_arbitration"}
    assert set(ATTRIBUTION_CATEGORIES) >= {
        "ok", "input_missing", "inference_bias", "FIELD_MISMATCH",
        "INFO_INCOMPLETE", "INPUT_STALE", "DIM_MISSING", "EDGE_MISSING",
        "NEED_DIM_ORDER", "DATA_QUALITY_PRECEDENT", "UNKNOWN"}
    assert len(ATTRIBUTION_CATEGORIES) == 11
    assert set(HUMAN_DISPOSITIONS) == {"OVERRIDDEN", "CORRECTED", "CONFIRMED", "APPROVED"}
    assert AUDIT4Q_KEYS == ("Q1", "Q2", "Q3", "Q4")
    assert AUDIT4Q_STATUSES == ("pass", "warn", "fail")
    assert len(CONFLICT_INVARIANTS) == 5 and len(ATTRIBUTION_INVARIANTS) == 6
    assert len(AUDIT4Q_INVARIANTS) == 6
    assert len(ROOT_CAUSE_LAYERS) == 8


def test_facade_exports_same_objects():
    assert api.resolve_conflict is resolve_conflict
    assert api.classify_root_cause is classify_root_cause
    assert api.evaluate_4q is evaluate_4q
    assert api.aggregate_4q is aggregate_4q
    from chiyu_kernel.contract import conflict_resolver as cr
    from chiyu_kernel.contract import attribution as at
    from chiyu_kernel.contract import audit_4q as aq
    assert api.CONFLICT_STRATEGIES is cr.CONFLICT_STRATEGIES
    assert api.ATTRIBUTION_CATEGORIES is at.ATTRIBUTION_CATEGORIES
    assert api.Q1_MIN_SUPPLIED_DIMS is aq.Q1_MIN_SUPPLIED_DIMS
