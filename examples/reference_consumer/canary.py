"""常驻 canary —— 一条命令证明「底座这条链路今天还通着」。

用法：
    python -m examples.reference_consumer.canary     # 或
    python examples/reference_consumer/canary.py

⛔ 它跑的是**探针**不是冒烟：判据是「字段相符 / 哈希自洽 / 边集相等 / 视图无幻影」，
   不是「跑完没报错」。机制失效 ⇒ 退出码 1。

建议：消费方把它挂到 CI 或夜间轨 —— 底座升级后先跑它，红了就别升。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple

from chiyu_kernel.contract.decision import RUBRIC_KEYS

# 自举：既支持 `python -m reference_consumer.canary`，也支持直接跑本文件
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reference_consumer.app import build_app, record_outcome, run_decision
from reference_consumer.domain import SCENARIO
from reference_consumer.probes import (
    ProbeResult, probe_closed_loop, probe_decision_really_persisted,
    probe_graph_is_derived, probe_memory_really_materialized,
    probe_redline_blocks_persist,
)

# ⛔ 八要素属 L0 契约面（sanctioned），不必碰 `chiyu_decision.scoring` 内部路径；
#    此前走 try/except 兜底 ⇒ 静默吞掉导入失败，八要素可能为空集而探针仍"绿"。
from chiyu_kernel.api import EIGHT_ELEMENTS


# ── 基准输入（消费方侧取值；满分 ⇒ 走「自主放行」分支）──────────────────────
DECISION_ID = "dec-1"
REDLINE_DECISION_ID = "dec-redline"

FULL_SCORES: Dict[str, float] = {k: 4.0 for k in RUBRIC_KEYS}
FULL_ELEMENTS: Dict[str, object] = {e: "ok" for e in EIGHT_ELEMENTS}

# 记忆供给：键即七条记忆谓词的落点
REFERENCES: Dict[str, Sequence[str]] = {
    "subject": ["doc-1"],
    "precedents": ["dec-0"],
    "exceptions": ["kb-2"],
    "frames": ["kb-3"],
    "overrides": [],
    "causes": ["task-1"],
    "influencers": ["dec-9"],
}

# ⛔ 预期由调用方**声明**（探针只比对，不重算内核逻辑 ⇒ 无两套语义漂移风险）
EXPECTED_NET_TRIPLES: Set[Tuple[str, str, str]] = {
    (DECISION_ID, "doc-1", "DECIDED_ON"),
    (DECISION_ID, "dec-0", "REFERENCED_PRECEDENT"),
    (DECISION_ID, "kb-2", "DERIVED_FROM_EXCEPTION"),
    (DECISION_ID, "kb-3", "ESTABLISHES_FRAME"),
    (DECISION_ID, "task-1", "CAUSED"),
    (DECISION_ID, "dec-9", "INFLUENCED"),
}

CONCEPT_REFS: Tuple[str, ...] = ("kb-1",)
REDLINE_ITEMS: Tuple[str, ...] = ("受限事项",)


def run_canary() -> Dict[str, Any]:
    """跑完整链路 + 五条探针，返回结果 dict（`ok` 为总判定）。"""
    app = build_app()

    res = run_decision(
        app, decision_id=DECISION_ID, text="常规评审场景",
        rubric_scores=FULL_SCORES, elements=FULL_ELEMENTS,
        references=REFERENCES, concept_refs=CONCEPT_REFS,
        subject_id="doc-1", policy_version="v1")
    # 回填结果（闭环「结果→D」边的证据）
    record_outcome(app, DECISION_ID, {"status": "applied"}, subject_id="doc-1")

    probe_results: List[ProbeResult] = [
        probe_decision_really_persisted(
            app, DECISION_ID,
            expected={"confidence": res.confidence, "redline_hit": False,
                      "autonomous": True, "policy_version": "v1"}),
        probe_memory_really_materialized(
            app, DECISION_ID, expected_triples=EXPECTED_NET_TRIPLES),
        probe_graph_is_derived(app, DECISION_ID),
        probe_closed_loop(app, DECISION_ID, references=REFERENCES,
                          concept_refs=CONCEPT_REFS),
        probe_redline_blocks_persist(
            app, decision_id=REDLINE_DECISION_ID,
            rubric_scores=FULL_SCORES, elements=FULL_ELEMENTS,
            redline_items=REDLINE_ITEMS),
    ]

    ok = all(p.ok for p in probe_results)
    not_wired = [k for k, v in probe_results[3].evidence.items()
                 if isinstance(v, Mapping) and not v.get("connected")]
    return {
        "ok": ok,
        "probes": [p.as_dict() for p in probe_results],
        "not_wired": sorted(not_wired),
        "counts": {
            "events": len(app.store.events),
            "particles": len(app.store.particles),
            "edges": len(app.store.edges),
            "audit": len(app.audit),
            "scenario": SCENARIO["id"],
        },
    }


def main() -> int:
    verdict = run_canary()
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
