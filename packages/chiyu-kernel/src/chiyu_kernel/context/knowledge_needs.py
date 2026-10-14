"""需求侧编码 + 供需缺口判定（SKILL #4 —— 内核版，去领域化）。

抽取自 demo `context/knowledge_needs.py`（2026-09-21，P1 T4）。
⛔ 去领域化的三处精确化（源码核实）：
   1. demo `REQUIRED_FIELDS_8`（text_sim/…/cluster_size…）与
      `DEFAULT_DATA_SOURCES`（candidates/cluster_profile…）含**领域字面量**
      （cluster/place 类），属 L4 领域取值 ⇒ 全部参数化，调用方显式传；
      本模块只保留**机制**（上限约束、缺口判据、七维齐全轴）。
   2. 返回类型 → `KnowledgeNeeds`（与 assembly.KnowledgeNeed 的对接经\n      `to_assembly_needs()`）。
   3. `check_supply_demand` 的 `supply` 契约键（entity_links/historical_cases/\n      embedding_coverage/data_rows/hitl_checkpoints/gates）为**机制层判据**，保留。

四层模型：L1 知识底座 / L2 历史决策 / L3 执行协同 / L4 治理决策。
缺口类型：MISSING_ENTITY / INSUFFICIENT_EXPERIENCE / LOW_COVERAGE /\nMISSING_DATA / MISSING_HITL / MISSING_GATE。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .assembly import KnowledgeNeed

# Batch-2a（GAP-2）：四层模型 / 七维 / 上限 / 阈值 / 缺口类型上收
# `chiyu_kernel/contract/context.py`（sanctioned 契约面单一事实源）。
from chiyu_kernel.contract.context import (
    CONTEXT_DIMENSIONS,
    CONTEXT_LAYER_LABELS_ZH,
    GAP_INSUFFICIENT_EXPERIENCE,
    GAP_LOW_COVERAGE,
    GAP_MISSING_DATA,
    GAP_MISSING_ENTITY,
    GAP_MISSING_GATE,
    GAP_MISSING_HITL,
    KNOWLEDGE_LAYERS,
    MAX_DATASOURCES,
    MAX_ENTITIES,
    MAX_QUERY_TERMS,
    MAX_REQUIRED_FIELDS,
    MIN_EMBEDDING_COVERAGE,
    MIN_PRECEDENTS,
)

# 兼容别名（旧名仍可用，deprecation 政策：先 warn 一版再移除）
LAYER_NAMES = CONTEXT_LAYER_LABELS_ZH


def _clamp_unique(items: Iterable[str], limit: int) -> tuple[str, ...]:
    """去重 + 保序 + 截断（空串丢弃）。需求编码一律走此入口，防「无声膨胀」。"""
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        s = str(raw).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    return tuple(out)


@dataclass(frozen=True)
class KnowledgeNeeds:
    """需求侧编码：本次决策任务**需要**哪些知识。"""

    task_name: str
    knowledge_level: int
    semantic_entities: tuple[str, ...] = ()
    data_sources: tuple[str, ...] = ()
    required_fields: tuple[str, ...] = ()
    query_terms: tuple[str, ...] = ()

    @property
    def active_layers(self) -> tuple[str, ...]:
        """累积语义：level=x → 注入 L1..Lx（对齐 SKILL #4「level≥1 → L1」）。"""
        lv = max(0, min(int(self.knowledge_level), len(KNOWLEDGE_LAYERS)))
        return KNOWLEDGE_LAYERS[:lv]

    @property
    def semantic_entity_limit(self) -> int:
        return MAX_ENTITIES

    def to_assembly_needs(self, *, dims_by_layer: Mapping[str, Sequence[str]] | None = None,
                          keys_by_layer: Mapping[str, str] | None = None) -> tuple[KnowledgeNeed, ...]:
        """（+T4 对接）转为 `assembly.KnowledgeNeed` 序列，供 `assemble()` 消费。

        dims_by_layer / keys_by_layer 缺省时用机制默认（dims=()、key=""），
        即「该层有供给即计入」。调用方可按场景细化。
        """
        dims = dims_by_layer or {}
        keys = keys_by_layer or {}
        return tuple(
            KnowledgeNeed(layer=lv,
                          dims=tuple(dims.get(lv, ())),
                          key=keys.get(lv, ""))
            for lv in self.active_layers
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_name": self.task_name,
            "knowledge_level": self.knowledge_level,
            "semanticEntities": list(self.semantic_entities),
            "dataSources": list(self.data_sources),
            "requiredFields": list(self.required_fields),
            "queryTerms": list(self.query_terms),
            "activeLayers": list(self.active_layers),
        }


@dataclass(frozen=True)
class SupplyDemandGap:
    """供需缺口：显式标注（不静默吞）。"""

    layer: str
    code: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"layer": self.layer, "code": self.code, "detail": self.detail}


