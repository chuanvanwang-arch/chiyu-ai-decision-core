"""test_scenario_pack.py —— ScenarioPack 模型/存储/MCP 工具面全量单测。

变异自证（T4 契约判据，2026-09-26 实测记录）：
- 删除 model.py `_validate_workflow` 里的 Kahn 环检测分支 → `test_workflow_cycle_rejected` 红；
- 删除 store.py `lock` 的异 holder 互斥分支 → `test_lock_conflicting_holder_rejected` 红；
还原后复绿。只跑绿不算验收。
"""
from __future__ import annotations

import json

import pytest

from chiyu_kernel.api import (
    LEVEL_IDS, ScenarioPack, ScenarioPackError, ScenarioPackLockDenied,
    ScenarioPackStore, scenario_build_in_memory_server, scenario_from_dict,
)
from chiyu_kernel.mcp import McpBridge
from chiyu_kernel.plugins import BUILTIN_PLUGINS, PluginRegistry
from chiyu_kernel.tools import ToolRegistry

# ── fixtures ────────────────────────────────────────────────────────────────

VALID_PACK = {
    "id": "demo-pack",
    "name": "演示包",
    "level": "flow",
    "direction": "generic",
    "mode": "standard",
    "plugins": ["terminal", "loop"],
    "workflow": {"steps": [
        {"name": "step-a", "prompt": "做 A", "depends_on": []},
        {"name": "step-b", "prompt": "做 B", "depends_on": ["step-a"]},
    ]},
    "knowledge_needs": [{"layer": "L1", "dims": ["semantics"]}],
}


def _registry() -> PluginRegistry:
    reg = PluginRegistry()
    for spec in BUILTIN_PLUGINS:
        reg.register(spec)
    return reg


# ── T1 模型：from_dict 四类非法输入逐一抛对应错误码 ─────────────────────────

def test_valid_pack_roundtrip():
    pack = scenario_from_dict(VALID_PACK, plugin_registry=_registry())
    assert pack.id == "demo-pack" and pack.level == "flow" and pack.mode == "standard"
    d = pack.to_dict()
    assert d["workflow"]["steps"][1]["depends_on"] == ["step-a"]
    # to_dict → from_dict 往返一致
    pack2 = scenario_from_dict(d, plugin_registry=_registry())
    assert pack2.to_dict() == d


def test_meta_invalid_bad_id():
    with pytest.raises(ScenarioPackError) as ei:
        scenario_from_dict({**VALID_PACK, "id": "Bad_Id"})
    assert ei.value.code == "PACK_META_INVALID"


def test_meta_invalid_empty_name():
    with pytest.raises(ScenarioPackError) as ei:
        scenario_from_dict({**VALID_PACK, "name": "  "})
    assert ei.value.code == "PACK_META_INVALID"


def test_meta_invalid_bad_level():
    with pytest.raises(ScenarioPackError) as ei:
        scenario_from_dict({**VALID_PACK, "level": "mega"})
    assert ei.value.code == "PACK_META_INVALID"


def test_meta_invalid_bad_mode():
    with pytest.raises(ScenarioPackError) as ei:
        scenario_from_dict({**VALID_PACK, "mode": "turbo"})
    assert ei.value.code == "PACK_META_INVALID"


def test_plugin_unknown_rejected():
    bad = {**VALID_PACK, "plugins": ["terminal", "no-such-plugin"]}
    with pytest.raises(ScenarioPackError) as ei:
        scenario_from_dict(bad, plugin_registry=_registry())
    assert ei.value.code == "PACK_PLUGIN_UNKNOWN"


def test_workflow_invalid_empty_steps():
    with pytest.raises(ScenarioPackError) as ei:
        scenario_from_dict({**VALID_PACK, "workflow": {"steps": []}})
    assert ei.value.code == "PACK_WORKFLOW_INVALID"


def test_workflow_invalid_duplicate_names():
    bad = {**VALID_PACK, "workflow": {"steps": [
        {"name": "step-a", "prompt": "p", "depends_on": []},
        {"name": "step-a", "prompt": "q", "depends_on": []},
    ]}}
    with pytest.raises(ScenarioPackError) as ei:
        scenario_from_dict(bad)
    assert ei.value.code == "PACK_WORKFLOW_INVALID"


def test_workflow_invalid_missing_dep():
    bad = {**VALID_PACK, "workflow": {"steps": [
        {"name": "step-a", "prompt": "p", "depends_on": ["ghost"]},
    ]}}
    with pytest.raises(ScenarioPackError) as ei:
        scenario_from_dict(bad)
    assert ei.value.code == "PACK_WORKFLOW_INVALID"


def test_workflow_cycle_rejected():
    bad = {**VALID_PACK, "workflow": {"steps": [
        {"name": "a", "prompt": "p", "depends_on": ["b"]},
        {"name": "b", "prompt": "p", "depends_on": ["a"]},
    ]}}
    with pytest.raises(ScenarioPackError) as ei:
        scenario_from_dict(bad)
    assert ei.value.code == "PACK_WORKFLOW_INVALID"


def test_needs_invalid_bad_layer():
    bad = {**VALID_PACK, "knowledge_needs": [{"layer": "L9", "dims": []}]}
    with pytest.raises(ScenarioPackError) as ei:
        scenario_from_dict(bad)
    assert ei.value.code == "PACK_NEEDS_INVALID"


