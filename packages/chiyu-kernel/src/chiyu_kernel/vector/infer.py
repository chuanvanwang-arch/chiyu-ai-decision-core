"""推理后端统一抽象：本地 ONNX 真向量 → API 真向量（须显式放行）→ 哈希兜底。
INFER_BACKEND: auto|api|local|cpu|cuda|ascend|none
- auto（2026-09-21 方案 B′ 起改为**本地优先**）：
    1) 本地 ONNX（`models/bge-small-zh-v1.5/model.onnx`，需 onnxruntime+tokenizers）→ `cpu`
    2) 云端 API（**仅当** CHIYU_EMBEDDING_ALLOW_NETWORK=1 且有 key）→ `api`
    3) 本机 torch + transformers（≈2.5GB，离线镜像不装）→ `local`
    4) 加速器 torch_npu → `ascend`；torch+cuda → `cuda`
    5) 都没有 → `none`（哈希兜底）
- api:  OpenAI 兼容 /v1/embeddings（移植自 CRM embeddingClient.js，见 embedding_api.py）
- local: transformers + torch CPU 推理（CLS 池化 + 归一化，bge 官方检索口径）
- cpu/cuda/ascend: 本地 ONNX（onnx_runner.py），按 provider 偏好选执行器
- none: 无模型，一律哈希降级（零 GPU 可跑）

⛔ 出网纪律：`auto` **只有**在 `CHIYU_EMBEDDING_ALLOW_NETWORK=1` 显式声明时才允许选 `api`。

⛔ 测试基线冻结：`CHIYU_TEST=1` 时 `auto` 直接返回 `none`（哈希），
   使流水线用例的簇数/并入数完全确定（见 `_resolve` 内的理由）。

本模块同时并入 demo `ontology/embedding.py` 的 `stable_stringify` / `content_hash` /
`hash_vector`（P1 T3 Step 1 映射表：并入本模块）。
"""
import hashlib
import json
import os
from typing import Any

import numpy as np

from chiyu_kernel.contract.particle import HASH_DIM

from . import embedding_api
from . import onnx_runner

# LOCAL_MODEL_DIR 定义在 onnx_runner.py（无依赖一方）—— 单向引用，避免循环 import。
# 后续使用处须改为 ``onnx_runner.LOCAL_MODEL_DIR`` 或经 resolve 引用。
DEFAULT_DIM = 384


def _network_allowed() -> bool:
    """D3：出网必须**显式声明**（默认 0 = 禁出网）。

    实现归 `embedding_api.network_allowed()`（单一事实源）。此处保留同名包装仅为兼容既有引用。
    """
    return embedding_api.network_allowed()


def hash_signature(text: str, dim: int = HASH_DIM) -> np.ndarray:
    """确定性哈希签名向量（可复现，无随机性）。"""
    v = np.zeros(dim, dtype=np.float32)
    tokens = _tokenize(text)
    for i, tok in enumerate(tokens):
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
        v[idx] += sign
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def _tokenize(text: str) -> list:
    # 简中切分：单字 + 英文单词
    toks = []
    for w in __import__("re").findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fa5]", text):
        toks.append(w)
    # 中文二元组补充
    cjk = [c for c in text if "\u4e00" <= c <= "\u9fa5"]
    toks += [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]
    return toks


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ── 并入 ontology/embedding.py 的稳定序列化 / 内容哈希 / 哈希向量 ────────

def stable_stringify(obj: Any) -> str:
    """JSON 键递归排序的稳定序列化（防键序漂移导致同语义文本哈希漂移）。"""
    if isinstance(obj, dict):
        return "{" + ",".join(
            f"{json.dumps(k, ensure_ascii=False)}:{stable_stringify(v)}"
            for k, v in sorted(obj.items())
        ) + "}"
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(stable_stringify(v) for v in obj) + "]"
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return json.dumps(obj, ensure_ascii=False)
    return json.dumps(obj, ensure_ascii=False, default=str)


def content_hash(payload: Any) -> str:
    """内容哈希：SHA-256 十六进制，用于写时幂等判变。"""
    return hashlib.sha256(stable_stringify(payload).encode("utf-8")).hexdigest()


