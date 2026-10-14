"""J9 两项落地守卫：要素缺失封顶（J9-C）× 结构化红线消费（J9-P3）。

⛔ 反假绿判据（每条对应破坏性构造，判据失效必转红）：
   1. 封顶单向：min(原分, cap)，永不升分 —— 改成 max/覆盖 = 升分假绿；
   2. 封顶只动映射尺子：fairness 无映射，任何要素缺失都不得波及 —— 改映射 = 波及无辜；
   3. 默认零行为变更：element_cap=False（缺省）时 confidence 与现状逐位一致；
   4. sensitive 强制人工在环：闸裁 APPROVED 必被降级 PENDING —— 删除该分支 =
      敏感项静默自动放行（本轮要堵的假绿）；
   5. 硬红线 > 敏感档：红线优先改判 REJECTED 不得被 sensitive 分支翻成 PENDING；
   6. 回调契约零变更：redline_callback 只见到 redline_items，mutex_top 不得混入。
"""
from typing import Dict, List, Mapping, Tuple

import pytest

from chiyu_kernel.approval import DecisionApprovalVerdict, DecisionVerdictState
from chiyu_kernel.contract.decision import (
    EIGHT_ELEMENTS, ELEMENT_MISSING_CAP, ELEMENT_RUBRIC_CAPS, RUBRIC_KEYS,
)
from chiyu_kernel.contract.profile import RedlineSpec

import chiyu_decision.api as decision_api
from chiyu_decision.api import cap_rubric_by_elements, run_spine


class _ApprovedGate:
    def decide(self, **kw) -> DecisionApprovalVerdict:
        return DecisionApprovalVerdict(state=DecisionVerdictState.APPROVED)


_FULL_ELEMENTS: Dict[str, object] = {e: "x" for e in EIGHT_ELEMENTS}
_FULL_SCORES: Dict[str, float] = {k: 4.0 for k in RUBRIC_KEYS}


def _run(**kw):
    base = dict(
        context={"text": "普通事项", "decision_id": "dJ9"},
        profile=None, rubric_scores=dict(_FULL_SCORES),
        elements=dict(_FULL_ELEMENTS),
    )
    base.update(kw)
    return run_spine(**base)


# ── J9-C：cap_rubric_by_elements 纯函数 ─────────────────────────────────

def test_cap_lowers_only_mapped_rulers():
    """impact 缺 ⇒ importance 封顶 2；其余尺子（含无映射的 fairness）逐键原样。"""
    scores = dict(_FULL_SCORES, importance=4.0, fairness=4.0)
    out = cap_rubric_by_elements(scores, elements_missing=("impact",))
    assert out["importance"] == float(ELEMENT_MISSING_CAP) == 2.0
    assert out["fairness"] == 4.0, "fairness 无要素映射，不得被波及"
    for k in RUBRIC_KEYS:
        if k != "importance":
            assert out[k] == scores[k]


def test_cap_never_raises_and_never_adds_keys():
    """单向下调（低分原样）＋不补键（缺失尺子键保持缺失，missing 判定不被抹掉）。"""
    scores = {"importance": 1.0}                    # depth 整键缺失
    out = cap_rubric_by_elements(scores, elements_missing=("risk_register",))
    assert out == {"importance": 1.0}, "低于 cap 的分数不得被抬升"
    assert "depth" not in out, "⛔ 封顶函数补键 = 把『缺失』伪造成『0 分』"


def test_cap_no_missing_elements_is_identity():
    assert cap_rubric_by_elements(dict(_FULL_SCORES), ()) == dict(_FULL_SCORES)


def test_contract_mapping_guard():
    """映射键恰为 EIGHT_ELEMENTS、值 ⊆ RUBRIC_KEYS、fairness 显式无映射。"""
    assert set(ELEMENT_RUBRIC_CAPS) == set(EIGHT_ELEMENTS)
    mapped = {r for ks in ELEMENT_RUBRIC_CAPS.values() for r in ks}
    assert mapped <= set(RUBRIC_KEYS)
    assert "fairness" not in mapped, "fairness 评利益平衡，无要素对应（显式留白）"


# ── J9-C：spine element_cap 接线 ────────────────────────────────────────

def test_spine_element_cap_off_by_default_is_bit_identical():
    """缺省（False）零行为变更：confidence 与既有路径逐位一致。"""
    partial = {e: "x" for e in EIGHT_ELEMENTS if e in ("impact", "risk_register",
                                                       "stop_loss")}
    scores = dict(_FULL_SCORES)
    r_default = _run(elements=partial, rubric_scores=scores)
    r_explicit = _run(elements=partial, rubric_scores=scores, element_cap=False)
    assert r_default.confidence == r_explicit.confidence
    from chiyu_decision.api import score_rubric, aggregate_confidence
    uncapped = aggregate_confidence(score_rubric(scores))
    assert r_default.confidence == uncapped, "⛔ 默认路径被改动 = 破坏向后兼容"


