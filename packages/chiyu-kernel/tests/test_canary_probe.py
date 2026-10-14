"""canary 探针件（N7）三判据 —— 打桩 store + 真实 persister + 真实脊柱集成。

⛔ 判别力（反假绿）设计：每个判据都配一个**负场景**——
   ① persister 假接线（回调谎报 persisted=True 但 store 无行）⇒ 判据 1 必 False；
   ② store 少写一条 engine 边 ⇒ 判据 2（恰好相等）必 False；
   ③ 红线决策被放行落库 ⇒ 判据 3 必 False。
   只测"三判据全绿"而不测负场景 = 探针可能是恒绿（本仓踩过同族假绿）。
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# 兄弟包 src 上 sys.path（单跑本文件时 root conftest 可能不在收集链上，幂等自举）
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
for _pkg in ("chiyu-decision", "chiyu-kernel"):
    _src = os.path.join(_ROOT, "packages", _pkg, "src")
    if os.path.isdir(_src) and _src not in sys.path:
        sys.path.insert(0, _src)

from chiyu_kernel.api import canary_probe
from chiyu_kernel.canary import CanaryReport
from chiyu_kernel.contract.decision import EIGHT_ELEMENTS, RUBRIC_KEYS
from chiyu_kernel.domain import profile_from_dict
from chiyu_kernel.persist import PgVectorStorePersister
from chiyu_kernel.approval import RedlinePriorityGate
from chiyu_decision.api import run_spine

SCHEMA = "t_canary"


class FakeStore:
    """内存版 store（鸭子类型对齐 PgVectorStore 消费面：schema/execute/execute_fetch/upsert_particle）。"""

    def __init__(self) -> None:
        self.schema = SCHEMA
        self.events: Dict[str, tuple] = {}
        self.particles: Dict[str, dict] = {}
        self.edges: List[tuple] = []

    def execute(self, sql: str, params: Any = None) -> None:
        if re.search(r"INSERT INTO\s+\S*\.event\b", sql, re.I):
            self.events[params[0]] = params
        elif re.search(r"INSERT INTO\s+\S*\.graph_edge\b", sql, re.I):
            self.edges.append(params)          # (from,to,pred,layer,dims,source,...)
        else:
            raise AssertionError(f"FakeStore 未实现的写路径: {sql[:60]!r}")

    def execute_fetch(self, sql: str, params: Any = None,
                      *, fetch_all: bool = False) -> Any:
        if "content_hash" in sql:                       # persister 幂等判变
            ev = self.events.get(params[0]) if params else None
            if ev is None:
                return None
            return {"ch": json.loads(ev[5]).get("content_hash")}
        if re.search(r"FROM\s+\S*\.event\b", sql, re.I):
            return {"id": params[0]} if params and params[0] in self.events else None
        if re.search(r"FROM\s+\S*\.particle\b", sql, re.I):
            pid = params[0] if params else None
            return {"particle_id": pid} if pid in self.particles else None
        if re.search(r"FROM\s+\S*\.graph_edge\b", sql, re.I):
            n = sum(1 for e in self.edges if e[0] == params[0] and e[5] == "engine")
            return {"n": n}
        raise AssertionError(f"FakeStore 未实现的读路径: {sql[:60]!r}")

    def upsert_particle(self, particle_id: str, ptype: str, layer: str = "L1",
                        **kw: Any) -> None:
        self.particles[particle_id] = {"type": ptype, "layer": layer, **kw}


def _profile():
    # 与 examples/reference_consumer 同构的中性域（内核测试不得携带真实业务词）
    return profile_from_dict({
        "domain": "canary-demo",
        "particle_types": {"names": ["unstructured_asset", "entity", "decision",
                                     "memory", "knowledge", "document"]},
        "predicates": {"knowledge": [
            {"predicate": "DESCRIBES", "from_type": "knowledge",
             "to_type": "document", "layer": "K", "source": "rule"},
        ]},
        "autonomous_threshold": 0.79,
    })


REFERENCES: Dict[str, Tuple[str, ...]] = {
    "subject": ("doc-1",), "precedents": ("dec-0",), "exceptions": ("kb-2",),
    "frames": ("kb-3",), "causes": ("task-1",), "influencers": ("dec-9",),
    "overrides": (),
}


def _runner(store: FakeStore, profile, decision_id: str, *, redline: bool = False):
    persister = PgVectorStorePersister(store, profile, materialize=False)

    def run() -> Any:
        return run_spine(
            context={"text": "卫生健康" if redline else "普通事项",
                     "decision_id": decision_id},
            profile=profile,
            rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
            elements={e: "x" for e in EIGHT_ELEMENTS},
            redline_items=("卫生健康",) if redline else (),
            approval_gate=RedlinePriorityGate(),
            # references 仅正常决策注入（红线决策本就不落库，无记忆网可写）
            persister=lambda r: persister.persist(
                r, subject_id="subj-1",
                references=None if redline else REFERENCES) or True,
        )
    return run


def test_canary_three_criteria_green_end_to_end() -> None:
    """全绿场景：真接线（FakeStore + persister + 脊柱）⇒ 三判据全 True。"""
    store = FakeStore()
    profile = _profile()
    report = canary_probe(
        store=store, run_decision=_runner(store, profile, "can-ok"),
        decision_id="can-ok", references=REFERENCES,
        run_redline_decision=_runner(store, profile, "can-red", redline=True))
    assert isinstance(report, CanaryReport)
    assert report.decision_persisted, report.details
    assert report.memory_net_materialized, report.details
    assert report.redline_blocked, report.details
    assert report.ok is True


def test_criterion1_catches_persister_lying() -> None:
    """负场景①：回调谎报 persisted 但 store 无行 ⇒ 判据 1 必 False（禁恒绿）。"""
    store = FakeStore()
    profile = _profile()

    def lying() -> Any:
        class R:
            persisted = True                      # 谎报：store 里什么都没有
            approval_rejected = None
            pending = False
        return R()

    report = canary_probe(store=store, run_decision=lying,
                          decision_id="can-lie", references=REFERENCES,
                          run_redline_decision=_runner(
                              store, profile, "can-lie-red", redline=True))
    assert report.decision_persisted is False
    assert report.ok is False


def test_criterion2_catches_missing_edge() -> None:
    """负场景②：engine 边少一条（幻影/漏物化）⇒ 判据 2 必 False。"""
    store = FakeStore()
    profile = _profile()
    report = canary_probe(
        store=store, run_decision=_runner(store, profile, "can-edge"),
        decision_id="can-edge", references=REFERENCES,
        run_redline_decision=_runner(store, profile, "can-edge-red", redline=True))
    # 破坏：删掉一条 engine 边 ⇒ "恰好相等"判定必须转 False
    assert store.edges, "前置失效：本应已写 engine 边"
    store.edges.pop()
    report2 = canary_probe(
        store=store, run_decision=_runner(store, profile, "can-edge2"),
        decision_id="can-edge", references=REFERENCES,
        run_redline_decision=_runner(store, profile, "can-edge2-red", redline=True))
    assert report2.memory_net_materialized is False, report2.details


def test_criterion2_catches_phantom_edge() -> None:
    """负场景②′：engine 边**多**一条（幻影边）⇒ 判据 2 必 False。

    ⛔ 判别力补充：`==` 改成 `>=` 的变异曾逃逸（少写场景两种写法都红）。
       幻影边场景让 `==` 成为承重判据 —— 多写同样是记忆网污染。
    """
    store = FakeStore()
    profile = _profile()
    report = canary_probe(
        store=store, run_decision=_runner(store, profile, "can-phan"),
        decision_id="can-phan", references=REFERENCES,
        run_redline_decision=_runner(store, profile, "can-phan-red", redline=True))
    assert report.memory_net_materialized is True
    store.edges.append(
        ("can-phan", "kb-phantom", "CAUSED", "M", (), "engine",
         None, None, None, None, None))
    report2 = canary_probe(
        store=store, run_decision=_runner(store, profile, "can-phan2"),
        decision_id="can-phan", references=REFERENCES,
        run_redline_decision=_runner(store, profile, "can-phan2-red", redline=True))
    assert report2.memory_net_materialized is False, report2.details


def test_criterion3_catches_redline_leaking_to_persist() -> None:
    """负场景③：红线决策被放行落库 ⇒ 判据 3 必 False。"""
    store = FakeStore()
    profile = _profile()

    def leaking_redline() -> Any:
        class R:
            persisted = True                      # 红线却落库 = 严重违规
            approval_rejected = None
            pending = False
        return R()

    report = canary_probe(store=store, run_decision=_runner(
        store, profile, "can-leak"), decision_id="can-leak",
        references=REFERENCES, run_redline_decision=leaking_redline)
    assert report.redline_blocked is False


def test_undecidable_criteria_are_false_not_true() -> None:
    """缺红线回调 / 缺 references ⇒ 对应判据 False（不可判定 ≠ 通过）。"""
    store = FakeStore()
    profile = _profile()
    report = canary_probe(store=store, run_decision=_runner(
        store, profile, "can-part"), decision_id="can-part")
    assert report.memory_net_materialized is False
    assert report.redline_blocked is False
    assert "不可判定" in str(report.details.get("memory_net", "")) or \
        report.details.get("memory_net")