def hash_vector(text: str, dim: int = HASH_DIM) -> np.ndarray:
    """确定性签名向量：SHA-256 字节映射 `dim` 桶的有符号扰动向量并归一化。"""
    return hash_signature(text, dim)


class InferBackend:
    """统一推理后端。encode(text) -> ndarray。
    text 须为清洗后文本（≤480 字符）。"""

    def __init__(self, backend: str | None = None, model_dir: str | None = None):
        # ⚠ 默认 None（**不是** "auto"）：None 的语义是"读 env `INFER_BACKEND`，缺省 auto"。
        #    显式传 "auto"/"cpu"/... 仍表示"覆盖 env"，测试隔离不受影响。
        self.model_dir = model_dir
        self.backend = self._resolve(backend, model_dir)
        self._session = None          # ONNX 会话（非 ONNX 通道恒 None）；状态判定见 model_status
        self._runner = None
        self._dim = HASH_DIM
        self.last_error: str | None = None
        if self.backend == "api":
            self._dim = 1024   # BAAI/bge-large-zh-v1.5 原生维度（CRM 同源）
        if self.backend in ("local", "cpu", "cuda", "ascend"):
            self._load_model()

    @staticmethod
    def _resolve(b: str | None, model_dir: str | None = None) -> str:
        # 语义（2026-09-21 修）：
        #   · 显式非 auto 值（"cpu"/"api"/"none"…）⇒ **覆盖 env**，测试隔离依赖这条；
        #   · "auto" / 未传 ⇒ **跟随 env `INFER_BACKEND`**，env 未设才走自动探测。
        # 旧写法 `b or env or "auto"` 有个静默缺陷：调用点都显式传 "auto"（truthy）
        # ⇒ env 永远读不到。改成"auto 也读 env"后单点修好。
        b = (b or "").strip().lower()
        if not b or b == "auto":
            b = (os.environ.get("INFER_BACKEND") or "auto").strip().lower()
        if b != "auto":
            return b
        # ⛔ 测试基线冻结（CHIYU_TEST=1）⇒ 一律哈希。
        #    真实 ONNX 会让全部流水线用例的簇数/并入数整体漂移并拖垮全量。
        #    测试断言的是**接线与判据**，不是模型数值；需要真向量数值的用例请显式
        #    `InferBackend("cpu")` 或直接调 onnx_runner。
        if os.environ.get("CHIYU_TEST") == "1":
            return "none"
        # D1：**本地 ONNX 优先**（赛题硬约束是离线）。
        if onnx_runner.is_available(model_dir or os.environ.get("CHIYU_MODEL_DIR")
                                    or onnx_runner.LOCAL_MODEL_DIR):
            return "cpu"
        # D3：云通道须显式放行出网 —— 闸门本身在 `embedding_api.available()`。
        if embedding_api.available():
            return "api"
        if os.path.isfile(os.path.join(
                model_dir or os.environ.get("CHIYU_MODEL_DIR") or onnx_runner.LOCAL_MODEL_DIR,
                "model.safetensors")):
            try:
                import torch  # noqa: F401
                import transformers  # noqa: F401
                return "local"
            except ImportError:
                pass
        try:
            import torch_npu  # noqa: F401
            return "ascend"
        except ImportError:
            pass
        try:
            import torch  # noqa: F401
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "none"

    _local_singleton: tuple | None = None   # (tok, model, torch) 进程级缓存：标定网格/服务会话复用
    @classmethod
    def _get_local(cls):
        """bge 模型进程级单例（加载 ~30s，避免每次构造 Pipeline 重载）。"""
        if cls._local_singleton is None:
            from transformers import AutoModel, AutoTokenizer
            import torch
            d = os.environ.get("CHIYU_MODEL_DIR", onnx_runner.LOCAL_MODEL_DIR)
            tok = AutoTokenizer.from_pretrained(d, local_files_only=True)
            model = AutoModel.from_pretrained(d, local_files_only=True)
            model.eval()
            cls._local_singleton = (tok, model, torch)
        return cls._local_singleton

    def _load_model(self):
        """local: transformers bge（dev 通道）；cpu/cuda/ascend: 本地 ONNX（B′ 主通道）。

        失败一律 fail-open 降级 `none` 并留 `last_error`（不阻断主流程），
        但**绝不静默**：`model_status` 会实报 hash，可被 /healthz 与自检抓到。
        """
        if self.backend == "local":
            try:
                tok, model, torch = self._get_local()
                self._tok, self._model, self._torch = tok, model, torch
                self._dim = int(self._model.config.hidden_size)   # bge-small=512 / bge-large=1024
                return
            except Exception as e:  # noqa: BLE001
                self.last_error = f"local 模型加载失败: {e}"
                self.backend = "none"
                self._dim = HASH_DIM
                return
        try:
            self._runner = onnx_runner.get_runner(self.model_dir, backend=self.backend)
            self._session = self._runner.session    # 兼容既有读取点
            self._dim = self._runner.dim
        except Exception as e:  # noqa: BLE001
            self.last_error = f"ONNX 加载失败: {e}"
            self._runner = None
            self._session = None
            self.backend = "none"
            self._dim = HASH_DIM

    def _encode_local(self, text: str) -> np.ndarray:
        """bge 官方检索口径：CLS 池化 + L2 归一化（≤512 token 由 tokenizer 截断）。"""
        with self._torch.no_grad():
            enc = self._tok(text, return_tensors="pt", truncation=True, max_length=512)
            out = self._model(**enc)
            v = out.last_hidden_state[:, 0, :]          # [CLS]
            v = self._torch.nn.functional.normalize(v, p=2, dim=1)
        return v.squeeze(0).numpy().astype(np.float32)

    def encode(self, text: str) -> np.ndarray:
        # R2.5：API 真向量路径（fail-open：任何失败降级哈希，拒因留存）
        if self.backend == "api":
            vec = embedding_api.embed(text)
            if vec is not None:
                return np.asarray(vec, dtype=np.float32)
            self.backend = "none"   # 本次会话降级（下次 _resolve 可恢复，不烧重试）
            self._dim = HASH_DIM    # 与真实返回值对齐（否则 model_info 会谎报 1024）
            self.last_error = embedding_api.LAST_ERROR
        if self.backend == "local":
            try:
                return self._encode_local(text)
            except Exception as e:  # noqa: BLE001
                self.last_error = f"local 推理失败: {e}"
                self.backend = "none"
                self._dim = HASH_DIM
        if self._runner is not None:
            try:
                return self._runner.encode(text)
            except Exception as e:  # noqa: BLE001
                self.last_error = f"ONNX 推理失败: {e}"
                self._runner = None
                self._session = None
                self.backend = "none"
                self._dim = HASH_DIM
        return hash_signature(text, HASH_DIM)

    # ------------------------------------------------------ 可观测性

    @property
    def model_status(self) -> str:
        """向量通道**真相**：`onnx` / `api` / `local` / `hash`。**/healthz 的唯一取值点**。

        ⛔ 历史缺陷（2026-09-21 实测）：曾用 `_session is not None` 判定，而 `api`/`local`
        分支从不赋值 `_session` ⇒ 真向量正在跑却恒报 `"hash"`（假红）。此处按 `backend`
        实报，且只依据**已发生的事实**（runner 构造成功、模型已加载）。
        """
        b = self.backend
        if b == "api":
            return "api"
        if b in ("cpu", "cuda", "ascend"):
            return "onnx" if self._runner is not None else "hash"
        if b == "local":
            return "local" if getattr(self, "_model", None) is not None else "hash"
        return "hash"

    def model_info(self) -> dict:
        """可观测性扩展字段：状态 + 维度 + 是否需补零 + 实际执行器。

        `padded` 语义 = **本通道输出维度小于列维 ⇒ 落库前需显式补零**（不是"已经补过"）。
        """
        from chiyu_kernel.contract.particle import VECTOR_DIM as COLUMN_DIM
        dim = int(self._dim)
        info = {"model_status": self.model_status, "vector_dim": dim,
                "column_dim": int(COLUMN_DIM), "padded": dim < int(COLUMN_DIM)}
        if self._runner is not None:
            info["providers"] = list(self._runner.providers)
        return info
