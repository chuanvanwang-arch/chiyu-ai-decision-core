"""SecurityDecision.extensions 扩展槽守卫（裁定 APS ②a：消费方统一基座 5 字段形）。

裁定：消费方（APS）统一采用基座 SecurityDecision 5 字段形，留痕字段经 extensions
Mapping 携带；基座对 extensions 仅保证结构（Mapping + 键不与核心字段冲突），不参与判定不变量。

⛔ 变异自证：删 extensions 冲突校验 ⇒ test_extension_key_collision_with_core_field_rejected 必红；
   删 Mapping 形态校验 ⇒ test_extension_must_be_mapping 必红（删判据分支→转红→还原）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract import (
    SECURITY_DECISION_EXTENSION_RULE,
    SECURITY_DECISION_FIELDS,
    SecurityDecision,
)


def test_extension_rule_constant_present_and_generic():
    """裁定约定以契约常量落地（契约层写清，非仅文档）。"""
    assert isinstance(SECURITY_DECISION_EXTENSION_RULE, str)
    assert "extensions" in SECURITY_DECISION_EXTENSION_RULE
    # 核心判定语义面仍是 5 字段，extensions 不参与不变量
    assert SECURITY_DECISION_FIELDS == ("mode", "allowed", "would_deny", "reason", "scope")


def test_default_extensions_is_empty_mapping_and_frozen_ok():
    """默认 extensions={}；frozen dataclass 仍可正常构造与哈希。"""
    d = SecurityDecision(mode="advisory", allowed=True, would_deny=False)
    assert d.extensions == {}
    assert hash(d) == hash(d)


def test_aps_trace_fields_carried_in_extensions():
    """APS 留痕字段（action/namespace/required_perm）经 extensions 携带不丢值。"""
    d = SecurityDecision(
        mode="enforced", allowed=False, would_deny=True,
        extensions={"action": "approve", "namespace": "tenant:acme",
                     "required_perm": "redline.approve"},
    )
    assert d.extensions["action"] == "approve"
    assert d.extensions["namespace"] == "tenant:acme"
    assert d.extensions["required_perm"] == "redline.approve"


def test_extension_key_collision_with_core_field_rejected():
    """扩展键镜像核心字段（如 mode）⇒ 结构保证抛错（防基线漂移 / 双副本失真）。"""
    with pytest.raises(ValueError):
        SecurityDecision(mode="advisory", allowed=True, would_deny=False,
                         extensions={"mode": "enforced"})


def test_extension_must_be_mapping():
    """extensions 非 Mapping（如 list）⇒ 抛错（基座不解释内容但须保证形态）。"""
    with pytest.raises(ValueError):
        SecurityDecision(mode="advisory", allowed=True, would_deny=False,
                         extensions=["action"])  # type: ignore[arg-type]


def test_enforced_invariant_holds_with_extensions_present():
    """enforced 下 would_deny==(not allowed) 不变量在 extensions 非空时仍成立。"""
    ok = SecurityDecision(mode="enforced", allowed=False, would_deny=True,
                          extensions={"action": "approve"})
    assert ok.would_deny == (not ok.allowed)
    with pytest.raises(ValueError):
        SecurityDecision(mode="enforced", allowed=False, would_deny=False,
                         extensions={"action": "approve"})
