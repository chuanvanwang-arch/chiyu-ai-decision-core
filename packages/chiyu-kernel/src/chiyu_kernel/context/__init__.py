"""上下文层 —— 需求侧编码 + L1-L4 装配 + 三级降级召回（L0/L1）。

抽取自 demo `context/{knowledge_needs,retrieval}.py` + 新增 `assembly.py`
（SKILL #4 上下文分层的机制化，2026-09-21，P1 T4）。
⛔ `timeline.py` 不搬迁 —— 属 demo 应用层（群诉时间线语义），内核只提供
`assembly` 这一**机制**。
"""
from .assembly import (
    AssemblyResult,
    CONTEXT_LAYERS,
    KNOWLEDGE_NEEDS_DEFAULT_DIMS,
    KnowledgeNeed,
    LAYER_LABELS_ZH,
    SupplyReport,
    assemble,
)
from .knowledge_needs import (
    MAX_DATASOURCES,
    MAX_ENTITIES,
    MAX_QUERY_TERMS,
    MAX_REQUIRED_FIELDS,
    MIN_EMBEDDING_COVERAGE,
    MIN_PRECEDENTS,
    CONTEXT_DIMENSIONS,
    GAP_INSUFFICIENT_EXPERIENCE,
    GAP_LOW_COVERAGE,
    GAP_MISSING_DATA,
    GAP_MISSING_ENTITY,
    GAP_MISSING_GATE,
    GAP_MISSING_HITL,
    KnowledgeNeeds,
    KNOWLEDGE_LAYERS,
    LAYER_NAMES,
    SupplyDemandGap,
    build_knowledge_needs,
    check_supply_demand,
    missing_context_dimensions,
)
from .retrieval import (
    RecalledItem,
    RetrievalEvidence,
    RetrievalResult,
    TIER_FTS,
    TIER_FTS_VECTOR,
    TIER_NONE,
    TIER_ORDER,
    TIER_VECTOR,
    VTIER_FTS,
    VTIER_FTS_VECTOR,
    VTIER_NONE,
    VTIER_ORDER,
    VTIER_VECTOR,
    degraded_recall,
    to_supply_layer,
)
from .fuse import RRF_K_DEFAULT, rrf_fuse  # noqa: E401  T42：多源 RRF 融合
from .recall_memory import (  # noqa: E401  T41：记忆召回消费点（写了能读）
    RECALL_FRAME_PREDICATE, RECALL_REFERENCE_PREDICATE,
    build_memory_recaller, recall_precedents,
)

__all__ = [
    # assembly
    "CONTEXT_LAYERS", "KnowledgeNeed", "SupplyReport", "AssemblyResult",
    "assemble", "LAYER_LABELS_ZH", "KNOWLEDGE_NEEDS_DEFAULT_DIMS",
    # knowledge_needs
    "KNOWLEDGE_LAYERS", "LAYER_NAMES", "KnowledgeNeeds", "SupplyDemandGap",
    "build_knowledge_needs", "check_supply_demand", "missing_context_dimensions",
    "MAX_ENTITIES", "MAX_DATASOURCES", "MAX_REQUIRED_FIELDS", "MAX_QUERY_TERMS",
    "MIN_PRECEDENTS", "MIN_EMBEDDING_COVERAGE", "CONTEXT_DIMENSIONS",
    "GAP_MISSING_ENTITY", "GAP_INSUFFICIENT_EXPERIENCE", "GAP_LOW_COVERAGE",
    "GAP_MISSING_DATA", "GAP_MISSING_HITL", "GAP_MISSING_GATE",
    # retrieval
    "VTIER_FTS_VECTOR", "VTIER_VECTOR", "VTIER_FTS", "VTIER_NONE", "VTIER_ORDER",
    "TIER_FTS_VECTOR", "TIER_VECTOR", "TIER_FTS", "TIER_NONE", "TIER_ORDER",
    "RecalledItem", "RetrievalEvidence", "RetrievalResult",
    "degraded_recall", "to_supply_layer",
    # T41：记忆召回消费点（记忆网回链 + 双轨 NOTE 两源 → 三级降级）
    "RECALL_REFERENCE_PREDICATE", "RECALL_FRAME_PREDICATE",
    "recall_precedents", "build_memory_recaller",
    # T42：多源 RRF 融合（跨源量纲不同，用名次而非分数）
    "RRF_K_DEFAULT", "rrf_fuse",
]
