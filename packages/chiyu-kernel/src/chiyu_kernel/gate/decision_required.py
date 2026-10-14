"""第0闸机制：写操作入口锚定决策（轻量凭证契约）。

消费方两种接入形态：
  - 直接形态：payload 含 decision_id ⇒ require_decision_id（与 D1 outcome 同源）；
  - 凭证形态：独立 decision_credential 对象 ⇒ verify_decision_credential
    （消费方签发、内核只验结构，不产决策；第0闸选型 (a)）。
"""
from __future__ import annotations

from typing import Mapping, Optional

from chiyu_kernel.contract.gate import (
    DecisionCredentialError, DecisionRequiredError, require_decision_id,
    verify_decision_credential,
)


def gate_write(payload: Mapping, *, decision_cred: Optional[Mapping] = None,
               on_missing: str = "raise") -> str:
    """写通道入口 first-call：锚定决策（第0闸）。

    - decision_cred 给定 ⇒ 先 verify_decision_credential（轻量凭证，fail-closed）；
    - 否则回退 require_decision_id(payload)（只验 payload 含 decision_id）；
    - on_missing="raise"（默认）缺则抛 DecisionRequiredError；
      on_missing="return_none" 返回 None 供调用方柔性处理。
    返回 decision_id（凭证形态返回凭证内的 decision_id）。
    """
    if decision_cred is not None:
        return verify_decision_credential(decision_cred)
    try:
        return require_decision_id(payload)
    except DecisionRequiredError:
        if on_missing == "return_none":
            return None
        raise
