"""T8 幂等键 —— 含反向用例（空 scope / 空 window 必须抛，换 window 必须换键）。"""
from __future__ import annotations

import pytest

from chiyu_kernel.orchestration.idem import (
    IDEM_PREFIX,
    derive_idem_key,
    nightly_idem_key,
)


def test_same_content_same_key():
    a = derive_idem_key("scope-a", [{"k": 1, "j": 2}, "x"])
    b = derive_idem_key("scope-a", [{"j": 2, "k": 1}, "x"])
    assert a == b, "键序不同不应影响键（排序后序列化）"
    assert a.startswith(f"{IDEM_PREFIX}:scope-a:")


def test_content_change_changes_key():
    a = derive_idem_key("s", [{"k": 1}])
    b = derive_idem_key("s", [{"k": 2}])
    assert a != b


def test_scope_change_changes_key():
    assert derive_idem_key("s1", ["x"]) != derive_idem_key("s2", ["x"])


def test_empty_scope_rejected():
    """空 scope ⇒ 不同批次撞同一个键，必须在入口就拒。"""
    for bad in ("", "   "):
        with pytest.raises(ValueError, match="scope"):
            derive_idem_key(bad, ["x"])


def test_nightly_window_in_key():
    """换 window ⇒ 键变。这是"跨天不撞键"的唯一保证。"""
    a = nightly_idem_key("tune", window="2026-09-22", parts=[{"k": 1}])
    b = nightly_idem_key("tune", window="2026-09-23", parts=[{"k": 1}])
    assert a != b
    assert "tune@2026-09-22" in a


def test_nightly_same_window_same_key():
    a = nightly_idem_key("tune", window="2026-09-22", parts=[{"k": 1}])
    b = nightly_idem_key("tune", window="2026-09-22", parts=[{"k": 1}])
    assert a == b, "同窗口同内容重跑应拿到同键（据此判重）"


def test_nightly_reason_and_window_required():
    with pytest.raises(ValueError, match="reason"):
        nightly_idem_key("", window="2026-09-22", parts=["x"])
    with pytest.raises(ValueError, match="window"):
        nightly_idem_key("tune", window="", parts=["x"])
