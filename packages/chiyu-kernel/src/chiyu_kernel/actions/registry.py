"""Action 表面注册表（R1–R6 基数规则的**可执行形式**）—— ★ 新建，demo 未收敛。

⛔ 为什么要有注册表而不是继续加端点
──────────────────────────────────
demo 的 59 个端点里出现"同一能力多端点并存"（如 `/api/retro/*` 4 个），
这是 R5（一能力一 Action）被违反的典型。加端点不会报错，所以没人拦得住 ——
除非有一个注册表在**注册期**就拒绝重复。

R1–R6（判定规则）：
    R1 一个业务域 5–9 个 Action（过多=CRUD 爆炸，过少=能力不足）
    R2 Action 名 = 动词 + 对象（`submit_request` 而非 `requestSubmit`）
    R3 读操作不单独占位（读并入对象的 query Action）
    R4 写操作必须有决策锚（decision_id）
    R5 一个能力一个 Action（同能力的多入口必须折叠）
    R6 高危写必须有 force 确认位

⛔ 零领域词：注册表只承载**判定机制**；具体 Action 清单是 L4（消费方域内容）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

ACTION_MIN, ACTION_MAX = 5, 9
_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")
_HIGH_RISK_HINTS = ("delete", "purge", "reset", "drop", "approve", "release")


@dataclass(frozen=True)
class ActionSpec:
    name: str
    capability: str                 # R5：同一 capability 只能有一个 Action
    mutating: bool = False          # R4：写操作必须有决策锚
    high_risk: bool = False         # R6：高危写必须有 force
    has_force: bool = False

    def violations(self) -> List[str]:
        out: List[str] = []
        if not _NAME_RE.match(self.name):
            out.append(f"R2 命名不合规（须 verb_object）：{self.name}")
        if self.high_risk and not self.has_force:
            out.append(f"R6 高危写缺 force 确认位：{self.name}")
        if not self.high_risk and self.has_force:
            out.append(f"R6 非高危动作不应带 force 位：{self.name}")
        return out


class ActionRegistry:
    def __init__(self) -> None:
        self._by_name: Dict[str, ActionSpec] = {}
        self._by_capability: Dict[str, str] = {}

    def register(self, spec: ActionSpec) -> None:
        if spec.name in self._by_name:
            raise ValueError(f"重复注册 Action：{spec.name}")
        owner = self._by_capability.get(spec.capability)
        if owner is not None:
            raise ValueError(
                f"R5 违反：capability {spec.capability!r} 已由 {owner!r} 占用，"
                f"新增 {spec.name!r} ⇒ 应折叠到既有 Action，而不是新开端点")
        self._by_name[spec.name] = spec
        self._by_capability[spec.capability] = spec.name

    def audit(self) -> Tuple[List[str], List[str]]:
        """返回 (errors, warnings)。errors 非空 ⇒ 表面不合规，不得发布。"""
        errors: List[str] = []
        warnings: List[str] = []
        n = len(self._by_name)
        if n < ACTION_MIN:
            warnings.append(f"R1 Action 数偏少（{n} < {ACTION_MIN}）")
        if n > ACTION_MAX:
            errors.append(f"R1 Action 数超限（{n} > {ACTION_MAX}）⇒ CRUD 爆炸")
        for spec in self._by_name.values():
            errors.extend(spec.violations())
        return errors, warnings

    def by_name(self, name: str) -> Optional[ActionSpec]:
        return self._by_name.get(name)

    def names(self) -> Tuple[str, ...]:
        return tuple(sorted(self._by_name))


__all__ = ["ActionSpec", "ActionRegistry", "ACTION_MIN", "ACTION_MAX"]
