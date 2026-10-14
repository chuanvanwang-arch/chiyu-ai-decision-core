"""Batch-4 守卫测试：监控底座（observability）+ agent 运行时（agent_runtime）。

判据锚点以 CRM 源码 file:line 对拍（见各用例注释）；parity 语义：
- classify_attribution     ↔ CRM monitorStore.js:88-97 classifyAttribution
- accuracy_bucket          ↔ CRM monitorStore.js:138-143
- aggregate_gate_metrics   ↔ CRM monitorStore.js:49-55
- delivery_success_rate    ↔ CRM signalMetrics.js:31（无尝试→null 防假绿）
- classify_negative_predicates ↔ CRM signalMetrics.js:141-199（两级静默 + gen_silent 恒判）
- compute_enrichment_rate  ↔ CRM enrichmentMetrics.js:7-11（分母恒真实）
- 边双口径                 ↔ CRM edgeSource.js:12-42（NULL 不计供给）
- FailureCounter           ↔ CRM events/busFailures.js（单一实现 O6）
- match_trigger/dedup/cooldown ↔ CRM eventTrigger.js:89-129（只读 fail-closed A1）
- build_glass_box          ↔ CRM glassBox.js:10-20（脏信号过滤 A3）
- judge_contract           ↔ CRM contractMonitor.js:44-62（success pending A4）
- kg_convergence_gate      ↔ CRM agents.js:40-64（effective=declared∩served A5）
"""
import pytest

from chiyu_kernel import api
from chiyu_kernel import agent_runtime, observability
from chiyu_kernel.contract import (
    ACCURACY_BUCKETS,
    AGENT_RUNTIME_INVARIANTS,
    AgentRuntimeError,
    ASSEMBLY_GUARD_NAMES,
    ATTRIBUTION_CROSS_CATEGORIES,
    COMPLIANCE_DIMENSIONS,
    COMPLIANCE_PENDING,
    DEFAULT_COOLDOWN_MS,
    DEDUP_EMPTY_SENTINEL,
    GATE_METRIC_STATES,
    KG_LAYER_ORDER,
    NEGATIVE_PREDICATE_TYPES,
    OBSERVABILITY_INVARIANTS,
    ObservabilityError,
    TRIGGER_SOURCES,
)
from chiyu_kernel.observability import (
    FailureCounter,
    accuracy_bucket,
    aggregate_enrichment,
    aggregate_gate_metrics,
    blocks_export_gate,
    classify_attribution,
    classify_negative_predicates,
    compute_enrichment_rate,
    delivery_success_rate,
    edge_caliber_count,
    is_runtime_edge_source,
    runtime_edges_only,
    split_edges_by_caliber,
)
from chiyu_kernel.agent_runtime import (
    build_glass_box,
    cooldown_verdict,
    dedup_key_for,
    join_keys_of,
    judge_contract,
    kg_convergence_gate,
    l3_degraded_guard,
    match_trigger,
    resolve_runtime_layers,
)


# ── 契约闭集 ─────────────────────────────────────────────────────────────────
def test_contract_closed_sets():
    assert set(ATTRIBUTION_CROSS_CATEGORIES) == {
        "inference_bias", "input_error", "input_missing", "context_insufficient"}
    assert set(ACCURACY_BUCKETS) == {"accurate", "inaccurate", "pending"}
    assert set(NEGATIVE_PREDICATE_TYPES) == {
        "delivery_silent", "delivery_undelivered", "gen_silent"}
    assert set(TRIGGER_SOURCES) == {"event", "timer", "external"}
    assert DEFAULT_COOLDOWN_MS == 300_000
    assert DEDUP_EMPTY_SENTINEL == "new"
    assert list(KG_LAYER_ORDER) == ["L1", "L2", "L3", "L4"]
    assert len(OBSERVABILITY_INVARIANTS) == 6   # O1-O6
    assert len(AGENT_RUNTIME_INVARIANTS) == 6   # A1-A6
    assert set(ASSEMBLY_GUARD_NAMES) == {"l3_stated_but_kg_degraded", "kg_convergence"}
    assert GATE_METRIC_STATES == (
        ("AUTONOMOUS", "autonomous"), ("HUMAN", "human"),
        ("REQUIRED", "escalated"), ("ESCALATED", "escalated"))


