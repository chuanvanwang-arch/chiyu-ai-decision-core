"""GAP-9 promotion/reflux 守卫（Batch-2b，2026-10-14）。

覆盖：升格三态四路径 / 候选抽取只认显式声明 / 漂移 None 告警 /
audit_drift checked==0≠零漂移 / 覆盖守卫 / 载荷红线（恒 PROMOTED）/
通道路由（未知 kind 抛错 + 未登记默认 c3p）/ 后见之明 AND 条件 +
no_data≠healthy + stagnant 停方 / deviation_rate parity 键集 /
reflux_prescribe_guard 四道闸 / load_json_policy 逐键回落与未知键不入 /
PRESCRIPTION_PENDING 与 evolution 状态机对拍 / 门面与契约同一对象 /
APS 锚点 parity 形态。

parity 锚点（APS 仓只读，file:line 可反证）：
    · ``platform/promotion.py:135``   promote_gate 三态（白名单→证据→一致性）
    · ``platform/promotion.py:237``   drift_detected 三值（True/False/None）
    · ``platform/promotion.py:257``   build_promotion_payload（params_source 红线）
    · ``platform/promotion.py:295``   extract_numeric_candidates（显式声明）
    · ``platform/promotion.py:313``   promotion_overwrite_guard（calibrated 禁覆盖）
    · ``platform/promotion.py:332``   audit_drift（checked==0≠零漂移）
    · ``platform/promotion.py:90``    load_promotion_policy（逐键回落）
    · ``platform/reflux.py:157``      prescribe 四道闸（白名单→解析→依据→恒 PENDING）
    · ``platform/reflux.py:281``      route_retro（kind 分流，未知即拒）
    · ``platform/reflux.py:367``      PROPOSAL_CHANNELS/DEFAULT_CHANNEL=c3p
    · ``platform/reflux.py:476``      deviation_rate 同键集（no_data≠healthy）
    · ``platform/reflux.py:523``      hindsight_check（AND 条件 + 每次留痕）
"""
from __future__ import annotations

import json

import pytest

from chiyu_kernel import api
from chiyu_kernel import promotion
from chiyu_kernel.contract import promotion as contract_promo
from chiyu_kernel.contract.promotion import (
    DEFAULT_MIN_CONSISTENCY,
    DEFAULT_MIN_EVIDENCE,
    PARAMS_SOURCE_PROMOTED,
    PRESCRIPTION_PENDING,
    PROMOTED,
    REFLUX_CHANNELS,
    REFLUX_KINDS,
    PROTECTED_STAGES,
    RefluxChannelError,
)
from chiyu_kernel.promotion import (
    audit_drift,
    build_promotion_payload,
    default_reflux_policy,
    deviation,
    deviation_rate,
    drift_detected,
    extract_numeric_candidates,
    kind_to_channel,
    load_json_policy,
    positive_float,
    positive_int,
    promote_gate,
    promotion_overwrite_guard,
    proposal_channel,
    reflux_prescribe_guard,
    should_prescribe,
    unit_float,
    window_status,
)

PROMOTABLE = ("c2a_width_shrink", "c2b_margin_floor")


# ── 升格闸门三态四路径 ──────────────────────────────────────────────

def test_gate_whitelist_outside_rejected():
    out = promote_gate("objective.unknown", [1, 1, 1], promotable=PROMOTABLE)
    assert out["status"] == "rejected"
    assert out["value"] is None
    assert out["evidence_count"] == 3
    # 白名单外直接拒绝：不得降级为 blocked 的"待补证据"形态
    assert "不在可升格键集合" in out["reason"]


def test_gate_insufficient_evidence_blocked():
    out = promote_gate("c2a_width_shrink", [1, 1], promotable=PROMOTABLE)
    assert out["status"] == "blocked"
    assert "孤证" in out["reason"] or "证据不足" in out["reason"]


def test_gate_inconsistent_evidence_blocked():
    # 3 条证据达数但众数占比 1/3 < 0.7 ⇒ 自相矛盾
    out = promote_gate("c2a_width_shrink", [1, 2, 3], promotable=PROMOTABLE)
    assert out["status"] == "blocked"
    assert "不一致" in out["reason"]


