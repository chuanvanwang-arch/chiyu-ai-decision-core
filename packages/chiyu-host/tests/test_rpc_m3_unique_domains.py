"""M3 本平台独有域（tables / memory / decision）RPC 判别测试。

不连 pg：tables 反射 contract.particle 常量、decision 反射 contract.decision 常量；
memory/decision 写域走 session 投影桥接（仿 goal）。每域含判别项 + 变异自证位点。
"""
from chiyu_kernel.contract import particle as _pc

from chiyu_host.methods import (
    RpcError, session_create, table_list, table_describe,
    memory_write, memory_read, decision_spine, decision_record, session_history,
)


def _new_session(sid: str = "m3-sess-1") -> str:
    session_create({"sessionId": sid})
    return sid


# ── tables（只读反射 contract.particle，零 pg）──────────────────────────────
def test_table_list_reflects_core_roles():
    val = table_list({})["tables"]
    assert len(val) >= 5, "粒子表应含 ≥5 个 CORE_ROLES"
    got = {t["particleType"] for t in val}
    assert got == set(_pc.CORE_ROLES), f"应反射全部 CORE_ROLES，实得 {got}"


def test_table_describe_has_predicates():
    val = table_describe({"particleType": "decision"})
    assert "attrTypes" in val and len(val["attrTypes"]) == len(_pc.ATTR_TYPES)
    pred_names = {p["predicate"] for p in val["predicates"]}
    assert "DECIDED_ON" in pred_names, "decision 表应含 M 层谓词 DECIDED_ON（假绿防护）"


# ── memory（session 投影，六元组严写）──────────────────────────────────────
def test_memory_write_six_tuple_strict_and_read():
    sid = _new_session("m3-mem-1")
    full = {"sessionId": sid, "topic": "t1", "layer": "L2", "anchor_kind": "decision",
            "anchor_id": "d-1", "actor": "agent", "occurred_at": "2026-09-26T00:00:00Z",
            "kind": "note", "text": "结论"}
    res = memory_write(full)
    assert res["written"] is True and res["count"] == 1
    read = memory_read({"sessionId": sid, "topic": "t1"})
    assert read["count"] == 1 and read["entries"][0]["text"] == "结论"


def test_memory_write_rejects_missing_address():
    sid = _new_session("m3-mem-2")
    bad = {"sessionId": sid, "topic": "t1", "layer": "L2", "anchor_kind": "decision",
           "anchor_id": "d-1", "occurred_at": "2026-09-26T00:00:00Z",  # 缺 actor
           "kind": "note", "text": "x"}
    try:
        memory_write(bad)
    except RpcError as e:
        assert e.code == "memory-address-incomplete"
        return
    raise AssertionError("缺六元组寻址项应拒写（strict），却落库了 → 静默假绿")


# ── decision（只读反射 + 投影桥接）─────────────────────────────────────────
def test_decision_spine_reflects_contract():
    val = decision_spine({})
    assert val["spineOrder"][0] == "S1_context", "SPINE_ORDER 首段须为 S1_context（不可重排）"
    assert len(val["spineOrder"]) == 6, "SPINE_ORDER 须 6 段"
    assert len(val["rubricKeys"]) == 9, "九尺子须 9 项"
    assert len(val["sevenDims"]) == 7, "七维须 7 项"
    assert "S2_score" in val["spineOrder"] and "S5_persist" in val["spineOrder"]


def test_decision_record_projection_and_event():
    sid = _new_session("m3-dec-1")
    created = decision_record({"sessionId": sid, "objective": "采纳 L1–L2 装配",
                                "rationale": "契约授权层", "stage": "S2_score"})
    assert created["ref"]["id"] == f"decision:{sid}", "决策记录 id 须 decision:<sid>"
    assert created["ref"]["revision"] == 1
    # session 投影事件：history 含 decision/record
    events = [e["event"] for e in session_history({"sessionId": sid})["events"]]
    dec_ev = [e for e in events if e.get("type") == "decision/record"]
    assert dec_ev, "会话缺 decision/record 投影事件（假绿）"
    # 读取回投影
    read = decision_record({"sessionId": sid, "ref": {"id": f"decision:{sid}", "revision": 1}})
    assert read["objective"] == "采纳 L1–L2 装配"
