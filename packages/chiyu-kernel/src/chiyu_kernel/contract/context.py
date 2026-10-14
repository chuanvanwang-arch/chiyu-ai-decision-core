"""上下文契约 —— L0 词汇与不变式（GAP-2，Batch-2a，2026-10-14）。

定位：上下文分层装配（`chiyu_kernel/context/`）的**词汇单一事实源**：
四层模型 / 七维齐全轴 / 供需缺口类型 / 三级降级召回档位 / 机制级上限与阈值。
此前 context 只有 impl 无 sanctioned contract，消费方（APS
`platform/context.py`，enterprise `memory/*`）被迫 import 内部路径
（APS 盘点 §四 GAP-2）。

⛔ 本层零第三方依赖、零 IO、零领域字面量。impl（assembly/knowledge_needs/
   retrieval）改为从本模块导入这些闭集 —— 同名符号是**同一对象**，
   不存在双份漂移；`__all__` 名与 impl 侧保持一致（消费方无感）。
"""
from __future__ import annotations

from typing import Tuple

# ── 四层模型（SKILL #4；顺序即层级，累积语义 level=x → L1..Lx）─────────
CONTEXT_LAYERS: Tuple[str, ...] = ("L1", "L2", "L3", "L4")
#: 层名（中文标签单一事实源；impl 的 LAYER_LABELS_ZH / LAYER_NAMES 均指向本表）。
CONTEXT_LAYER_LABELS_ZH = {
    "L1": "知识底座",   # 实体/本体/字典（图谱一跳 + 实体向量）
    "L2": "历史决策",   # 先例/经验（向量+全文 RRF 召回）
    "L3": "执行协同",   # HITL/审批（结构化直查，无 I/O 失败面）
    "L4": "治理决策",   # 红线/闸门（实时查询，禁缓存）
}
#: 知识层别名（与 CONTEXT_LAYERS 同集；impl knowledge_needs.KNOWLEDGE_LAYERS）。
KNOWLEDGE_LAYERS: Tuple[str, ...] = CONTEXT_LAYERS
#: 默认供给维度（机制默认：dim 键缺省时按此匹配；消费方可覆盖）。
KNOWLEDGE_NEEDS_DEFAULT_DIMS: Tuple[str, ...] = (
    "semantics", "precedent", "operation", "governance")

# ── 七维齐全轴（与深度轴正交；任一缺失即显式标记，禁 AI 脑补）──────────
CONTEXT_DIMENSIONS: Tuple[str, ...] = (
    "identity", "structure", "semantics", "time_config",
    "decision_history", "operational_state", "governance",
)

# ── 需求编码上限（对齐 SKILL #4 第 2 轮编码约束，机制级）───────────────
MAX_ENTITIES: int = 24
MAX_DATASOURCES: int = 16
MAX_REQUIRED_FIELDS: int = 40
MAX_QUERY_TERMS: int = 20

# ── 判据阈值（对齐 SKILL #4 §5.2 规则矩阵，机制级）─────────────────────
MIN_PRECEDENTS: int = 3                # level>=2 → historicalCases >= 3
MIN_EMBEDDING_COVERAGE: float = 0.80   # level>=2 → 向量覆盖率 >= 80%

# ── 供需缺口类型（机制级闭集；显式标注，禁静默吞）─────────────────────
GAP_MISSING_ENTITY = "MISSING_ENTITY"
GAP_INSUFFICIENT_EXPERIENCE = "INSUFFICIENT_EXPERIENCE"
GAP_LOW_COVERAGE = "LOW_COVERAGE"
GAP_MISSING_DATA = "MISSING_DATA"
GAP_MISSING_HITL = "MISSING_HITL"
GAP_MISSING_GATE = "MISSING_GATE"
GAP_KINDS: Tuple[str, ...] = (
    GAP_MISSING_ENTITY, GAP_INSUFFICIENT_EXPERIENCE, GAP_LOW_COVERAGE,
    GAP_MISSING_DATA, GAP_MISSING_HITL, GAP_MISSING_GATE,
)

# ── 三级降级召回档位（顺序即决策优先级；VTIER_* 为向量降级族主名）─────
VTIER_FTS_VECTOR = "fts+vector"  # 一级：FTS 预过滤 + 池内向量排序（理想）
VTIER_VECTOR = "vector"          # 二级：纯向量排序（FTS 0 命中放宽）
VTIER_FTS = "fts"                # 三级：纯 FTS 排序（无向量 / 向量 0 命中）
VTIER_NONE = "none"              # 无候选（池内无语料）
VTIER_ORDER: Tuple[str, ...] = (
    VTIER_FTS_VECTOR, VTIER_VECTOR, VTIER_FTS, VTIER_NONE)
# 弃用别名（旧名仍可用，不破坏既有消费方；deprecation 政策：先 warn 一版再移除）
TIER_FTS_VECTOR = VTIER_FTS_VECTOR
TIER_VECTOR = VTIER_VECTOR
TIER_FTS = VTIER_FTS
TIER_NONE = VTIER_NONE
TIER_ORDER = VTIER_ORDER

# ── 不变式（有守卫测试，不是注释）────────────────────────────────────
CONTEXT_INVARIANTS: Tuple[str, ...] = (
    "gaps_structured_not_swallowed",   # 供需缺口结构化返回，调用方必须显式处理
    "degraded_layers_reported",        # 缺供给的层进 degraded_layers，不静默
    "retrieval_degradation_evidenced",  # 降级必须留痕（tier/coverage/notes）
    "dimensions_checked_complete",     # 七维齐全轴：任一缺失即显式标记
)

__all__ = [
    "CONTEXT_LAYERS", "CONTEXT_LAYER_LABELS_ZH", "KNOWLEDGE_LAYERS",
    "KNOWLEDGE_NEEDS_DEFAULT_DIMS", "CONTEXT_DIMENSIONS",
    "MAX_ENTITIES", "MAX_DATASOURCES", "MAX_REQUIRED_FIELDS", "MAX_QUERY_TERMS",
    "MIN_PRECEDENTS", "MIN_EMBEDDING_COVERAGE",
    "GAP_MISSING_ENTITY", "GAP_INSUFFICIENT_EXPERIENCE", "GAP_LOW_COVERAGE",
    "GAP_MISSING_DATA", "GAP_MISSING_HITL", "GAP_MISSING_GATE", "GAP_KINDS",
    "VTIER_FTS_VECTOR", "VTIER_VECTOR", "VTIER_FTS", "VTIER_NONE", "VTIER_ORDER",
    "TIER_FTS_VECTOR", "TIER_VECTOR", "TIER_FTS", "TIER_NONE", "TIER_ORDER",
    "CONTEXT_INVARIANTS",
]
