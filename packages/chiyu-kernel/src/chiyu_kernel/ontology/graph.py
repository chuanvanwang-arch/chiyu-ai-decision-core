"""本体受控关系图（写时同步钩子的内核版 —— 去领域化）。

demo 版是「五类节点 / 六类受控边」：TICKET-ENTITY / TICKET-PLACE / TICKET-CATEGORY /
ENTITY-PLACE 共现 / TICKET-TICKET 相似 / TICKET-EVENT 归属 —— 节点名与谓词名全是
**群诉领域字面量**。

⛔ 泛化：受控谓词清单由消费方注入的 `profile.predicates`（TenantProfile）提供，
内核只提供「有界谓词 + 幂等加边 + 一跳邻域」的**机制**：

    ```
    graph = OntologyGraph(predicates=profile.predicates)   # K 层知识谓词即受控谓词
    graph.link(predicate="mentions",  _from=pid_a, _to=pid_b)
    graph.link(predicate="belongs_to", _from=pid_b, _to=pid_c)
    graph.neighbors(pid_a)   # 一跳邻域（含谓词标签）
    ```

主体名归一（写时身份校验闸）：内核提供 `normalize()` **机制**，后缀规则由调用方
注入（默认空 ⇒ 不剥；demo 的工商后缀「有限公司/集团…」属领域默认，不得进内核）。
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable, Mapping, Optional, Sequence

from chiyu_kernel.contract.particle import PredicateSet


def normalize(name: str, suffixes: Sequence[str] = ()) -> str:
    """主体名归一（通用机制）：循环剥离 `suffixes` 中的后缀。

    默认空后缀 ⇒ 原样返回（内核不携带任何单域默认，防单域退化）。
    调用方可注入领域后缀（如 demo 的工商主体后缀）。
    """
    if not name:
        return name
    n = name.strip()
    pat = re.compile("|".join(re.escape(s) for s in suffixes)) if suffixes else None
    if not pat:
        return n
    while True:
        m = pat.search(n)
        if m and len(n) - len(m.group(0)) >= 2:
            n = n[: -len(m.group(0))]
        else:
            break
    return n


class OntologyGraph:
    """本体受控关系图：受控谓词由 profile 提供；`link()` 幂等；写库即图。

    边存储两个方向索引：
        _out[predicate][from_id] -> set[to_id]
        _in[predicate][to_id]    -> set[from_id]
    """

    def __init__(self, predicates: Optional[PredicateSet] = None):
        self._predicate_names: set = set()
        if predicates is not None:
            self._predicate_names = {
                p.predicate for p in predicates.knowledge if p.layer == "K"
            }
        self._out: dict = defaultdict(lambda: defaultdict(set))
        self._in: dict = defaultdict(lambda: defaultdict(set))

    # ── 受控谓词 ──────────────────────────────────────────────────
    def controlled(self) -> tuple:
        """当前受控谓词清单（K 层知识谓词；空=未注入 profile 时无受控边）。"""
        return tuple(sorted(self._predicate_names))

    def add_predicates(self, predicates: PredicateSet) -> None:
        """（可重入）追加受控谓词清单 —— profile 注入（幂等，重复覆盖）。"""
        self._predicate_names |= {
            p.predicate for p in predicates.knowledge if p.layer == "K"
        }

    # ── 写入（写库即图，钩子3）──────────────────────────────────────
    def link(self, predicate: str, _from: str, _to: str) -> None:
        """加一条受控边。⛔ 谓词必须是受控清单中的 K 层知识谓词（有界）。"""
        if predicate not in self._predicate_names:
            raise ValueError(f"未受控谓词：{predicate!r}（须 ∈ profile.predicates 的 K 层）")
        self._out[predicate][_from].add(_to)
        self._in[predicate][_to].add(_from)

    def sync_particle(self, particle: Any) -> None:
        """钩子3 落图：从粒子 `raw_refs` 建立「particle → 引用对象」的受控边。

        ⛔ 谓词名由调用方在构造 graph 时指定 —— `controlled_ref_predicate`（默认
        `"references"`，消费方可用 `add_predicates` 扩展/替换）。这里不硬编码
        领域谓词（如 demo 的 entity/place/category 三条）。
        """
        refs = particle.raw_refs or ()
        pid = particle.particle_id
        pred = self._controlled_ref_predicate()
        if not pred:
            return                        # 未注入受控谓词 ⇒ 无受控边（不伪造）
        for r in refs:
            self.link(pred, pid, str(r))

    def _controlled_ref_predicate(self) -> Optional[str]:
        for name in ("references", "mentions", "refers_to"):
            if name in self._predicate_names:
                return name
        return None

    # ── 查询（供候选召回 / 决策详情一跳邻域）────────────────────────
    def neighbors(self, node_id: str,
                  predicates: Optional[Iterable[str]] = None) -> dict:
        """一跳邻域：出边 + 入边（含谓词标签）。泛化 demo `one_hop`。"""
        preds = list(predicates) if predicates is not None else sorted(self.controlled())
        out_: dict = {}
        in_: dict = {}
        for p in preds:
            o = self._out[p].get(node_id)
            if o:
                out_[p] = sorted(o)
            i = self._in[p].get(node_id)
            if i:
                in_[p] = sorted(i)
        return {"node": node_id, "out": out_, "in": in_}

    def out_edges(self, node_id: str, predicate: str) -> set:
        return set(self._out[predicate].get(node_id, ()))

    def in_edges(self, node_id: str, predicate: str) -> set:
        return set(self._in[predicate].get(node_id, ()))


__all__ = ["OntologyGraph", "normalize"]
