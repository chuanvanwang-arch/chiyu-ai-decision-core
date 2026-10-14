"""B′·T2 守卫（内核版）：离线 ONNX 后端接线（auto 本地优先 / 构造期自证 / 反假绿）。

抽取自 demo `tests/test_offline_onnx_backend.py`（P1 T3 Step 4）。改 import 为内核包路径；
**排除** demo 专属的 `test_pipeline_backend_auto_follows_env`（依赖 `chiyu_group.pipeline`，
应用层测试，不属于内核）。其余逐字保留。

要钉死的四件事（每一件都对应一种"看起来在工作其实没有"的形态）：
  1. `auto` 本地优先（D1）：有本地 ONNX 就不许先撞外网；
  2. 产物不在时不得谎报：model_status 必须回落 hash；
  3. 构造期自证：坏产物必须在构造时抛错；
  4. 语义能力真的在：同义改写相似度必须显著高于无关文本。

环境口径：逐用例解冻 `CHIYU_TEST`（否则 `auto` 恒哈希）。
"""
from __future__ import annotations

import json
import os
import shutil

import numpy as np
import pytest

from chiyu_kernel.vector import onnx_runner
from chiyu_kernel.vector.infer import HASH_DIM, InferBackend, cosine

MODEL_DIR = onnx_runner.resolve_model_dir()
ARTIFACT = os.path.join(MODEL_DIR, onnx_runner.DEFAULT_ONNX)
TOKENIZER = os.path.join(MODEL_DIR, onnx_runner.DEFAULT_TOKENIZER)


