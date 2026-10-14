"""B 双轨记忆的 PG 绑定（T40：memory 毕业 · PG 落库）。

`memory_tracks.py` 只给协议 + 内存参考实现（零建表铁则：PG 绑定"由消费方适配"），
本模块把这条"待适配"路径在内核内补完 —— 复用既有三表，**零新增 DDL**：

    · LOG 轨  → `event`（event_type='memory_log'，条目光载荷进 payload jsonb）
    · NOTE 轨 → `particle`（type 由 profile 注入，默认 'memory'，layer='L2'）
                + `particle_attribute`（content_hash / content / explicit /
                  horizon_days / source_entry_ids，source='engine'）

⛔ 零建表铁则（与 `memory_tracks.py`、`persist/__init__.py` 同款）：
   不新增表、不新增列、不另起可写存储；读侧经 H 单源双视图派生。

⛔ append-only 的 PG 形态（本模块最关键的不变量）：
   LOG 轨 INSERT 用 `ON CONFLICT (id) DO NOTHING` —— 同 id 二次 append
   **静默跳过**而非覆盖。协议 `MemoryLogStore` 故意不含 update/delete，
   PG 绑定不得开后门；写成 `DO UPDATE` 即破坏 append-only（守卫测试对拍此点）。

⛔ 幂等（G contentHash 判变同款）：NOTE upsert 先比对 content_hash，
   同 hash 不写（返回 False，禁伪 updated_at）。

⛔ 机制非清单：note 的粒子类型 / layer 由构造参数注入并**构造期校验**
   ∈ `profile.particle_types`（`memory` 属 CORE_ROLES，任何合法 profile 必含；
   传入未登记类型 ⇒ 构造期红，而非运行期撞 CHECK 约束）。
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterator, Mapping, Optional, Tuple

from chiyu_kernel.contract import TenantProfile
from chiyu_kernel.persist.memory_tracks import (
    MemoryLogEntry, MemoryNote, MemoryLogStore, NoteStore, parse_ts,
)

__all__ = [
    "EVENT_TYPE_MEMORY_LOG",
    "NOTE_ATTR_CONTENT_HASH", "NOTE_ATTR_CONTENT", "NOTE_ATTR_EXPLICIT",
    "NOTE_ATTR_HORIZON_DAYS", "NOTE_ATTR_SOURCE_ENTRY_IDS",
    "PgMemoryLogStore", "PgNoteStore",
]

# ── 常量（落库字面量集中于此，禁散落 SQL 拼接处）─────────────────────────
EVENT_TYPE_MEMORY_LOG = "memory_log"
NOTE_ATTR_CONTENT_HASH = "content_hash"
NOTE_ATTR_CONTENT = "content"
NOTE_ATTR_EXPLICIT = "explicit"
NOTE_ATTR_HORIZON_DAYS = "horizon_days"
NOTE_ATTR_SOURCE_ENTRY_IDS = "source_entry_ids"

#: `particle_attribute.source` 闭集（ATTR_SOURCES）取值；内核写入一律 'engine'
_NOTE_ATTR_SOURCE = "engine"

#: 默认 note 粒子类型（CORE_ROLES 之一，任何合法 profile 必含）
DEFAULT_NOTE_TYPE = "memory"
DEFAULT_NOTE_LAYER = "L2"


def _q(schema: str, table: str) -> str:
    """schema/表引用（与 `store/pg_store.py` 同款；schema 已过白名单校验）。"""
    return f"{schema}.{table}"


class PgMemoryLogStore:
    """LOG 轨 PG 绑定：`MemoryLogStore` 协议实现（append-only，无 update/delete）。

    ⛔ 与协议同形：本类**故意不提供** update / delete / clear 方法；
       幂等靠 `ON CONFLICT (id) DO NOTHING` 而非覆盖写。
    """

    def __init__(self, store: Any, profile: TenantProfile) -> None:
        self.store = store
        self.profile = profile

    # ── 写：append-only ──────────────────────────────────────────────────
    def append(self, entry: MemoryLogEntry) -> None:
        schema = self.store.schema
        payload = {
            "kind": entry.kind,
            "payload": dict(entry.payload),
            "transient": entry.transient,
            "explicit": entry.explicit,
        }
        self.store.execute(
            f"INSERT INTO {_q(schema, 'event')} "
            f"(id, ts, domain, event_type, stage, subject_id, decision_id, payload) "
            f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb) "
            f"ON CONFLICT (id) DO NOTHING",
            (entry.entry_id, parse_ts(entry.created_at), self.profile.domain,
             EVENT_TYPE_MEMORY_LOG, "memory_log_append",
             entry.source_decision_id or None,
             entry.source_decision_id or None,
             json.dumps(payload, ensure_ascii=False)))

    # ── 读：按写入顺序（seq）─────────────────────────────────────────────
    def iter_all(self) -> Iterator[MemoryLogEntry]:
        schema = self.store.schema
        rows = self.store.execute_fetch(
            f"SELECT id, ts, decision_id, payload "
            f"FROM {_q(schema, 'event')} "
            f"WHERE domain = %s AND event_type = %s ORDER BY seq",
            (self.profile.domain, EVENT_TYPE_MEMORY_LOG), fetch_all=True)
        for r in rows:
            body = r.get("payload") or {}
            if isinstance(body, str):            # 驱动未走 jsonb 解析时兜底
                body = json.loads(body)
            yield MemoryLogEntry(
                entry_id=r["id"],
                kind=body.get("kind", ""),
                payload=body.get("payload") or {},
                created_at=r["ts"].isoformat() if hasattr(r["ts"], "isoformat")
                else str(r["ts"]),
                source_decision_id=r.get("decision_id") or "",
                transient=bool(body.get("transient", False)),
                explicit=bool(body.get("explicit", False)),
            )

    def __len__(self) -> int:
        schema = self.store.schema
        row = self.store.execute_fetch(
            f"SELECT count(*)::int AS n FROM {_q(schema, 'event')} "
            f"WHERE domain = %s AND event_type = %s",
            (self.profile.domain, EVENT_TYPE_MEMORY_LOG), fetch_all=False)
        return int(row["n"]) if row else 0


class PgNoteStore:
    """NOTE 轨 PG 绑定：`NoteStore` 协议实现（content_hash 幂等 upsert）。

    落库形状（零建表）：
      · `particle`（particle_id=note.key，type / layer 由构造参数注入）
      · `particle_attribute`（五个属性槽位承载 note 全部字段）
    读回即 `MemoryNote`，与内存参考实现**同语义**（对拍测试保证）。
    """

    def __init__(self, store: Any, profile: TenantProfile, *,
                 note_type: str = DEFAULT_NOTE_TYPE,
                 layer: str = DEFAULT_NOTE_LAYER) -> None:
        # ⛔ 构造期校验：类型未登记 ⇒ 运行期必然撞 CHECK 约束（配了却没生效族）
        if not profile.particle_types.covers(note_type):
            raise ValueError(
                f"note 粒子类型 {note_type!r} 不在 profile.particle_types "
                f"（{sorted(profile.particle_types.names)}）⇒ 落库将被 CHECK 约束拒绝")
        self.store = store
        self.profile = profile
        self.note_type = note_type
        self.layer = layer

    # ── 写：幂等 upsert ──────────────────────────────────────────────────
    def upsert(self, note: MemoryNote) -> bool:
        """返回 True=产生变更；False=同 content_hash 幂等跳过（禁伪 updated_at）。"""
        if self._current_hash(note.key) == note.content_hash:
            return False
        self.store.upsert_particle(
            particle_id=note.key, ptype=self.note_type, layer=self.layer,
            label=note.key, status="active", ai_generated=False)
        self._write_attr(note.key, NOTE_ATTR_CONTENT_HASH, "text",
                         value_text=note.content_hash)
        self._write_attr(note.key, NOTE_ATTR_CONTENT, "text",
                         value_text=note.content)
        self._write_attr(note.key, NOTE_ATTR_EXPLICIT, "boolean",
                         value_bool=bool(note.explicit))
        self._write_attr(note.key, NOTE_ATTR_HORIZON_DAYS, "number",
                         value_num=float(note.horizon_days))
        self._write_attr(note.key, NOTE_ATTR_SOURCE_ENTRY_IDS, "multi_select",
                         value_set=list(note.source_entry_ids))
        return True

    # ── 读 ───────────────────────────────────────────────────────────────
    def get(self, key: str) -> Optional[MemoryNote]:
        row = self.store.execute_fetch(
            f"SELECT particle_id, updated_at FROM {_q(self.store.schema, 'particle')} "
            f"WHERE particle_id = %s", (key,), fetch_all=False)
        if row is None:
            return None
        attrs = self._read_attrs(key)
        if NOTE_ATTR_CONTENT_HASH not in attrs or NOTE_ATTR_CONTENT not in attrs:
            return None          # 半写状态（有粒子无属性）视作不存在，禁返回残缺 note
        updated = row.get("updated_at")
        return MemoryNote(
            key=key,
            content=str(attrs[NOTE_ATTR_CONTENT]),
            content_hash=str(attrs[NOTE_ATTR_CONTENT_HASH]),
            horizon_days=int(attrs.get(NOTE_ATTR_HORIZON_DAYS) or 0),
            explicit=bool(attrs.get(NOTE_ATTR_EXPLICIT, False)),
            updated_at=updated.isoformat() if hasattr(updated, "isoformat")
            else str(updated or ""),
            source_entry_ids=tuple(attrs.get(NOTE_ATTR_SOURCE_ENTRY_IDS) or ()),
        )

    def iter_all(self) -> Iterator[MemoryNote]:
        """T41：召回消费点 —— 遍历 NOTE 轨（半写状态由 `get` 过滤）。

        ⛔ 半写粒子（有 particle 无完整属性）在 `get` 内返回 None，此处跳过，
           禁把残缺 note 喂进召回池（防召回脏候选）。
        """
        rows = self.store.execute_fetch(
            f"SELECT particle_id FROM {_q(self.store.schema, 'particle')} "
            f"WHERE type = %s AND layer = %s ORDER BY particle_id",
            (self.note_type, self.layer), fetch_all=True)
        for r in rows:
            n = self.get(r["particle_id"])
            if n is not None:
                yield n

    def __len__(self) -> int:
        row = self.store.execute_fetch(
            f"SELECT count(*)::int AS n FROM {_q(self.store.schema, 'particle')} "
            f"WHERE type = %s AND layer = %s",
            (self.note_type, self.layer), fetch_all=False)
        return int(row["n"]) if row else 0

    # ── 属性读写（列化存储，禁自由 JSON）───────────────────────────────
    def _write_attr(self, particle_id: str, attr: str, attr_type: str, *,
                    value_text: Optional[str] = None,
                    value_num: Optional[float] = None,
                    value_bool: Optional[bool] = None,
                    value_set: Optional[list] = None) -> None:
        self.store.execute(
            f"INSERT INTO {_q(self.store.schema, 'particle_attribute')} "
            f"(particle_id, attr, attr_type, value_text, value_num, value_bool, "
            f"value_set, source) "
            f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            f"ON CONFLICT (particle_id, attr, source) DO UPDATE SET "
            f"value_text=EXCLUDED.value_text, value_num=EXCLUDED.value_num, "
            f"value_bool=EXCLUDED.value_bool, value_set=EXCLUDED.value_set, "
            f"observed_at=now()",
            (particle_id, attr, attr_type, value_text, value_num, value_bool,
             value_set, _NOTE_ATTR_SOURCE))

    def _read_attrs(self, particle_id: str) -> Dict[str, Any]:
        rows = self.store.execute_fetch(
            f"SELECT attr, value_text, value_num, value_bool, value_set "
            f"FROM {_q(self.store.schema, 'particle_attribute')} "
            f"WHERE particle_id = %s AND source = %s",
            (particle_id, _NOTE_ATTR_SOURCE), fetch_all=True)
        out: Dict[str, Any] = {}
        for r in rows:
            v = r.get("value_text")
            if v is None:
                v = r.get("value_num")
            if v is None:
                v = r.get("value_bool")
            if v is None:
                v = r.get("value_set")
            out[r["attr"]] = v
        return out

    def _current_hash(self, key: str) -> Optional[str]:
        row = self.store.execute_fetch(
            f"SELECT value_text FROM {_q(self.store.schema, 'particle_attribute')} "
            f"WHERE particle_id = %s AND attr = %s AND source = %s",
            (key, NOTE_ATTR_CONTENT_HASH, _NOTE_ATTR_SOURCE), fetch_all=False)
        return None if row is None else row.get("value_text")


# ── 协议符合性（静态断言：供 `test_facade_import_vs_all` 之外的形态守卫用）──
if False:  # pragma: no cover — 仅类型检查期生效，运行期零开销
    _: MemoryLogStore = PgMemoryLogStore(None, None)   # type: ignore[arg-type]
    __: NoteStore = PgNoteStore(None, None)            # type: ignore[arg-type]
