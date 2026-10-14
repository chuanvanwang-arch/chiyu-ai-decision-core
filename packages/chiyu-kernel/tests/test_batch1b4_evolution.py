"""Batch-1b-4 守卫测试——ab_experiment + quota_gate + param_health_check + assemble_prescription。

对拍锚点（CRM 只读快照，判据逐条对齐）：
  - `decision/routingReview.js` judgeArms 三取二（§7.1：≥2 显著且符号一致、方向以 ΔQ 为准、
    样本不足 insufficient_evidence 不硬凑）+ DEFAULT_JUDGE_CFG 四值
  - `context/routingExperiment.js` applyExperimentArm（fail-open 原样 + on 加 off 删）
  - `billing/quotaGate.js` enforceTokenQuota 判决段（block/bill、included×3、-1 哨兵、system 豁免）
  - `monitor/diagnosis.js` recommend 三档 + isRoutingKnob 红线过滤（只展示不产处方）
  - `calibration/patchAssembler.js` enrichPatchesAndSave 组装段（guards 命中不出方 /
    非 threshold/weight 不自动产出 / expected_impact 前后对照）
"""
import pytest

from chiyu_kernel import api
from chiyu_kernel.ab_experiment import JUDGE_CFG_DEFAULTS, apply_arm, close_decision, judge_arms
from chiyu_kernel.evolution.assemble import assemble_prescription
from chiyu_kernel.param_health_check import recommend_prescription, split_red_line
from chiyu_kernel.quota_gate import judge_quota
from chiyu_kernel.contract import (
    AB_ARMS, AB_INVARIANTS, AB_MIN_ARM_SAMPLE_DEFAULT, AB_O_EPS_DEFAULT,
    AB_Q_EPS_DEFAULT, AB_R_EPS_DEFAULT, AB_VERDICTS, AbExperimentError,
    ASSEMBLE_AUTO_KNOBS, ASSEMBLE_EXPECTED_IMPACT_FIELDS, ASSEMBLE_INVARIANTS,
    AssembleError, BILL_HARDCAP_MULTIPLIER, HIGH_RISK_FAIL_RATE,
    PARAM_RISK_LEVELS, QUOTA_INVARIANTS, RECOMMEND_INVARIANTS,
    RECOMMEND_OUTCOMES,
)


def _arm(n, qbar, success_rate, override_rate):
    return {"n": n, "qbar": qbar, "success_rate": success_rate,
            "override_rate": override_rate}


# ── ab_experiment：三取二判据 ───────────────────────────────────────────────
def test_judge_cfg_defaults_match_crm():
    # CRM DEFAULT_JUDGE_CFG 逐值同源（routingReview.js:15-20）
    assert JUDGE_CFG_DEFAULTS == {"q_eps": 0.05, "o_eps": 0.10, "r_eps": 0.05,
                                  "min_arm_sample": 20}
    assert (AB_Q_EPS_DEFAULT, AB_O_EPS_DEFAULT, AB_R_EPS_DEFAULT,
            AB_MIN_ARM_SAMPLE_DEFAULT) == (0.05, 0.10, 0.05, 20)
    assert set(AB_ARMS) == {"on", "off"}
    assert set(AB_VERDICTS) == {"prefer_on", "prefer_off", "insufficient"}


def test_judge_arms_three_of_two_prefers():
    # 双显著同号 → prefer_on（ΔQ>0）；方向以 ΔQ 为准
    j = judge_arms(_arm(30, 0.80, 0.90, 0.10), _arm(30, 0.70, 0.75, 0.20))
    assert j["verdict"] == "prefer_on" and j["reason"] == "significant"
    assert j["significant"] == {"quality": True, "outcome": True, "override": True}
    assert j["hits"] == 3 and j["delta"]["dq"] == pytest.approx(0.10)
    # ΔQ 负向 → prefer_off（rSig 同向：on 覆写率更高 = 不利）
    j = judge_arms(_arm(30, 0.60, 0.70, 0.25), _arm(30, 0.75, 0.85, 0.10))
    assert j["verdict"] == "prefer_off" and j["hits"] >= 2


