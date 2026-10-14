"""粒子运行时模型（L0 形态）—— 领域无关。

⛔ 泛化点：demo 的 `TicketParticle`（工单专用，字段含 `order_id`/`identity`/`entities_raw`/`fts`）
   泛化为 `Particle`。字段语义保留，命名去领域化：
       order_id      → particle_id        （粒子主键，任意域都有）
       identity      → subject_id         （主体标识，任意域都有）
       entities_raw  → raw_refs           （未解析的引用原文集合）
       fts           → fulltext           （全文索引文本）
   旧名保留为 `property` 别名（deprecated，标 `TODO(remove@0.3)`，不在本期移除）。
   领域身份的子维度（如"地点/类目/分区"这类单域一等对象）一律放 `attrs`，
   由消费方填充 —— 内核不声明任何具体身份维度（防单域退化，见 test_contract_no_domain_literals）。

⛔ 类型说明（相对计划模板的两处精确化，源码核实）：
   · demo `entities_raw` 是 `list`（引用原文集合）⇒ `raw_refs` 用 `tuple[str, ...]`
     （集合语义，frozen 友好）。计划模板写 `Optional[str]` 系简化，语义保留要求集合形态。
   · demo `identity` 是 `dict`（entities/place/category 子键）⇒ 泛化后子维度全部下沉
     `attrs`，`subject_id` 只承载主体标识（str）。`identity` property 保持返回
     `subject_id`（计划模板原样）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# 默认上下文层（粒子归属；与 contract.particle.LAYERS 对齐的形态默认）
DEFAULT_LAYER = "L1"


@dataclass
class Particle:
    """粒子的运行时形态（写时三钩子的载体）。"""

    particle_id: str
    type: str                                   # 取值来自 profile.particle_types
    layer: str = DEFAULT_LAYER
    label: Optional[str] = None
    status: Optional[str] = None
    subject_id: Optional[str] = None            # 原 identity（去领域化；主体标识）
    raw_refs: Optional[Tuple[str, ...]] = None  # 原 entities_raw（引用原文集合）
    fulltext: Optional[str] = None              # 原 fts
    embedding: Optional[List[float]] = None     # 未补零的原始维度
    provider: Optional[str] = None              # 'model' | 'model-p{n}' | 'hash'
    content_hash: Optional[str] = None
    attrs: dict = field(default_factory=dict)   # 领域身份子维度 / 扩展（消费方填充）

    # ── 兼容别名（demo 迁移期用；标 deprecated）─────────────────────────
    @property
    def identity(self) -> Optional[str]:        # TODO(remove@0.3)
        """旧名 identity → subject_id 的别名（计划模板原样：返回 subject_id）。"""
        return self.subject_id

    @property
    def entities_raw(self) -> list:             # TODO(remove@0.3)
        """旧名 entities_raw → raw_refs 的别名（list 视图，兼容 demo 迁移钩子）。"""
        return list(self.raw_refs or ())

    @property
    def fts(self) -> Optional[str]:             # TODO(remove@0.3)
        """旧名 fts → fulltext 的别名。"""
        return self.fulltext


__all__ = ["Particle", "DEFAULT_LAYER"]