def test_gate_promoted_returns_mode_value():
    out = promote_gate("c2a_width_shrink", [0.85, 0.85, 0.85, 0.9],
                       promotable=PROMOTABLE)
    assert out["status"] == PROMOTED
    assert out["value"] == 0.85
    assert out["consistency"] == 0.75
    assert out["evidence_count"] == 4


def test_gate_default_thresholds_from_contract():
    # 默认口径：min_evidence=3 / min_consistency=0.7（契约常量，不得漂移）
    assert DEFAULT_MIN_EVIDENCE == 3
    assert DEFAULT_MIN_CONSISTENCY == 0.7
    out = promote_gate("c2a_width_shrink", [0.85, 0.85, 0.85],
                       promotable=PROMOTABLE)
    assert out["status"] == PROMOTED
    # 3 条样本众数 2/3 ≈ 0.67 < 0.7 ⇒ 默认口径下判矛盾（不是"差不多就行"）
    out2 = promote_gate("c2a_width_shrink", [0.85, 0.85, 0.86],
                        promotable=PROMOTABLE)
    assert out2["status"] == "blocked"


def test_gate_unhashable_samples_do_not_crash():
    # 分段表等不可哈希样本：不崩、不静默丢
    out = promote_gate("c2a_width_shrink",
                       [{"tiers": [1, 2]}, {"tiers": [1, 2]}, {"tiers": [1, 2]}],
                       promotable=PROMOTABLE)
    assert out["status"] == PROMOTED
    assert out["value"] == {"tiers": [1, 2]}


def test_gate_is_pure_no_side_effects():
    # 零副作用：不发射事件、不落库——签名里没有 bus/store 入口
    import inspect
    params = inspect.signature(promote_gate).parameters
    assert "bus" not in params and "store" not in params


# ── 候选抽取：只认显式声明 ──────────────────────────────────────────

def test_extract_candidates_explicit_declarations_only():
    text = 'width_shrink: 0.85\n备注：大概打了八五折，约 3 单\n"width_shrink":0.9'
    got = extract_numeric_candidates(text, "width_shrink")
    # 只认 `<key>[:=]<数值>`：散文里的"八五折/3 单"不得被猜成证据
    assert got == [0.85, 0.9]


def test_extract_candidates_no_declaration_yields_empty():
    assert extract_numeric_candidates("八五折成交，客户很满意", "width_shrink") == []
    assert extract_numeric_candidates("", "width_shrink") == []
    assert extract_numeric_candidates("width_shrink: 1", "") == []


def test_extract_candidates_negative_and_decimal():
    got = extract_numeric_candidates("margin_floor: -0.5; margin_floor=1.25", "margin_floor")
    assert got == [-0.5, 1.25]


# ── 漂移判定：None 不可比必须冒泡 ───────────────────────────────────

def test_drift_detected_three_values():
    assert drift_detected(0.85, [0.85]) is False
    assert drift_detected(0.90, [0.85]) is True
    # 无真值 ⇒ 不可比（None），调用方必须当告警处理，不得读成"无漂移"
    assert drift_detected(0.85, []) is None


def test_drift_detected_non_number_against_truth_alerts():
    # 真值是标量而升格值不是 ⇒ 无法确认一致 ⇒ 告警（不是 False）
    assert drift_detected("wide", [0.85]) is True


def test_drift_tolerance_absorbs_float_noise():
    assert drift_detected(0.85 + 1e-9, [0.85]) is False


def test_audit_drift_checked_zero_is_not_zero_drift():
    # checked==0 的含义是"没有可审计项"，不是"零漂移"
    out = audit_drift([{"rule_key": "x.y", "params": {"y": 1.0}}],
                      truth_lookup=lambda comp: [])
    assert out["summary"]["checked"] == 0
    assert out["summary"]["drifted"] == 0
    # 零命中不得被读成"全通过"——items 为空即无审计覆盖面
    assert out["items"] == []