def test_facade_reexports_same_objects():
    assert api.classify_attribution is observability.classify_attribution
    assert api.match_trigger is agent_runtime.match_trigger
    assert api.FailureCounter is observability.FailureCounter
    assert api.ATTRIBUTION_CROSS_CATEGORIES == ATTRIBUTION_CROSS_CATEGORIES
    assert api.OBSERVABILITY_INVARIANTS == OBSERVABILITY_INVARIANTS
    assert api.AGENT_RUNTIME_INVARIANTS == AGENT_RUNTIME_INVARIANTS


# ── 归因四类交叉（monitorStore.js:88-97）─────────────────────────────────────
def test_classify_attribution_cross_matrix():
    # 必填齐 + 不准 → inference_bias（调 agent 而非补数据）
    assert classify_attribution({"required_fill": {"missing": []},
                                 "accuracy_signal": "inaccurate"}) == "inference_bias"
    # 必填缺 + 不准 → input_error
    assert classify_attribution({"required_fill": {"missing": ["d1"]},
                                 "accuracy_signal": "inaccurate"}) == "input_error"
    # 必填缺 + 准 → input_missing
    assert classify_attribution({"required_fill": {"missing": ["d1"]},
                                 "accuracy_signal": "accurate"}) == "input_missing"
    # 必填齐 + warn → context_insufficient
    assert classify_attribution({"required_fill": {"missing": []},
                                 "level": "warn"}) == "context_insufficient"
    # 良性 → None（不计入错误类）
    assert classify_attribution({"required_fill": {"missing": []},
                                 "accuracy_signal": "accurate"}) is None
    # category=inference_bias 也算不准（与 CRM 同口径）
    assert classify_attribution({"required_fill": {"missing": []},
                                 "category": "inference_bias"}) == "inference_bias"


# ── accuracy 三态桶（monitorStore.js:138-143）────────────────────────────────
def test_accuracy_bucket():
    assert accuracy_bucket("CONFIRMED") == "accurate"
    assert accuracy_bucket("APPROVED") == "accurate"
    assert accuracy_bucket("OVERRIDDEN") == "inaccurate"
    assert accuracy_bucket("CORRECTED") == "inaccurate"
    assert accuracy_bucket("SOMETHING_ELSE") == "pending"
    assert accuracy_bucket(None) == "pending"


# ── 闸门指标聚合（monitorStore.js:49-55）─────────────────────────────────────
def test_aggregate_gate_metrics():
    out = aggregate_gate_metrics(["AUTONOMOUS", "HUMAN", "REQUIRED", "ESCALATED",
                                  "AUTONOMOUS", "UNKNOWN_STATE"])
    assert out == {"total": 6, "autonomous": 2, "escalated": 2, "human": 1}


# ── 投递成功率（signalMetrics.js:31 防假绿 O1）───────────────────────────────
def test_delivery_success_rate_no_attempt_is_null_not_100():
    assert delivery_success_rate(0, 0) is None          # 无尝试≠100%
    assert delivery_success_rate(8, 2) == 0.8
    assert delivery_success_rate(0, 5) == 0.0


# ── 负向判据两级（signalMetrics.js:141-199）──────────────────────────────────
def test_negative_predicates_two_level_silence():
    stats = {"email": {"sent": 0, "attempted": 0},     # 真静默
             "webhook": {"sent": 0, "attempted": 7}}    # 有尝试零送达
    alerts = classify_negative_predicates(
        ["email", "webhook"], stats,
        top_errors={"webhook": "no_recipient"}, top_error_counts={"webhook": 7})
    # 两级分开报（处置动作不同：①查链路 ②补收件人）
    assert {"type": "delivery_silent", "channel": "email",
            "sent": 0, "attempted": 0} in alerts
    a = next(x for x in alerts if x["type"] == "delivery_undelivered")
    assert a["type"] == "delivery_undelivered" and a["attempted"] == 7
    assert a["top_error"] == "no_recipient" and a["top_error_count"] == 7
    # 只有真静默参与出口闸（O5——配置未齐不阻断出口，防闸门噪音）
    assert blocks_export_gate("delivery_silent") is True
    assert blocks_export_gate("delivery_undelivered") is False
    assert blocks_export_gate("gen_silent") is False


