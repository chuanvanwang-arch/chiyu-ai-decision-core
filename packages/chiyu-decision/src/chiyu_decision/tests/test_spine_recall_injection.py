"""T41 守卫：run_spine 记忆召回注入（decision 侧）。

判据：
  ① 默认 None ⇒ **零行为变更**：不注入召回键，脊柱结果与此前完全一致
  ② 注入 recaller ⇒ S1 之后、S4 之前 context 已含 precedents（召回真的进了决策回路）
  ③ 「写了能读」闭环：NOTE 轨里的内容经 recaller 出现在 context["precedents"]
  ④ 注入发生在 S1 非空校验之前（空 context 经召回器补料后仍须通过校验）

变异自证（删判据分支必转红）：
  · 去掉 spine.py 中 `memory_recaller` 的调用分支 ⇒ ②③ 红（context 无 precedents）
  · 把调用挪到 `if not context` 之后 ⇒ ④ 红（空 context 先抛）
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

from chiyu_kernel.approval import RedlinePriorityGate
from chiyu_kernel.contract.decision import EIGHT_ELEMENTS, RUBRIC_KEYS
from chiyu_kernel.context import build_memory_recaller
from chiyu_kernel.domain import profile_from_dict
from chiyu_kernel.persist import InMemoryNoteStore, MemoryNote, note_hash
from chiyu_decision.redline import RedlineVerdict
from chiyu_decision.spine import run_spine

_PROFILE_DICT: Dict[str, Any] = {
    "domain": "spine-recall-demo",
    "particle_types": {"names": ["unstructured_asset", "entity", "decision",
                                 "memory", "knowledge", "document"]},
    "predicates": {"knowledge": [
        {"predicate": "DESCRIBES", "from_type": "knowledge",
         "to_type": "document", "layer": "K", "source": "rule"},
    ]},
    "autonomous_threshold": 0.79,
}

PROFILE = profile_from_dict(_PROFILE_DICT)


def _recall_probe(sink: Dict[str, Any]) -> Any:
    """redline_callback 探针：捕获 S4 时刻的 context（召回已注入之后）。"""
    def _cb(*, context: Any, redline_items: Any) -> RedlineVerdict:
        sink.update(context)
        return RedlineVerdict(hit=False, reasons=())
    return _cb


def _run(context: Dict[str, Any], **kw: Any) -> Any:
    return run_spine(
        context=context, profile=PROFILE,
        rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
        elements={e: "x" for e in EIGHT_ELEMENTS},
        redline_items=(), approval_gate=RedlinePriorityGate(), **kw)


def _note(key: str, content: str) -> MemoryNote:
    return MemoryNote(key=key, content=content,
                      content_hash=note_hash(key, content))


# ── ① 默认 None ⇒ 零行为变更 ────────────────────────────────────────────
def test_default_none_preserves_prior_behavior() -> None:
    sink: Dict[str, Any] = {}
    res = _run({"text": "alpha", "decision_id": "d-1", "subject_id": "s-1"},
               redline_callback=_recall_probe(sink))
    assert res.stage_reached == "S5_persist"
    assert "precedents" not in sink, "未注入召回器时 context 不得凭空多出召回键"
    assert "memory_recall" not in sink


# ── ② 注入 ⇒ context 含召回键 ───────────────────────────────────────────
def test_memory_recaller_injects_into_decision_context() -> None:
    notes = InMemoryNoteStore()
    notes.upsert(_note("n-1", "alpha token"))
    sink: Dict[str, Any] = {}
    _run({"text": "alpha", "decision_id": "d-2", "subject_id": "s-1"},
         memory_recaller=build_memory_recaller(notes=notes),
         redline_callback=_recall_probe(sink))
    assert "precedents" in sink, "召回器已注入但 context 未携带召回结果"
    assert "memory_recall" in sink


# ── ③ 写了能读：NOTE 内容真的进决策回路 ──────────────────────────────────
def test_memory_recall_closes_write_to_read_loop() -> None:
    notes = InMemoryNoteStore()
    notes.upsert(_note("n-alpha", "alpha token"))
    notes.upsert(_note("n-other", "zeta token"))
    sink: Dict[str, Any] = {}
    _run({"text": "alpha", "decision_id": "d-3", "subject_id": "s-1"},
         memory_recaller=build_memory_recaller(notes=notes),
         redline_callback=_recall_probe(sink))
    assert "n-alpha" in sink.get("precedents", []), (
        f"写了的 NOTE 应被读到：{sink.get('precedents')}")
    assert "n-other" not in sink.get("precedents", [])


# ── ④ 注入排在 S1 非空校验之前 ──────────────────────────────────────────
def test_recaller_runs_before_s1_nonempty_check() -> None:
    """空 context 经召回器补料后仍须通过 S1 校验（顺序：factory→recaller→校验）。"""
    notes = InMemoryNoteStore()
    notes.upsert(_note("n-1", "alpha token"))

    def _filler(context: Any) -> Any:
        return {"text": "alpha", "decision_id": "d-4", "subject_id": "s-1"}

    res = _run({}, context_factory=_filler,
               memory_recaller=build_memory_recaller(notes=notes))
    assert res.stage_reached == "S5_persist"


# ── ⑤ 空 context 且无召回器 ⇒ 仍然抛（既有行为不变）──────────────────────
def test_empty_context_still_rejected_without_recaller() -> None:
    from chiyu_decision.errors import DecisionError

    with pytest.raises(DecisionError, match="S1_context 为空"):
        _run({})
