"""T5 守卫：Agent 注册期拒绝 —— 判别力自证。

⛔ 必须能**拒绝**：若缺 `success` 的 agent 也能注册，它跑完后无人能判定成败；
   若契约键可被两个 agent 共用，追溯时就分不清是谁干的。两者都必须注册期抛错。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.orchestration.agent_registry import (
    AgentRegistry,
    AgentRegistryError,
    AgentSpec,
)


def _spec(key="a1", task="ct-x", success="契约校验退出码为 0", **over) -> AgentSpec:
    base = dict(key=key, contract_task_id=task, skills=("ai-capability-audit",),
                memory=("chiyu-foundation",), success=success)
    base.update(over)
    return AgentSpec(**base)


# ── 正常注册 ──────────────────────────────────────────────────────────
def test_well_formed_agent_is_registered():
    r = AgentRegistry()
    r.register(_spec())
    assert r.keys() == ("a1",)
    assert r.get("a1").contract_task_id == "ct-x"


# ── 契约缺项 ⇒ 注册期拒绝 ─────────────────────────────────────────────
@pytest.mark.parametrize("field", ["contract_task_id", "skills", "memory", "success"])
def test_missing_contract_field_is_rejected(field):
    r = AgentRegistry()
    spec = _spec(**{field: "" if field != "skills" else ()})
    with pytest.raises(AgentRegistryError, match="契约不完整"):
        r.register(spec)
    assert r.keys() == (), "被拒的 agent 不得进入注册表"


def test_empty_key_is_rejected():
    with pytest.raises(AgentRegistryError, match="契约不完整"):
        AgentRegistry().register(_spec(key="  "))


# ── 冲突 ⇒ 注册期拒绝 ─────────────────────────────────────────────────
def test_duplicate_key_is_rejected():
    r = AgentRegistry()
    r.register(_spec())
    with pytest.raises(AgentRegistryError, match="重复注册"):
        r.register(_spec(success="另一条成功标准"))


def test_contract_task_conflict_is_rejected():
    """同一契约键被第二个 agent 持有 ⇒ 追溯时无法定位责任方。"""
    r = AgentRegistry()
    r.register(_spec(key="a1"))
    with pytest.raises(AgentRegistryError, match="契约键"):
        r.register(_spec(key="a2"))
    assert r.keys() == ("a1",)


def test_same_task_different_keys_both_rejected_but_first_survives():
    r = AgentRegistry()
    r.register(_spec(key="a1", task="ct-1"))
    with pytest.raises(AgentRegistryError):
        r.register(_spec(key="a2", task="ct-1"))
    assert r.get("a2") is None


# ── 形容词式 success 要出声（不是静默通过）────────────────────────────
def test_adjective_success_is_flagged_by_audit():
    r = AgentRegistry()
    r.register(_spec(success="很好"))          # 过短，疑似形容词
    problems = r.audit()
    assert problems and "success" in problems[0]


def test_judgement_style_success_passes_audit():
    r = AgentRegistry()
    r.register(_spec(success="契约校验器退出码为 0 且回归 180 全绿"))
    assert r.audit() == []
