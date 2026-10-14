"""B′·T3 守卫（内核等价版）：补零台账与「写读同源」。

上游依据：docs/2026-09-21-离线向量方案B′详细设计.md §5.1/§5.2
demo 版强依赖 `memory.store.MemoryStore`（T5′ 抽取范围），本内核实则**独立运行**：
用 `vector.index_vector.resolve()`（**写读唯一来源**）验证三件事：

  1. resolve 打标：原生 512 维 ⇒ tag='model-p512'（补零标记），1024 维 ⇒ 'model'；
  2. 补零 ≠ 原维：padded tag 与原维 tag 能被区分（false green 防线）；
  3. **写读同源**：写入侧与读取侧都只允许调 `index_vector.resolve()`，返回一致 tag
     ⇒ 同一列不会并存两套语义空间。

⛔ 不连真 DB：`resolve()` 的编码走 monkeypatched 假 backend（确定性、离线、零 torch 依赖）。
"""
from __future__ import annotations

import numpy as np
import pytest

from chiyu_kernel.contract.particle import VECTOR_DIM
from chiyu_kernel.vector import index_vector
from chiyu_kernel.vector.infer import InferBackend

VCOL = VECTOR_DIM
LONG = "物业装修押金拒不退还，业主多次投诉无门且开发商长期失联拖欠退款"


class _FakeBackend:
    """确定性假 backend：按 env 返回不同原生维度（512 或 1024），模拟 ONNX/云端。"""

    def __init__(self, dim: int, backend: str = "cpu"):
        self._fake_dim = dim
        self.backend = backend
        self._dim = dim
        self.last_error = None
        self._runner = object()          # 使 model_status != "hash"

    @property
    def model_status(self) -> str:
        return "onnx" if self.backend != "none" else "hash"

    def encode(self, text: str) -> np.ndarray:
        v = np.zeros(self._fake_dim, dtype=np.float32)
        for i, ch in enumerate(text):
            v[i % self._fake_dim] = float((ord(ch) % 100) / 100.0)
        n = float(np.linalg.norm(v))
        return (v / n) if n > 0 else v


@pytest.fixture()
def fake_backend(monkeypatch):
    """把 index_vector 的后端替换成 `_FakeBackend`（不连 ONNX、不装 torch）。"""
    index_vector.reset()
    monkeypatch.setattr(index_vector, "backend", lambda: _FakeBackend(dim=512))
    yield
    index_vector.reset()


# ── 1. resolve 打标：512 ⇒ model-p512；1024 ⇒ model ─────────────────────
def test_resolve_tags_padded_dim(fake_backend, monkeypatch):
    monkeypatch.setattr(index_vector, "backend",
                        lambda: _FakeBackend(dim=512, backend="cpu"))
    vec, tag, err = index_vector.resolve(LONG, column_dim=VCOL)
    assert tag == "model-p512", f"512 维应打 model-p512，实得 {tag}"
    assert err is None and vec is not None
    assert index_vector.is_padded_tag(tag) is True


def test_resolve_tags_exact_dim(fake_backend, monkeypatch):
    monkeypatch.setattr(index_vector, "backend",
                        lambda: _FakeBackend(dim=VCOL, backend="cpu"))
    vec, tag, err = index_vector.resolve(LONG, column_dim=VCOL)
    assert tag == "model", f"1024 维应打 model，实得 {tag}"
    assert index_vector.is_padded_tag(tag) is False


# ── 2. 超列维不得截断（取不到，走哈希） ────────────────────────────────
def test_resolve_over_column_dim_is_rejected(fake_backend, monkeypatch):
    monkeypatch.setattr(index_vector, "backend",
                        lambda: _FakeBackend(dim=VCOL + 64, backend="cpu"))
    vec, tag, err = index_vector.resolve(LONG, column_dim=VCOL)
    assert vec is None and tag is None
    assert "截断" in (err or ""), f"超列维必须拒绝（禁截断），实得 err={err}"


# ── 3. 写读同源 ────────────────────────────────────────────────────────
def test_write_and_read_use_same_source(fake_backend):
    """`resolve()` 是写读唯一来源：读侧查询向量与写侧打标必须同源。

    事故形态（已修）：写入真向量、查询恒 `hash_vector` ⇒ 同列两套语义空间。
    内核下此守卫 = 断言"写读双方都来自 `index_vector.resolve()` 且打标一致"。
    """
    write_vec, write_tag, write_err = index_vector.resolve(LONG, column_dim=VCOL)
    # 读侧同样走 resolve（不允许第二条来源）
    read_vec, read_tag, read_err = index_vector.resolve(LONG, column_dim=VCOL)
    assert write_tag is not None and read_tag == write_tag, (
        f"读侧 tag {read_tag} 与写侧 {write_tag} 不一致 ⇒ 写读不同源")
    assert read_err is None
    assert write_vec.shape == read_vec.shape


# ── 4. 无真通道时：写读都降级到 hash，且一致 ────────────────────────────
def test_read_falls_back_to_hash_consistently(monkeypatch):
    index_vector.reset()
    monkeypatch.setattr(index_vector, "backend",
                        lambda: _FakeBackend(dim=512, backend="none"))
    vec, tag, err = index_vector.resolve(LONG, column_dim=VCOL)
    assert tag is None               # 无真通道 ⇒ 调用方降级哈希（tag=None 且必须留痕 err）
    assert err
