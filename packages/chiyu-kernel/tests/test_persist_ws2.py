"""WS2 测试 + 反假绿探针（不依赖真实 PG；FakeStore 记录调用，全绿可离线跑）。

⛔ 探针不是装饰：每条「测试绿」之外必须过变异自证，否则判假绿
   （项目铁律 · ai-capability-audit）。本文件两处 MUTATION 禁用闸后断言转红。
"""
from __future__ import annotations

import json
from typing import Any, Sequence

from chiyu_kernel.contract import (
    ParticleTypeSet, PredicateSet, PredicateSpec, RedlineSpec, TenantProfile,
)
from chiyu_kernel.persist import (
    DecisionRecord, PgVectorStorePersister, judge_worthiness,
    write_decision_memory_net,
)


class FakeStore:
    """不连 PG 的 store 桩：记录 event / particle / edge 写入，供断言与探针。"""

    def __init__(self, schema: str = "public") -> None:
        self.schema = schema
        self.events: dict[str, dict] = {}
        self.particles: dict[str, dict] = {}
        self.edges: list[tuple] = []
        self.executes: list[tuple[str, Any]] = []

    def execute(self, sql: str, params: Any = None) -> None:
        self.executes.append((sql, params))
        if f"{self.schema}.event" in sql or "event" in sql.split():
            eid = params[0]
            payload = json.loads(params[-1])  # 末参是 jsonb 字符串
            self.events[eid] = payload
        elif "graph_edge" in sql:
            p = list(params)
            self.edges.append((p[0], p[1], p[2], p[3], tuple(p[4]), p[5]))

    def execute_fetch(self, sql: str, params: Any = None) -> Any:
        if "payload->>'content_hash'" in sql:
            eid = params[0]
            if eid in self.events:
                return {"ch": self.events[eid].get("content_hash")}
            return None
        return None

    def upsert_particle(self, particle_id: str, ptype: str, layer: str = "L1",
                        *, label=None, status=None, vec=None, provider=None,
                        ai_generated=False, dim=1024) -> None:
        self.particles[particle_id] = dict(ptype=ptype, layer=layer, label=label,
                                           status=status, provider=provider,
                                           ai_generated=ai_generated, dim=dim)

    def count(self, table: str) -> int:
        return 0

    def query(self, table: str, *, where: str = "", params=None, limit: int = 100):
        return []

    def close(self) -> int:
        return 0

    def created_schemas(self):
        return set()


def _profile() -> TenantProfile:
    return TenantProfile(
        domain="test",
        particle_types=ParticleTypeSet(names=(
            "unstructured_asset", "entity", "decision", "memory", "knowledge", "lead")),
        predicates=PredicateSet(knowledge=(
            PredicateSpec("REFERENCES", "knowledge", "entity", layer="K"),)),
        redline=RedlineSpec(mutex_top=frozenset(), sensitive=frozenset()),
    )


def _refs() -> dict[str, Sequence[str]]:
    return {
        "subject": ["e1"], "precedents": ["p1", "p2"], "exceptions": ["x1"],
        "frames": ["f1"], "overrides": [], "causes": ["c1"], "influencers": ["i1"],
    }


def _count_event_inserts(store: FakeStore) -> int:
    return sum(1 for sql, _ in store.executes if "event" in sql and "INSERT INTO" in sql)


def test_persist_writes_event_particle_and_seven_edges() -> None:
    store = FakeStore()
    persister = PgVectorStorePersister(store, _profile(), materialize=False)
    rec = DecisionRecord(decision_id="d1", confidence=0.9, redline_hit=False, autonomous=True)

    eid = persister.persist(rec, references=_refs())

    assert eid == "d1"
    assert "d1" in store.events
    assert store.particles["d1"]["ptype"] == "decision"
    # N 统一降级协议：测试环境无真向量 ⇒ provider='hash' 且 degraded 显式留痕（禁伪健康）
    assert store.particles["d1"]["provider"] == "hash"
    assert store.events["d1"]["vector_degraded"] is True
    # F K-M-D：7 谓词边全写出（DECIDED_ON 1 + REFERENCED_PRECEDENT 2 + DERIVED_FROM_EXCEPTION 1
    #          + ESTABLISHES_FRAME 1 + OVERRIDES 0 + CAUSED 1 + INFLUENCED 1 = 7）
    assert len(store.edges) == 7
    assert all(e[5] == "engine" for e in store.edges)  # 显式 edge_source='engine'