def test_judge_arms_requires_two_significant():
    # 仅 ΔQ 显著（ΔO 同号但低于阈值、ΔR 上升不利）→ hits=1 → insufficient
    j = judge_arms(_arm(30, 0.80, 0.76, 0.15), _arm(30, 0.70, 0.75, 0.10))
    assert j["verdict"] == "insufficient" and j["reason"] == "not-significant"
    assert j["significant"]["quality"] is True
    assert j["significant"]["outcome"] is False      # 同号但 |ΔO|<0.10
    assert j["significant"]["override"] is False     # MUTANT：ΔR 上升记显著即红


def test_judge_arms_insufficient_evidence_never_concludes():
    # 单臂样本 < 20 ⇒ 显式 insufficient_evidence（不硬凑结论）
    j = judge_arms(_arm(19, 0.9, 0.9, 0.1), _arm(30, 0.5, 0.5, 0.5))
    assert j["verdict"] == "insufficient" and j["reason"] == "insufficient_evidence"
    assert j["samples"] == {"on": 19, "off": 30, "need": 20}
    assert judge_arms(None, _arm(30, 0.5, 0.5, 0.5))["reason"] == "missing-arm"
    # 指标缺失 ≠ 零差异：qbar 非数值 → no-data（不硬凑）
    j = judge_arms(_arm(30, "bad", 0.9, 0.1), _arm(30, 0.5, 0.5, 0.5))
    assert j["verdict"] == "insufficient" and j["reason"] == "no-data"


def test_judge_arms_cfg_validation():
    j = judge_arms(_arm(30, 0.80, 0.9, 0.1), _arm(30, 0.70, 0.5, 0.2),
                   cfg={"min_arm_sample": 10})
    assert j["verdict"] == "prefer_on"
    with pytest.raises(AbExperimentError):
        judge_arms(_arm(30, 0.8, 0.9, 0.1), _arm(30, 0.7, 0.5, 0.2),
                   cfg={"q_eps": None})            # 显式 None 禁静默置 0（判据失效）
    with pytest.raises(AbExperimentError):
        judge_arms(_arm(30, 0.8, 0.9, 0.1), _arm(30, 0.7, 0.5, 0.2),
                   cfg={"bogus": 1})               # 未知判据键


def test_apply_arm_fail_open_and_projection():
    base = ["narrative", "tool"]
    # on=加入 / off=移除；恒新列表（禁原地改）
    out = apply_arm(base, {"track": "memory", "arm": "on"})
    assert out == ["narrative", "tool", "memory"] and base == ["narrative", "tool"]
    assert apply_arm(out, {"track": "memory", "arm": "off"}) == ["narrative", "tool"]
    # 重复 on 不产生重复项（Set 同口径）
    assert apply_arm(base, {"track": "narrative", "arm": "on"}) == base
    # fail-open：实验信息非法 ⇒ 原样返回（装配不因实验读失败而炸）
    assert apply_arm(base, None) == base
    assert apply_arm(base, {"track": "", "arm": "on"}) == base
    assert apply_arm(base, {"track": "x", "arm": "bogus"}) == base


def test_close_decision_three_way_split():
    exp = {"scenario": "s1", "track": "memory", "arm": "on", "baseline": "off"}
    # insufficient ⇒ 排反向臂（append-only 新开一期，禁删原行由消费方落库纪律承载）
    out = close_decision(exp, {"verdict": "insufficient", "reason": "insufficient_evidence",
                               "samples": {"on": 5, "off": 5, "need": 20}})
    assert out["action"] == "next_arm" and out["next_arm"] == "off" and out["patch"] is None
    # 显著且偏好臂 == baseline ⇒ 维持现状（配置已经是对的，不出处方）
    out = close_decision({"track": "memory", "arm": "on", "baseline": "on"},
                         {"verdict": "prefer_on"})
    assert out["action"] == "maintain" and out["patch"] is None
    # 显著且偏好臂 != baseline ⇒ PENDING 处方：to_value=完整轨道数组、from_value=当前原值
    cur = ["narrative"]
    out = close_decision(exp, {"verdict": "prefer_on"}, current_tracks=cur)
    assert out["action"] == "patch"
    p = out["patch"]
    assert p["status"] == "pending" and p["preferred_arm"] == "on"
    assert p["from_tracks"] == ["narrative"] and p["to_tracks"] == ["narrative", "memory"]
    # 缺 current_tracks 即抛（禁猜回滚目标）
    with pytest.raises(AbExperimentError):
        close_decision(exp, {"verdict": "prefer_on"})
    # exp 非法 / 判据结论非法 ⇒ fail-closed
    with pytest.raises(AbExperimentError):
        close_decision({"track": "x", "arm": "bogus", "baseline": "on"}, {"verdict": "prefer_on"})
    with pytest.raises(AbExperimentError):
        close_decision(exp, {"verdict": "prefer_maybe"})


