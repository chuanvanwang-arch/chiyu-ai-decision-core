"""向量契约 —— L0 词汇与不变式（GAP-3，Batch-2a，2026-10-14）。

定位：离线向量内核（`chiyu_kernel/vector/`）的**词汇单一事实源**：
推理后端闭集 / 模型状态口径 / 解析顺序 / 出网闸 / 维度纪律。
此前 vector 只有 impl 无 sanctioned contract，消费方（APS
`platform/embedding.py`，enterprise `memory/*`）被迫 import 内部路径
（APS 盘点 §四 GAP-3）。

⛔ 本层零第三方依赖、零 IO、零领域字面量。`HASH_DIM` / `VECTOR_DIM`
   自 `contract.particle` 再导出（列维与哈希维的契约原本就在那里，
   此处只做向量族的归口，不制造第二份）。
"""
from __future__ import annotations

from typing import Tuple

from .particle import HASH_DIM, VECTOR_DIM

# ── 推理后端闭集（infer.InferBackend 的合法取值）──────────────────────
#: `auto` = 按解析顺序自动探测；`none` = 无模型，一律哈希兜底（零 GPU 可跑）。
EMBEDDING_BACKENDS: Tuple[str, ...] = (
    "auto", "api", "local", "cpu", "cuda", "ascend", "none")

# ── auto 解析顺序（本地 ONNX 优先 → 云端 API 须放行 → 哈希兜底）────────
#: 顺序即优先级；每级失败不抛，降级并留痕（禁静默）。
EMBEDDING_RESOLUTION_ORDER: Tuple[str, ...] = (
    "onnx_local", "cloud_api", "torch_local", "accelerator", "hash_degrade")

# ── 模型状态口径（model_status 闭集；/healthz 唯一取值点）─────────────
#: 按**已发生的事实**实报（runner 构造成功 / 模型已加载），不按意愿报。
EMBEDDING_MODEL_STATUS: Tuple[str, ...] = ("onnx", "api", "local", "hash")

# ── 出网闸（D3：默认禁出网，交付物默认离线安全）──────────────────────
#: 云端 API 通道**仅当**该 env 显式置 1 时才允许被 auto 选中。
EMBEDDING_NETWORK_ENV = "CHIYU_EMBEDDING_ALLOW_NETWORK"

# ── 维度纪律（三条硬约束，有守卫测试）────────────────────────────────
EMBEDDING_DIM_INVARIANTS: Tuple[str, ...] = (
    "no_truncation",             # 超列维不得截断 ⇒ 视为取不到、走哈希
    "exact_dim_or_explicit_pad",  # 写入维度须恰等 dim，补零必须显式 pad_to_dim
    "hash_dim_deterministic",    # 哈希签名确定性可复现（无随机性）
)

__all__ = [
    "HASH_DIM", "VECTOR_DIM",
    "EMBEDDING_BACKENDS", "EMBEDDING_RESOLUTION_ORDER", "EMBEDDING_MODEL_STATUS",
    "EMBEDDING_NETWORK_ENV", "EMBEDDING_DIM_INVARIANTS",
]
