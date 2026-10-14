"""A3 判据：消费方只许 import 契约与门面，不得 import 内核内部实现。

实现方式：扫描"消费方目录"的 import 语句（AST），命中
`chiyu_kernel.<内部模块>` 即失败。白名单：`chiyu_kernel` / `chiyu_kernel.contract`
/ `chiyu_kernel.api`。

⛔ 为什么必须扫描源码而不是"看代码习惯"：习惯不会在 CI 里变红。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ALLOWED = {"chiyu_kernel", "chiyu_kernel.contract", "chiyu_kernel.api"}


def _imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend((node.lineno, a.name) for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append((node.lineno, node.module))
    return out


def check_consumer_dir(root: Path) -> list[str]:
    bad: list[str] = []
    for p in sorted(root.rglob("*.py")):
        for lineno, mod in _imports(p):
            if mod.startswith("chiyu_kernel") and mod not in ALLOWED:
                bad.append(f"{p.relative_to(root)}:{lineno} import {mod}")
    return bad


@pytest.mark.parametrize("sample", ["violating", "clean"])
def test_guard_discriminates(tmp_path: Path, sample: str):
    """判别力自证：含违约 import 的样本必须被检出，干净样本必须通过。"""
    d = tmp_path / sample
    d.mkdir()
    if sample == "violating":
        (d / "a.py").write_text("from chiyu_kernel.store.pg_store import PgVectorStore\n")
    else:
        (d / "a.py").write_text("from chiyu_kernel.contract import TenantProfile\n")
    found = check_consumer_dir(d)
    assert bool(found) is (sample == "violating")
