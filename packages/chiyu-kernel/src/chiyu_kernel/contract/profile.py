"""消费方画像契约 —— L4 领域内容进入内核的**唯一通道**。

⛔ 单向：内核只读 profile，绝不反向 import 消费方。
⛔ 内核**不提供** profile 的默认领域值——若提供，等价于把某个域的取值当默认，
   其他项目"不改也能跑"，最终所有项目都是同一个域。故 `domain` 与
   `particle_types` 必填、无默认。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .decision import AUTONOMOUS_RELEASE_DEFAULT, RUBRIC_THRESHOLDS_DEFAULT
from .particle import ParticleTypeSet, PredicateSet


@dataclass(frozen=True)
class RedlineSpec:
    """红线判据（L4 取值；内核只提供**两档判别**的形态）。

    barrier     仅禁止并入（不需要人工）—— 语义是"不像同一群体"
    redline     强制人工在环 —— 责任主体冲突 / 跨敏感边界
    历史缺陷：两档混为一档 ⇒ 大量正常单被送人工池。故形态上强制分开。
    """

    mutex_top: frozenset = field(default_factory=frozenset)
    sensitive: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class TenantProfile:
    """一个消费方项目的完整领域画像。"""

    domain: str
    particle_types: ParticleTypeSet
    predicates: PredicateSet = field(default_factory=PredicateSet)
    redline: RedlineSpec = field(default_factory=RedlineSpec)
    rubric_thresholds: Mapping[str, float] = field(
        default_factory=lambda: dict(RUBRIC_THRESHOLDS_DEFAULT)
    )
    autonomous_threshold: float = AUTONOMOUS_RELEASE_DEFAULT
    extras: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.domain:
            raise ValueError("profile.domain 必填（内核不提供默认领域）")
        if not 0.0 <= float(self.autonomous_threshold) <= 1.0:
            raise ValueError(
                f"autonomous_threshold 须 ∈ [0,1]：{self.autonomous_threshold}"
            )
        # 谓词的 from/to 必须落在声明的粒子类型集内（否则边永远建不起来）
        for p in self.predicates.all():
            for end, t in (("from", p.from_type), ("to", p.to_type)):
                if t is not None and not self.particle_types.covers(t):
                    raise ValueError(
                        f"谓词 {p.predicate} 的 {end}_type={t!r} 不在 "
                        f"particle_types 中 ⇒ 该边永远无法建立"
                    )


__all__ = ["RedlineSpec", "TenantProfile"]