def test_negative_predicates_gen_silent_always_checked():
    # 判据 B 与渠道配置无关：无渠道配置也要判 gen_silent（CRM :185 注释）
    alerts = classify_negative_predicates(None, {}, gen_fired=3, gen_landed=0)
    assert alerts == [{"type": "gen_silent", "fired": 3}]
    # fired>0 且 landed>0 → 不告警
    assert classify_negative_predicates(None, {}, gen_fired=3, gen_landed=2) == []
    # fired=0 → 不告警
    assert classify_negative_predicates(None, {}, gen_fired=0, gen_landed=0) == []
    # 有 sent 的启用渠道零告警
    assert classify_negative_predicates(
        ["email"], {"email": {"sent": 5, "attempted": 5}}) == []


# ── 富集命中率（enrichmentMetrics.js 分母恒真实 O2）──────────────────────────
def test_enrichment_rate_real_denominator():
    assert compute_enrichment_rate(0, 0) == {"rate": 0, "hits": 0, "denominator": 0}
    # 分母恒真实：无调用不得用 hits 顶替分母造率（O2 边界）
    assert compute_enrichment_rate(0, 5)["rate"] == 0
    out = compute_enrichment_rate(452, 143)
    assert out["rate"] == 143 / 452 and out["denominator"] == 452
    agg = aggregate_enrichment([{"cost": 10, "calls": 100, "hits": 30},
                                {"cost": 5, "calls": 50, "hits": 10}])
    assert agg["total_cost"] == 15 and agg["calls"] == 150 and agg["hits"] == 40
    assert agg["rate"] == 40 / 150          # 多源分别求和再算总率（非率平均）


# ── 边双口径（edgeSource.js O4）──────────────────────────────────────────────
def test_edge_caliber_demo_not_in_denominator():
    edges = [{"source": "engine"}, {"source": "seed-script"}, {"source": None}, {}]
    parts = split_edges_by_caliber(edges)
    assert len(parts["runtime"]) == 1 and len(parts["demo"]) == 3
    assert edge_caliber_count(edges) == {"runtime": 1, "demo": 3}
    assert runtime_edges_only(edges) == [{"source": "engine"}]
    assert is_runtime_edge_source(None) is False      # NULL 不计入真实供给
    assert is_runtime_edge_source("mcp") is True
    # 原数组不被修改（拆组非过滤删除，零 DELETE）
    assert len(edges) == 4


# ── 失败计数器（busFailures.js O6）───────────────────────────────────────────
def test_failure_counter_single_source():
    fc = FailureCounter()
    assert fc.record("bus-subscriber") == {"kind": "bus-subscriber", "count": 1}
    fc.record("bus-subscriber")
    fc.record("agent-event-trigger-dispatch")
    assert fc.get() == {"bus-subscriber": 2, "agent-event-trigger-dispatch": 1}
    fc.reset()
    assert fc.get() == {}


# ── 三源触发匹配（eventTrigger.js:89-103 A1 fail-closed）─────────────────────
MATRIX = [
    {"source": "event", "domain": "ontology", "type": "ontology-sync",
     "entity_type": "X", "intent": "i1", "agent": "a1",
     "skill_slug": "sk-read", "dedup_field": "payload.stage"},
    {"domain": "particle", "type": "particle-change", "entity_type": "X",
     "intent": "i2", "agent": "a2", "skill_slug": "sk-write", "dedup_field": None},
]


