"""WS2 标准 persister + 记忆网 canonical writer（内核机制，非领域清单）。

⛔ 内核零领域字面量：本模块只承载「决策落库机制 + 记忆网 canonical writer」。
   粒子类型 / 谓词取值 / 红线目录 / 八要素取值一律由调用方经 TenantProfile 注入。

⛔ 决策落库模型（零建表铁则 · 设计 §0.3 落地）：决策**不单独开表**，落既有
   `event` 表（event_type='decision'，决策字段进 payload jsonb——event.payload 是
   零建表铁则允许的三处 jsonb 例外之一）+ 同库 upsert 一个 `particle`
   （type='decision'，layer='L1' 作为决策主体锚点）。读侧经 H 单源双视图（时间线叙事
   视图）派生，禁另起可写存储。

⛔ 不反向依赖 chiyu_decision：persister 用 getattr 鸭子类型接收 `SpineResult`，
   另提供内核原生 `DecisionRecord` 给显式调用方。脊柱 `run_spine` 的
   `persister: Callable[[SpineResult], object]` 回调可直接接本类 `.persist`。

embody（吸收专利蓝图 + 10 SKILL 方法论，中性化）：
  N 四轨同库     → 全部写经同一 PgVectorStore（particle + graph_edge + event 同 schema）
  B 双轨四闸     → `write_decision_memory_net` 经 `judge_worthiness` 闸（凭证硬拒 / 瞬态噪声）
  F K-M-D 三段   → 7 记忆谓词边即 knowledge↔memory↔decision 的 M 层闭环链
  G 写时三钩子   → content_hash 幂等判变 + provider/degraded 显式留痕（禁伪健康）
                  + ensure_tsvector / ontology_sync（降级不中断）
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

from chiyu_kernel.contract import TenantProfile, VECTOR_DIM
from chiyu_kernel.contract.particle import MEMORY_PREDICATES
from chiyu_kernel.persist.graph_edges import (  # noqa: F401  T47 R9 方案 A：受控边写原语（graph_edge 唯一落库点）
    EdgeWrite, EdgeWriteReport, upsert_graph_edge, write_controlled_edges,
)
from chiyu_kernel.vector import is_available as vector_is_available
from chiyu_kernel.vector.infer import content_hash
from chiyu_kernel.persist.memory_tracks import (  # noqa: F401  B 双轨记忆运行时 + F 回流白名单
    DistillReport, InMemoryMemoryLog, InMemoryNoteStore, MemoryLogEntry,
    MemoryLogStore, MemoryNote, NoteStore, PRESCRIBABLE_PREDICATES,
    distill, is_prescribable, note_hash, parse_ts,
)
from chiyu_kernel.persist.pg_memory_stores import (  # noqa: F401  T40：双轨记忆 PG 落库（零新增 DDL）
    EVENT_TYPE_MEMORY_LOG, PgMemoryLogStore, PgNoteStore,
    NOTE_ATTR_CONTENT, NOTE_ATTR_CONTENT_HASH, NOTE_ATTR_EXPLICIT,
    NOTE_ATTR_HORIZON_DAYS, NOTE_ATTR_SOURCE_ENTRY_IDS,
)
from chiyu_kernel.ontology import Particle, OntologyGraph
from chiyu_kernel.ontology.hooks import (
    ensure_embedding, ensure_tsvector, ontology_sync,
)

EVENT_TYPE_DECISION = "decision"
DEFAULT_NET_SERVES_DIMS: Tuple[str, ...] = ("decision_history", "governance")

# MEMORY_PREDICATES 谓词名 → references 中的取值键
_NET_REF_KEYS: Mapping[str, str] = {
    "DECIDED_ON": "subject",
    "REFERENCED_PRECEDENT": "precedents",
    "DERIVED_FROM_EXCEPTION": "exceptions",
    "ESTABLISHES_FRAME": "frames",
    "OVERRIDES": "overrides",
    "CAUSED": "causes",
    "INFLUENCED": "influencers",
}


@dataclass
class DecisionRecord:
    """内核原生决策结果（persister 的标准输入；亦可由 SpineResult 转换）。

    ⛔ 只承载落库所需的形态字段；具体取值（concept_refs / disposition / policy_version）
       由调用方经 SpineResult 或显式参数注入，内核不提供默认领域值。
    """

    decision_id: str
    confidence: float
    redline_hit: bool
    redline_reasons: Tuple[str, ...] = ()
    autonomous: bool = False
    rubric_missing: Tuple[str, ...] = ()
    elements_missing: Tuple[str, ...] = ()
    concept_refs: Tuple[str, ...] = ()
    disposition: str = "auto"
    policy_version: str = ""
    tenant_id: str = ""
    subject_id: str = ""
    occurred_at: Any = None

    @classmethod
    def from_spine(cls, obj: Any) -> "DecisionRecord":
        """鸭子类型转换：接收 chiyu_decision.SpineResult 等任意带属性的对象。

        ⛔ 不 import chiyu_decision（防反向依赖）；用 getattr 提取，缺项给中性默认。
        """
        return cls(
            decision_id=str(getattr(obj, "decision_id", "")),
            confidence=float(getattr(obj, "confidence", 0.0) or 0.0),
            redline_hit=bool(getattr(obj, "redline_hit", False)),
            redline_reasons=tuple(getattr(obj, "redline_reasons", ()) or ()),
            autonomous=bool(getattr(obj, "autonomous", False)),
            rubric_missing=tuple(getattr(obj, "rubric_missing", ()) or ()),
            elements_missing=tuple(getattr(obj, "elements_missing", ()) or ()),
        )


def _to_record(obj: Any) -> DecisionRecord:
    if isinstance(obj, DecisionRecord):
        return obj
    return DecisionRecord.from_spine(obj)


# ── B 双轨四闸：记忆网写入闸门 ───────────────────────────────────────────────
def judge_worthiness(record: DecisionRecord, *, value_horizon_days: int = 30,
                     transient: bool = False) -> Tuple[bool, str]:
    """决策→记忆网 的写入闸门（embody B 双轨四闸的两道可落库闸）。

    返回 (worthy, reason)。worthy=False ⇒ 记忆网不写（但决策 event 仍落库，供审计回链）。

    落库侧可执行的闸：
      · 凭证硬拒：红线命中 ⇒ 被拒决策不建立正向先例边（防红线决策污染记忆网）。
      · 瞬态噪声：调用方显式 transient ⇒ 低于价值视界的预览/抖动不落网。
    ⚠ 边界：B 的「价值视界<30天」「显式优先」两闸作用于 memory LOG/NOTE 蒸馏
      （记忆运行时 writer，独立 WS），不在决策网写入层落位——此处不假装有。
    """
    if record.redline_hit:
        return False, "凭证硬拒：红线命中决策不建立正向先例边"
    if transient:
        return False, "瞬态噪声：低于价值视界的预览/抖动不落记忆网"
    return True, "worthy"


def _q(schema: str, table: str) -> str:
    return f"{schema}.{table}"


def write_decision_memory_net(
    decision_id: str,
    *,
    references: Mapping[str, Sequence[str]],
    profile: TenantProfile,
    write_edge: Callable[..., None],
    record: Optional[DecisionRecord] = None,
    judge: Callable[[DecisionRecord], Tuple[bool, str]] = judge_worthiness,
) -> int:
    """7 记忆谓词 canonical writer（embody F K-M-D 的 M 层闭环链）。

    参数：
      decision_id   决策粒子 id（from 端锚点）
      references     取值键 → 目标 id 列表（见 _NET_REF_KEYS）
      profile        TenantProfile（取值校验：边名 ∈ 谓词集、端类型 ∈ particle_types）
      write_edge     落边回调（duck-typed，真实环境 = store 的 graph_edge upsert）
      record         决策记录（供 judge 闸裁定是否值得落网）
      judge          闸门（默认 judge_worthiness；变异自证时传入恒 True 模拟闸失效）

    返回：实际写入的边条数。

    ⛔ 受控边六映射 + 显式 edge_source='engine'（与 MEMORY_PREDICATES.source 一致）。
    幂等：write_edge 自身须幂等（真实环境 ON CONFLICT (from_id,to_id,predicate)）。
    """
    if record is not None:
        worthy, _reason = judge(record)
        if not worthy:
            return 0

    written = 0
    declared = set(profile.predicates.names())
    types = set(profile.particle_types.names)
    for pred in MEMORY_PREDICATES:
        if pred.predicate not in declared:
            # 该谓词不在 profile 谓词集 ⇒ 边永远无法建立（构造期已挡，运行期再保险）
            continue
        ref_key = _NET_REF_KEYS.get(pred.predicate, pred.predicate.lower())
        targets = references.get(ref_key) or ()
        for tid in targets:
            if not tid:
                continue
            # 端类型校验：from 固定 decision；to 为 None 表示「决策→其主体」由调用方保证
            if pred.to_type is not None and pred.to_type not in types:
                continue
            write_edge(
                decision_id, tid, pred.predicate,
                layer=pred.layer, serves_dims=DEFAULT_NET_SERVES_DIMS,
                edge_source=pred.source,
            )
            written += 1
    return written


class PgVectorStorePersister:
    """标准 persister（SpineResult → particle / event / 记忆网 映射 shim）。

    ⛔ 机制非清单：具体决策取值（concept_refs / disposition / policy_version / 红线目录）
       全部由调用方经参数或 SpineResult 注入；本类只做映射 + 闸门 + G 钩子。

    embody：
      N 四轨同库   → particle + event + graph_edge 全部经同一 store（同 schema 同事务边界）
      G 写时三钩子 → content_hash 幂等判变 + provider/degraded 显式留痕 + tsvector/ontology_sync
    """

    def __init__(self, store: Any, profile: TenantProfile, *,
                 onto: Optional[OntologyGraph] = None,
                 event_bus: Any = None, materialize: bool = True) -> None:
        self.store = store
        self.profile = profile
        self.onto = onto
        self.event_bus = event_bus
        self.materialize = materialize
        self._skip_idempotency = False  # 变异自证开关（默认 False=启用幂等）

    # ── 主入口：S5_persist 回调 ──────────────────────────────────────────
    def persist(self, result: Any, *, policy_version: str = "",
                concept_refs: Sequence[str] = (), disposition: str = "auto",
                subject_id: str = "", tenant_id: str = "",
                occurred_at: Any = None,
                references: Optional[Mapping[str, Sequence[str]]] = None) -> str:
        """落库一个决策结果，返回 event id（= decision_id，供脊柱置 persisted=True）。

        落库三件套（同 store、幂等）：
          1. event（event_type='decision'，payload jsonb 携带决策字段 + content_hash）
          2. particle（type='decision'，layer='L1'，决策主体锚点，provider/degraded 留痕）
          3. 记忆网（references 非空时写 7 谓词边，受 judge 闸 + F 闭环）
        写后触发 G 钩子（tsvector / ontology_sync，降级不中断）+ 事件总线回流。
        """
        rec = _to_record(result)
        payload = self._build_payload(
            rec, policy_version, tuple(concept_refs), disposition,
            subject_id, tenant_id, occurred_at)
        ch = content_hash({k: payload[k] for k in (
            "confidence", "redline_hit", "redline_reasons", "autonomous",
            "rubric_missing", "elements_missing", "concept_refs",
            "disposition", "policy_version")})
        payload["content_hash"] = ch

        event_id = rec.decision_id
        schema = self.store.schema

        # ── G：content_hash 幂等判变（内容未变跳过重落，禁伪写）────────
        if not self._skip_idempotency:
            existing = self.store.execute_fetch(
                f"SELECT payload->>'content_hash' AS ch "
                f"FROM {_q(schema, 'event')} WHERE id=%s", (event_id,))
            if existing is not None and existing.get("ch") == ch:
                return event_id  # 幂等：内容未变，跳过

        # 2. particle（决策主体锚点；upsert 幂等，provider/degraded 留痕）
        #    ⛔ 在 event 写入前解析，确保 provider/degraded 随 payload 同事务落库（禁伪健康）
        provider, degraded = self._resolve_provider(rec, subject_id)
        payload["vector_degraded"] = degraded
        payload["vector_provider"] = provider

        # 1. event（upsert，幂等）
        self.store.execute(
            f"INSERT INTO {_q(schema, 'event')} "
            f"(id, ts, domain, event_type, stage, subject_id, decision_id, dims, payload) "
            f"VALUES (%s, now(), %s, '{EVENT_TYPE_DECISION}', 'S5_persist', %s, %s, %s, %s::jsonb) "
            f"ON CONFLICT (id) DO UPDATE SET payload=EXCLUDED.payload, ts=now()",
            (event_id, self.profile.domain, subject_id or None, rec.decision_id,
             list(DEFAULT_NET_SERVES_DIMS),
             json.dumps(payload, ensure_ascii=False)))

        self.store.upsert_particle(
            particle_id=rec.decision_id, ptype="decision", layer="L1",
            label=subject_id or rec.decision_id, status="persisted",
            provider=provider, ai_generated=False, dim=VECTOR_DIM)

        # 3. 记忆网（7 谓词边；受 B 闸 + F 闭环）
        written = 0
        if references:
            written = write_decision_memory_net(
                rec.decision_id, references=references, profile=self.profile,
                write_edge=self._store_write_edge(), record=rec)

        # G 钩子：tsvector + ontology_sync（降级不中断）
        if self.materialize:
            self._materialize(rec, subject_id)

        # 事件总线回流（G 事件总线 + SSE 通道的消费侧由调用方接）
        if self.event_bus is not None:
            try:
                self.event_bus.publish(
                    {"type": "decision_persisted", "decision_id": rec.decision_id,
                     "edges": written, "degraded": degraded}, lambda m: None)
            except Exception:
                pass

        return event_id

    # ── 辅助 ──────────────────────────────────────────────────────────────
    def _build_payload(self, rec: DecisionRecord, policy_version: str,
                       concept_refs: Tuple[str, ...], disposition: str,
                       subject_id: str, tenant_id: str, occurred_at: Any) -> dict:
        return {
            "decision_id": rec.decision_id,
            "confidence": rec.confidence,
            "redline_hit": rec.redline_hit,
            "redline_reasons": list(rec.redline_reasons),
            "autonomous": rec.autonomous,
            "rubric_missing": list(rec.rubric_missing),
            "elements_missing": list(rec.elements_missing),
            "concept_refs": list(concept_refs),
            "disposition": disposition,
            "policy_version": policy_version or "",
            "subject_id": subject_id or "",
            "tenant_id": tenant_id or "",
            "occurred_at": occurred_at.isoformat() if hasattr(occurred_at, "isoformat") else occurred_at,
        }

    def _resolve_provider(self, rec: DecisionRecord, subject_id: str) -> Tuple[str, bool]:
        """G：provider 来源 + 降级显式留痕（N 统一降级协议）。

        ⛔ 降级不中断、provider 显式留痕（禁伪健康）：拿不到真向量 ⇒ provider='hash'，
           degraded=True，绝不冒充 model。
        """
        text = subject_id or rec.decision_id
        if self.materialize and vector_is_available():
            p = Particle(particle_id=rec.decision_id, type="decision",
                         subject_id=subject_id, fulltext=text)
            try:
                provider = ensure_embedding(p, column_dim=VECTOR_DIM, text=text)
            except Exception:
                provider = "hash"
        else:
            provider = "hash"
        return provider, (provider == "hash")

    def _materialize(self, rec: DecisionRecord, subject_id: str) -> None:
        """G 钩子2/3：全文索引 + 受控边同步（降级不中断）。"""
        p = Particle(particle_id=rec.decision_id, type="decision",
                     subject_id=subject_id, fulltext=subject_id or rec.decision_id)
        try:
            ensure_tsvector(p)
        except Exception:
            pass
        try:
            ontology_sync(p, self.onto)
        except Exception:
            pass

    def _store_write_edge(self) -> Callable[..., None]:
        store = self.store

        def _w(from_id: str, to_id: str, predicate: str, *, layer: str = "M",
               serves_dims: Sequence[str] = (), edge_source: str = "engine",
               evidence_ref: Optional[str] = None, valid_from: Any = None,
               valid_until: Any = None, weight: Optional[float] = None,
               confidence: Optional[float] = None) -> None:
            # T47：委托 graph_edges.upsert_graph_edge（全仓唯一 graph_edge 落库点，
            # SQL 与参数序与原内联实现逐字节一致——零行为变更，守卫白名单随迁）。
            upsert_graph_edge(store, EdgeWrite(
                from_id=from_id, to_id=to_id, predicate=predicate, layer=layer,
                serves_dims=serves_dims, edge_source=edge_source,
                evidence_ref=evidence_ref, valid_from=valid_from,
                valid_until=valid_until, weight=weight, confidence=confidence))

        return _w


__all__ = [
    "EVENT_TYPE_DECISION",
    "DecisionRecord",
    "judge_worthiness",
    "write_decision_memory_net",
    "PgVectorStorePersister",
    # B 双轨记忆运行时（memory_tracks：LOG append-only 轨 + notes upsert 轨 + 蒸馏两闸）
    "MemoryLogEntry", "MemoryNote", "DistillReport",
    "MemoryLogStore", "InMemoryMemoryLog", "NoteStore", "InMemoryNoteStore",
    "note_hash", "distill", "parse_ts",
    # F K-M-D 闭环回流白名单（审计凭证边不可改写）
    "PRESCRIBABLE_PREDICATES", "is_prescribable",
    # T40：双轨记忆 PG 落库（复用既有 event / particle / particle_attribute，零新增 DDL）
    "EVENT_TYPE_MEMORY_LOG", "PgMemoryLogStore", "PgNoteStore",
    "NOTE_ATTR_CONTENT", "NOTE_ATTR_CONTENT_HASH", "NOTE_ATTR_EXPLICIT",
    "NOTE_ATTR_HORIZON_DAYS", "NOTE_ATTR_SOURCE_ENTRY_IDS",
    # T47：R9 方案 A 受控边写原语（graph_edge 唯一落库点，谓词闭集 M∪K fail-fast）
    "EdgeWrite", "EdgeWriteReport", "write_controlled_edges",
]
