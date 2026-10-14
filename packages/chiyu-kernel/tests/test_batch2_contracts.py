"""三支柱批次二守卫 —— D5 度量 / D6 审计合一 / D7 判定接口 / D3 HITL 断言实现。

判据面（2026-10-13，docs/plans/2026-10-13-foundation三大支柱详细设计.md 批次二）：
  G1 门面覆盖：批次二符号入 contract.__all__ 且 api 门面同对象（E9/X2 同族纪律）。
  G2 闭集判别力：非法值/矛盾判定/裸字符串扩展必须被拒（变异自证见 git 历史）。
  G3 形状不可变：canonical schema / 聚合键闭集 / 墓碑不变量键恒定（重排即全链失配）。
  G4 HITL 结构保证：「无 approve 不可生效」= 入口断言（缺字段即抛错，非文档纪律）；
     别名通道只认 L0 登记键（CRM 修订②防字段名分裂）；迁移域扩展须显式 extra
     二元组（CRM 修订①，禁裸字符串）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel import api as api_facade
from chiyu_kernel.approval import (
    ApprovalTransitionError,
    HITLEvidenceError,
    assert_hitl_evidence,
    assert_transition,
    missing_hitl_evidence_fields,
)
from chiyu_kernel.contract import (
    APPROVAL_TRANSITION_EXTENSION_RULE,
    AUDIT_CANONICAL_SCHEMA,
    AUDIT_CHAIN_RULE,
    AUDIT_REQUIRED_FIELDS,
    AUDIT_TOMBSTONE_FIELD,
    AUDIT_TOMBSTONE_INVARIANTS,
    AUDIT_TOMBSTONE_REASON_FIELD,
    AGGREGATE_METRIC_KEYS,
    HONEST_DEGRADATION_INVARIANTS,
    HITL_EVIDENCE_FIELDS,
    HITL_RESUME_FIELD_ALIASES,
    METRIC_SUMMARY_FIELDS,
    PRINCIPAL_FIELDS,
    SCORECARD_FIELDS,
    SECURITY_DECISION_FIELDS,
    HITLEvidenceError as C_HITLEvidenceError,
    MetricSummary,
    Principal,
    RoleGate,
    ScoreCard,
    SecurityDecision,
)


def _load_manifest() -> dict:
    import json
    from pathlib import Path
    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "chiyu_kernel" / "contract" / "manifest.json")
    return json.loads(manifest_path.read_text(encoding="utf-8"))

# ══ G1 门面覆盖（contract 与 api 同对象）══════════════════════════════════

BATCH2_SYMBOLS = (
    "HITL_RESUME_FIELD_ALIASES", "APPROVAL_TRANSITION_EXTENSION_RULE",
    "SCORECARD_FIELDS", "METRIC_SUMMARY_FIELDS", "AGGREGATE_METRIC_KEYS",
    "HONEST_DEGRADATION_INVARIANTS", "ScoreCard", "MetricSummary",
    "PRINCIPAL_FIELDS", "SECURITY_DECISION_FIELDS",
    "Principal", "SecurityDecision", "RoleGate",
    "AUDIT_CANONICAL_SCHEMA", "AUDIT_CHAIN_RULE",
    "AUDIT_TOMBSTONE_FIELD", "AUDIT_TOMBSTONE_REASON_FIELD",
    "AUDIT_TOMBSTONE_INVARIANTS",
    "HITLEvidenceError", "ApprovalTransitionError",
    "missing_hitl_evidence_fields", "assert_hitl_evidence",
    "assert_approval_transition",
)


def test_g1_contract_all_covers_batch2():
    for name in BATCH2_SYMBOLS:
        assert name in chiyu_kernel_contract_all(), name
        assert hasattr(chiyu_kernel_contract_mod(), name), name


def test_g1_api_facade_same_objects():
    for name in BATCH2_SYMBOLS:
        assert name in api_facade.__all__, name
        assert getattr(api_facade, name) is getattr(chiyu_kernel_contract_mod(), name), name


# ══ G2 闭集判别力（变异自证：删判据分支 → 构造非法值 → 须红）══════════════


def test_g2_security_decision_mode_closed_set():
    for mode in ("bypass", "OFF", "", "enforce"):
        with pytest.raises(ValueError, match="SECURITY_MODES"):
            SecurityDecision(mode=mode, allowed=True, would_deny=False)


def test_g2_enforced_drift_rejected():
    # D2 防漂移不变量单对象投影：enforced 下 would_deny 必须 == (not allowed)
    with pytest.raises(ValueError, match="防漂移"):
        SecurityDecision(mode="enforced", allowed=True, would_deny=True)
    with pytest.raises(ValueError, match="防漂移"):
        SecurityDecision(mode="enforced", allowed=False, would_deny=False)


def test_g2_off_never_denies():
    with pytest.raises(ValueError, match="恒放行"):
        SecurityDecision(mode="off", allowed=False, would_deny=True)


def test_g2_principal_requires_id():
    with pytest.raises(ValueError, match="必填"):
        Principal(id="")
    assert Principal(id="u1").scopes == ()


def test_g2_honest_degradation_no_fake_summary():
    # no_sample_no_fake_summary：无样本 ⇒ degraded 且不得携带汇总值
    with pytest.raises(ValueError, match="伪造"):
        MetricSummary(window="w1", sample_count=0, degraded=False)
    with pytest.raises(ValueError, match="伪造"):
        MetricSummary(window="w1", sample_count=0, degraded=True,
                      metrics={"hit_rate": 0.9})


def test_g2_degraded_requires_reason():
    with pytest.raises(ValueError, match="degraded_reason"):
        MetricSummary(window="w1", sample_count=5, degraded=True)
    with pytest.raises(ValueError, match="互斥"):
        MetricSummary(window="w1", sample_count=5, degraded=False,
                      degraded_reason="oops")
    s = MetricSummary(window="w1", sample_count=0, degraded=True,
                      degraded_reason="无样本")
    assert s.metrics == {}


def test_g2_scorecard_requires_decision_id():
    with pytest.raises(ValueError, match="decision_id"):
        ScoreCard(decision_id="")


def test_g2_hitl_alias_channel_registered_only():
    # 裸字符串别名 → 拒（禁裸字符串扩展；新别名须先入 L0 契约）
    with pytest.raises(ValueError, match="HITL_RESUME_FIELD_ALIASES"):
        missing_hitl_evidence_fields({}, aliases=("who_approved",))


# ══ G4 HITL 结构保证（无 approve 不可生效 = 入口断言）══════════════════════


def test_g4_missing_evidence_raises_with_field_names():
    with pytest.raises(HITLEvidenceError) as ei:
        assert_hitl_evidence({"approver_id": "u1"})
    msg = str(ei.value)
    for field in ("approved_at", "evidence_ref"):
        assert field in msg, field


def test_g4_full_evidence_passes():
    assert_hitl_evidence({"approver_id": "u1", "approved_at": "2026-10-13T00:00:00",
                          "evidence_ref": "ev-1"})


def test_g4_resume_alias_channel_explicit_only():
    payload = {"resume_principal": "u1", "resumed_at": "t", "basis": "b"}
    # 未声明别名 ⇒ resume 字段名不算数（防字段名分裂，CRM 修订②）
    with pytest.raises(HITLEvidenceError):
        assert_hitl_evidence(payload)
    # 显式声明别名 ⇒ 同判据等价切换
    assert_hitl_evidence(payload,
                         aliases=("resume_principal", "resumed_at", "basis"))
    # 别名映射指向 HITL 字段名（机检：三对齐）
    assert set(HITL_RESUME_FIELD_ALIASES.values()) == set(HITL_EVIDENCE_FIELDS)


def test_g4_resume_alias_missing_field_raises():
    # ⛔ 变异自证（T81 修复断言语义后）：aliases=RESUME_EVIDENCE_FIELDS 须真校验
    # resume_principal/resumed_at/basis；缺任一枚红（删本判据 ⇒ resume 缺证据被放行）。
    full = {"resume_principal": "u1", "resumed_at": "t", "basis": "b"}
    assert_hitl_evidence(full, aliases=("resume_principal", "resumed_at", "basis"))
    for missing_one in (
        {"resumed_at": "t", "basis": "b"},            # 缺 resume_principal
        {"resume_principal": "u1", "basis": "b"},      # 缺 resumed_at
        {"resume_principal": "u1", "resumed_at": "t"}, # 缺 basis
    ):
        with pytest.raises(HITLEvidenceError):
            assert_hitl_evidence(
                missing_one, aliases=("resume_principal", "resumed_at", "basis"))


def test_g4_transition_core_closed_set():
    assert_transition("pending", "approved")
    assert_transition("pending", "rejected")
    assert_transition("pending", "canceled")
    for bad in (("pending", "pending"), ("approved", "pending"),
                ("rejected", "approved")):
        with pytest.raises(ApprovalTransitionError):
            assert_transition(*bad)


def test_g4_transition_extra_explicit_tuples_only():
    # CRM 修订①：域扩展通道（加签/转办/退回/撤回回流）须显式 extra 二元组
    assert_transition("approving", "add_sign",
                      extra=(("approving", "add_sign"), ("add_sign", "approving")))
    with pytest.raises(ApprovalTransitionError):
        assert_transition("approving", "transfer")  # 未声明 extra ⇒ 拒
    for malformed in (("a->b",), ("a",), ("", "b"), ("a", None), "ab"):
        with pytest.raises(ValueError, match="禁裸字符串|形状非法"):
            assert_transition("a", "b", extra=(malformed,))


def test_g4_advisory_enforced_share_judge():
    # 两档共享同一判定器 ⇒ advisory.would_deny 与 enforced 拦截结构一致
    payload = {"approver_id": "u1"}
    advisory_missing = missing_hitl_evidence_fields(payload)
    with pytest.raises(HITLEvidenceError):
        assert_hitl_evidence(payload)
    assert advisory_missing == ("approved_at", "evidence_ref")


# ══ G3 形状不可变（重排即全链失配）════════════════════════════════════════


def test_g3_metric_shapes_frozen():
    assert SCORECARD_FIELDS == (
        "decision_id", "rubric_scores", "elements", "metrics")
    assert METRIC_SUMMARY_FIELDS == (
        "window", "sample_count", "metrics", "degraded", "degraded_reason")
    assert AGGREGATE_METRIC_KEYS == (
        "auditability_pct", "full", "hit_rate", "reversal_rate")
    assert HONEST_DEGRADATION_INVARIANTS == (
        "no_sample_no_fake_summary", "degraded_requires_reason",
        "unrated_not_masked_green")


def test_g3_audit_canonical_schema_extends_required():
    # canonical = 必填字段 + 三毕业键（enterprise Q1.3），顺序不可重排
    assert AUDIT_CANONICAL_SCHEMA == AUDIT_REQUIRED_FIELDS + (
        "record_kind", "rubric_scores", "elements")
    assert AUDIT_CHAIN_RULE == "hash = sha256(prev_hash + canonical(record))"
    assert AUDIT_TOMBSTONE_FIELD == "tombstoned"
    assert AUDIT_TOMBSTONE_REASON_FIELD == "tombstone_reason"
    assert AUDIT_TOMBSTONE_INVARIANTS == (
        "tombstone_never_physical_delete", "tombstone_stays_in_chain",
        "tombstone_requires_reason")


def test_g3_manifest_covers_batch2_modules():
    manifest = _load_manifest()
    assert {"metrics.py", "iam.py"} <= set(manifest["files"])


# ── 辅助（延迟取模块，避免顶层 import 环风险）────────────────────────────


def chiyu_kernel_contract_mod():
    import chiyu_kernel.contract as m
    return m


def chiyu_kernel_contract_all():
    return set(chiyu_kernel_contract_mod().__all__)
