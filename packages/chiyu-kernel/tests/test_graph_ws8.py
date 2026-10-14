"""WS8 图存储抽象 —— 测试 + 反假绿探针。

覆盖：受控谓词闸 / 多跳遍历+环检测+深度上限 / 关系图谱视图 / 时间线叙事视图
（决策时间基准）/ 决策回链审计 / 协议禁写方法 / PG CTE SQL 形状 / 两后端对拍。

⛔ 反假绿：每个判据都有对应探针；改闸后探针须转红（见文件末尾变异自证说明）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.graph import (
    DECISION_TIME_BASIS, MAX_TRAVERSAL_HOPS, TIMELINE_SOURCES,
    GraphEdge, GraphStore, InMemoryGraphStore, PgCteGraphStore,
    decision_backlinks, relation_view, timeline_view,
)

# 受控谓词 = M 层 7 条（L0 契约）
PREDS = ("CAUSED", "DECIDED_ON", "DERIVED_FROM_EXCEPTION", "ESTABLISHES_FRAME",
         "INFLUENCED", "OVERRIDES", "REFERENCED_PRECEDENT")


def _edges() -> list:
    """构造一小张图：d1 --REFERENCED_PRECEDENT--> d0 ; d1 --OVERRIDES--> d2 ; d2 --INFLUENCED--> d3"""
    return [
        GraphEdge("d1", "d0", "REFERENCED_PRECEDENT"),
        GraphEdge("d1", "d2", "OVERRIDES"),
        GraphEdge("d2", "d3", "INFLUENCED"),
        GraphEdge("d3", "d1", "CAUSED"),          # 回边 ⇒ 构成环
    ]


def _store() -> InMemoryGraphStore:
    return InMemoryGraphStore(PREDS, _edges())


# ── 受控谓词闸 ──────────────────────────────────────────────────────────────
def test_uncontrolled_predicate_is_rejected() -> None:
    s = _store()
    with pytest.raises(ValueError, match="未受控谓词"):
        s.out_edges("d1", ["GUESS"])
    with pytest.raises(ValueError, match="未受控谓词"):
        s.traverse("d1", predicates=["GUESS"])


def test_probe_uncontrolled_predicate_discriminates() -> None:
    """探针：未受控谓词必须抛（若闸失效静默返回空 ⇒ 图查询会越权读全表）。"""
    s = _store()
    try:
        s.out_edges("d1", ["GUESS"])
    except ValueError as e:
        assert "GUESS" in str(e)
    else:
        pytest.fail("未受控谓词未抛 ⇒ 受控闸失效（会退化为全表遍历）")


def test_empty_controlled_predicates_yield_no_edges() -> None:
    """无受控谓词 ⇒ 恒空（不伪造、不退化成全表）。"""
    s = InMemoryGraphStore((), _edges())
    assert s.out_edges("d1") == ()
    assert s.traverse("d1").nodes == ("d1",)


# ── 一跳邻域 ────────────────────────────────────────────────────────────────
def test_out_in_edges() -> None:
    s = _store()
    assert [e.to_id for e in s.out_edges("d1", ["OVERRIDES"])] == ["d2"]
    assert [e.from_id for e in s.in_edges("d2", ["OVERRIDES"])] == ["d1"]


# ── 多跳遍历：深度 + 环检测 ─────────────────────────────────────────────────
def test_traverse_multi_hop() -> None:
    s = _store()
    res = s.traverse("d1", max_hops=2)
    assert "d3" in res.nodes                     # 二跳可达
    assert ("d1", "d2", "d3") in res.paths


def test_traverse_respects_hop_cap() -> None:
    s = _store()
    one = s.traverse("d1", max_hops=1)
    assert one.nodes == ("d0", "d1", "d2")       # 一跳只到 d0/d2
    assert "d3" not in one.nodes


def test_depth_gate_rejects_out_of_range() -> None:
    s = _store()
    for bad in (0, -1, MAX_TRAVERSAL_HOPS + 1, 99):
        with pytest.raises(ValueError, match="max_hops"):
            s.traverse("d1", max_hops=bad)


def test_probe_depth_cap_discriminates() -> None:
    """探针：深度上限若失效，遍历会一路走穿（本图有环，无上限将无限展开）。"""
    s = _store()
    res = s.traverse("d1", max_hops=1)
    assert "d3" not in res.nodes, "深度上限失效 ⇒ 一跳竟抵达二跳节点"


def test_cycle_does_not_blow_up() -> None:
    """环图遍历必须终止（d3 → d1 回边）。"""
    s = _store()
    res = s.traverse("d1", max_hops=MAX_TRAVERSAL_HOPS)
    assert "d1" in res.nodes
    assert len(res.paths) <= len(_edges()) * MAX_TRAVERSAL_HOPS


def test_truncated_flag_is_honest() -> None:
    """触深度上限仍有 frontier ⇒ truncated=True（不谎称已全量）。"""
    s = _store()
    res = s.traverse("d1", max_hops=1)
    assert res.truncated is True


# ── 视图 1：关系图谱 ────────────────────────────────────────────────────────
def test_relation_view_shape() -> None:
    s = _store()
    v = relation_view(s, "d1", max_hops=MAX_TRAVERSAL_HOPS)
    assert v["root"] == "d1"
    assert {"d0", "d1", "d2", "d3"} <= set(v["nodes"])
    assert all({"from", "to", "predicate"} <= set(e) for e in v["edges"])
    assert sorted(v["controlled"]) == sorted(PREDS)
    # 本图在 MAX 深度内前沿已耗尽 ⇒ truncated=False（走完了，不谎称未走完）
    assert v["truncated"] is False
    # 收窄到二跳：d3 的前沿被截断 ⇒ 必须标 True（前沿在最后一跳仍有新增）
    assert relation_view(s, "d1", max_hops=2)["truncated"] is True


# ── 视图 2：时间线叙事（决策时间基准）──────────────────────────────────────
def test_timeline_view_uses_decision_time_basis() -> None:
    """decided_at 优先于 created_at —— 否则叙事退化成落库时间线。"""
    rows = timeline_view(
        decisions=[
            {"decision_id": "dA", "decided_at": "2026-10-02", "created_at": "2026-10-09"},
            {"decision_id": "dB", "created_at": "2026-10-01"},
        ],
    )
    assert [r["ref"] for r in rows] == ["dB", "dA"]   # dA 按 decided_at 排后
    assert rows[0]["time_basis"] == "2026-10-01"      # 缺 decided_at 回落 created_at


def test_probe_timeline_prefers_decided_at() -> None:
    """探针：若时间基准错用 ts/created_at，排序即反 ⇒ 转红。"""
    rows = timeline_view(decisions=[{"decision_id": "dA", "decided_at": "2026-10-05",
                                     "created_at": "2026-10-01"}])
    assert rows[0]["time_basis"] == "2026-10-05", "时间基准未优先 decided_at"


def test_timeline_aggregates_four_sources() -> None:
    assert TIMELINE_SOURCES == ("particle", "graph_edge", "event", "decision")
    rows = timeline_view(
        particles=[{"particle_id": "p1", "created_at": "2026-10-01"}],
        edges=[{"from_id": "p1", "to_id": "p2", "predicate": "DECIDED_ON", "ts": "2026-10-02"}],
        events=[{"id": "e1", "event_type": "note", "ts": "2026-10-03"}],
        decisions=[{"decision_id": "d1", "decided_at": "2026-10-04"}],
    )
    assert [r["source"] for r in rows] == ["particle", "graph_edge", "event", "decision"]


def test_timeline_missing_source_is_not_fabricated() -> None:
    """源缺失即无行 —— 不用别的源脑补。"""
    rows = timeline_view(decisions=[{"decision_id": "d1", "decided_at": "2026-10-04"}])
    assert all(r["source"] == "decision" for r in rows)
    assert len(rows) == 1


# ── 视图 3：决策回链审计 ────────────────────────────────────────────────────
def test_decision_backlinks() -> None:
    s = _store()
    b = decision_backlinks(s, "d1")
    assert b["overrides"] == ("d2",)              # d1 覆盖 d2
    assert b["referenced_by"] == ()               # 无人把 d1 当前例
    b0 = decision_backlinks(s, "d0")
    assert b0["referenced_by"] == ("d1",)         # d1 把 d0 当前例


def test_probe_backlinks_uncontrolled_predicate() -> None:
    """探针：回链谓词未受控必须抛（否则审计链可被任意谓词伪造）。"""
    s = InMemoryGraphStore(("CAUSED",), _edges())
    with pytest.raises(ValueError, match="回链谓词未受控"):
        decision_backlinks(s, "d1")


# ── 协议禁写 ────────────────────────────────────────────────────────────────
def test_protocol_has_no_write_methods() -> None:
    """图存储只读：协议里不得出现任何写方法（出现即事实源分裂风险）。"""
    for banned in ("link", "add_edge", "upsert_edge", "write_edge", "delete_edge"):
        assert not hasattr(GraphStore, banned), f"协议出现写方法 {banned}"
        assert not hasattr(InMemoryGraphStore, banned)
        assert not hasattr(PgCteGraphStore, banned)


def test_probe_write_method_presence_discriminates() -> None:
    """探针：给实现偷偷加个 link()，上一条必须检出（防日后"就加一个写方法"）。"""
    class _Evil(InMemoryGraphStore):
        def link(self, *a, **k):  # pragma: no cover - 仅用于探针
            return None

    assert hasattr(_Evil, "link")           # 探针自身有效（能看见写方法）
    assert not hasattr(InMemoryGraphStore, "link")


# ── PG CTE 后端：SQL 形状 + 对拍 ────────────────────────────────────────────
class _FakeStore:
    """最小 PgVectorStore 替身：只记录 SQL，返回可控行（无 PG 也能跑）。"""

    def __init__(self, rows=None):
        self.schema = "public"
        self.sql: list = []
        self.rows = rows or []
        self.query_calls: list = []

    def execute_fetch(self, sql, params=None, *, fetch_all=False):
        self.sql.append((sql, params))
        return self.rows if fetch_all else (self.rows[0] if self.rows else None)

    def query(self, table, *, where="", params=None, limit=100):
        self.query_calls.append((table, where, params))
        return self.rows


def test_pg_cte_sql_has_recursion_guards() -> None:
    """CTE 必须同时具备：递归、深度上限、环检测 —— 缺一即可能无限展开。"""
    st = _FakeStore()
    g = PgCteGraphStore(st, PREDS)
    g.traverse("d1", max_hops=2)
    sql = st.sql[0][0]
    assert "WITH RECURSIVE" in sql
    assert "w.depth < %s" in sql                 # 深度上限
    assert "NOT (e.to_id = ANY(w.path))" in sql  # 环检测


def test_probe_cte_depth_guard_present() -> None:
    """探针：删掉深度上限后本条须转红（见变异自证）。"""
    st = _FakeStore()
    g = PgCteGraphStore(st, PREDS)
    g.traverse("d1", max_hops=2)
    assert "w.depth < %s" in st.sql[0][0]


def test_pg_store_reads_only() -> None:
    """PG 后端只发 SELECT（store 侧另有禁 DELETE/DROP 硬拦）。"""
    st = _FakeStore(rows=[{"from_id": "d1", "to_id": "d0", "predicate": "DECIDED_ON",
                           "depth": 1, "path": ["d1", "d0"]}])
    g = PgCteGraphStore(st, PREDS)
    res = g.traverse("d1", max_hops=1)
    assert res.nodes == ("d0", "d1")
    assert all(s.strip().upper().startswith(("WITH", "SELECT")) for s, _ in st.sql)


def test_two_backends_agree() -> None:
    """对拍：同输入，内存后端与 PG 后端结果须一致（防两套语义漂移）。"""
    rows = [{"from_id": "d1", "to_id": "d2", "predicate": "OVERRIDES",
             "layer": "M", "depth": 1, "path": ["d1", "d2"]}]
    mem = InMemoryGraphStore(PREDS, [GraphEdge("d1", "d2", "OVERRIDES")])
    pg = PgCteGraphStore(_FakeStore(rows=rows), PREDS)
    a = relation_view(mem, "d1", max_hops=1)
    b = relation_view(pg, "d1", max_hops=1)
    assert a["nodes"] == b["nodes"]
    assert [(e["from"], e["to"], e["predicate"]) for e in a["edges"]] == \
           [(e["from"], e["to"], e["predicate"]) for e in b["edges"]]


def test_decision_time_basis_constant() -> None:
    assert DECISION_TIME_BASIS == "COALESCE(decided_at, created_at)"


# ── 变异自证（2026-10-09 实测）──────────────────────────────────────────────
# ① 注释掉 `_resolve` 的未知谓词抛错 → test_uncontrolled_predicate_is_rejected
#    与 test_probe_uncontrolled_predicate_discriminates 转红（DID NOT RAISE）。
# ② 把 `_check_hops` 的上界判断删掉 → test_depth_gate_rejects_out_of_range 与
#    test_traverse_respects_hop_cap 转红（一跳竟达二跳节点）。
# ③ 把 CTE 里 `w.depth < %s` 去掉 → test_pg_cte_sql_has_recursion_guards 与
#    test_probe_cte_depth_guard_present 转红。
# 三者均已实测转红后还原，证明探针非恒绿。
