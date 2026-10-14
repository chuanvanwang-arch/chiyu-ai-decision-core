"""P2-1 真向量通道守卫（内核版）—— 抽取自 demo `tests/test_vector_channel.py`。

⛔ **T3 抽取范围**：demo 版大量用例依赖 `MemoryStore`（T5′ memory 抽取）与真 PG，
   当前内核**尚无 memory 包**，故仅保留**不依赖 memory/PG、能独立运行**的核心断言：

   1. `provider_info()` 配置态/运行态分离 + `degraded` 反假绿（F1 可观测性骗人）；
   2. `embedding_api.error_class` 402/401/429 归因（拒绝合并 4xx）；
   3. 维度纪律的**纯函数**部分：`index_vector.tag_for_dim` 补零可/截断禁（配合
      `test_pad_ledger.py` 的 resolve 级验证）。

   依赖 MemoryStore/PG 的「真向量落库打标 / 覆盖率 / backfill 端到端」用例，
   待 T5′ 抽取 memory 后补全（`TODO-T5prime` 标注）。本文件不得伪造这些能力为绿。

⛔ 所有"真向量可用"路径用 monkeypatch 离线模拟（不碰真实 SiliconFlow、不出网）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.vector import embedding_api, index_vector


# ── 1. provider_info 配置态/运行态分离（修 F1 可观测性骗人）────────────
def test_provider_info_config_vs_effective(monkeypatch):
    # 复位运行态
    monkeypatch.setattr(embedding_api, "_LAST_PROVIDER", "unknown")
    monkeypatch.setattr(embedding_api, "LAST_ERROR", None)
    monkeypatch.delenv("CHIYU_EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("CHIYU_EMBEDDING_ALLOW_NETWORK", raising=False)
    # 默认（无 key / 未放行）⇒ 未配置
    info = embedding_api.provider_info()
    assert info["api_key_configured"] is False
    assert info["provider"] == "hash"
    assert info["effective_provider"] == "unknown"
    assert info["degraded"] is False
    for k in ("effective_provider", "degraded", "error_class", "last_error"):
        assert k in info

    # 配了 key 且真向量成功
    monkeypatch.setenv("CHIYU_EMBEDDING_API_KEY", "sk-x")
    monkeypatch.setenv("CHIYU_EMBEDDING_ALLOW_NETWORK", "1")
    monkeypatch.setattr(embedding_api, "available", lambda: True)
    monkeypatch.setattr(embedding_api, "embed",
                        lambda text: (embedding_api.__dict__.__setitem__("_LAST_PROVIDER", "model") or
                                      embedding_api.__dict__.__setitem__("LAST_ERROR", None) or
                                      [0.01] * 1024))
    embedding_api.embed("probe")
    info = embedding_api.provider_info()
    assert info["api_key_configured"] is True
    assert info["provider"] == "api"
    assert info["effective_provider"] == "model"
    assert info["degraded"] is False

    # 配了 key 但 embed 失败（402 类）→ 配置态仍是 api，运行态显形为 hash 且 degraded=True
    msg = "Embedding HTTP 402：Insufficient balance (payment required)"
    monkeypatch.setattr(embedding_api, "embed",
                        lambda text: (embedding_api.__dict__.__setitem__("_LAST_PROVIDER", "hash") or
                                      embedding_api.__dict__.__setitem__("LAST_ERROR", msg) or
                                      None))
    embedding_api.embed("probe")
    info = embedding_api.provider_info()
    assert info["api_key_configured"] is True
    assert info["provider"] == "api"          # 配置态：确实配了
    assert info["effective_provider"] == "hash"  # 运行态：实际没用上
    assert info["degraded"] is True           # ⛔ 这一行原缺陷里永远 False


# ── 2. error_class 归因：402 单列，不并入 4xx ──────────────────────────
def test_error_class_attributes_402_separately():
    """`http-402 余额不足` 必须单列 payment_required（处置动作不同：去充值而非改配置）。"""
    assert embedding_api.error_class("Embedding HTTP 402: Payment Required") == "payment_required"
    assert embedding_api.error_class("HTTP 401 unauthorized") == "auth_failed"
    assert embedding_api.error_class("HTTP 429 rate limit exceeded") == "rate_limited"
    assert embedding_api.error_class("Model not exist") == "model_unavailable"
    assert embedding_api.error_class("timed out after 20s") == "timeout"
    assert embedding_api.error_class("") is None          # 没失败过 ⇒ None（≠ unknown）


# ── 3. 维度纪律纯函数：补零可（model-p{n}）、截断禁（None）─────────────
def test_tag_for_dim_pads_below_and_rejects_above():
    """短于列维 ⇒ 'model-p{n}'（合法补零）；等于 ⇒ 'model'；超列维 ⇒ None（禁截断）。"""
    assert index_vector.tag_for_dim(512, column_dim=1024) == "model-p512"
    assert index_vector.tag_for_dim(1024, column_dim=1024) == "model"
    assert index_vector.tag_for_dim(2048, column_dim=1024) is None
    assert index_vector.tag_for_dim(0, column_dim=1024) is None
    assert index_vector.is_padded_tag("model-p512") is True
    assert index_vector.is_padded_tag("model") is False
    assert index_vector.is_padded_tag(None) is False


# ── TODO-T5prime（依赖 MemoryStore + PG，T5′ 后补全，不得在此伪造绿）：──
#   test_real_vector_lands_and_is_tagged / test_fallback_hash_has_no_tag /
#   test_dim_below_column_is_padded_and_tagged / test_dim_over_column_is_refused_not_truncated /
#   test_backfill_reembeds_unmarked / test_backfill_skips_when_embed_down
