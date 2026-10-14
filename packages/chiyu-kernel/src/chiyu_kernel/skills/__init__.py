"""技能注册表 —— dsh `skill` 能力吸收（L2）。

忠实重写 dsh `packages/skill/skill/src/index.ts` 的**注册表语义**（Service Definition 角色）：
- `is_skill_name`：kebab-case 名称语法（公共地址约定）
- `SkillSpec`：胜出技能定义（name / description / content markdown 体 / invocation 控制 / source / provider / rank / metadata）
- `SkillRegistry`：register（runtime 贡献）+ get（按名解析胜出）+ list（摘要）
- `load_catalog`：批量注册（faithful to dsh provider catalog merge 的内存简化版）

⛔ 不引入 Cordis provider 框架——仅吸收「注册/解析/列表」行为，避免与本仓机制重复。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

_SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RUNTIME_PROVIDER = "runtime"
RUNTIME_RANK = 250


def is_skill_name(name: str) -> bool:
    """kebab-case 技能名语法（dsh `SKILL_NAME` 正则）。"""
    return bool(_SKILL_NAME.fullmatch(name or ""))


@dataclass(frozen=True)
class SkillSpec:
    """胜出技能定义（dsh `SkillDefinition` 的 Python 对应）。"""

    name: str
    description: str
    content: str = ""
    when_to_use: str = ""
    model_invocable: bool = True
    user_invocable: bool = True
    source: str = "runtime"
    provider: str = RUNTIME_PROVIDER
    rank: int = RUNTIME_RANK
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not is_skill_name(self.name):
            raise ValueError(f"非法技能名：{self.name!r}（须 kebab-case）")


class SkillConflict(KernelError):
    code = "CONTRACT_VIOLATION"
    """同名同 rank 注册冲突（dsh 用 rank 决胜，同 rank 无法决胜）。"""


class SkillRegistry:
    """运行时技能注册表：register / get / list。

    rank 语义（faithful to dsh）：同名技能，**更低 rank 胜出**；已有胜出者 rank 更低或相等时，
    新注册若 rank 更高则被忽略，若 rank 相等则抛 `SkillConflict`（无法决胜）。
    """

    def __init__(self) -> None:
        self._by_name: dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec) -> None:
        if not isinstance(spec, SkillSpec):
            raise TypeError("spec 须为 SkillSpec")
        existing = self._by_name.get(spec.name)
        if existing is None:
            self._by_name[spec.name] = spec
            return
        if existing.rank < spec.rank:
            return  # 现有胜出，忽略新注册
        if existing.rank == spec.rank:
            raise SkillConflict(
                f"技能 {spec.name!r} 同名同 rank({spec.rank}) 无法决胜；"
                f"请降低新注册 rank 以显式覆盖"
            )
        self._by_name[spec.name] = spec  # 新注册 rank 更低，胜出

    def get(self, name: str) -> SkillSpec:
        if name not in self._by_name:
            raise KeyError(name)
        return self._by_name[name]

    def list(self) -> list[SkillSpec]:
        return list(self._by_name.values())

    def summaries(self) -> list[dict[str, Any]]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "when_to_use": s.when_to_use,
                "model_invocable": s.model_invocable,
                "user_invocable": s.user_invocable,
                "source": s.source,
                "provider": s.provider,
            }
            for s in self._by_name.values()
        ]


def load_catalog(catalog: Mapping[str, Mapping[str, Any]]) -> SkillRegistry:
    """从 dict 批量注册（dsh provider catalog merge 的内存简化版）。

    `catalog` 形如 `{"summarizer": {"description":..., "content":..., "when_to_use":...}, ...}`；
    未给字段用 `SkillSpec` 默认值。
    """
    reg = SkillRegistry()
    allowed = {
        "description", "content", "when_to_use", "model_invocable",
        "user_invocable", "source", "provider", "rank", "metadata",
    }
    for name, body in catalog.items():
        if not isinstance(body, Mapping):
            raise TypeError(f"技能 {name!r} 目录项须为 Mapping")
        kwargs = {k: body[k] for k in allowed if k in body}
        reg.register(SkillSpec(name=name, **kwargs))
    return reg


__all__ = [
    "SkillSpec", "SkillRegistry", "SkillConflict", "is_skill_name", "load_catalog",
]
