"""Agent 注册表（自变对象①）—— 范式照抄 `actions/registry.py` 的注册期拒绝。

⛔ 为什么必须是注册期而不是事后审计
──────────────────────────────────
静态 dict 式的注册表（无闸）意味着"加一个 agent"永远不报错，等事后审计发现它
没契约 / 没成功标准时，它**已经跑过了**。注册期拒绝让缺陷停在写入之前。

⛔ 为什么 `success` 必填且要求判定式
────────────────────────────────────
没有成功标准的 agent 跑完了也无法判定成败——它的产出只能靠人看。
故 `success` 必填，`audit()` 另对**过短**的 success 给出告警（形容词不算判据）。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Tuple

# Batch-2a（GAP-5）：Agent 契约字段面与 success 最短长度上收
# `chiyu_kernel/contract/orchestration.py`（sanctioned 契约面单一事实源）。
from chiyu_kernel.contract.orchestration import MIN_SUCCESS_LEN


class AgentRegistryError(KernelError):
    code = "CONTRACT_VIOLATION"
    """Agent 注册契约违规 ⇒ **注册期**抛错（非事后审计）。"""


@dataclass(frozen=True)
class AgentSpec:
    key: str
    contract_task_id: str
    skills: Tuple[str, ...] = ()
    memory: Tuple[str, ...] = ()
    knowledge_scope: Mapping = field(default_factory=dict)
    success: str = ""

    def missing(self) -> List[str]:
        """契约缺项清单（空 = 完整）。"""
        out: List[str] = []
        if not (self.key or "").strip():
            out.append("key")
        if not (self.contract_task_id or "").strip():
            out.append("contract_task_id")
        if not self.skills:
            out.append("skills")
        if not self.memory:
            out.append("memory")
        if not (self.success or "").strip():
            out.append("success")
        return out


class AgentRegistry:
    def __init__(self) -> None:
        self._by_key: Dict[str, AgentSpec] = {}
        self._by_task: Dict[str, str] = {}

    def register(self, spec: AgentSpec) -> None:
        # ① 必携完整契约（缺一即拒）
        miss = spec.missing()
        if miss:
            raise AgentRegistryError(
                f"agent {spec.key!r} 契约不完整（缺 {miss}）⇒ 拒绝注册"
                "（无成功标准的 agent 跑完了也无法判定成败）")
        # ② 重复 key
        if spec.key in self._by_key:
            raise AgentRegistryError(f"重复注册 agent：{spec.key!r}")
        # ③ 契约键冲突（一个契约键只能被一个 agent 持有）
        owner = self._by_task.get(spec.contract_task_id)
        if owner is not None:
            raise AgentRegistryError(
                f"契约键 {spec.contract_task_id!r} 已由 {owner!r} 持有，"
                f"新增 {spec.key!r} ⇒ 应并入既有 agent，不得另起")
        self._by_key[spec.key] = spec
        self._by_task[spec.contract_task_id] = spec.key

    def get(self, key: str) -> Optional[AgentSpec]:
        return self._by_key.get(key)

    def keys(self) -> Tuple[str, ...]:
        return tuple(sorted(self._by_key))

    def audit(self) -> List[str]:
        """返回告警（非空 ⇒ 注册表不合规）。过短的 success 视为"形容词而非判据"。"""
        return [
            f"agent {k}：success 仅 {len(s.success.strip())} 字"
            f"（< {MIN_SUCCESS_LEN}）⇒ 疑似形容词而非判定式"
            for k, s in sorted(self._by_key.items())
            if len(s.success.strip()) < MIN_SUCCESS_LEN
        ]


__all__ = ["AgentRegistryError", "AgentSpec", "AgentRegistry", "MIN_SUCCESS_LEN"]
