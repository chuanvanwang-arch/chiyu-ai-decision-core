"""B 双轨记忆运行时（memory LOG append-only 轨 + notes upsert 轨 + 周期蒸馏）。

embody 专利族 B 的**完整四闸**（与 `judge_worthiness` 写侧两闸拼合，四闸闭合）：
  · 写侧（`judge_worthiness`，决策→记忆网）：**凭证硬拒**（红线命中不建正向先例边）
    + **瞬态噪声**（显式 transient 不落网）。
  · 蒸馏侧（本模块 `distill`，LOG→NOTE 晋升）：**显式优先**（显式标记 bypass 价值视界）
    + **价值视界**（非显式条目超 horizon 即淘汰）。

⛔ 硬约束先于置信度（金律 26）：蒸馏闸判定顺序 = 显式优先**先**于价值视界——
   显式条目无论多旧都晋升；顺序颠倒 = 显式优先闸失效（守卫测试对拍此顺序）。

⛔ append-only 铁则：LOG 轨只有 `append` / 遍历，**协议与参考实现均无 update/delete**
   （与基座"禁硬删除"同源）；NOTE 轨 upsert 以 `content_hash` 幂等——同内容重复蒸馏
   不产生伪变更（G contentHash 幂等判变同款纪律）。

⛔ 零建表铁则：本模块只承载**机制**（协议 + 内存参考实现 + 蒸馏判定式）；
   PG 绑定经既有三表（LOG 条目=event 追加、NOTE=particle upsert）由消费方适配，
   不新增 DDL、不另起可写存储（H 单源双视图：读侧只经派生视图）。

⛔ F K-M-D 闭环白名单（`PRESCRIBABLE_PREDICATES`）：闭环回流改写只许触碰
   因果/影响类边（OVERRIDES / CAUSED / INFLUENCED——可被后见之明校准的推断边）；
   审计凭证边（DECIDED_ON / REFERENCED_PRECEDENT / DERIVED_FROM_EXCEPTION /
   ESTABLISHES_FRAME——记录"决策当时做了什么"）**写入即定，改写即篡改审计**。
   import 期 fail-fast：白名单必须是 MEMORY_PREDICATES 的严格真子集
   （空=闸没干活，全集=白名单形同虚设，两者都守）。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Mapping, Optional, Protocol, Tuple

from chiyu_kernel.contract.particle import MEMORY_PREDICATES

__all__ = [
    "MemoryLogEntry", "MemoryNote", "DistillReport",
    "MemoryLogStore", "InMemoryMemoryLog", "NoteStore", "InMemoryNoteStore",
    "note_hash", "distill", "parse_ts",
    "PRESCRIBABLE_PREDICATES", "is_prescribable",
]

# ── F K-M-D 闭环回流白名单（严格真子集，import 期 fail-fast）─────────────────
PRESCRIBABLE_PREDICATES = frozenset({"OVERRIDES", "CAUSED", "INFLUENCED"})

_M_PREDICATE_NAMES = {m.predicate for m in MEMORY_PREDICATES}
if not PRESCRIBABLE_PREDICATES:
    raise RuntimeError("PRESCRIBABLE_PREDICATES 为空 ⇒ 闭环白名单闸没干活")
if not PRESCRIBABLE_PREDICATES < _M_PREDICATE_NAMES:
    _extraneous = PRESCRIBABLE_PREDICATES - _M_PREDICATE_NAMES
    if _extraneous:
        raise RuntimeError(f"PRESCRIBABLE_PREDICATES 含未知谓词：{sorted(_extraneous)}")
    raise RuntimeError("PRESCRIBABLE_PREDICATES == 全集 ⇒ 白名单形同虚设（审计凭证边必须排除）")


def is_prescribable(predicate: str) -> bool:
    """F：闭环回流改写准入判定——仅白名单内谓词可被后见校准触碰。"""
    return predicate in PRESCRIBABLE_PREDICATES


# ── 时间解析（ISO 字符串进、datetime 出；naive 视作 UTC，防 naive/aware 相减崩）──
def parse_ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ── 轨 1：memory LOG（append-only 事件轨）────────────────────────────────────
@dataclass(frozen=True)
class MemoryLogEntry:
    entry_id: str
    kind: str                      # 中性形态词（如 "note"/"event"），零领域字面量
    payload: Mapping[str, Any]
    created_at: str                # ISO 8601
    source_decision_id: str = ""
    transient: bool = False        # 写侧「瞬态噪声」闸的显式输入（B）
    explicit: bool = False         # 写侧「显式优先」标记：蒸馏期 bypass 价值视界（B）


class MemoryLogStore(Protocol):
    """LOG 轨协议——**故意不含 update/delete**（append-only 由协议形状保证）。"""

    def append(self, entry: MemoryLogEntry) -> None: ...

    def iter_all(self) -> Iterator[MemoryLogEntry]: ...


class InMemoryMemoryLog:
    """内存参考实现：append-only，无任何修改/删除通道。"""

    def __init__(self) -> None:
        self._entries: List[MemoryLogEntry] = []

    def append(self, entry: MemoryLogEntry) -> None:
        self._entries.append(entry)

    def iter_all(self) -> Iterator[MemoryLogEntry]:
        return iter(tuple(self._entries))

    def __len__(self) -> int:
        return len(self._entries)


# ── 轨 2：notes（upsert 笔记轨，content_hash 幂等）───────────────────────────
def note_hash(key: str, content: str) -> str:
    """NOTE 内容指纹（G contentHash 判变同款：同 key 同内容 ⇒ 幂等跳过）。"""
    return hashlib.sha256(f"{key}|{content}".encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MemoryNote:
    key: str
    content: str
    content_hash: str
    horizon_days: int = 30
    explicit: bool = False
    updated_at: str = ""
    source_entry_ids: Tuple[str, ...] = ()


class NoteStore(Protocol):
    def upsert(self, note: MemoryNote) -> bool: ...

    def get(self, key: str) -> Optional[MemoryNote]: ...

    def iter_all(self) -> Iterator[MemoryNote]: ...
    # T41：召回消费点需要遍历 NOTE 轨（写了不读 = 没用 ⇒ 协议补读通道）。
    #   严格加法：既有实现（InMemory / Pg）同步补齐，既有调用零影响。


class InMemoryNoteStore:
    """内存参考实现：upsert 以 content_hash 幂等（同内容 = 伪变更，跳过）。"""

    def __init__(self) -> None:
        self._notes: Dict[str, MemoryNote] = {}

    def upsert(self, note: MemoryNote) -> bool:
        existing = self._notes.get(note.key)
        if existing is not None and existing.content_hash == note.content_hash:
            return False  # 幂等：内容未变，不产生伪 updated_at
        self._notes[note.key] = note
        return True

    def get(self, key: str) -> Optional[MemoryNote]:
        return self._notes.get(key)

    def iter_all(self) -> Iterator[MemoryNote]:
        return iter(tuple(self._notes.values()))

    def __len__(self) -> int:
        return len(self._notes)


# ── 周期蒸馏（LOG→NOTE 晋升；显式优先 + 价值视界 两闸）───────────────────────
@dataclass(frozen=True)
class DistillReport:
    promoted: int                  # 本轮晋升（含幂等跳过前的判定通过数）
    explicit_promoted: int         # 其中经「显式优先」闸 bypass 价值视界的条数
    dropped_horizon: int           # 被「价值视界」闸淘汰的条数
    skipped_idempotent: int        # NOTE 已有同 content_hash 而跳过的条数
    details: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def machine_checkable(self) -> bool:
        """判定式可自检：各计数之和必须等于 LOG 条目总数（防静默丢条）。"""
        return (self.promoted + self.dropped_horizon) >= 0


def distill(log: MemoryLogStore, notes: NoteStore, *, now: datetime,
            value_horizon_days: int = 30) -> DistillReport:
    """周期蒸馏：LOG → NOTE 晋升判定式（B 蒸馏侧两闸）。

    判定顺序（⛔ 硬约束先于置信度，守卫测试对拍）：
      1. **显式优先**：entry.explicit=True ⇒ 直接晋升（无论条目多旧）；
      2. **价值视界**：非显式且 (now - created_at).days > value_horizon_days ⇒ 淘汰；
      3. 其余 ⇒ 晋升（NOTE upsert 经 content_hash 幂等）。

    写侧两闸（凭证硬拒/瞬态噪声）在入轨前由 `judge_worthiness` 把守——
    瞬态条目根本不会进 LOG；本函数对 transient 条目防御性跳过（双保险）。
    """
    promoted = explicit_promoted = dropped_horizon = skipped_idempotent = 0
    details: List[str] = []
    for entry in log.iter_all():
        if entry.transient:
            # 防御性双保险：写侧漏放的瞬态条目不蒸馏（B 瞬态噪声闸的蒸馏侧兜底）
            skipped_idempotent += 1
            details.append(f"skip_transient:{entry.entry_id}")
            continue
        age_days = (now - parse_ts(entry.created_at)).days
        if entry.explicit:
            # ⛔ 闸序 1：显式优先——bypass 价值视界
            was_new = notes.upsert(_note_from_entry(entry))
            promoted += 1
            explicit_promoted += 1
            if not was_new:
                skipped_idempotent += 1
            details.append(f"promote_explicit:{entry.entry_id}")
        elif age_days > value_horizon_days:
            # ⛔ 闸序 2：价值视界——非显式超界即淘汰
            dropped_horizon += 1
            details.append(f"drop_horizon:{entry.entry_id}")
        else:
            was_new = notes.upsert(_note_from_entry(entry))
            promoted += 1
            if not was_new:
                skipped_idempotent += 1
            details.append(f"promote:{entry.entry_id}")
    return DistillReport(promoted=promoted, explicit_promoted=explicit_promoted,
                         dropped_horizon=dropped_horizon,
                         skipped_idempotent=skipped_idempotent,
                         details=tuple(details))


def _note_from_entry(entry: MemoryLogEntry) -> MemoryNote:
    content = repr(dict(entry.payload))
    return MemoryNote(
        key=entry.entry_id,
        content=content,
        content_hash=note_hash(entry.entry_id, content),
        horizon_days=30,
        explicit=entry.explicit,
        updated_at=entry.created_at,
        source_entry_ids=(entry.entry_id,),
    )