# ── quota_gate：配额判决核 ──────────────────────────────────────────────────
def test_judge_quota_block_and_bill():
    # block：used ≥ included 即断
    d = judge_quota(mode="block", included=1000, used=1000)
    assert d["verdict"] == "deny" and d["reason"] == "block_exhausted" and d["ok"] is False
    # block 缺省 cap = included 本身
    a = judge_quota(mode="block", included=1000, used=999)
    assert a["verdict"] == "allow" and a["cap"] == 1000
    # bill：缺省安全上限 = included × 3（BILL_HARDCAP_MULTIPLIER）
    assert BILL_HARDCAP_MULTIPLIER == 3
    d = judge_quota(mode="bill", included=1000, used=3000)
    assert d["verdict"] == "deny" and d["reason"] == "bill_hard_cap" and d["cap"] == 3000
    a = judge_quota(mode="bill", included=1000, used=2999)
    assert a["verdict"] == "allow" and a["cap"] == 3000
    # 显式 hard_cap 覆盖缺省倍数
    a = judge_quota(mode="bill", included=1000, used=1500, hard_cap=2000)
    assert a["verdict"] == "allow" and a["cap"] == 2000
    d = judge_quota(mode="bill", included=1000, used=2001, hard_cap=2000)
    assert d["verdict"] == "deny" and d["reason"] == "bill_hard_cap"


def test_judge_quota_unlimited_exempt_and_fail_closed():
    # -1 不限哨兵（CRM 与 seatPolicy 同口径）
    a = judge_quota(mode="block", included=-1, used=10**9)
    assert a["verdict"] == "allow" and a["mode"] == "unlimited" and a["cap"] is None
    # 豁免直通（名单由消费方判定后传入——基座不认 'system' 域名）
    a = judge_quota(mode="block", included=10, used=100, exempt=True)
    assert a["verdict"] == "allow" and a["mode"] == "unlimited" and a["exempt"] is True
    # 未知 mode fail-closed（CRM 静默放行——基座加固，报备差异）
    with pytest.raises(Exception):
        judge_quota(mode="bogus", included=10, used=1)
    # used 缺失（运行时事实必填）/ 非法数值
    with pytest.raises(Exception):
        judge_quota(mode="block", included=10, used=None)
    with pytest.raises(Exception):
        judge_quota(mode="block", included="bad", used=1)


# ── param_health_check：recommend 三档 + 红线分离 ───────────────────────────
def test_recommend_three_tiers_matches_crm():
    assert HIGH_RISK_FAIL_RATE == 0.3
    # HIGH + fail>0.3 → approve（严格大于：0.3 本身 reject，CRM > 同口径）
    assert recommend_prescription({"risk": "HIGH"}, 0.31)["recommend"] == "approve"
    assert recommend_prescription({"risk": "HIGH"}, 0.30)["recommend"] == "reject"
    assert recommend_prescription({"risk": "HIGH"}, 0.10)["recommend"] == "reject"
    # MEDIUM + fail>0 → approve
    assert recommend_prescription({"risk": "MEDIUM"}, 0.01)["recommend"] == "approve"
    assert recommend_prescription({"risk": "MEDIUM"}, 0)["recommend"] == "reject"
    # LOW 一律 reject（无自动放行通道；MUTANT：LOW 放行即红）
    assert recommend_prescription({"risk": "LOW"}, 0.9)["recommend"] == "reject"
    # 缺档保守降 LOW ⇒ reject 方向（fail-closed）；未知档抛错；fail 缺省 0
    assert recommend_prescription({}, 0.9)["recommend"] == "reject"
    with pytest.raises(Exception):
        recommend_prescription({"risk": "URGENT"}, 0.5)
    assert recommend_prescription({"risk": "HIGH"}, None)["recommend"] == "reject"


