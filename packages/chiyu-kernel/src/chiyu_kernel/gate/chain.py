"""八闸框架机制：可配置 N 级、四分类、串行 fail-closed 闸链编排。

内核只编排、不解释具体闸语义；具体 check 由消费方注入（与 GATE_CLASSES 四分类对齐）。
域闸名（sales_* 等）由消费方 GateSpec.name 注入，内核不持有、不约束。
"""
from __future__ import annotations

from typing import Callable, Iterable, List, Tuple

from chiyu_kernel.contract.gate import (
    GATE_CHAIN_INVARIANTS, GATE_CLASSES, GateChainError, GateSpec,
)


def run_gate_chain(
    payload: Mapping,
    gates: Iterable[Tuple[GateSpec, Callable[[Mapping], bool]]],
    *,
    on_fail: Callable[[GateSpec, str], Exception],
) -> List[str]:
    """串行执行各闸 check（消费方注入），fail-closed。

    - 空链 ⇒ 抛 GateChainError（空链 = 不通过，GATE_CHAIN_INVARIANTS[0]）；
    - 任一闸 check=False ⇒ 调 on_fail(spec, "denied") 抛异常（短路，整体拒）；
    - check 抛异常 ⇒ 视为拒（fail-closed），调 on_fail(spec, reason)；
    - 全过 ⇒ 返回通过的闸名列表。
    机制层只编排，不持有任何域闸名（域闸名由消费方 GateSpec.name 注入）。
    """
    gate_list = list(gates)
    if not gate_list:
        raise GateChainError("空闸链 = fail-closed（无闸不通过）")
    passed: List[str] = []
    for spec, check in gate_list:
        if not isinstance(spec, GateSpec):
            raise GateChainError(
                f"闸声明必须是 GateSpec，得到 {type(spec).__name__}")
        if spec.cls not in GATE_CLASSES:
            raise GateChainError(f"闸类名 {spec.cls!r} 不在四分类 {GATE_CLASSES}")
        try:
            ok = bool(check(payload))
        except Exception as exc:  # check 异常 = 拒（fail-closed）
            raise on_fail(spec, f"check 异常: {type(exc).__name__}: {exc}")
        if not ok:
            raise on_fail(spec, "denied")
        passed.append(spec.name)
    return passed


def evaluate_chain(
    gate_results: Iterable[Tuple[GateSpec, bool]],
) -> bool:
    """纯函数形态：给定各闸结果，判定整体放行（全过才放行）。

    空结果集 ⇒ False（fail-closed）。供测试 / 审计对账（与 run_gate_chain 短路语义一致）。
    """
    results = list(gate_results)
    if not results:
        return False
    return all(ok for _, ok in results)
