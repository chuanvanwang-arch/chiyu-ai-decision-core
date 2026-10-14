"""记忆召回消费点（T41：memory 毕业批次二）—— 打通「写了能读」。

⛔ 根因直述：T41 之前 memory 有两条支线却**无消费点**——决策写了记忆网、
   双轨蒸馏了 NOTE，而 `run_spine` 在 S1→S2 之间从不读记忆 ⇒
   「写了不读 = 没用」。这正是 memory 长期卡在 `experimental` 的实质缺口：
   不是能力没实现，而是**能力没接进决策回路**。

本模块把记忆接进召回，两源合并成池后交既有 `degraded_recall`（复用三级降级，
不另发明排序）：
  · 源 A 记忆网回链（图只读派生）：当前主体的 `ESTABLISHES_FRAME` /
    `REFERENCED_PRECEDENT` 出边目标 + 决策回链 `referenced_by` ⇒ 先例候选
  · 源 B 双轨 NOTE 轨：全部 note 的 content ⇒ 语料候选

⛔ 诚实降级（禁伪健康）：
  · NOTE 粒子落库时 vec=NULL ⇒ 池内 coverage=0 ⇒ `degraded_recall` 如实走
    fts 档并留痕；本模块**不伪造向量分**（与 persist 的 provider/degraded 留痕同纪律）。
  · 图源 / NOTE 源不可用 ⇒ 捕获并在 `evidence.notes` 留痕，防静默丢源。

⛔ 谓词名不发明：默认谓词来自 L0 契约 `MEMORY_PREDICATES`，import 期
   fail-fast 校验（契约漂移即红，而非运行期静默召回空）。
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Optional, Sequence

from chiyu_kernel.contract.particle import MEMORY_PREDICATES
from chiyu_kernel.graph import decision_backlinks
from .fuse import RRF_K_DEFAULT, rrf_fuse
from .retrieval import RetrievalResult, degraded_recall, to_supply_layer

__all__ = [
    "RECALL_REFERENCE_PREDICATE", "RECALL_FRAME_PREDICATE",
    "recall_precedents", "build_memory_recaller",
]

# ── 默认谓词（取自 L0 契约，import 期 fail-fast）─────────────────────────
RECALL_REFERENCE_PREDICATE = "REFERENCED_PRECEDENT"
RECALL_FRAME_PREDICATE = "ESTABLISHES_FRAME"

_M_PREDICATE_NAMES = {m.predicate for m in MEMORY_PREDICATES}
for _p in (RECALL_REFERENCE_PREDICATE, RECALL_FRAME_PREDICATE):
    if _p not in _M_PREDICATE_NAMES:
        raise RuntimeError(
            f"召回默认谓词 {_p} 不在 L0 契约 MEMORY_PREDICATES ⇒ 谓词漂移（禁静默召回空）")


def _pool_from_memory_net(graph: Any, subject_id: str, *,
                          reference_predicate: str,
                          frame_predicate: str) -> list:
    """源 A：记忆网回链 → 先例候选（图只读，禁写）。"""
    pool: list = []
    seen: set = set()
    for pred in (reference_predicate, frame_predicate):
        for e in graph.out_edges(subject_id, [pred]):
            k = getattr(e, "to_id", None)
            if k and k not in seen:
                seen.add(k)
                pool.append({"key": k, "text": k, "vector": None})
    links = decision_backlinks(graph, subject_id,
                               reference_predicate=reference_predicate)
    for k in links.get("referenced_by", ()):
        if k not in seen:
            seen.add(k)
            pool.append({"key": k, "text": k, "vector": None})
    return pool


def recall_precedents(query_terms: Sequence[str], *,
                      notes: Any = None,
                      graph: Any = None,
                      subject_id: str = "",
                      query_vector: Optional[Sequence[float]] = None,
                      top_k: int = 10,
                      rrf_k: int = RRF_K_DEFAULT,
                      reference_predicate: str = RECALL_REFERENCE_PREDICATE,
                      frame_predicate: str = RECALL_FRAME_PREDICATE,
                      ) -> RetrievalResult:
    """记忆召回：记忆网回链 + 双轨 NOTE 两源 → 各自三级降级 → RRF 融合。

    `notes` 需满足 `NoteStore`（`iter_all()`）；`graph` 需满足 `GraphStore`
    （`out_edges` / `controlled`）。

    源数分派（T42）：
      · 0 源  ⇒ 显式空（tier=none，不伪造候选）
      · 1 源  ⇒ 直接返回该源结果，并在 notes 留痕「不经 RRF 融合」
      · ≥2 源 ⇒ `rrf_fuse` 名次融合（跨源量纲不同，禁直接比分数）
    """
    sources: list = []
    extra: list = []

    if graph is not None and subject_id:
        try:
            gpool = _pool_from_memory_net(
                graph, subject_id,
                reference_predicate=reference_predicate,
                frame_predicate=frame_predicate)
            if gpool:
                sources.append(degraded_recall(
                    query_terms, gpool, query_vector=query_vector, top_k=top_k))
        except Exception as exc:                       # noqa: BLE001
            extra.append(f"记忆网回链不可用，图源降级：{type(exc).__name__}")

    if notes is not None:
        try:
            npool = [{"key": n.key, "text": n.content, "vector": None}
                     for n in notes.iter_all()]
            if npool:
                sources.append(degraded_recall(
                    query_terms, npool, query_vector=query_vector, top_k=top_k))
        except Exception as exc:                       # noqa: BLE001
            extra.append(f"NOTE 轨不可用，笔记源降级：{type(exc).__name__}")

    if not sources:
        # 无可用源 ⇒ 显式空（与 degraded_recall 空池语义一致，不伪造候选）
        res = degraded_recall(query_terms, [], query_vector=query_vector,
                              top_k=top_k)
    elif len(sources) == 1:
        res = sources[0]
        extra.append("仅单源可用 ⇒ 不经 RRF 融合（降级路径留痕）")
    else:
        res = rrf_fuse(sources, k=rrf_k, top_k=top_k)

    if extra:
        res = replace(res, evidence=replace(
            res.evidence, notes=res.evidence.notes + tuple(extra)))
    return res


def build_memory_recaller(*, notes: Any = None, graph: Any = None,
                          top_k: int = 10) -> Any:
    """构造 `run_spine(memory_recaller=...)` 钩子：`(context) -> context`。

    注入键（中性形态词，零领域字面量）：
      · `precedents`      召回到的先例 key 列表（供 S2 之后的域逻辑消费）
      · `precedent_supply`  `to_supply_layer` 形态（可直接喂 `assemble()`）
      · `memory_recall`   召回自证（`evidence.to_dict()`，降级留痕可审计）

    ⛔ 严格加法：返回**新** Mapping，不改传入 context（无副作用）。
    """
    def _hook(context: Mapping) -> Mapping:
        terms = context.get("query_terms")
        if not isinstance(terms, (list, tuple)):
            terms = str(context.get("text") or "").split()
        subject_id = str(context.get("subject_id")
                         or context.get("decision_id") or "")
        res = recall_precedents(list(terms), notes=notes, graph=graph,
                                subject_id=subject_id, top_k=top_k)
        merged = dict(context)
        merged["precedents"] = [i.key for i in res.items]
        merged["precedent_supply"] = to_supply_layer(res)
        merged["memory_recall"] = res.evidence.to_dict()
        return merged

    return _hook
