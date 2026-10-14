"""本体层 —— 粒子运行时形态 + 写时三钩子 + 受控关系图（L0/L1）。

抽取自 demo `ontology/{particle,hooks,graph,backfill}.py`（2026-09-21，P1 T4）。
⛔ 领域无关：粒子字段名去领域化；受控边由消费方注入的 `profile.predicates` 提供；
主体名归一的后缀规则由调用方注入（内核不携带任何单域默认）。
"""
from .backfill import BackfillChannel
from .graph import OntologyGraph, normalize
from .hooks import ensure_embedding, ensure_tsvector, ontology_sync
from .particle import Particle

__all__ = [
    "Particle",
    "OntologyGraph",
    "normalize",
    "ensure_embedding",
    "ensure_tsvector",
    "ontology_sync",
    "BackfillChannel",
]
