"""写操作安全闸机制层（八闸框架 + 第0闸决策锚定）。

经 chiyu_kernel.api 门面 re-export；消费方经 sanctioned 面接入。
"""
from __future__ import annotations

from .chain import evaluate_chain, run_gate_chain
from .decision_required import gate_write

__all__ = ["gate_write", "run_gate_chain", "evaluate_chain"]
