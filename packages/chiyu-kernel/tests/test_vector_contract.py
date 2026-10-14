"""GAP-3 向量契约守卫（Batch-2a，2026-10-14）。

判据面：
  · 契约后端闭集 = impl 可解析值（每个档位显式构造不炸、不越界）；
  · 模型状态口径在契约闭集内（/healthz 唯一取值点不漂移）；
  · 维度纪律与出网闸键名在契约内。
"""
from __future__ import annotations

from chiyu_kernel.contract import vector as vec_contract
from chiyu_kernel.contract.particle import HASH_DIM as PARTICLE_HASH_DIM
from chiyu_kernel.contract.particle import VECTOR_DIM as PARTICLE_VECTOR_DIM
from chiyu_kernel.vector import InferBackend


def test_backend_closed_set_matches_impl_resolution():
    # 契约闭集即 impl 合法取值：逐档显式构造（删档位 ⇒ 本判据红）
    for b in vec_contract.EMBEDDING_BACKENDS:
        ib = InferBackend(b)
        assert ib.backend in vec_contract.EMBEDDING_BACKENDS


def test_model_status_within_contract_set():
    ib = InferBackend("none")
    assert ib.model_status == "hash"
    assert "hash" in vec_contract.EMBEDDING_MODEL_STATUS
    info = ib.model_info()
    assert info["model_status"] in vec_contract.EMBEDDING_MODEL_STATUS


def test_resolution_order_local_first_network_gated():
    assert vec_contract.EMBEDDING_RESOLUTION_ORDER[0] == "onnx_local"
    assert vec_contract.EMBEDDING_RESOLUTION_ORDER[-1] == "hash_degrade"
    assert vec_contract.EMBEDDING_NETWORK_ENV == "CHIYU_EMBEDDING_ALLOW_NETWORK"


def test_dim_invariants_present():
    assert "no_truncation" in vec_contract.EMBEDDING_DIM_INVARIANTS
    assert "exact_dim_or_explicit_pad" in vec_contract.EMBEDDING_DIM_INVARIANTS


def test_dims_reexported_from_particle():
    # 契约 vector 族的维度口径再导出自 particle（不制造第二份）
    assert vec_contract.HASH_DIM == PARTICLE_HASH_DIM
    assert vec_contract.VECTOR_DIM == PARTICLE_VECTOR_DIM
