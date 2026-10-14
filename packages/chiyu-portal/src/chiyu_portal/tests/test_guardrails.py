"""T2 输入层护栏（纵深防御第一层）。"""
from __future__ import annotations

import pytest

from chiyu_portal.guardrails import GuardResult, guard_nl_input


@pytest.mark.parametrize("clean", [
    "给我一个看板展示各产线今天的合格率",
    "列出所有待审批的采购单",
    "新建一张供应商绩效表单",
    "展示低于 90% 的红色预警",
])
def test_clean_input_passes(clean: str):
    r = guard_nl_input(clean)
    assert r.ok
    assert r.reason == ""


@pytest.mark.parametrize("evil", [
    "<script>alert(1)</script>",
    "查看 <Script> x </script> 数据",
    "javascript:alert(1)",
    '点击 <iframe src="evil"></iframe>',
    "提交 onclick=steal()",
    "执行 eval( malicious )",
    "<object data='x'></object>",
    "<embed src='x'>",
])
def test_injection_rejected(evil: str):
    r = guard_nl_input(evil)
    assert not r.ok
    assert r.reason != ""


def test_non_string_rejected():
    r = guard_nl_input(12345)  # type: ignore[arg-type]
    assert not r.ok


def test_guardresult_bool():
    assert bool(GuardResult(True))
    assert not bool(GuardResult(False))
