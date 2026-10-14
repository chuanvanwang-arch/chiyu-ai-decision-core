"""离线向量内核 —— 零 torch、可离线交付。

抽取自 demo `features/{onnx_runner,index_vector,embedding_api,infer}.py` +
`ontology/embedding.py`（2026-09-21，P1 T3）。包路径改写；零领域字面量。

⛔ 三条既有纪律（有守卫测试，不得改）：
  1. 解析顺序 = 本地 ONNX 优先 → 云端 API（须显式放行出网）→ 哈希降级。
  2. 返回三元组 (vec, tag, err)：tag='model'|'model-p{n}'|None；None ⇒ 调用方降级哈希并留痕。
  3. 超列维不得截断 ⇒ 视为取不到、走哈希。

出网闸（D3）：`CHIYU_EMBEDDING_ALLOW_NETWORK` 默认 `0` = 禁出网。交付物默认离线安全。
"""
from .coverage import (
    DEFAULT_MIN_COVERAGE,
    HASH_PROVIDER,
    CoverageReport,
    backfill_plan,
    compute_coverage,
)
from .index_vector import available, backend, info, is_padded_tag, resolve, tag_for_dim
from .infer import (
    HASH_DIM,
    InferBackend,
    cosine,
    hash_signature,
    stable_stringify,
    content_hash,
    hash_vector,
)
from .onnx_runner import (
    OnnxRunner,
    OnnxUnavailable,
    artifact_info,
    clear_cache,
    config_dim,
    get_runner,
    is_available,
    resolve_model_dir,
)

__all__ = [
    "OnnxRunner", "OnnxUnavailable", "get_runner", "is_available",
    "resolve_model_dir", "artifact_info", "config_dim", "clear_cache",
    "InferBackend", "HASH_DIM", "hash_signature", "cosine",
    "stable_stringify", "content_hash", "hash_vector",
    "available", "backend", "resolve", "tag_for_dim", "is_padded_tag", "info",
    "CoverageReport", "compute_coverage", "backfill_plan",
    "DEFAULT_MIN_COVERAGE", "HASH_PROVIDER",
]