def test_to_workflow_topo_and_fallback():
    pack = scenario_from_dict(VALID_PACK)
    wf = pack.to_workflow()
    assert wf.topo_order() == ["step-a", "step-b"]
    # Workflow 构造自身二次兜底：绕过校验闸直接注入环 → topo_order 抛 ValueError
    from chiyu_kernel.api import Workflow, WorkflowMeta, WorkflowStep
    cyclic = Workflow(
        meta=WorkflowMeta(name="cyclic", description="x"),
        steps=[
            WorkflowStep(name="a", prompt="p", depends_on=["b"]),
            WorkflowStep(name="b", prompt="p", depends_on=["a"]),
        ],
    )
    with pytest.raises(ValueError):
        cyclic.topo_order()


# ── T2 Store：落盘往返 / 锁定幂等与互斥 ─────────────────────────────────────

def test_store_save_scan_get_roundtrip(tmp_path):
    store = ScenarioPackStore(tmp_path / "packs")
    store.save(scenario_from_dict(VALID_PACK))
    store2 = ScenarioPackStore(tmp_path / "packs")
    loaded = store2.scan()
    assert loaded == ["demo-pack"]
    assert store2.get("demo-pack").to_dict()["level"] == "flow"
    # 磁盘上是合法 JSON（可被 MCP 客户端直接读取）
    raw = json.loads((tmp_path / "packs" / "demo-pack.json").read_text(encoding="utf-8"))
    assert raw["id"] == "demo-pack"


def test_get_missing_pack_raises():
    store = ScenarioPackStore("/nonexistent-packs-for-test")
    store.scan()
    with pytest.raises(ScenarioPackError) as ei:
        store.get("ghost")
    assert ei.value.code == "PACK_NOT_FOUND"


def test_lock_idempotent_same_holder(tmp_path):
    store = ScenarioPackStore(tmp_path / "packs")
    store.save(scenario_from_dict(VALID_PACK))
    store.lock("demo-pack", "alice")
    store.lock("demo-pack", "alice")  # 同 holder 幂等
    assert store.get("demo-pack").locked_by == "alice"


def test_lock_conflicting_holder_rejected(tmp_path):
    store = ScenarioPackStore(tmp_path / "packs")
    store.save(scenario_from_dict(VALID_PACK))
    store.lock("demo-pack", "alice")
    with pytest.raises(ScenarioPackError) as ei:
        store.lock("demo-pack", "bob")
    assert ei.value.code == "PACK_ALREADY_LOCKED"
    assert store.get("demo-pack").locked_by == "alice"  # 状态未被破坏


def test_unlock_requires_holder_or_force(tmp_path):
    store = ScenarioPackStore(tmp_path / "packs")
    store.save(scenario_from_dict(VALID_PACK))
    store.lock("demo-pack", "alice")
    with pytest.raises(ScenarioPackError) as ei:
        store.unlock("demo-pack", "bob")
    assert ei.value.code == "PACK_LOCKED_OTHER"
    store.unlock("demo-pack", "bob", force=True)  # 显式 force 放行
    assert store.get("demo-pack").locked_by is None


def test_select_marks_state(tmp_path):
    store = ScenarioPackStore(tmp_path / "packs")
    store.save(scenario_from_dict(VALID_PACK))
    store.select("demo-pack")
    listed = store.list()
    assert listed[0]["id"] == "demo-pack" and listed[0]["selected"] is True


# ── T3 MCP 工具面：真桥路径（McpBridge + InMemoryServer）───────────────────

def _bridge(tmp_path) -> tuple[McpBridge, ToolRegistry, ScenarioPackStore]:
    store = ScenarioPackStore(tmp_path / "packs")
    server = scenario_build_in_memory_server(store)
    bridge = McpBridge(server, "scenario")
    registry = ToolRegistry()
    tools = bridge.connect(registry)
    return bridge, registry, store


def test_mcp_bridge_registers_three_tools(tmp_path):
    bridge, registry, _ = _bridge(tmp_path)
    names = [n for n in registry.names() if n.startswith("mcp__scenario__")]
    assert len(names) == 3
    bridge.disconnect(registry)


def test_mcp_write_persists_pack(tmp_path):
    bridge, registry, store = _bridge(tmp_path)
    pub = "mcp__scenario__scenario-pack-write"
    res = bridge.call_tool(pub, {"pack": VALID_PACK})
    assert res["ok"] is True
    assert (tmp_path / "packs" / "demo-pack.json").exists()
    # 走的是同一 from_dict 校验闸：非法包被拒
    from chiyu_kernel.api import ToolNotFound
    with pytest.raises(ScenarioPackError):
        bridge.call_tool(pub, {"pack": {**VALID_PACK, "level": "mega"}})
    bridge.disconnect(registry)


def test_mcp_lock_requires_confirm(tmp_path):
    bridge, registry, store = _bridge(tmp_path)
    bridge.call_tool("mcp__scenario__scenario-pack-write", {"pack": VALID_PACK})
    lock_pub = "mcp__scenario__scenario-pack-lock"
    with pytest.raises(ScenarioPackLockDenied):
        bridge.call_tool(lock_pub, {"id": "demo-pack", "holder": "alice"})  # 缺 confirm
    res = bridge.call_tool(lock_pub, {"id": "demo-pack", "holder": "alice", "confirm": True})
    assert res["locked_by"] == "alice"
    assert store.get("demo-pack").locked_by == "alice"
    bridge.disconnect(registry)
