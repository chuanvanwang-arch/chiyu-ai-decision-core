"""SHA-256 链式审计的判别力自证 —— 三类篡改都必须被检出。

⛔ 为什么必须测「删中间一条」：逐条哈希拦不住它，链式才行 —— 这是本模块存在的理由。
   若删用例只测到"改字段"，则整条链退化成"逐条哈希"而无人察觉（假绿）。
"""
from __future__ import annotations

import hashlib

from chiyu_kernel.audit.chain import (
    EMPTY_PLACEHOLDER,
    build_chain,
    canonical,
    chain_hash,
    verify_chain,
)
from chiyu_kernel.contract import (
    AUDIT_GENESIS_HASH,
    AUDIT_HASH_ALGO,
    AUDIT_REQUIRED_FIELDS,
)


def _recs() -> list[dict]:
    return [
        {"audit_id": "a1", "ts": "2026-09-21T10:00:00", "domain": "d",
         "action": "create", "subject_id": "s1", "decision_id": "dec1"},
        {"audit_id": "a2", "ts": "2026-09-21T10:01:00", "domain": "d",
         "action": "update", "subject_id": "s1", "decision_id": "dec2"},
        {"audit_id": "a3", "ts": "2026-09-21T10:02:00", "domain": "d",
         "action": "close", "subject_id": "s1", "decision_id": "dec3"},
    ]


def test_genesis_is_all_zero_and_algo_is_sha256():
    assert AUDIT_HASH_ALGO == "sha256"
    assert AUDIT_GENESIS_HASH == "0" * 64
    # 6 元数据 + 4 载荷值字段（from_value/to_value/verdict/prescription_id）
    assert len(AUDIT_REQUIRED_FIELDS) == 10


def test_clean_chain_verifies():
    r = _recs()
    res = verify_chain(r, build_chain(r))
    assert res.ok is True and res.checked == 3 and res.first_bad_index == -1


def test_first_hash_is_sha256_of_genesis_plus_canonical():
    r = _recs()[:1]
    expect = hashlib.sha256(
        (AUDIT_GENESIS_HASH + canonical(r[0])).encode("utf-8")
    ).hexdigest()
    assert build_chain(r) == [expect]


def test_chain_is_deterministic():
    assert build_chain(_recs()) == build_chain(_recs())


def test_tampered_field_is_caught_at_the_right_index():
    r = _recs()
    h = build_chain(r)
    r[1]["action"] = "delete"                       # 改内容
    res = verify_chain(r, h)
    assert res.ok is False and res.first_bad_index == 1
    assert "失配" in res.reason


def test_deleted_record_is_caught():
    """⛔ 逐条哈希拦不住这个，链式才行 —— 本模块存在的唯一理由。"""
    r = _recs()
    h = build_chain(r)
    del r[1]                                        # 删中间一条
    assert verify_chain(r, h).ok is False


def _value_recs() -> list[dict]:
    """带载荷值字段的自变审计记录（契约字段全集）。"""
    return [
        {"audit_id": "p1", "ts": "2026-09-21T10:00:00", "domain": "retro",
         "action": "tune", "subject_id": "k", "decision_id": "d1",
         "prescription_id": "rx1", "from_value": 1, "to_value": 2, "verdict": "pass"},
        {"audit_id": "p2", "ts": "2026-09-21T10:01:00", "domain": "retro",
         "action": "tune", "subject_id": "k", "decision_id": "d2",
         "prescription_id": "rx2", "from_value": 2, "to_value": 3, "verdict": "pass"},
    ]


def test_tampering_value_field_is_caught():
    """⛔ 载荷值字段（to_value）必须进链：篡改实际改值必须被检出。

    这是 §12.3-5 审计链防篡改的实质——自变记录的本质是"把标尺从 A 改成 B"，
    只哈希元数据会让 B 值篡改漏网。回归测试中曾缺失此覆盖。
    """
    r = _value_recs()
    h = build_chain(r)
    r[0]["to_value"] = 999                              # 篡改实际改值
    res = verify_chain(r, h)
    assert res.ok is False and res.first_bad_index == 0
    assert "失配" in res.reason


def test_missing_value_field_hashes_differently():
    """载荷值字段缺失（∅ 占位）与有值必须区分，防止蓄意抹除改值字段。"""
    a = {"audit_id": "p1"}
    b = {"audit_id": "p1", "to_value": 2}
    assert canonical(a) != canonical(b)


def test_appended_record_is_caught():
    r = _recs()
    h = build_chain(r)
    r.append({"audit_id": "a4", "ts": "2026-09-21T10:03:00", "domain": "d",
              "action": "close", "subject_id": "s1", "decision_id": "dec4"})
    assert verify_chain(r, h).ok is False


def test_length_mismatch_is_reported_with_both_lengths():
    r = _recs()
    res = verify_chain(r[:2], build_chain(r))
    assert res.ok is False and "长度不一致" in res.reason
    assert res.checked == 2


def test_missing_field_hashes_differently_from_empty_value():
    """⛔ 占位符规则：删字段 ≠ 值为空（否则蓄意者可抹除字段而不被发现）。"""
    a = {"audit_id": "a1"}
    b = {"audit_id": "a1", "ts": ""}
    assert canonical(a) != canonical(b)
    assert EMPTY_PLACEHOLDER in canonical(a)


def test_canonical_is_order_insensitive_on_input_but_field_order_is_fixed():
    """字段顺序由契约固定（参与 canonical 序列化，不可重排）；入参字典顺序无关。"""
    x = {"audit_id": "a1", "ts": "t", "domain": "d",
         "action": "create", "subject_id": "s1", "decision_id": "dec1"}
    y = dict(reversed(list(x.items())))
    assert canonical(x) == canonical(y)
    assert chain_hash(AUDIT_GENESIS_HASH, x) == chain_hash(AUDIT_GENESIS_HASH, y)


def test_extra_fields_do_not_change_the_hash():
    """链只对**契约字段**负责：链外字段改了不算篡改（口径必须写明白，不能靠猜）。"""
    r = _recs()
    base = build_chain(r)
    r2 = [dict(x, note="extra") for x in r]
    assert build_chain(r2) == base