def test_split_red_line_separates_not_drops():
    # CRM isRoutingKnob 同口径：包含匹配、大小写不敏感（前缀清单由消费方注入）
    rows = [{"knob": "context-routing", "v": 1},
            {"knob": "threshold", "v": 2},
            {"knob": "RoutingStrategy", "v": 3}]
    out = split_red_line(rows, ["routing", "context-routing"])
    assert [r["knob"] for r in out["prescribable"]] == ["threshold"]
    assert sorted(r["knob"] for r in out["display_only"]) == ["RoutingStrategy", "context-routing"]
    assert all(r["red_line"] is True for r in out["display_only"])   # 只展示不产处方
    # 空前缀 ⇒ 全部可处方（互斥完备）
    out = split_red_line(rows, [])
    assert len(out["prescribable"]) == 3 and out["display_only"] == []


# ── evolution.assemble：处方组装核 ──────────────────────────────────────────
def _replay_metrics(decisions, conf):
    """同源重放替身（确定性：autonomy 随 threshold 线性变化）。"""
    return {"autonomy": 1.0 - conf.get("threshold", 0.5) * 0.5,
            "escalated": conf.get("threshold", 0.5) * 10,
            "estimated_override_rate": 0.2}


def test_assemble_guards_block_all():
    att = {"guards": [{"id": "G1", "reason": "红线命中"}],
           "patches": [{"knob": "threshold", "delta": {"threshold": 0.1}}]}
    out = assemble_prescription(decisions=[{"x": 1}], conf={"threshold": 0.5, "weights": {}},
                                attribute_result=att, replay=_replay_metrics)
    assert out["blocked_by"] == [{"rule_id": "G1", "reason": "红线命中"}]
    assert out["patches"] == [] and out["skipped"] == []


def test_assemble_threshold_and_weight_enrichment():
    conf = {"threshold": 0.5, "weights": {"quality": 0.3}}
    att = {"guards": [],
           "patches": [{"id": "R1", "label": "提阈值", "knob": "threshold",
                        "delta": {"threshold": 0.1}, "evidence": {"n": 5}},
                       {"id": "R2", "label": "调权重", "knob": "weight",
                        "delta": {"weights": {"quality": 0.05}}}]}
    out = assemble_prescription(decisions=[{"x": 1}, {"x": 2}], conf=conf,
                                attribute_result=att, replay=_replay_metrics)
    assert out["sample"] == 2 and out["blocked_by"] == []
    th, wt = out["patches"]
    # threshold：from=当前原值 / to=原值+delta（from_value 禁猜回滚目标）
    assert th["from_value"] == {"threshold": 0.5} and th["to_value"] == {"threshold": 0.6}
    assert th["expected_impact"]["autonomy_before"] == pytest.approx(0.75)
    assert th["expected_impact"]["autonomy_after"] == pytest.approx(0.70)
    assert th["expected_impact"]["sample_size"] == 2
    # weight：单目标键 from/to 成对
    assert wt["target"] == "quality"
    assert wt["from_value"] == {"weights": {"quality": 0.3}}
    assert wt["to_value"] == {"weights": {"quality": 0.35}}
    # 幂等键：同输入恒同键；delta 变则键变（确定性派生）
    again = assemble_prescription(decisions=[{"x": 1}, {"x": 2}], conf=conf,
                                  attribute_result=att, replay=_replay_metrics)
    assert th["idempotency_key"] == again["patches"][0]["idempotency_key"]
    assert th["idempotency_key"] != wt["idempotency_key"]


