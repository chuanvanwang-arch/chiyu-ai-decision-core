"""上下文装配（L1–L4）+ KnowledgeNeeds 供需校验（★ 新增，demo 未收敛）。

四层语义（SKILL #4）：
    L1 知识底座      静态领域知识（本体 / 受控词表 / 规格）
    L2 历史决策      先例（含**反面先例** —— 第 9 尺 fairmess 的输入）
    L3 执行协同      任务态 / 派发 / 编排上下文
    L4 治理决策      红线 / 审批 / 权限 / 合规

⛔ 供需一致性校验（为什么必须可失败）
────────────────────────────────────
第 9 尺的 relevance 尺算的是「所需维度 ∩ 已供给维度」。若供给表能静默缺少
某层（例如反例只在"检索到了"但从未"被消费"），relevance 会在**看起来正常**的
情况下恒得低分——这正是 demo 里"评分被降级为叙述留痕"的同族缺陷。
故 assemble() 返回 `supply_report`，缺口以**结构化字段**给出，调用方必须显式处理。

⛔ 零领域词：本模块只声明机制，不声明任何领域取值（无"群诉/工单/粒子"字面量）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

# Batch-2a（GAP-2）：四层模型 / 层名 / 默认供给维度上收
# `chiyu_kernel/contract/context.py`（sanctioned 契约面单一事实源）。
from chiyu_kernel.contract.context import (
    CONTEXT_LAYERS,
    CONTEXT_LAYER_LABELS_ZH,
    KNOWLEDGE_NEEDS_DEFAULT_DIMS,
)

# 兼容别名（旧名仍可用，deprecation 政策：先 warn 一版再移除）
LAYER_LABELS_ZH = CONTEXT_LAYER_LABELS_ZH


@dataclass(frozen=True)
class KnowledgeNeed:
    """需求侧编码：本决策需要哪一层、哪几个维度、哪个键。"""

    layer: str
    dims: tuple = ()
    key: str = ""

    def __post_init__(self) -> None:
        if self.layer not in CONTEXT_LAYERS:
            raise ValueError(f"layer 须 ∈ {CONTEXT_LAYERS}：{self.layer!r}")


@dataclass
class SupplyReport:
    required: tuple = ()
    supplied: tuple = ()
    missing: tuple = ()
    degraded_layers: tuple = ()

    @property
    def consistent(self) -> bool:
        return not self.missing

    def as_metrics(self) -> Mapping[str, float]:
        req = len(self.required)
        hit = req - len(self.missing)
        return {
            "context_supply_rate": round(hit / req, 4) if req else 1.0,
            "context_missing": float(len(self.missing)),
            "context_degraded_layers": float(len(self.degraded_layers)),
        }


@dataclass
class AssemblyResult:
    facts: dict = field(default_factory=dict)
    supply_report: SupplyReport = field(default_factory=SupplyReport)


def assemble(needs: Sequence[KnowledgeNeed],
             provided: Mapping[str, Iterable]) -> AssemblyResult:
    """按需装配。

    needs    KnowledgeNeed 序列（需求侧，由调用方按场景声明）
    provided {layer: [{"dim":..., "key":..., "value":...}, ...]}（供给侧）
    返回    facts + supply_report（缺口**结构化**返回，不吞不糊）
    """
    facts: dict = {}
    supplied_keys: list = []
    missing: list = []
    degraded: list = []
    for need in needs:
        rows = list(provided.get(need.layer) or [])
        if not rows:
            degraded.append(need.layer)
        hit = [r for r in rows
               if (not need.dims or _dim_of(r) in need.dims)
               and (not need.key or r.get("key") == need.key)]
        if hit:
            supplied_keys.append((need.layer, need.key))
            for r in hit:
                facts.setdefault(need.layer, []).append(r.get("value"))
        else:
            missing.append((need.layer, need.key))
    return AssemblyResult(
        facts=facts,
        supply_report=SupplyReport(
            required=tuple((n.layer, n.key) for n in needs),
            supplied=tuple(supplied_keys),
            missing=tuple(missing),
            degraded_layers=tuple(degraded),
        ),
    )


def _dim_of(row: Mapping) -> str:
    d = row.get("dim")
    if isinstance(d, dict):
        return d.get("key") or d.get("dim") or ""
    return d or ""


__all__ = ["CONTEXT_LAYERS", "LAYER_LABELS_ZH", "KNOWLEDGE_NEEDS_DEFAULT_DIMS",
           "KnowledgeNeed", "SupplyReport", "AssemblyResult", "assemble"]