def test_persist_accepts_spine_result_via_duck_typing() -> None:
    """内核不反向依赖 chiyu_decision：SpineResult 经 getattr 提取即可落库。"""
    store = FakeStore()
    persister = PgVectorStorePersister(store, _profile(), materialize=False)

    class _SpineResult:  # 模拟 chiyu_decision.SpineResult 的形态
        decision_id = "d2"
        confidence = 0.85
        redline_hit = False
        redline_reasons = ()
        autonomous = True
        rubric_missing = ("fairness",)
        elements_missing = ()

    eid = persister.persist(_SpineResult(), references=_refs())
    assert eid == "d2"
    assert store.events["d2"]["confidence"] == 0.85
    assert store.events["d2"]["rubric_missing"] == ["fairness"]


def test_judge_suppresses_net_on_redline_hit() -> None:
    """B 双轨四闸：红线命中的决策仍落 event（审计），但不建正向先例边。"""
    store = FakeStore()
    persister = PgVectorStorePersister(store, _profile(), materialize=False)
    rec = DecisionRecord(decision_id="d3", confidence=0.9, redline_hit=True,
                         redline_reasons=("互斥红线",))

    eid = persister.persist(rec, references=_refs())

    assert eid == "d3"
    assert "d3" in store.events                 # 决策 event 仍落（审计回链）
    assert store.events["d3"]["redline_hit"] is True
    assert len(store.edges) == 0               # 记忆网被闸拦（防红线污染）


def test_probe_idempotency_mutation_self_proof() -> None:
    """G content_hash 幂等判变：相同内容二次落库不新增 event 行。

    MUTATION：禁用幂等闸后，二次落库**会**新增 event 行 ⇒ 断言转红，证闸非假绿。
    """
    store = FakeStore()
    persister = PgVectorStorePersister(store, _profile(), materialize=False)
    rec = DecisionRecord(decision_id="d4", confidence=0.9, redline_hit=False)

    n0 = _count_event_inserts(store)
    persister.persist(rec, references=_refs())          # 1st
    n1 = _count_event_inserts(store)
    assert n1 - n0 == 1                                  # 首落 1 行

    persister.persist(rec, references=_refs())          # 2nd 同内容 ⇒ 幂等跳过
    n2 = _count_event_inserts(store)
    assert n2 == n1, "幂等失效：相同内容二次落库产生了新 event 行"

    # ── MUTATION：禁用幂等闸 ──
    persister._skip_idempotency = True
    persister.persist(rec, references=_refs())          # 闸失效 ⇒ 必新增
    n3 = _count_event_inserts(store)
    assert n3 == n2 + 1, "变异自证失败：禁用幂等闸后仍未新增 event 行"


def test_probe_judge_gate_mutation_self_proof() -> None:
    """judge 闸是「记忆网不写」的唯一起因（非其它副作用）。

    MUTATION：传入恒 True 的 judge ⇒ 红线决策也写边 ⇒ 断言转红，证闸非假绿。
    """
    store = FakeStore()
    persister = PgVectorStorePersister(store, _profile(), materialize=False)
    rec = DecisionRecord(decision_id="d5", confidence=0.9, redline_hit=True)

    # 默认 judge ⇒ 0 边
    persister.persist(rec, references=_refs())
    assert len(store.edges) == 0

    # ── MUTATION：闸失效（强制 worthy）──
    store2 = FakeStore()
    persister2 = PgVectorStorePersister(store2, _profile(), materialize=False)
    write_decision_memory_net("d5", references=_refs(), profile=_profile(),
                              write_edge=persister2._store_write_edge(),
                              record=rec, judge=lambda r: (True, "forced"))
    assert len(store2.edges) > 0, "变异自证失败：强制闸后仍未写边"


def test_payload_carries_content_hash() -> None:
    store = FakeStore()
    persister = PgVectorStorePersister(store, _profile(), materialize=False)
    rec = DecisionRecord(decision_id="d6", confidence=0.7, redline_hit=False)
    persister.persist(rec, references=_refs())
    ch = store.events["d6"]["content_hash"]
    assert isinstance(ch, str) and len(ch) == 64        # SHA-256 十六进制


def test_judge_worthiness_transient() -> None:
    from dataclasses import replace

    rec = DecisionRecord(decision_id="d7", confidence=0.9, redline_hit=False)
    assert judge_worthiness(rec) == (True, "worthy")
    assert judge_worthiness(rec, transient=True)[0] is False
    assert judge_worthiness(replace(rec, redline_hit=True))[0] is False