@pytest.fixture(autouse=True)
def _unfreeze(monkeypatch):
    monkeypatch.delenv("CHIYU_TEST", raising=False)
    monkeypatch.delenv("INFER_BACKEND", raising=False)
    monkeypatch.delenv("CHIYU_EMBEDDING_ALLOW_NETWORK", raising=False)
    monkeypatch.delenv("CHIYU_EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("CHIYU_MODEL_DIR", raising=False)
    onnx_runner.clear_cache()


def _need_artifact():
    if not (os.path.isfile(ARTIFACT) and os.path.isfile(TOKENIZER)):
        pytest.skip(f"缺 ONNX 产物（{ARTIFACT}）：先跑 tools/export_bge_onnx.py。"
                    f"**不要**把 skip 当绿——离线环境没有第二来源")


# ── 1. D1：auto 本地优先 ────────────────────────────────────────────────

def test_auto_picks_local_onnx(monkeypatch):
    _need_artifact()
    monkeypatch.setenv("CHIYU_EMBEDDING_API_KEY", "sk-should-not-be-used")
    monkeypatch.setenv("CHIYU_EMBEDDING_ALLOW_NETWORK", "1")   # 即便放行出网，也要先选本地
    be = InferBackend(backend="auto")
    assert be.backend == "cpu", f"auto 未优先本地 ONNX，实得 {be.backend}"
    assert be.model_status == "onnx"
    assert be._dim == 512
    info = be.model_info()
    assert info["vector_dim"] == 512 and info["column_dim"] >= 512
    assert info["padded"] is True, "512 < 列维 ⇒ 必须标记'落库需补零'"


def test_encode_offline_is_real_and_semantic(monkeypatch):
    """离线编码：512 维、非零、已归一化，且**同义改写显著高于无关文本**。"""
    _need_artifact()
    be = InferBackend(backend="cpu")
    v1 = be.encode("工地夜间施工噪音扰民")
    v2 = be.encode("晚上工地施工太吵了")
    v3 = be.encode("公园座椅损坏无人修")
    assert v1.shape == (512,) and v1.dtype == np.float32
    assert float(np.linalg.norm(v1)) == pytest.approx(1.0, abs=1e-5)
    assert np.any(v1)
    near, far = cosine(v1, v2), cosine(v1, v3)
    assert near > far + 0.10, (
        f"语义能力异常：同义改写 sim={near:.4f} 未显著高于无关 sim={far:.4f}"
        f"（哈希向量才会出现这种塌陷）")
    assert be.last_error is None


# ── 2. 反假绿：产物不在 ⇒ 必须回落 hash ─────────────────────────────────

def test_missing_artifact_reports_hash_not_onnx(tmp_path, monkeypatch):
    """模型目录里没有产物时，auto 必须回落 `hash` 且如实上报。"""
    empty = tmp_path / "models-empty"
    empty.mkdir()
    monkeypatch.setenv("CHIYU_MODEL_DIR", str(empty))
    onnx_runner.clear_cache()
    assert onnx_runner.is_available(str(empty)) is False
    be = InferBackend(backend="auto")
    assert be.backend not in ("cpu", "cuda", "ascend", "api"), (
        f"无产物却选了 {be.backend} —— 后端选择依据失效")
    assert be.model_status == "hash"
    assert be._dim == HASH_DIM
    v = be.encode("工地夜间施工噪音扰民")
    assert v.shape == (HASH_DIM,) and float(np.linalg.norm(v)) == pytest.approx(1.0, abs=1e-5)


def test_is_available_negative_when_files_missing(tmp_path):
    d = tmp_path / "m"
    d.mkdir()
    assert onnx_runner.is_available(str(d)) is False
    (d / onnx_runner.DEFAULT_TOKENIZER).write_bytes(b"{}")     # 只有分词器
    assert onnx_runner.is_available(str(d)) is False
    (d / onnx_runner.DEFAULT_ONNX).write_bytes(b"garbage")     # 有 ONNX 但内容是垃圾
    assert onnx_runner.is_available(str(d)) is True, (
        "is_available 应只做廉价存在性判断；内容合法性由构造期自证负责")


# ── 3. 构造期自证：坏产物必须当场炸 ─────────────────────────────────────

def test_bogus_onnx_raises_at_construction(tmp_path):
    """坏 onnx 不可能"加载成功但一跑就错"：`OnnxRunner()` 必须当场抛 OnnxUnavailable。"""
    if not os.path.isfile(TOKENIZER):
        pytest.skip("缺 tokenizer.json")
    d = tmp_path / "bad"
    d.mkdir()
    shutil.copy(TOKENIZER, d / onnx_runner.DEFAULT_TOKENIZER)
    (d / onnx_runner.DEFAULT_ONNX).write_bytes(b"\x00" * 1024)
    with pytest.raises(onnx_runner.OnnxUnavailable):
        onnx_runner.OnnxRunner(str(d))
    # 上层必须 fail-open 到哈希，而不是把异常冒给主流程
    be = InferBackend(backend="cpu", model_dir=str(d))
    assert be.backend == "none" and be.model_status == "hash"
    assert be.last_error and "ONNX" in be.last_error


def test_runner_dim_matches_config_json(tmp_path):
    """`config.json.hidden_size` 与图实际输出维度不一致 ⇒ 必须拒（产物/配置错配）。"""
    _need_artifact()
    d = tmp_path / "mismatch"
    d.mkdir()
    shutil.copy(TOKENIZER, d / onnx_runner.DEFAULT_TOKENIZER)
    shutil.copy(ARTIFACT, d / onnx_runner.DEFAULT_ONNX)
    (d / onnx_runner.DEFAULT_CONFIG).write_text(
        json.dumps({"hidden_size": 768}), encoding="utf-8")
    with pytest.raises(onnx_runner.OnnxUnavailable) as e:
        onnx_runner.OnnxRunner(str(d))
    assert "768" in str(e.value)


# ── 4. 测试基线冻结本身也要有守卫 ───────────────────────────────────────

def test_auto_follows_env_backend(monkeypatch):
    """`backend="auto"` 必须**跟随** env `INFER_BACKEND`；显式具体值必须**覆盖** env。"""
    monkeypatch.setenv("INFER_BACKEND", "none")
    assert InferBackend(backend="auto").backend == "none", "auto 未跟随 env（死配置回归）"
    assert InferBackend().backend == "none"
    # 显式具体值优先于 env —— 测试隔离（大量用例显式传 backend）依赖这条
    assert InferBackend(backend="api").backend == "api"


def test_chiyu_test_freezes_to_hash(monkeypatch):
    """`CHIYU_TEST=1` ⇒ auto 一律哈希（全量用例的簇数/并入数依赖这条）。"""
    _need_artifact()
    monkeypatch.setenv("CHIYU_TEST", "1")
    be = InferBackend(backend="auto")
    assert be.backend == "none" and be.model_status == "hash"
    assert be._dim == HASH_DIM