def test_audit_drift_flags_and_incomparable():
    rules = [
        {"rule_key": "c2a", "params": {"width": 0.9, "extra": 1},
         "stage": "promoted", "params_source": "PROMOTED"},
        {"rule_key": "c2b", "params": {"floor": 0.5}},
    ]
    truth = {"c2a.width": [0.85], "c2b.floor": ["wide"]}
    out = audit_drift(rules, truth_lookup=lambda comp: truth.get(comp, []))
    assert out["summary"]["checked"] == 2
    # drift_alert 计入不可比告警（不可比 = 不静默）：真实漂移 1 + 不可比 1
    assert out["summary"]["drifted"] == 2
    assert out["summary"]["incomparable"] == 1  # "wide" 非数值
    by_key = {i["rule_key"]: i for i in out["items"]}
    assert by_key["c2a.width"]["drift_alert"] is True
    assert by_key["c2a.width"]["comparable"] is True
    assert by_key["c2b.floor"]["drift_alert"] is True   # 不可比 ⇒ 告警不静默
    assert by_key["c2b.floor"]["comparable"] is False


# ── 覆盖守卫 + 载荷红线 ─────────────────────────────────────────────

def test_overwrite_guard_calibrated_is_protected():
    ok, reason = promotion_overwrite_guard("calibrated")
    assert ok is False
    assert "污染" in reason
    assert "calibrated" in PROTECTED_STAGES


def test_overwrite_guard_other_stages_writable():
    assert promotion_overwrite_guard(None)[0] is True
    assert promotion_overwrite_guard("promoted")[0] is True
    assert promotion_overwrite_guard("candidate")[0] is True


def test_payload_redline_params_source_never_calibrated():
    out = build_promotion_payload("c2a.width", value=0.85, confidence=0.9,
                                  sources=["note-1", "note-2"])
    # ★ 红线：绝不写 CALIBRATED
    assert out["params_source"] == PARAMS_SOURCE_PROMOTED
    assert out["params_source"] != "CALIBRATED"
    assert out["stage"] == "promoted"
    assert out["aiGenerated"] is True
    assert out["rule_confidence"] == 0.9
    assert out["evidence"] == "note-1;note-2"
    assert out["params"] == {"width": 0.85}


def test_payload_unspecified_evidence_is_explicit():
    out = build_promotion_payload("c2a.width", value=0.85, confidence=0.5)
    # 缺来源不得静默留空——显式标记 unspecified
    assert out["evidence"] == "promotion:unspecified"


def test_payload_incomparable_drift_alerts():
    # drift_lookup 无真值 ⇒ 不可比 ⇒ drift_alert=True（不静默）
    out = build_promotion_payload("c2a.width", value=0.85, confidence=0.9,
                                  drift_lookup=lambda key: [])
    assert out["drift_alert"] is True
    # 显式传入 False（已比对一致）不得被覆盖成告警
    out2 = build_promotion_payload("c2a.width", value=0.85, confidence=0.9,
                                   drift=False)
    assert out2["drift_alert"] is False


# ── 回流四通道路由 ──────────────────────────────────────────────────

def test_kind_to_channel_full_mapping():
    assert kind_to_channel("fact") == "c1"
    assert kind_to_channel("falsified") == "c2"
    assert kind_to_channel("config_patch") == "c3"
    assert kind_to_channel("hindsight") == "c3p"


def test_kind_to_channel_unknown_raises():
    # 未知 kind ⇒ 抛错（禁静默丢弃：事实没落任何通道却报"已处理"= 假绿）
    with pytest.raises(RefluxChannelError):
        kind_to_channel("whatever")
    assert set(REFLUX_KINDS) == {"fact", "falsified", "config_patch", "hindsight"}


def test_proposal_channel_unregistered_defaults_to_suggestion():
    # 未登记 kind ⇒ 默认建议通道 c3p（永远不会被自动 apply）
    assert proposal_channel("brand_new_kind", mapping={"a": "c3"}) == "c3p"


def test_proposal_channel_illegal_channel_raises():
    with pytest.raises(RefluxChannelError):
        proposal_channel("x", mapping={"x": "c9"})


