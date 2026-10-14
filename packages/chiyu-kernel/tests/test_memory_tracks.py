"""B 双轨记忆运行时守卫（memory_tracks：LOG/NOTE 双轨 + 蒸馏两闸 + F 回流白名单）。

守四条：
  1. **四闸闭合**：写侧两闸（judge_worthiness：凭证硬拒/瞬态噪声）已在 test_approval_gate
     族覆盖；本文件守蒸馏侧两闸（显式优先/价值视界）+ 瞬态防御性兜底；
  2. **闸序即纪律**：显式优先**先**于价值视界（硬约束先于置信度）——显式旧条目必须
     晋升而非被视界淘汰；
  3. **幂等**：NOTE upsert 以 content_hash 判变，同内容重复蒸馏不产生伪变更；
  4. **F 回流白名单**：PRESCRIBABLE_PREDICATES 是 MEMORY_PREDICATES 的严格真子集
     （空=闸没干活，全集=形同虚设），审计凭证边不可被闭环改写。

对应文档：docs/plans/2026-10-09-foundation-maturity-blueprint.md（B 双轨四闸映射）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

import pytest

from chiyu_kernel.contract.particle import MEMORY_PREDICATES
from chiyu_kernel.persist import (
    DistillReport, InMemoryMemoryLog, InMemoryNoteStore, MemoryLogEntry,
    MemoryNote, PRESCRIBABLE_PREDICATES, distill, is_prescribable,
    judge_worthiness, note_hash,
)
from chiyu_kernel.persist.memory_tracks import parse_ts

NOW = datetime(2026, 10, 9, tzinfo=timezone.utc)
FRESH = "2026-10-08T00:00:00+00:00"     # 1 天前：视界内
STALE = "2026-08-15T00:00:00+00:00"     # 55 天前：超 30 天视界


def _entry(entry_id: str, *, created_at: str = FRESH, explicit: bool = False,
           transient: bool = False) -> MemoryLogEntry:
    return MemoryLogEntry(entry_id=entry_id, kind="note", payload={"k": "v"},
                          created_at=created_at, explicit=explicit,
                          transient=transient)


# ── 闸序 1：显式优先 bypass 价值视界 ─────────────────────────────────────────
def test_explicit_stale_entry_promotes_not_dropped() -> None:
    log, notes = InMemoryMemoryLog(), InMemoryNoteStore()
    log.append(_entry("old-explicit", created_at=STALE, explicit=True))
    report = distill(log, notes, now=NOW, value_horizon_days=30)
    assert report.promoted == 1 and report.explicit_promoted == 1, report
    assert report.dropped_horizon == 0, f"显式旧条目被视界淘汰 ⇒ 显式优先闸失效：{report}"
    assert notes.get("old-explicit") is not None


# ── 闸序 2：非显式超界淘汰 ───────────────────────────────────────────────────
def test_stale_non_explicit_entry_dropped_by_horizon() -> None:
    log, notes = InMemoryMemoryLog(), InMemoryNoteStore()
    log.append(_entry("old-plain", created_at=STALE))
    report = distill(log, notes, now=NOW, value_horizon_days=30)
    assert report.dropped_horizon == 1, report
    assert report.promoted == 0
    assert notes.get("old-plain") is None, "被视界淘汰的条目不得落 NOTE 轨"


def test_fresh_entry_promotes() -> None:
    log, notes = InMemoryMemoryLog(), InMemoryNoteStore()
    log.append(_entry("fresh"))
    report = distill(log, notes, now=NOW, value_horizon_days=30)
    assert report.promoted == 1 and report.dropped_horizon == 0, report
    assert notes.get("fresh") is not None


# ── 瞬态防御性兜底（写侧漏放也不蒸馏）───────────────────────────────────────
def test_transient_entry_defensively_skipped() -> None:
    log, notes = InMemoryMemoryLog(), InMemoryNoteStore()
    log.append(_entry("noisy", transient=True))
    report = distill(log, notes, now=NOW)
    assert report.promoted == 0 and notes.get("noisy") is None, report
    assert "skip_transient:noisy" in report.details


# ── 幂等：content_hash 判变 ─────────────────────────────────────────────────
def test_note_upsert_is_content_hash_idempotent() -> None:
    notes = InMemoryNoteStore()
    h = note_hash("k1", "同内容")
    first = notes.upsert(MemoryNote(key="k1", content="同内容", content_hash=h))
    assert first is True, "首次 upsert 必须写入"
    second = notes.upsert(MemoryNote(key="k1", content="同内容", content_hash=h))
    assert second is False, "同 content_hash 重复 upsert = 伪变更，必须跳过"
    changed = notes.upsert(MemoryNote(key="k1", content="改了",
                                      content_hash=note_hash("k1", "改了")))
    assert changed is True, "内容变化必须写入"


def test_distill_rerun_is_idempotent() -> None:
    log, notes = InMemoryMemoryLog(), InMemoryNoteStore()
    log.append(_entry("fresh"))
    r1 = distill(log, notes, now=NOW)
    r2 = distill(log, notes, now=NOW)
    assert r1.promoted == 1
    assert r2.skipped_idempotent == 1, f"重复蒸馏必须幂等跳过：{r2}"


# ── append-only 形状守卫 ─────────────────────────────────────────────────────
def test_memory_log_is_append_only_by_shape() -> None:
    log = InMemoryMemoryLog()
    log.append(_entry("e1"))
    assert len(log) == 1
    entries: Tuple[MemoryLogEntry, ...] = tuple(log.iter_all())
    assert entries[0].entry_id == "e1"
    # 协议形状：LOG 轨不得提供修改/删除通道（禁硬删除同源纪律）
    for banned in ("delete", "remove", "update", "clear", "pop", "discard"):
        assert not hasattr(log, banned), f"LOG 轨出现了 {banned} ⇒ append-only 被破坏"


# ── 蒸馏判定式自检 ───────────────────────────────────────────────────────────
def test_distill_counts_are_machine_checkable() -> None:
    log, notes = InMemoryMemoryLog(), InMemoryNoteStore()
    log.append(_entry("fresh"))
    log.append(_entry("old-explicit", created_at=STALE, explicit=True))
    log.append(_entry("old-plain", created_at=STALE))
    log.append(_entry("noisy", transient=True))
    report = distill(log, notes, now=NOW, value_horizon_days=30)
    total = 4
    assert report.promoted + report.dropped_horizon + 1 == total, \
        f"计数守恒破坏（+1 为瞬态兜底跳过）：{report}"


# ── F 回流白名单：严格真子集 + 成员判定 ─────────────────────────────────────
def test_prescribable_is_strict_nonempty_subset() -> None:
    all_names = {m.predicate for m in MEMORY_PREDICATES}
    assert PRESCRIBABLE_PREDICATES, "白名单为空 ⇒ 闸没干活"
    assert PRESCRIBABLE_PREDICATES < all_names, \
        "白名单 == 全集 ⇒ 审计凭证边可被闭环改写，形同虚设"
    # 审计凭证边必须被排除（写入即定，改写即篡改审计）
    for audit_edge in ("DECIDED_ON", "REFERENCED_PRECEDENT",
                       "DERIVED_FROM_EXCEPTION", "ESTABLISHES_FRAME"):
        assert not is_prescribable(audit_edge), f"{audit_edge} 是审计凭证边，不得可改写"
    # 因果/影响推断边可被后见校准
    for calibratable in ("OVERRIDES", "CAUSED", "INFLUENCED"):
        assert is_prescribable(calibratable), f"{calibratable} 应在回流白名单内"


# ── 四闸闭合：写侧两闸仍在位（跨模块对拍）────────────────────────────────────
def test_four_gates_closed_across_write_and_distill() -> None:
    from chiyu_kernel.persist import DecisionRecord
    rec = DecisionRecord(decision_id="d", confidence=0.9,
                         rubric_missing=(), elements_missing=(),
                         redline_hit=True, redline_reasons=("r",),
                         autonomous=True)
    worthy, reason = judge_worthiness(rec)
    assert not worthy and "凭证硬拒" in reason, "写侧凭证硬拒闸失踪 ⇒ 四闸不闭合"
    rec_ok = DecisionRecord(decision_id="d2", confidence=0.9,
                            rubric_missing=(), elements_missing=(),
                            redline_hit=False, redline_reasons=(),
                            autonomous=True)
    worthy2, _ = judge_worthiness(rec_ok, transient=False)
    assert worthy2
    assert {m.predicate for m in MEMORY_PREDICATES} >= PRESCRIBABLE_PREDICATES
