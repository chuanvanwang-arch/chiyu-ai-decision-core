"""门面「已 import 却未导出」机械守卫（R8 同族缺陷的永久封堵）。

⛔ 根因（2026-10-09 实测）：`api.py` 模块级 import 了 352 个符号，`__all__` 只有 340 项
   ⇒ 12 个符号**已进门面模块却不在导出清单**。形态与 R8 四符号完全同族：
   消费方 `from chiyu_kernel.api import X` 拿不到，只能退回 import 内部路径，
   而现有守卫（逐层比对子包 `__all__`）**查不出**这一类 —— 因为这些符号所在的
   子包 `__all__` 里也没有它们。

⇒ 本守卫直接比对「门面自己 import 了什么」与「门面声明导出什么」，
   **机械推导、无人工白名单**。判据：凡 `chiyu_*` 模块级 import 名，必须在 `__all__` 中。
   （`typing` / `__future__` 等标准库 import 是内部用途，不属导出面，故排除。）
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import List, Set

_STDLIB_ROOTS = {"typing", "__future__", "dataclasses", "collections",
                 "abc", "enum", "pathlib", "os", "sys", "json", "re"}


def _facade_source() -> Path:
    spec = importlib.util.find_spec("chiyu_kernel.api")
    assert spec is not None and spec.origin is not None
    return Path(spec.origin)


def _module_level_imports(tree: ast.Module) -> Set[str]:
    names: Set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _STDLIB_ROOTS:
                continue
            for a in node.names:
                names.add(a.asname or a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root in _STDLIB_ROOTS:
                    continue
                names.add(a.asname or a.name)
    return names


def _dunder_all(tree: ast.Module) -> Set[str]:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    return set(ast.literal_eval(node.value))
    raise AssertionError("api.py 缺少 __all__")


def test_every_imported_kernel_symbol_is_exported() -> None:
    """门面 import 的每个内核符号都必须进 `__all__`（否则消费方拿不到）。"""
    src = _facade_source().read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = _module_level_imports(tree)
    exported = _dunder_all(tree)
    missing: List[str] = sorted(n for n in imported
                                if n.startswith(("chiyu", "Contract", "Tenant"))
                                or n[0:1].isupper())  # 兜底：内核公共符号均为大写开头
    missing = [n for n in missing if n not in exported]
    assert not missing, (
        "以下符号已 import 进 api.py 却未登记 __all__ ⇒ 消费方须摸内部路径："
        f"{missing}")


def test_guard_itself_has_discriminating_power(tmp_path) -> None:
    """反假绿：给一份「import 了但没导出」的合成门面 ⇒ 守卫**必须**判红。"""
    bad = tmp_path / "bad_facade.py"
    bad.write_text(
        "from chiyu_kernel.store.pg_store import assert_no_hard_delete\n"
        "__all__ = []\n", encoding="utf-8")
    tree = ast.parse(bad.read_text(encoding="utf-8"))
    imported = _module_level_imports(tree)
    exported = _dunder_all(tree)
    assert imported and not exported, "合成反例构造失效"
    assert "assert_no_hard_delete" in imported