def test_channels_closed_set_matches_contract():
    assert REFLUX_CHANNELS == ("c1", "c2", "c3", "c3p")


# ── 后见之明：AND 条件 + 窗口判据 ───────────────────────────────────

def test_deviation_is_absolute_distance():
    assert deviation(0.9, 0.8) == pytest.approx(0.1)
    assert deviation(0.7, 0.8) == pytest.approx(0.1)


def test_should_prescribe_and_condition():
    # 单条超阈 AND 窗口告警才出方——不是 OR
    assert should_prescribe(delta=0.5, threshold=0.3, rate=0.5, rate_alarm=0.3) is True
    assert should_prescribe(delta=0.5, threshold=0.3, rate=0.1, rate_alarm=0.3) is False
    assert should_prescribe(delta=0.1, threshold=0.3, rate=0.9, rate_alarm=0.3) is False


def test_window_status_no_data_is_not_healthy():
    # 空窗口显式 no_data——"没数据" ≠ "运行良好"
    assert window_status(samples=0, deviations=0, approved=0,
                         rate=0.0, rate_alarm=0.3) == "no_data"


def test_window_status_stagnant_when_deviations_zero_approved():
    assert window_status(samples=10, deviations=2, approved=0,
                         rate=0.2, rate_alarm=0.3) == "stagnant"


def test_window_status_alarm_and_healthy():
    assert window_status(samples=10, deviations=5, approved=2,
                         rate=0.5, rate_alarm=0.3) == "alarm"
    assert window_status(samples=10, deviations=1, approved=3,
                         rate=0.1, rate_alarm=0.3) == "healthy"


def test_deviation_rate_parity_key_set_and_statuses():
    now = 1_000_000_000.0
    day = 86400.0
    effects = [(now - 30 * day, 0.5), (now - 60 * day, 0.1),
               (now - 200 * day, 0.9)]  # 窗口外 → 不计
    out = deviation_rate(effects, approved_prescriptions=1,
                         threshold=0.3, rate_alarm=0.3, window_days=90, now=now)
    # APS reflux.deviation_rate:476 同键集
    assert set(out) == {"window_days", "threshold", "rate_alarm", "samples",
                        "deviations", "rate", "alarm", "approved_prescriptions",
                        "stagnant", "status"}
    assert out["samples"] == 2
    assert out["deviations"] == 1
    assert out["rate"] == 0.5
    assert out["alarm"] is True
    assert out["status"] == "alarm"


def test_deviation_rate_empty_window_no_data():
    out = deviation_rate([], now=1_000_000_000.0)
    assert out["samples"] == 0
    assert out["status"] == "no_data"     # 不是 healthy
    assert out["rate"] == 0.0
    assert out["stagnant"] is False


def test_deviation_rate_stagnant_stops_prescribing_semantics():
    out = deviation_rate([(1_000_000_000.0, 0.5)], approved_prescriptions=0,
                         threshold=0.3, rate_alarm=0.3, now=1_000_000_000.0)
    # 有偏差零批准 ⇒ 空转：问题不在"没有建议"而在"没人采纳"
    assert out["status"] == "stagnant"
    assert out["stagnant"] is True


def test_deviation_rate_window_filtering():
    now = 1_000_000_000.0
    day = 86400.0
    out = deviation_rate([(now - 91 * day, 0.9)], window_days=90, now=now)
    assert out["samples"] == 0   # 恰在窗外不得混入


def test_default_reflux_policy_returns_fresh_copy():
    p1 = default_reflux_policy()
    p1["threshold"] = 999.0
    # 返回副本：调用方改默认值不得污染契约常量
    assert default_reflux_policy()["threshold"] == 0.3


# ── 回流处方守卫四道闸 ──────────────────────────────────────────────

def test_prescribe_guard_whitelist_outside_rejected():
    out = reflux_prescribe_guard(key="objective.margin", value=0.2,
                                 rationale="依据充分",
                                 prescribable=("reschedule.cadence",))
    assert out["status"] == "rejected"
    assert out["reason"] is not None
    assert "不在可处方键集合" in out["reason"]


