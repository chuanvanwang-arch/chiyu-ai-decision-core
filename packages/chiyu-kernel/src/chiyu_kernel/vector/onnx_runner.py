"""离线 ONNX 向量推理通道（方案 B′ 主通道）。

抽取自 demo `features/onnx_runner.py`（2026-09-21，P1 T3）。包路径改写；零 torch 不变。

三条硬约束：
  1. **零 torch / 零 transformers / 零出网**。只允许 `onnxruntime` + `tokenizers`。
  2. **池化口径与 `infer.InferBackend._encode_local` 逐位对齐**：CLS（第 0 个 token）+ L2 归一化。
  3. **构造期自证**：`OnnxRunner()` 构造成功 ⇒ 已经跑通一次真实推理并核对过输出维度。

失败一律抛 `OnnxUnavailable`；**降级决策留给调用方**（InferBackend fail-open 到哈希），
本模块不静默吞错、不返回零向量。
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import numpy as np

# 仓库根（chiyu-foundation）下的默认模型目录；env `CHIYU_MODEL_DIR` 优先。
# ⛔ 定义在本模块（无依赖一方），infer.py 单向引用 —— 避免 infer ⇄ onnx_runner 循环 import。
# onnx_runner.py: parents[0]=vector, [1]=chiyu_kernel, [2]=src, [3]=chiyu-kernel,
# [4]=packages, [5]=仓库根。
LOCAL_MODEL_DIR = os.path.join(
    str(Path(__file__).resolve().parents[5]), "models", "bge-small-zh-v1.5")

DEFAULT_ONNX = "model.onnx"
DEFAULT_TOKENIZER = "tokenizer.json"
DEFAULT_CONFIG = "config.json"
MAX_LEN = 512          # bge 系列位置编码上限

EXPECTED_INPUTS = ("input_ids", "attention_mask", "token_type_ids")
EXPECTED_OUTPUT = "last_hidden_state"

# 逻辑后端 → ORT provider 偏好（onnxruntime 会自行跳过不可用项，我们只报"实际用了哪个"）
_PROVIDER_PREFERENCE = {
    "cpu": ("CPUExecutionProvider",),
    "cuda": ("CUDAExecutionProvider", "CPUExecutionProvider"),
    "ascend": ("CANNExecutionProvider", "CPUExecutionProvider"),
}

_CACHE: dict[tuple[str, str], "OnnxRunner"] = {}


class OnnxUnavailable(RuntimeError):
    """产物缺失 / 依赖缺失 / 图不合契约。调用方据此 fail-open 降级哈希，不阻断主流程。"""


def resolve_model_dir(model_dir: str | None = None) -> str:
    """模型目录解析（唯一事实源：`CHIYU_MODEL_DIR` → 默认 models 目录）。"""
    if model_dir:
        return os.path.abspath(model_dir)
    env = os.environ.get("CHIYU_MODEL_DIR")
    if env:
        return os.path.abspath(env)
    return os.path.abspath(LOCAL_MODEL_DIR)


def is_available(model_dir: str | None = None) -> bool:
    """**廉价**可用性探针（只查文件与依赖存在性，不加载模型）。

    `auto` 的后端选择依赖它，故必须便宜且无副作用；任何异常一律视为不可用。
    """
    try:
        d = resolve_model_dir(model_dir)
        if not (os.path.isfile(os.path.join(d, DEFAULT_ONNX))
                and os.path.isfile(os.path.join(d, DEFAULT_TOKENIZER))):
            return False
        return (importlib.util.find_spec("onnxruntime") is not None
                and importlib.util.find_spec("tokenizers") is not None)
    except Exception:  # noqa: BLE001
        return False


def artifact_info(model_dir: str | None = None) -> dict:
    """产物元信息（供 /healthz 与离线自检取证；不加载模型）。"""
    d = resolve_model_dir(model_dir)
    onnx_path = os.path.join(d, DEFAULT_ONNX)
    info = {"model_dir": d, "onnx": os.path.basename(onnx_path),
            "present": os.path.isfile(onnx_path)}
    if info["present"]:
        info["bytes"] = os.path.getsize(onnx_path)
    cfg = os.path.join(d, DEFAULT_CONFIG)
    if os.path.isfile(cfg):
        try:
            with open(cfg, encoding="utf-8") as f:
                info["declared_dim"] = int(json.load(f).get("hidden_size") or 0)
        except Exception:  # noqa: BLE001
            pass
    return info


def config_dim(model_dir: str | None = None) -> int:
    """模型原生维度（读 config.json.hidden_size）。读不到返回 0（由上层判为不可用）。"""
    try:
        with open(os.path.join(resolve_model_dir(model_dir), DEFAULT_CONFIG), encoding="utf-8") as f:
            return int(json.load(f).get("hidden_size") or 0)
    except Exception:  # noqa: BLE001
        return 0


class OnnxRunner:
    """bge ONNX 推理器。`encode(text) -> np.float32[dim]`（CLS 池化 + L2 归一化）。"""

    def __init__(self, model_dir: str | None = None, backend: str = "cpu"):
        self.model_dir = resolve_model_dir(model_dir)
        onnx_path = os.path.join(self.model_dir, DEFAULT_ONNX)
        tok_path = os.path.join(self.model_dir, DEFAULT_TOKENIZER)
        for p, what in ((onnx_path, "ONNX 权重"), (tok_path, "tokenizer.json")):
            if not os.path.isfile(p):
                raise OnnxUnavailable(
                    f"缺 {what}：{p}（离线环境无第二来源，不得静默降级为哈希而不留痕）")
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except ImportError as e:  # noqa: BLE001
            raise OnnxUnavailable(
                f"运行期依赖缺失（{e}）：需要 onnxruntime + tokenizers，"
                f"**不需要** torch/transformers") from e

        self.tokenizer = Tokenizer.from_file(tok_path)
        self.tokenizer.enable_truncation(max_length=MAX_LEN)

        avail = list(ort.get_available_providers())
        want = _PROVIDER_PREFERENCE.get(backend, _PROVIDER_PREFERENCE["cpu"])
        chosen = [p for p in want if p in avail] or ["CPUExecutionProvider"]
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        try:
            self.session = ort.InferenceSession(onnx_path, sess_options=opts, providers=chosen)
        except Exception as e:  # noqa: BLE001
            raise OnnxUnavailable(f"ONNX 加载失败（{type(e).__name__}: {e}）") from e

        self.providers = list(self.session.get_providers())
        self.input_names = [i.name for i in self.session.get_inputs()]
        self.output_names = [o.name for o in self.session.get_outputs()]
        if tuple(self.input_names) != EXPECTED_INPUTS or self.output_names != [EXPECTED_OUTPUT]:
            raise OnnxUnavailable(
                f"图契约不符：inputs={self.input_names} outputs={self.output_names}，"
                f"期望 inputs={list(EXPECTED_INPUTS)} outputs=['{EXPECTED_OUTPUT}']"
                f"（换了权重却忘了改 runner 会在这一步就炸，而不是产出错向量）")

        declared = config_dim(self.model_dir)
        self.dim = self._warmup()                       # ⚠ 构造期必须真跑一次（自证非假可用）
        if declared and declared != self.dim:
            raise OnnxUnavailable(
                f"config.json 声明维度 {declared} 与图实际输出 {self.dim} 不一致："
                f"产物与配置错配，禁止上线")

    # ---------------------------------------------------------------- 推理

    def _warmup(self) -> int:
        """空串跑一次：既验证图可执行，又取得真实输出维度（失败即构造失败）。"""
        try:
            v = self.encode("")
        except OnnxUnavailable:
            raise
        except Exception as e:  # noqa: BLE001
            raise OnnxUnavailable(f"预热推理失败（{type(e).__name__}: {e}）") from e
        if v.ndim != 1 or v.shape[0] <= 0:
            raise OnnxUnavailable(f"预热输出形状异常：{v.shape}")
        if not np.any(v):
            raise OnnxUnavailable("预热输出为全零向量 —— 图或分词器不可用（会静默污染相似度闸门）")
        return int(v.shape[0])

    def encode(self, text: str) -> np.ndarray:
        """文本 → L2 归一化的 float32 向量（CLS 池化，与 infer._encode_local 同口径）。"""
        e = self.tokenizer.encode(text or "")
        ids = np.asarray([e.ids], dtype=np.int64)
        mask = np.asarray([e.attention_mask], dtype=np.int64)
        types = np.asarray([e.type_ids], dtype=np.int64)
        feed = {"input_ids": ids, "attention_mask": mask, "token_type_ids": types}
        hidden = self.session.run([EXPECTED_OUTPUT],
                                 {n: feed[n] for n in self.input_names})[0]
        v = hidden[:, 0, :].astype(np.float32)          # [CLS] 池化
        n = float(np.linalg.norm(v))
        if n > 0:
            v = v / n                                   # L2 归一化
        return v.squeeze(0)

    def info(self) -> dict:
        """可观测性。"""
        return {
            "backend_kind": "onnx",
            "model_dir": self.model_dir,
            "dim": self.dim,
            "providers": self.providers,
        }


def get_runner(model_dir: str | None = None, backend: str = "cpu") -> OnnxRunner:
    """进程级单例（会话/标定网格/服务共用，避免重复加载 ≈1s + 预热）。"""
    d = resolve_model_dir(model_dir)
    key = (d, backend)
    r = _CACHE.get(key)
    if r is None:
        r = OnnxRunner(d, backend=backend)
        _CACHE[key] = r
    return r


def clear_cache() -> None:
    """仅供测试/自检使用：清空单例缓存。"""
    _CACHE.clear()
