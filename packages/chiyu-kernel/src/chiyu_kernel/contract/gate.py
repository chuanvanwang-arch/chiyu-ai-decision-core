"""L0 契约 —— 写操作安全闸（八闸框架）与决策凭证（第0闸）。

产品官方「写操作八闸」= 四大类安全范式（事前校验 / 权限边界 / 红线拦截 / 事后可溯）。
本契约只收**四分类骨架 + 编排协议**，不收任何具体域闸名（sales_* 等必须留消费方注入）。

⛔ 边界铁律（CRM 审定 #2 + Batch-0 去重收口）：
  - 零依赖（仅 dataclasses/typing）、零 IO、零领域字面量；
  - GATE_CLASSES 是安全范式分类（通用词），非 CRM 业务闸名；
  - 具体闸（含其 check 实现、域闸名）由消费方注入，内核只编排、不解释语义。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from dataclasses import dataclass
from typing import Mapping, Tuple


# ── 四分类安全范式（骨架，非具体闸）────────────────────────────────────────
# 事前校验 / 权限边界 / 红线拦截 / 事后可溯 —— 任意 N 级闸挂此四类之一。
GATE_CLASSES: Tuple[str, ...] = ("precheck", "permission", "redline", "traceability")


# ── 第0闸：轻量决策凭证（消费方签发、内核只验结构，不产决策）────────────────
# 与 D1 outcome.decision_id 强关联同源：写操作必须锚定一个决策（无决策不写）。
DECISION_CREDENTIAL_FIELDS: Tuple[str, ...] = (
    "decision_id",   # 决策标识（与 OUTCOME_REQUIRED_FIELDS.decision_id 同源）
    "issuer",        # 签发主体（消费方）
    "issued_at",     # 签发时间戳
    "ttl",           # 有效期（秒），≤0 视为永久
    "checksum",      # 结构校验和（消费方签发；内核只验形态，不验算法）
)


# ── 闸链结构不变量（机制层 run_gate_chain 必须保证，fail-closed）─────────────
GATE_CHAIN_INVARIANTS: Tuple[str, ...] = (
    "empty_chain_denied",            # 无闸链 = fail-closed，不通过
    "short_circuit_on_first_deny",   # 任一闸拒即整体拒（短路）
    "class_in_enum",                 # 闸类名必 ∈ GATE_CLASSES
    "all_pass_required",             # 全过才放行
)


class DecisionRequiredError(KernelError):
    code = "CONFIRM_REQUIRED"
    """第0闸：写操作缺少有效 decision_id（fail-closed）。"""


class DecisionCredentialError(KernelError):
    code = "CONTRACT_VIOLATION"
    """决策凭证结构校验失败（缺字段 / 形态非法）。"""


class GateChainError(KernelError):
    code = "CONTRACT_VIOLATION"
    """闸链编排错误（空链 / 类名非法 / 短路冲突）。"""


def require_decision_id(payload: Mapping, *, field: str = "decision_id") -> str:
    """第0闸原语：写操作必须锚定一个决策。

    fail-closed：payload 缺 ``field`` 或为空 ⇒ 抛 DecisionRequiredError。
    返回决策 id（不产决策、不验业务语义，与 D1 同源）。
    """
    did = payload.get(field) if isinstance(payload, Mapping) else None
    if not did or not str(did).strip():
        raise DecisionRequiredError(
            f"写操作第0闸：payload 缺有效 {field!r}（无决策不写）")
    return str(did)


def verify_decision_credential(cred: Mapping) -> str:
    """轻量决策凭证校验（消费方签发、内核只验结构，不产决策）。

    fail-closed：缺字段 / checksum 非字符串 / issuer 为空 ⇒ 抛 DecisionCredentialError。
    返回 decision_id。内核不校验 checksum 算法（那是消费方职责），只验形态存在。
    """
    for f in DECISION_CREDENTIAL_FIELDS:
        if f not in cred:
            raise DecisionCredentialError(f"决策凭证缺字段 {f!r}")
    did = cred.get("decision_id")
    issuer = cred.get("issuer")
    checksum = cred.get("checksum")
    if not str(did).strip():
        raise DecisionCredentialError("decision_id 为空")
    if not str(issuer).strip():
        raise DecisionCredentialError("issuer 为空（凭证无签发主体）")
    if not isinstance(checksum, str) or not checksum.strip():
        raise DecisionCredentialError("checksum 必须为非空字符串（结构校验和）")
    return str(did)


@dataclass(frozen=True)
class GateSpec:
    """闸声明（数据，不收实现）。具体 check 由消费方在机制层注入。

    name：任意字符串（消费方注入的域闸名，内核不解释语义、不约束取值）；
    cls：必 ∈ GATE_CLASSES（四分类范式）；
    required_on：触发该闸的判定键（可选，机制层用于短路路由）。
    """

    name: str
    cls: str
    required_on: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.cls not in GATE_CLASSES:
            raise GateChainError(
                f"闸类名 {self.cls!r} 不在四分类范式 {GATE_CLASSES}")
        if not self.name or not str(self.name).strip():
            raise GateChainError("闸 name 不得为空")


__all__ = [
    "GATE_CLASSES", "GATE_CHAIN_INVARIANTS",
    "DECISION_CREDENTIAL_FIELDS",
    "DecisionRequiredError", "DecisionCredentialError", "GateChainError",
    "require_decision_id", "verify_decision_credential", "GateSpec",
]
