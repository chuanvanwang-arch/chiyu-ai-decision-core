"""端到端装配 —— 消费方真正要写的那点代码。

一条主链路：
    inject_domain()        领域注入（三件套统一校验，配错即红，不静默）
      → run_spine()        决策脊柱 S1→S5（红线审批闸 + 落库 + 记忆网）
      → sync_graph()       从同一 store 事实派生图（只读，禁另起可写存储）
      → 视图 / MCP 工具    关系图谱 / 时间线 / 决策回链 / 工具暴露

⛔ 关键纪律（本文件逐处体现，改代码时勿破）：
  1. **单源**：图不是第二份存储。`sync_graph()` 每次从 `store` 的事实重建，
     视图里的每个节点/边都必须在 store 里找得到（探针 3 守着）。
  2. **不反向依赖**：内核不知道 `chiyu_decision`；脊柱在本层被装配进来。
  3. **零领域字面量**：本文件不含任何业务取值，全部来自 `domain.py`。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Mapping, Optional, Sequence, Tuple

from chiyu_kernel.api import (
    DomainBundle, GraphEdge, InMemoryGraphStore, McpServer, OntologyGraph,
    PgVectorStorePersister, RedlinePriorityGate, allow_principals,
    decision_backlinks, inject_domain, relation_view, timeline_view,
)
# ⛔ 决策脊柱走 `chiyu_decision.api`（sanctioned 面），不是 `chiyu_decision.spine`：
#    后者是内部路径；参考消费层是消费方样板，必须自己守纪律（B1/N2 门禁）。
from chiyu_decision.api import SpineResult, run_spine

from .domain import ACTIONS, PROFILE, SCENARIOS
from .store import InMemoryStore


# ── 装配体 ─────────────────────────────────────────────────────────────────
@dataclass
class ConsumerApp:
    """一个消费方应用的全部运行时状态。

    ⛔ `graph` 是**派生**物（每次 sync 重建），不是事实源；
       `store` 才是唯一事实源（particle + event + graph_edge）。
    """

    bundle: DomainBundle
    store: InMemoryStore
    persister: PgVectorStorePersister
    server: McpServer
    audit: List[tuple] = field(default_factory=list)
    graph: Optional[InMemoryGraphStore] = None

    # 便捷：受控谓词全集（K 层 + M 层七边）
    def controlled(self) -> Tuple[str, ...]:
        return self.bundle.profile.predicates.names()


def build_app(*, materialize: bool = False,
              principals: Sequence[str] = ("reader", "writer")) -> ConsumerApp:
    """一次注入，拿到可直接用的运行时。

    参数：
      materialize  是否跑 G 三钩子（向量/全文/本体同步）的**真实**物化。
                   样板默认 False：离线可复现，且降级显式留痕（provider='hash',
                   degraded=True，禁伪健康）。生产置 True 并注入真实 provider。
      principals   允许调用 MCP 工具的主体（零信任：未注入 auth ⇒ 一律拒绝）。
    """
    bundle = inject_domain(profile=PROFILE, actions=ACTIONS, scenarios=SCENARIOS)
    store = InMemoryStore()
    persister = PgVectorStorePersister(
        store, bundle.profile, onto=OntologyGraph(), materialize=materialize)
    app = ConsumerApp(
        bundle=bundle, store=store, persister=persister,
        server=McpServer(auth=allow_principals(*principals)),
    )
    sync_graph(app)
    _expose_tools(app)
    return app


# ── 主链路：跑一次决策 ──────────────────────────────────────────────────────
def run_decision(app: ConsumerApp, *, decision_id: str, text: str,
                 rubric_scores: Mapping[str, float],
                 elements: Mapping[str, object],
                 references: Optional[Mapping[str, Sequence[str]]] = None,
                 concept_refs: Sequence[str] = (),
                 redline_items: Tuple[str, ...] = (),
                 subject_id: str = "", tenant_id: str = "tenant-1",
                 policy_version: str = "v1",
                 threshold: float = 0.79) -> SpineResult:
    """S1→S5 跑一次决策：落库 + 审批闸 + 记忆网，随后重建派生图。

    `references` 的键即七条记忆谓词的落点（subject / precedents / exceptions /
    frames / overrides / causes / influencers），由 `persist` 层的映射表规定。
    """
    refs = dict(references or {})

    def _persist(result: Any) -> str:
        return app.persister.persist(
            result, policy_version=policy_version, concept_refs=tuple(concept_refs),
            subject_id=subject_id, tenant_id=tenant_id, references=refs)

    def _audit(event_type: str, payload: Mapping[str, Any]) -> None:
        app.audit.append((event_type, dict(payload)))

    res = run_spine(
        context={"text": text, "decision_id": decision_id},
        profile=app.bundle.profile,
        rubric_scores=rubric_scores,
        elements=elements,
        persister=_persist,
        approval_gate=RedlinePriorityGate(),
        audit_sink=_audit,
        redline_items=redline_items,
        threshold=threshold,
    )
    sync_graph(app)          # 单源：每次落库后从事实重建派生图
    return res


def record_outcome(app: ConsumerApp, decision_id: str, outcome: Mapping[str, Any],
                   *, subject_id: str = "") -> None:
    """记录决策的**执行结果**（闭环「结果→D」边）。

    底座不替消费方猜结果是什么 —— 结果由执行侧回填，落到同一 store 的 event。
    """
    app.store.events[f"{decision_id}:outcome"] = {
        "event_type": "outcome", "decision_id": decision_id,
        "subject_id": subject_id, **dict(outcome),
    }


def sync_graph(app: ConsumerApp) -> InMemoryGraphStore:
    """从 `store` 事实重建派生图（H 单源双视图：只读派生，禁另起可写存储）。

    ⛔ 每次重建 ⇒ 视图不可能比事实源「多出」东西；探针 3 正是验这一点。
    """
    edges = [GraphEdge.from_row(e) for e in app.store.edges]
    app.graph = InMemoryGraphStore(app.controlled(), edges)
    return app.graph


# ── 三个只读视图（消费方按需取用）───────────────────────────────────────────
def relations(app: ConsumerApp, root: str, *, max_hops: int = 2) -> dict:
    assert app.graph is not None, "图未同步：先跑 sync_graph(app)"
    return relation_view(app.graph, root, max_hops=max_hops)


def timeline(app: ConsumerApp, subject_id: Optional[str] = None, *,
             limit: int = 200) -> list:
    """时间线叙事：四源只读聚合（particle / graph_edge / event / decision）。

    ⛔ 缺源即该源无行 —— 不用别的源去填，否则叙事变成编造。
    """
    return timeline_view(
        particles=[{"particle_id": pid, **p} for pid, p in app.store.particles.items()],
        edges=app.store.edges,
        events=[{"id": eid, **pl} for eid, pl in app.store.events.items()],
        decisions=[{"decision_id": k, **pl}
                   for k, pl in app.store.decision_events().items()],
        subject_id=subject_id, limit=limit)


def backlinks(app: ConsumerApp, decision_id: str) -> dict:
    assert app.graph is not None, "图未同步：先跑 sync_graph(app)"
    return decision_backlinks(app.graph, decision_id)


# ── 工具暴露（WS7：注册守卫 + 零信任 + 两阶段确认）──────────────────────────
def _expose_tools(app: ConsumerApp) -> None:
    """暴露四个工具：三个只读 + 一个写（写须两阶段确认）。

    ⛔ 同名重复注册会抛（禁静默覆盖 —— 否则调用方打到错的处理器）。
    """
    app.server.expose(
        "list_decisions", lambda args, ctx=None: sorted(app.store.decision_events()),
        description="列出已落库决策 id", risk="read")
    app.server.expose(
        "read_timeline", lambda args, ctx=None: timeline(
            app, (args or {}).get("subject_id")),
        description="读时间线叙事（四源只读聚合）", risk="read")
    app.server.expose(
        "read_relations", lambda args, ctx=None: relations(
            app, (args or {}).get("root", ""),
            max_hops=int((args or {}).get("max_hops", 2))),
        description="读关系图谱（受控边多跳）", risk="read")
    app.server.expose(
        "record_decision_outcome",
        lambda args, ctx=None: record_outcome(
            app, (args or {})["decision_id"],
            {"status": (args or {}).get("status", "unknown")},
            subject_id=(args or {}).get("subject_id", "")),
        description="回填决策执行结果（写操作，需两阶段确认）", risk="write")


__all__ = [
    "ConsumerApp", "build_app", "run_decision", "record_outcome", "sync_graph",
    "relations", "timeline", "backlinks",
]
