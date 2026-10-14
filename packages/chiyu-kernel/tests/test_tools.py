import pytest
from chiyu_kernel.tools import (
    ToolSpec, ToolRegistry, ToolNotFound, ScopeDenied, GuardDenied,
)


def _reg() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ToolSpec("echo", "回显", scope="g1"), lambda a: a)
    reg.register(ToolSpec("secret", "受限", scope="g2"), lambda a: "x")
    return reg


def test_scoped_view_isolates():
    reg = _reg()
    view = reg.scoped("g1")
    assert "echo" in view.names("g1")
    assert "secret" not in view.names("g1")


def test_scope_denied_when_cross_scope():
    reg = _reg()
    with pytest.raises(ScopeDenied):
        reg.execute("secret", {}, scope="g1")          # g1 不得调 g2 工具


def test_redline_guard_blocks():
    reg = _reg()
    with pytest.raises(GuardDenied):
        reg.execute("echo", {}, scope="g1", redline_guard=lambda n, a: "hit")


def test_unknown_tool_not_found():
    reg = ToolRegistry()
    with pytest.raises(ToolNotFound):
        reg.execute("nope", {})
