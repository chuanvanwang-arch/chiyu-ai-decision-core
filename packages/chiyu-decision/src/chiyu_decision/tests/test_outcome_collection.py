"""P-1（D1.5）：结局采集 API ``append_outcome`` / ``list_outcomes`` 内核实现守卫。

⛔ 反假绿判据（每条对应破坏性构造，判据失效必转红）：
   1. 六必填字段缺失 ⇒ 拒绝落账（不静默放行）；
   2. outcome_kind 非法（∉ OUTCOME_KINDS ∪ extra_kinds）⇒ 拒绝；
   3. outcome_id 重复 ⇒ 拒绝（append-only 幂等防护）；
   4. list_outcomes 未知 decision 返回 ``()`` 诚实降级（不造空记录）；
   5. 同一 decision 多结局并存按采集顺序返回（CRM won/lost/paid 时间序列）。
"""
from __future__ import annotations

import pytest

from chiyu_decision.outcome import append_outcome, clear_outcomes, list_outcomes


def _valid_outcome(outcome_id: str = "o1", decision_id: str = "d1",
                   kind: str = "success", evidence_ref: str = "order-100") -> dict:
    return {
        "outcome_id": outcome_id,
        "decision_id": decision_id,
        "outcome_kind": kind,
        "recorded_ts": "2026-10-13T10:00:00",
        "recorded_by": "user-u1",
        "evidence_ref": "order-100",
    }


@pytest.fixture(autouse=True)
def _isolate_ledger():
    clear_outcomes()
    yield
    clear_outcomes()


def test_append_outcome_returns_id_and_lists():
    oid = append_outcome(_valid_outcome())
    assert oid == "o1"
    rows = list_outcomes("d1")
    assert len(rows) == 1
    assert rows[0]["outcome_id"] == "o1"
    assert rows[0]["outcome_kind"] == "success"


def test_append_outcome_rejects_missing_required_field():
    for missing in ("outcome_id", "decision_id", "outcome_kind",
                    "recorded_ts", "recorded_by", "evidence_ref"):
        bad = _valid_outcome()
        del bad[missing]
        with pytest.raises(ValueError, match="缺必填字段"):
            append_outcome(bad)


def test_append_outcome_rejects_empty_required_field():
    bad = _valid_outcome()
    bad["recorded_by"] = ""
    with pytest.raises(ValueError, match="缺必填字段"):
        append_outcome(bad)


def test_append_outcome_rejects_illegal_kind():
    with pytest.raises(ValueError, match="outcome_kind 非法"):
        append_outcome(_valid_outcome(kind="won"))  # 域扩展未声明


def test_append_outcome_allows_extra_kinds():
    # 域扩展经 extra_kinds 显式声明（CRM won/lost/paid 时间序列）
    oid = append_outcome(_valid_outcome(outcome_id="oW", kind="won"),
                         extra_kinds=("won", "lost", "paid"))
    assert oid == "oW"
    assert list_outcomes("d1")[0]["outcome_kind"] == "won"


def test_append_outcome_rejects_duplicate_id():
    append_outcome(_valid_outcome(outcome_id="dup"))
    with pytest.raises(ValueError, match="outcome_id 重复"):
        append_outcome(_valid_outcome(outcome_id="dup"))


def test_list_outcomes_unknown_decision_is_empty_tuple():
    assert list_outcomes("never") == ()  # 诚实降级，不造空记录


def test_list_outcomes_multi_outcome_same_decision_ordered():
    # CRM won/lost/paid 时间序列：同一 decision 多结局并存，按采集顺序
    append_outcome(_valid_outcome(outcome_id="oL", kind="lost",
                                  evidence_ref="order-1"), extra_kinds=("won", "lost", "paid"))
    append_outcome(_valid_outcome(outcome_id="oW", kind="won",
                                  evidence_ref="order-2"), extra_kinds=("won", "lost", "paid"))
    rows = list_outcomes("d1")
    assert [r["outcome_id"] for r in rows] == ["oL", "oW"]
    assert [r["outcome_kind"] for r in rows] == ["lost", "won"]


def test_outcome_not_polluting_confidence_source():
    # 与铁律 C-B 相容：append_outcome 只收事实，不回写 ratio 源
    append_outcome(_valid_outcome())
    rows = list_outcomes("d1")
    assert "confidence" not in rows[0] or rows[0].get("confidence") is None
