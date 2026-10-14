"""八闸框架闸链编排（Batch-1a）。

含 parity 形态（消费方用四分类编排任意 N 级闸，证明去重收口可行）与变异自证。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract.gate import GATE_CLASSES, GateChainError, GateSpec
from chiyu_kernel.gate import evaluate_chain, run_gate_chain


def _spec(name, cls):
    return GateSpec(name=name, cls=cls)


class _Deny(Exception):
    pass


def test_gate_spec_bad_class_raises():
    with pytest.raises(GateChainError):
        GateSpec(name="g", cls="not_a_class")


def test_gate_spec_empty_name_raises():
    with pytest.raises(GateChainError):
        GateSpec(name="  ", cls="redline")


def test_run_chain_empty_denied():
    with pytest.raises(GateChainError):
        run_gate_chain({}, [], on_fail=lambda s, r: _Deny())


def test_run_chain_short_circuit_on_deny():
    gates = [
        (_spec("pre", "precheck"), lambda p: True),
        (_spec("perm", "permission"), lambda p: False),
        (_spec("red", "redline"), lambda p: True),
    ]
    with pytest.raises(_Deny):
        run_gate_chain({}, gates, on_fail=lambda s, r: _Deny())


def test_run_chain_all_pass_returns_names():
    gates = [
        (_spec("pre", "precheck"), lambda p: True),
        (_spec("perm", "permission"), lambda p: True),
        (_spec("trace", "traceability"), lambda p: True),
    ]
    assert run_gate_chain({}, gates, on_fail=lambda s, r: _Deny()) == [
        "pre", "perm", "trace"]


def test_run_chain_check_exception_denied():
    gates = [(_spec("perm", "permission"), lambda p: 1 / 0)]
    with pytest.raises(_Deny):
        run_gate_chain({}, gates, on_fail=lambda s, r: _Deny())


def test_evaluate_chain_all_pass():
    gates = [(_spec("a", "precheck"), True), (_spec("b", "redline"), True)]
    assert evaluate_chain(gates) is True


def test_evaluate_chain_empty_false():
    assert evaluate_chain([]) is False


def test_evaluate_chain_with_deny_false():
    gates = [(_spec("a", "precheck"), True), (_spec("b", "redline"), False)]
    assert evaluate_chain(gates) is False


def test_parity_consumer_four_class_chain():
    """parity 形态：消费方用四分类编排任意 N 级闸（去重收口验证）。"""
    gates = [
        (_spec("scope_violation", "precheck"), lambda p: bool(p.get("scope"))),
        (_spec("rbac", "permission"), lambda p: p.get("role") == "admin"),
        (_spec("redline", "redline"), lambda p: not p.get("hit_redline")),
        (_spec("audit", "traceability"), lambda p: True),
    ]
    ok_payload = {"scope": "x", "role": "admin", "hit_redline": False}
    assert run_gate_chain(ok_payload, gates, on_fail=lambda s, r: _Deny()) == [
        "scope_violation", "rbac", "redline", "audit"]
    deny_payload = {"scope": "x", "role": "user", "hit_redline": False}
    with pytest.raises(_Deny):
        run_gate_chain(deny_payload, gates, on_fail=lambda s, r: _Deny())
