"""索引向量的**单一事实源**：写（memory store）与读（recall）必须走同一解析。

为什么要单独成模块（而不是各自拼装）：
    旧的写入侧调 `embedding_api.embed()`（云端），读取侧调 `hash_vector(query)`
    ⇒ **同一列里并存两种语义空间**，检索"能跑但结果无意义"。
    模块化后 store/recall 都只调本模块，任何一侧想"顺手换个来源"都会立刻在
    tests/test_pad_ledger.py::test_write_and_read_use_same_source 上暴露。

解析顺序 = `InferBackend` 的 `auto` 语义（**本地优先**）：
    本地 ONNX → 云端 API（须显式放行出网）→ 本机 torch → 无（降级哈希）

返回三元组 `(vec, tag, err)`：
    vec  = `np.float32` 原始维度向量（**未补零**；补零是落库方的事）或 None
    tag  = `'model'`       真向量且维度恰好等于列维
           `'model-p{n}'`  真向量且原生维度 n < 列维 ⇒ 落库前须显式补零（余弦等价）
           None            取不到真向量 ⇒ 调用方降级哈希（**必须留痕**）
    err  = 拒因（云端 402/超时、ONNX 缺失…），供反静默上报；成功时为 None

⛔ 超列维（n > VECTOR_DIM）**不得截断**（截断 = 主动损毁判别力）⇒ 视为取不到，走哈希。
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from chiyu_kernel.contract.particle import HASH_DIM

from . import embedding_api
from .infer import InferBackend

_backend: Optional[InferBackend] = None


def backend() -> InferBackend:
    """进程级单例。构造走 `InferBackend()`（**不传 backend**）⇒ 跟随 env `INFER_BACKEND`。

    ⛔ 必须用默认参数（None）：显式传 "auto" 会读 env（语义等价），但显式传具体值会
       让测试与部署配置失效。默认 None 是本模块"配置驱动"的落点。
    """
    global _backend
    if _backend is None:
        _backend = InferBackend()
    return _backend


def reset() -> None:
    """仅供测试/自检：丢弃单例（配合 env 变更必须清，否则旧解析结果会粘住）。"""
    global _backend
    _backend = None


def tag_for_dim(n: int, column_dim: int) -> Optional[str]:
    """维度 → 打标。⛔ 超列维返回 None（调用方据此坚决退回哈希，不许截断凑列）。"""
    if n == column_dim:
        return "model"
    if 0 < n < column_dim:
        return f"model-p{n}"
    return None


def is_padded_tag(tag: Optional[str]) -> bool:
    return bool(tag) and tag.startswith("model-p")


def resolve(text: str, *, column_dim: int) -> tuple[Optional[np.ndarray], Optional[str], Optional[str]]:
    """解析索引向量。**这是 store 与 recall 唯一允许的来源。**"""
    be = backend()
    if be.model_status == "hash":
        # 无任何真向量通道（未配置 / 已降级）⇒ 调用方走哈希，err 说明为什么
        return None, None, be.last_error or "no_real_vector_channel"
    vec = np.asarray(be.encode(text), dtype=np.float32)
    if be.backend == "none":
        # encode 期间降级（如云端 402 / ONNX 推理异常）：本次用不了真向量，且后端已转 none
        return None, None, be.last_error or "channel_degraded_midway"
    if vec.ndim != 1 or vec.shape[0] <= 0:
        return None, None, f"bad_vector_shape:{vec.shape}"
    if not np.any(vec):
        return None, None, "all_zero_vector"
    tag = tag_for_dim(int(vec.shape[0]), column_dim)
    if tag is None:
        return None, None, (f"dim_over_column:{vec.shape[0]}>{column_dim}"
                            f"（禁止截断；改用哈希并在 provider_info 暴露）")
    return vec, tag, None


def available(*, column_dim: int) -> bool:
    """是否存在可用真向量通道（供 backfill 的准入闸；不实际编码）。"""
    be = backend()
    return be.model_status != "hash"


def info() -> dict:
    """可观测性：索引通道当前来自哪里（写进 coverage 报告，避免"不知道用了什么"）。"""
    be = backend()
    return {"backend": be.backend, "model_status": be.model_status, "vector_dim": be._dim,
            "last_error": be.last_error, "hash_dim": HASH_DIM}