def test_prescribe_guard_unresolvable_rejected():
    # 白名单内但配置解析失败 ⇒ 同样拒绝（防据不存在的键改配置）
    out = reflux_prescribe_guard(key="reschedule.cadence", value=5,
                                 rationale="依据充分",
                                 prescribable=("reschedule.cadence",),
                                 resolvable=False)
    assert out["status"] == "rejected"
    assert "解析失败" in out["reason"]


def test_prescribe_guard_empty_rationale_rejected():
    out = reflux_prescribe_guard(key="reschedule.cadence", value=5,
                                 rationale="   ",
                                 prescribable=("reschedule.cadence",),
                                 resolvable=True, current=3)
    assert out["status"] == "rejected"
    assert "rationale" in out["reason"]


def test_prescribe_guard_pending_with_from_to():
    out = reflux_prescribe_guard(key="reschedule.cadence", value=5,
                                 rationale="窗口偏差率 0.5 超告警线",
                                 prescribable=("reschedule.cadence",),
                                 resolvable=True, current=3)
    assert out["status"] == PRESCRIPTION_PENDING
    assert out["from"] == 3
    assert out["to"] == 5
    assert out["reason"] is None   # 允许出方 ⇒ 无拒绝理由


def test_prescribe_guard_never_mutates_config():
    # 本函数只裁决"能不能出方"：无任何写入口（签名里没有 config/bus/store）
    import inspect
    params = inspect.signature(reflux_prescribe_guard).parameters
    for banned in ("config", "bus", "store", "apply"):
        assert banned not in params


# ── 策略外部化：逐键回落 + 未知键不入 ───────────────────────────────

def test_load_json_policy_missing_file_all_defaults(tmp_path):
    out = load_json_policy(str(tmp_path / "nope.json"),
                           {"min_evidence": 3, "threshold": 0.3},
                           validators={"min_evidence": positive_int,
                                       "threshold": unit_float})
    assert out == {"min_evidence": 3, "threshold": 0.3}


def test_load_json_policy_unknown_keys_dropped(tmp_path):
    p = tmp_path / "pol.json"
    p.write_text(json.dumps({"min_evidence": 5, "rogue_key": "x"}), encoding="utf-8")
    out = load_json_policy(str(p), {"min_evidence": 3},
                           validators={"min_evidence": positive_int})
    # 未知键不进结果——防配置漂移被静默吞进运行时
    assert out == {"min_evidence": 5}
    assert "rogue_key" not in out


def test_load_json_policy_per_key_fallback(tmp_path):
    p = tmp_path / "pol.json"
    p.write_text(json.dumps({"min_evidence": -1, "threshold": 0.5, "window_days": "90"}),
                 encoding="utf-8")
    out = load_json_policy(str(p), {"min_evidence": 3, "threshold": 0.3, "window_days": 90},
                           validators={"min_evidence": positive_int,
                                       "threshold": unit_float,
                                       "window_days": positive_int})
    # 非法键逐键回落默认，不整体崩、不静默接受
    assert out == {"min_evidence": 3, "threshold": 0.5, "window_days": 90}


def test_load_json_policy_non_dict_falls_back(tmp_path):
    p = tmp_path / "pol.json"
    p.write_text(json.dumps([1, 2]), encoding="utf-8")
    out = load_json_policy(str(p), {"min_evidence": 3})
    assert out == {"min_evidence": 3}


def test_validators_reject_bool_and_range():
    # bool 是 int 子类但语义上不是数值
    assert positive_int(True) is None
    assert positive_int(0) is None
    assert positive_float(-0.1) is None
    assert unit_float(1.5) is None
    assert unit_float(0.0) == 0.0


# ── 跨契约一致性：PRESCRIPTION_PENDING 对拍 evolution 状态机 ─────────

def test_prescription_pending_matches_evolution_state_machine():
    # 本层 PRESCRIPTION_PENDING 必须与 contract.evolution.PRESCRIPTION_STATES
    # 的 "pending" 同值——处方状态机单一事实源在 evolution，本层只持回流侧词汇
    from chiyu_kernel.contract.evolution import PRESCRIPTION_STATES
    assert PRESCRIPTION_PENDING in PRESCRIPTION_STATES
    assert PRESCRIPTION_PENDING == "pending"