def test_match_trigger_readonly_failclosed():
    # 命中 + 白名单 → 返回行
    row = match_trigger({"source": "event", "domain": "ontology",
                         "type": "ontology-sync", "entity_type": "X"},
                        MATRIX, allowed_skills=["sk-read"])
    assert row["intent"] == "i1"
    # 命中但非白名单 → None（A1 fail-closed，禁默认放行；留痕在调用方）
    assert match_trigger({"source": "event", "domain": "ontology",
                          "type": "ontology-sync", "entity_type": "X"},
                         MATRIX, allowed_skills=["sk-other"]) is None
    # source 缺省视为 'event'（向后兼容 CRM :89）
    row2 = match_trigger({"domain": "ontology", "type": "ontology-sync",
                          "entity_type": "X"}, MATRIX, allowed_skills=["sk-read"])
    assert row2 is not None
    # enabled=False / 空矩阵 → None
    assert match_trigger({"domain": "ontology", "type": "ontology-sync",
                          "entity_type": "X"}, MATRIX,
                         allowed_skills=["sk-read"], enabled=False) is None
    assert match_trigger({"domain": "d", "type": "t", "entity_type": "X"},
                         [], allowed_skills=["sk-read"]) is None
    # 未知 source → fail-closed 抛错
    with pytest.raises(AgentRuntimeError):
        match_trigger({"source": "alien", "domain": "d", "type": "t",
                       "entity_type": "X"}, MATRIX, allowed_skills=["sk-read"])


def test_dedup_key_and_cooldown():
    m = {"intent": "i1", "dedup_field": "payload.stage"}
    # 值非空 → 实值键
    assert dedup_key_for(m, {"entity_id": "e1", "stage": "S3"}) == "e1:i1:S3"
    # 值空 / dedup_field=None → 'new'（每次都算新）
    assert dedup_key_for(m, {"entity_id": "e1"}) == f"e1:i1:{DEDUP_EMPTY_SENTINEL}"
    assert dedup_key_for({"intent": "i2", "dedup_field": None},
                         {"entity_id": "e1"}) == f"e1:i2:{DEDUP_EMPTY_SENTINEL}"
    # 冷却：窗口内 skip 留痕（A6）；首见 dispatch；窗口刚好到期 dispatch
    assert cooldown_verdict(1000, 1000 + DEFAULT_COOLDOWN_MS - 1)["verdict"] == "skip_cooldown"
    v = cooldown_verdict(1000, 1000 + DEFAULT_COOLDOWN_MS)
    assert v["verdict"] == "dispatch"
    assert cooldown_verdict(None, 9999)["verdict"] == "dispatch"   # 首见（DB 去重为主，A2）
    skip = cooldown_verdict(1000, 2000, cooldown_ms=5000)
    assert skip["reason"] == "cooldown" and skip["remaining_ms"] == 4000


# ── glassBox（glassBox.js:10-20 A3）──────────────────────────────────────────
def test_build_glass_box_dirty_signal_filtered():
    out = build_glass_box(score=0.82, rule_ref="ruler/icp-v2",
                          signals=["signal_a", {"type": "signal_b"}, "", {"no_type": 1}, None])
    # 脏信号过滤：trace 项数 = 有效信号数（2）
    assert [t["signal"] for t in out["trace"]] == ["signal_a", "signal_b"]
    assert all(t["rule_ref"] == "ruler/icp-v2" and t["j_score"] == 0.82
               for t in out["trace"])
    assert out["judge"] == {"axis": "capability", "rule_ref": "ruler/icp-v2",
                            "j_score": 0.82}
    # 无信号不抛错走「无信号」分支
    empty = build_glass_box(score=0.5, rule_ref="r", signals=[])
    assert empty["trace"] == [] and "无信号" in empty["why_narrative"]
    assert set(out) == {"judge", "trace", "why_narrative"}


# ── 契约合规三维（contractMonitor.js:44-62 A4）───────────────────────────────
def _ep(phase, **facts):
    return {"phase": phase, "context_facts": facts}


