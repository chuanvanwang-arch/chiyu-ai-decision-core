"""N6 守卫：AgentRegistry baseline 登记样例可用 + 注册期三闸真的会拒。

⛔ 可证伪判据（蓝图 §3）：不只测"登记成功"，还各配一条**破坏性构造**
   证明三道注册期闸真会转红 —— 否则样例只是恒绿装饰。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.api import AgentRegistry, AgentRegistryError, AgentSpec

from reference_consumer.agents import build_baseline_agents, register_baseline_agents


def test_baseline_agents_register_and_retrievable():
    """正向：baseline 登记成功、可取回、字段完整。"""
    registry = AgentRegistry()
    keys = register_baseline_agents(registry)
    assert keys == ("reference-consumer-agent",)
    spec = registry.get("reference-consumer-agent")
    assert spec is not None
    assert spec.contract_task_id == "ct-reference-consumer"
    assert spec.skills and spec.memory and spec.success  # 契约字段非空


def test_baseline_spec_passes_registry_gates():
    """baseline 清单本身必须过得了注册期闸（样例不能自己先违规）。"""
    registry = AgentRegistry()
    for spec in build_baseline_agents():  # 不经幂等包装，直接登记
        registry.register(spec)  # 违规即抛 ⇒ 测试红


def test_gate_missing_success_rejected():
    """闸①：缺 success ⇒ 注册期拒绝（无成功标准的 agent 跑完也无法判成败）。"""
    bad = AgentSpec(
        key="no-success-agent", contract_task_id="ct-x",
        skills=("s",), memory=("m",), success="  ",  # 空白 success
    )
    with pytest.raises(AgentRegistryError, match="success"):
        AgentRegistry().register(bad)


def test_gate_duplicate_key_rejected():
    """闸②：重复 key ⇒ 拒绝。"""
    spec = build_baseline_agents()[0]
    registry = AgentRegistry()
    registry.register(spec)
    with pytest.raises(AgentRegistryError, match="重复注册"):
        registry.register(spec)


def test_gate_contract_key_owned_rejected():
    """闸③：契约键已被他人持有 ⇒ 拒绝（应并入，不得另起）。"""
    first = build_baseline_agents()[0]
    second = AgentSpec(
        key="another-agent", contract_task_id=first.contract_task_id,
        skills=("s",), memory=("m",), success="另一 agent 的可判定成功判据",
    )
    registry = AgentRegistry()
    registry.register(first)
    with pytest.raises(AgentRegistryError, match="契约键"):
        registry.register(second)


def test_reregister_same_spec_is_idempotent():
    """幂等：同 spec 重复登记（同进程二次 build_app 场景）不抛、不重复。"""
    registry = AgentRegistry()
    keys1 = register_baseline_agents(registry)
    keys2 = register_baseline_agents(registry)
    assert keys1 == keys2 == ("reference-consumer-agent",)