def test_promotion_package_does_not_redefine_state_machine():
    # promotion 包严禁重造处方状态机（单源裁定）
    src = (promotion.__path__[0] + "/reflux.py").replace("\\", "/")
    with open(src, encoding="utf-8") as f:
        text = f.read()
    assert "PRESCRIPTION_TRANSITIONS" not in text
    assert "def transition" not in text


# ── 门面同对象 + 不变式清单 ─────────────────────────────────────────

def test_facade_reexports_same_objects():
    for name in ("promote_gate", "extract_numeric_candidates", "drift_detected",
                 "audit_drift", "promotion_overwrite_guard",
                 "build_promotion_payload", "kind_to_channel", "route_kind",
                 "proposal_channel", "reflux_prescribe_guard",
                 "default_reflux_policy", "deviation", "should_prescribe",
                 "window_status", "deviation_rate", "load_json_policy",
                 "positive_int", "positive_float", "unit_float"):
        assert getattr(api, name) is getattr(promotion, name)
    for name in ("PROMOTED", "BLOCKED", "REJECTED", "PROMOTION_STATUSES",
                 "PROMOTION_STAGE", "PARAMS_SOURCE_PROMOTED", "PROTECTED_STAGES",
                 "DEFAULT_MIN_EVIDENCE", "DEFAULT_MIN_CONSISTENCY",
                 "TRUTH_TOLERANCE", "PROMOTION_INVARIANTS", "REFLUX_CHANNELS",
                 "REFLUX_KINDS", "KIND_TO_CHANNEL", "DEFAULT_CHANNEL",
                 "PRESCRIPTION_PENDING", "DEFAULT_REFLUX_POLICY",
                 "REFLUX_INVARIANTS", "HINDSIGHT_STATUSES", "WINDOW_STATUSES",
                 "RefluxChannelError", "PromotionPolicyError"):
        assert getattr(api, name) is getattr(contract_promo, name)


def test_invariant_lists_non_empty_and_unique():
    assert len(contract_promo.PROMOTION_INVARIANTS) == 6
    assert len(contract_promo.REFLUX_INVARIANTS) == 9
    assert len(set(contract_promo.PROMOTION_INVARIANTS)) == 6
    assert len(set(contract_promo.REFLUX_INVARIANTS)) == 9


def test_pure_decision_modules_have_no_io():
    # 裁决/路由/后见之明/处方守卫：零 IO（IO 边界只在 policy.py 的策略读取）
    import pathlib
    pkg = pathlib.Path(promotion.__path__[0])
    for mod in ("gate.py", "candidates.py", "channels.py", "hindsight.py",
                "reflux.py"):
        text = (pkg / mod).read_text(encoding="utf-8")
        assert "import os" not in text
        assert "open(" not in text


# ── APS 锚点 parity 形态 ────────────────────────────────────────────

def test_parity_gate_core_key_set_matches_aps():
    # APS promote_gate 返回集 ⊉ 本包键集超集；核心六键必须同形
    core = {"status", "rule_key", "value", "consistency", "evidence_count", "reason"}
    for samples, expect in (([1, 2, 3], "blocked"), ([1, 1, 1], "promoted")):
        out = promote_gate("c2a_width_shrink", samples, promotable=PROMOTABLE)
        assert core <= set(out)
        assert out["status"] == expect


def test_parity_deviation_rate_matches_aps_hindsight_statuses():
    # APS hindsight_check 的 window_status 取值与本包 WINDOW_STATUSES 同集
    out = deviation_rate([], now=1.0)
    assert out["status"] in ("no_data", "stagnant", "alarm", "healthy")
    from chiyu_kernel.contract.promotion import HINDSIGHT_STATUSES
    # 本包后见之明状态闭集与 APS hindsight_check 的 status 取值对齐
    assert "checked" in HINDSIGHT_STATUSES and "no_baseline" in HINDSIGHT_STATUSES