def build_knowledge_needs(
    task_name: str,
    knowledge_level: int = 2,
    *,
    entities: Sequence[str] = (),
    places: Sequence[str] = (),
    categories: Sequence[str] = (),
    data_sources: Sequence[str] = (),
    required_fields: Sequence[str] = (),
    query_terms: Sequence[str] = (),
) -> KnowledgeNeeds:
    """四段解析（对齐 SKILL #4 第 2 轮）：种子 / 源 / 字段 / 查询词。

    语义实体 = ENTITY + PLACE + CATEGORY 合并去重（图种子，≤24）——\n    参数名 `places`/`categories` 是**调用方传入的领域取值**，本模块只做合并去重。\n    查询词**不含 snake_case 字段名**（字段走 requiredFields，混入会污染 embedding 引导）。
    """
    terms = [t for t in query_terms if "_" not in str(t)]
    return KnowledgeNeeds(
        task_name=str(task_name),
        knowledge_level=int(knowledge_level),
        semantic_entities=_clamp_unique(
            [*entities, *places, *categories], MAX_ENTITIES),
        data_sources=_clamp_unique(data_sources, MAX_DATASOURCES),
        required_fields=_clamp_unique(required_fields, MAX_REQUIRED_FIELDS),
        query_terms=_clamp_unique(terms, MAX_QUERY_TERMS),
    )


def _as_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def check_supply_demand(
    needs: KnowledgeNeeds,
    supply: Mapping[str, Any],
) -> list[SupplyDemandGap]:
    """供需一致性校验（SKILL #4 §5.2 规则矩阵，机制级翻译）。

    `supply` 契约（缺键 = 该层无供给 ⇒ 触发对应缺口）：
      - entity_links: Mapping[str, int]    语义实体 → 图谱关联数
      - historical_cases: int              可用先例数
      - embedding_coverage: float          向量覆盖率 0..1
      - data_rows: Mapping[str, int]       数据源 → 行数
      - hitl_checkpoints: Sequence         人工池待办
      - gates: Mapping[str, Any]           红线/闸门状态

    返回**缺口列表**（空 = 配齐）。任一缺口必须由调用方写入 trace，禁止吞。
    """
    gaps: list[SupplyDemandGap] = []
    layers = set(needs.active_layers)

    # L1：每个语义实体须在图谱有 ≥1 关联
    if "L1" in layers and needs.semantic_entities:
        links = supply.get("entity_links") or {}
        orphaned = [e for e in needs.semantic_entities if _as_int(links.get(e)) < 1]
        if orphaned:
            gaps.append(SupplyDemandGap(
                "L1", GAP_MISSING_ENTITY,
                f"{len(orphaned)}/{len(needs.semantic_entities)} 个强实体未入图："
                f"{orphaned[:5]}"))

    # L2：先例数 + 向量覆盖率
    if "L2" in layers:
        cases = _as_int(supply.get("historical_cases"))
        if cases < MIN_PRECEDENTS:
            gaps.append(SupplyDemandGap(
                "L2", GAP_INSUFFICIENT_EXPERIENCE,
                f"先例 {cases} < {MIN_PRECEDENTS}（新域冷启动）"))
        cov = supply.get("embedding_coverage")
        if cov is not None and float(cov) < MIN_EMBEDDING_COVERAGE:
            gaps.append(SupplyDemandGap(
                "L2", GAP_LOW_COVERAGE,
                f"向量覆盖率 {float(cov):.0%} < {MIN_EMBEDDING_COVERAGE:.0%}"))

    # 数据字段：必备源须有 ≥1 行
    if needs.data_sources:
        rows = supply.get("data_rows") or {}
        empty = [s for s in needs.data_sources if _as_int(rows.get(s)) < 1]
        if empty:
            gaps.append(SupplyDemandGap(
                "L2", GAP_MISSING_DATA, f"数据源为空：{empty[:5]}"))

    # L3：HITL 检查点
    if "L3" in layers:
        cps = supply.get("hitl_checkpoints") or []
        if len(list(cps)) < 1:
            gaps.append(SupplyDemandGap(
                "L3", GAP_MISSING_HITL, "人工池无待办（HITL 检查点缺失）"))

    # L4：闸门状态
    if "L4" in layers:
        gates = supply.get("gates") or {}
        if not gates:
            gaps.append(SupplyDemandGap(
                "L4", GAP_MISSING_GATE, "红线/闸门状态未定义"))

    return gaps


def missing_context_dimensions(
    supplied: Mapping[str, Any] | Iterable[str],
) -> list[str]:
    """七维齐全轴：返回**缺失**的维度名（对齐 §4「任一缺失即显式标记，禁 AI 脑补」）。

    `supplied` 可传 dict（判真值）或维度名序列（判成员）。
    """
    if isinstance(supplied, Mapping):
        present = {k for k, v in supplied.items() if v not in (None, "", [], {}, ())}
    else:
        present = set(supplied)
    return [d for d in CONTEXT_DIMENSIONS if d not in present]


__all__ = [
    "KNOWLEDGE_LAYERS", "LAYER_NAMES", "KnowledgeNeeds", "SupplyDemandGap",
    "build_knowledge_needs", "check_supply_demand", "missing_context_dimensions",
    "MAX_ENTITIES", "MAX_DATASOURCES", "MAX_REQUIRED_FIELDS", "MAX_QUERY_TERMS",
    "MIN_PRECEDENTS", "MIN_EMBEDDING_COVERAGE", "CONTEXT_DIMENSIONS",
    "GAP_MISSING_ENTITY", "GAP_INSUFFICIENT_EXPERIENCE", "GAP_LOW_COVERAGE",
    "GAP_MISSING_DATA", "GAP_MISSING_HITL", "GAP_MISSING_GATE",
]