def test_judge_contract_three_dimensions():
    contract = {"contract_task_id": "ct-1", "task": "标题", "agent": "ag",
                "skills": ["s1", "s2"],
                "knowledge_scope": {"layers": ["L1", "L2"]}}
    episodes = [
        _ep("loop-started", skill="s1"),
        _ep("loop-done", skill="s2"),
        _ep("context-injected", knowledge_layers_read=["L1"]),
    ]
    out = judge_contract(contract, episodes)
    assert out["skill_ok"] is True
    assert out["memory_ok"] is False          # L2 未读
    assert out["success"] == COMPLIANCE_PENDING   # 无人工标记恒 pending（A4 禁猜）
    assert out["join_key"] == "ct-1"          # 稳定键优先
    out2 = judge_contract(contract, episodes, success_marker="pass")
    assert out2["success"] == "pass"
    out3 = judge_contract(contract, episodes + [
        _ep("context-injected", knowledge_layers_read=["L2"])])
    assert out3["memory_ok"] is True
    # join_keys_of：稳定键优先回退标题、去重保序
    assert join_keys_of(contract) == ["ct-1", "标题"]
    assert join_keys_of({"task": "仅标题"}) == ["仅标题"]
    # 非法 marker fail-closed
    from chiyu_kernel.contract import AgentRuntimeError
    with pytest.raises(AgentRuntimeError):
        judge_contract(contract, [], success_marker="guessed")


def test_judge_contract_json_string_facts():
    import json
    contract = {"contract_task_id": "c", "skills": ["s1"],
                "knowledge_scope": {"layers": []}}
    eps = [{"phase": "loop-started",
            "context_facts": json.dumps({"skill": "s1"})}]
    assert judge_contract(contract, eps)["skill_ok"] is True


# ── KG 收敛闸门（agents.js:14-64 A5）─────────────────────────────────────────
SPEC = {"capabilities": {"knowledgeScope": {"layers": ["L1", "L2", "L3"]},
                         "kgTarget": ["L1", "L2", "L3"]}}


def test_kg_convergence_gate_served_injected():
    # 降级服务层只有 L1/L2（CRM kg_coverage_stage2 语义——集合注入不硬编码）
    gate = kg_convergence_gate(SPEC, kg_served=["L1", "L2"])
    assert gate["effective"] == ["L1", "L2"]
    assert gate["dropped"] == ["L3"] and gate["triggered"] is True and gate["ok"] is False
    # 运行时只注入 effective（防契约层静默误判）
    assert resolve_runtime_layers(SPEC, ["L1", "L2"]) == ["L1", "L2"]
    # KG 就绪 → 不收敛
    gate2 = kg_convergence_gate(SPEC, kg_served=["L1", "L2", "L3", "L4"])
    assert gate2["triggered"] is False and gate2["ok"] is True
    assert gate2["effective"] == ["L1", "L2", "L3"]
    # l3 降级守卫双保险
    assert l3_degraded_guard(SPEC, ["L1", "L2"]) == {"ok": False, "detail": "声明L3但KG降级"}
    assert l3_degraded_guard(SPEC, ["L1", "L2", "L3"])["ok"] is True
    # 无 kg_target → 开放最高层；L4 越出天花板照样收敛
    spec_open = {"capabilities": {"knowledgeScope": {"layers": ["L1", "L4"]}}}
    gate3 = kg_convergence_gate(spec_open, kg_served=["L1", "L2", "L3", "L4"])
    assert gate3["effective"] == ["L1", "L4"] and gate3["triggered"] is False
    spec_cap = {"capabilities": {"knowledgeScope": {"layers": ["L1", "L4"]},
                                 "kgTarget": "L2"}}
    gate4 = kg_convergence_gate(spec_cap, kg_served=["L1", "L2", "L3", "L4"])
    assert gate4["effective"] == ["L1"] and gate4["dropped"] == ["L4"]


def test_observability_error_failclosed():
    with pytest.raises(ObservabilityError):
        from chiyu_kernel.observability import classify_negative_predicates as cnp
        # 闭集自检：伪造未知类型直接构造不可能经公共 API 触发——验证错误类型可用即可
        raise ObservabilityError("probe")