def test_spine_element_cap_true_reduces_confidence():
    partial = {e: "x" for e in EIGHT_ELEMENTS if e not in ("impact",)}
    r_off = _run(elements=partial)
    r_on = _run(elements=partial, element_cap=True)
    assert r_on.confidence < r_off.confidence, "要素缺失必须实际拉低置信度"
    assert r_on.elements_missing == ("impact",)


# ── J9-P3：redline_spec 结构化红线 ──────────────────────────────────────

def test_spec_mutex_top_joins_hard_redline_track():
    res = _run(
        context={"text": "拟越权导出客户数据并批量出货", "decision_id": "dJ9m"},
        redline_spec=RedlineSpec(mutex_top=frozenset({"越权导出客户数据"}),
                                 sensitive=frozenset()),
    )
    assert res.redline_hit is True and "越权导出客户数据" in res.redline_reasons
    assert res.autonomous is False and res.sensitive_hits == ()


def test_spec_sensitive_forces_pending_on_passthrough():
    """透传路径（无显式闸）：sensitive 命中 ⇒ pending=True、不落库、审计 approval_pending。"""
    audits: List[tuple] = []
    res = _run(
        context={"text": "本单资金挪用风险需评估", "decision_id": "dJ9s"},
        redline_spec=RedlineSpec(sensitive=frozenset({"资金挪用"})),
        persister=lambda r: True, audit_sink=lambda t, p: audits.append((t, p)),
    )
    assert res.pending is True and res.persisted is False
    assert res.sensitive_hits == ("资金挪用",) and res.redline_hit is False
    assert res.autonomous is False, "强制人工在环 ⇒ 不得自主放行"
    assert len(audits) == 1 and audits[0][0] == "approval_pending"


def test_spec_sensitive_downgrades_explicit_approval():
    """显式闸裁 APPROVED + sensitive 命中 ⇒ 强制降级 PENDING（闸不得豁免人工在环）。"""
    audits: List[tuple] = []
    res = _run(
        context={"text": "涉敏感项 x1 的常规申请", "decision_id": "dJ9d"},
        approval_gate=_ApprovedGate(),
        redline_spec=RedlineSpec(sensitive=frozenset({"x1"})),
        persister=lambda r: True, audit_sink=lambda t, p: audits.append((t, p)),
    )
    assert res.pending is True and res.persisted is False
    assert res.approval_rejected is None
    assert audits[0][1]["reason"].startswith("敏感项命中")


def test_hard_redline_beats_sensitive():
    """mutex_top 与 sensitive 同命中 ⇒ 红线优先改判 REJECTED，sensitive 分支不得翻案。"""
    res = _run(
        context={"text": "未做小样确认即批量出货，且涉及敏感项 s1", "decision_id": "dJ9h"},
        approval_gate=_ApprovedGate(),
        redline_spec=RedlineSpec(
            mutex_top=frozenset({"未做小样确认即批量出货"}), sensitive=frozenset({"s1"})),
    )
    assert res.redline_hit is True and res.pending is False
    assert res.approval_rejected is not None, "硬红线必须压过敏感档（A 红线优先）"


def test_spec_rejects_non_spec_type():
    """类型闸：词表形态走 spec = 装错轨，fail-fast（防两轨混装）。"""
    with pytest.raises(TypeError, match="redline_items"):
        _run(redline_spec=["未做小样确认即批量出货"])


def test_callback_contract_unchanged_when_spec_present():
    """redline_callback 只见到 redline_items；mutex_top 由内置匹配独立判定后合并。"""
    seen: List[Tuple[str, ...]] = []

    def cb(*, context, redline_items):
        seen.append(tuple(redline_items))
        from chiyu_decision.api import RedlineVerdict
        return RedlineVerdict(hit=False, reasons=())

    res = _run(
        context={"text": "命中互斥项 m1 与敏感项 g1", "decision_id": "dJ9c"},
        redline_items=("词表项",),
        redline_callback=cb,
        redline_spec=RedlineSpec(mutex_top=frozenset({"m1"}), sensitive=frozenset({"g1"})),
    )
    assert seen == [("词表项",)], "⛔ 回调收到合并目录 = 回调契约被变更"
    assert res.redline_hit is True and "m1" in res.redline_reasons


# ── 门面 ────────────────────────────────────────────────────────────────

def test_facade_exports():
    assert "cap_rubric_by_elements" in decision_api.__all__
    assert decision_api.cap_rubric_by_elements is cap_rubric_by_elements
    from chiyu_kernel.api import ELEMENT_MISSING_CAP, ELEMENT_RUBRIC_CAPS
    assert ELEMENT_MISSING_CAP == 2 and set(ELEMENT_RUBRIC_CAPS) == set(EIGHT_ELEMENTS)