def test_assemble_fail_closed_edges():
    conf = {"threshold": 0.5, "weights": {"quality": 0.3}}
    ok = {"guards": [], "patches": []}
    # 非 threshold/weight 不自动产出（skipped 可见，禁静默吞也禁硬凑）
    att = {"guards": [], "patches": [{"id": "R9", "knob": "required_dims",
                                      "delta": {"x": 1}}]}
    out = assemble_prescription(decisions=[], conf=conf, attribute_result=att,
                                replay=_replay_metrics)
    assert out["skipped"] == [{"knob": "required_dims", "id": "R9",
                               "reason": "non_auto_knob"}] and out["patches"] == []
    # weight delta 多键歧义 / conf 缺权重键 / threshold 缺失 → fail-closed
    with pytest.raises(AssembleError):
        assemble_prescription(decisions=[], conf=conf,
                              attribute_result={"guards": [], "patches": [
                                  {"knob": "weight", "delta": {"weights": {"a": 1, "b": 2}}}]},
                              replay=_replay_metrics)
    with pytest.raises(AssembleError):
        assemble_prescription(decisions=[], conf={"threshold": 0.5, "weights": {}},
                              attribute_result={"guards": [], "patches": [
                                  {"knob": "weight", "delta": {"weights": {"quality": 1}}}]},
                              replay=_replay_metrics)
    with pytest.raises(AssembleError):
        assemble_prescription(decisions=[], conf={"weights": {}},
                              attribute_result={"guards": [], "patches": [
                                  {"knob": "threshold", "delta": {"threshold": 0.1}}]},
                              replay=_replay_metrics)
    # replay 非可调用 / 产出缺指标投影 → fail-closed（无对照即盲改）
    with pytest.raises(AssembleError):
        assemble_prescription(decisions=[], conf=conf, attribute_result=ok, replay="formula")
    with pytest.raises(AssembleError):
        assemble_prescription(decisions=[], conf=conf, attribute_result=ok,
                              replay=lambda d, c: {"autonomy": 1.0})   # 缺 escalated 等


# ── 契约词汇与门面同对象 ────────────────────────────────────────────────────
def test_contract_vocabularies():
    assert len(AB_INVARIANTS) == 7 and len(ASSEMBLE_INVARIANTS) == 6
    assert set(ASSEMBLE_AUTO_KNOBS) == {"threshold", "weight"}
    assert ASSEMBLE_EXPECTED_IMPACT_FIELDS == ("autonomy", "escalated",
                                               "estimated_override_rate")
    assert set(PARAM_RISK_LEVELS) == {"LOW", "MEDIUM", "HIGH"}
    assert len(RECOMMEND_INVARIANTS) == 5
    assert len(QUOTA_INVARIANTS) == 6


def test_facade_exports_same_objects():
    assert api.judge_arms is judge_arms
    assert api.apply_arm is apply_arm
    assert api.close_decision is close_decision
    assert api.judge_quota is judge_quota
    assert api.recommend_prescription is recommend_prescription
    assert api.split_red_line is split_red_line
    assert api.assemble_prescription is assemble_prescription
    from chiyu_kernel.contract import ab_experiment as ab
    from chiyu_kernel.contract import quota as q
    from chiyu_kernel.contract import param_health as ph
    assert api.AB_VERDICTS is ab.AB_VERDICTS
    assert api.QUOTA_MODES is q.QUOTA_MODES
    assert api.PARAM_RISK_LEVELS is ph.PARAM_RISK_LEVELS
    from chiyu_kernel.contract import evolution as ev
    assert api.ASSEMBLE_AUTO_KNOBS is ev.ASSEMBLE_AUTO_KNOBS


# ── open_store 注册表观测/测试面（enterprise 增补建议采纳）────────────────────
def test_store_registry_snapshot_and_reset():
    sentinel = dict(api._stores)
    try:
        api._stores.clear()
        api._stores[(1, "alpha")] = object()
        api._stores[(2, "beta")] = object()
        api._stores[(3, "alpha")] = object()      # 同 schema 异 profile：快照去重
        assert api.registered_store_schemas() == ("alpha", "beta")
        api.reset_store_registry()
        assert api.registered_store_schemas() == () and api._stores == {}
    finally:
        api._stores.clear()
        api._stores.update(sentinel)              # 还原全局态，防污染其他测试
