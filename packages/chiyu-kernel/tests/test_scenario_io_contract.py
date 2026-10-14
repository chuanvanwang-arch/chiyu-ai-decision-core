"""决策点 I/O 契约守卫（enterprise feedback #6 收口）。

覆盖：
- 正向：声明 inputs/outputs/required_gates 的登记 → require_scenario 原样取回 + to_dict 可序列化；
- 注册期 fail-fast：kind 出闭集 / name 非 kebab / 未知闸 / 闸重复 / 同侧 name 重复 / 非 DecisionIOField 项；
- 向后兼容：不声明 I/O 的旧式登记行为不变；
- 门面可达：`from chiyu_kernel.api import DecisionIOField`。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
_KERNEL_SRC = REPO / "packages" / "chiyu-kernel" / "src"
if str(_KERNEL_SRC) not in sys.path:
    sys.path.insert(0, str(_KERNEL_SRC))

from chiyu_kernel.scenario.registry import (  # noqa: E402
    DecisionIOField,
    DecisionScenarioProfile,
    GATE_KINDS,
    IO_KINDS,
    ScenarioRegistryError,
    clear_registry,
    register_scenario,
    require_scenario,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_registry()
    yield
    clear_registry()


def _io(name, kind, required=True, description=""):
    return DecisionIOField(name=name, kind=kind, required=required,
                           description=description)


def test_register_with_full_io_contract_roundtrip():
    p = register_scenario(
        "config-change",
        title="配置变更决策",
        inputs=(
            _io("config-snapshot", "particle"),
            _io("threshold-rules", "asset", required=False),
            _io("operator-id", "context"),
        ),
        outputs=(
            _io("decision-record", "particle"),
            _io("audit-trail", "event"),
            _io("referenced-precedent", "graph-edge"),
        ),
        required_gates=("redline", "approval"),
    )
    got = require_scenario("config-change")
    assert got is p
    assert [f.name for f in got.inputs] == [
        "config-snapshot", "threshold-rules", "operator-id"]
    assert got.inputs[1].required is False
    assert [f.kind for f in got.outputs] == ["particle", "event", "graph-edge"]
    assert got.required_gates == ("redline", "approval")
    # to_dict 可序列化且含 I/O
    d = got.to_dict()
    assert d["inputs"][0] == {"name": "config-snapshot", "kind": "particle",
                              "required": True, "description": ""}
    assert d["required_gates"] == ["redline", "approval"]


def test_list_input_normalized_to_tuple():
    p = register_scenario(
        "a-change", title="A",
        inputs=[_io("doc-asset", "particle")],   # list 而非 tuple
    )
    assert isinstance(p.inputs, tuple)


def test_kind_outside_closed_set_rejected():
    with pytest.raises(ScenarioRegistryError, match="闭集"):
        register_scenario("x-a", title="X",
                          inputs=(_io("foo-bar", "business-thing"),))


def test_non_kebab_name_rejected():
    with pytest.raises(ScenarioRegistryError, match="kebab"):
        register_scenario("x-b", title="X",
                          inputs=(_io("BadName", "particle"),))


def test_unknown_gate_rejected():
    with pytest.raises(ScenarioRegistryError, match="非法闸"):
        register_scenario("x-c", title="X", required_gates=("human-veto",))


def test_duplicate_gate_rejected():
    with pytest.raises(ScenarioRegistryError, match="重复"):
        register_scenario("x-d", title="X",
                          required_gates=("redline", "redline"))


def test_duplicate_name_within_side_rejected():
    with pytest.raises(ScenarioRegistryError, match="name 重复"):
        register_scenario("x-e", title="X",
                          inputs=(_io("same-key", "particle"),
                                  _io("same-key", "asset")))


def test_non_iofield_item_rejected():
    with pytest.raises(ScenarioRegistryError, match="DecisionIOField"):
        register_scenario("x-f", title="X", inputs=("naked-string",))


def test_backward_compat_no_io_registration_unchanged():
    p = register_scenario("legacy-key", title="旧式登记")
    assert p.inputs == () and p.outputs == () and p.required_gates == ()
    d = p.to_dict()
    assert d["inputs"] == [] and d["outputs"] == []
    assert d["required_gates"] == []


def test_io_kinds_and_gate_kinds_are_neutral_closed_sets():
    # 零领域字面量铁律的形态守卫：词汇表是内核自有中性词，非业务词
    assert IO_KINDS == frozenset(
        {"particle", "asset", "context", "event", "graph-edge"})
    assert GATE_KINDS == frozenset({"redline", "approval"})


def test_facade_exports_decision_io_field():
    import chiyu_kernel.api as api
    assert "DecisionIOField" in api.__all__
    assert api.DecisionIOField is DecisionIOField
    assert isinstance(api.DecisionScenarioProfile, type)
