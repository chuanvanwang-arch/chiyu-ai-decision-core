"""可编译友好检查器的**判别力自证**（探针不得骗人）。

每条检查项必须"该红则红、该绿则绿"双向验证；只有"干净文件绿"而无突变红，
说明检查器可能是空跑（本项目已踩过这类假绿）。

⛔ C4 用例随判据修正而调整：C4 的靶子是「用运行时手段造类」，故
   ① 契约里定义类却不 import dataclasses ⇒ 红；
   ② 纯常量模块 / 纯 re-export 模块（无类定义）⇒ 绿。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from check_cython_friendly import (  # noqa: E402
    CODE_C1, CODE_C2, CODE_C3, CODE_C4, check_file,
)

CLEAN = '''\
from dataclasses import dataclass


@dataclass(frozen=True)
class Foo:
    a: int = 1


def bar(x: int) -> int:
    return x + 1
'''


def _run(tmp_path: Path, name: str, body: str):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return check_file(p, tmp_path)


def test_clean_file_has_no_findings(tmp_path: Path):
    assert _run(tmp_path, "clean.py", CLEAN) == []


def test_c1_runtime_class_is_caught(tmp_path: Path):
    body = 'X = type("X", (object,), {"a": 1})\n'
    codes = [f["code"] for f in _run(tmp_path, "c1.py", body)]
    assert CODE_C1 in codes


def test_c1_new_class_is_caught(tmp_path: Path):
    body = "import types\nX = types.new_class('X', (object,))\n"
    assert CODE_C1 in [f["code"] for f in _run(tmp_path, "c1b.py", body)]


def test_c2_kwargs_is_caught(tmp_path: Path):
    body = "def f(**kwargs):\n    return kwargs\n"
    codes = [f["code"] for f in _run(tmp_path, "c2.py", body)]
    assert CODE_C2 in codes


def test_c3_variable_getattr_is_caught_but_constant_is_not(tmp_path: Path):
    bad = "import os\nn = 'getcwd'\nf = getattr(os, n)\n"
    assert CODE_C3 in [f["code"] for f in _run(tmp_path, "c3a.py", bad)]
    good = "import os\nf = getattr(os, 'getcwd')\n"
    assert CODE_C3 not in [f["code"] for f in _run(tmp_path, "c3b.py", good)]


def test_c3_importlib_is_caught(tmp_path: Path):
    body = "import importlib\nm = importlib.import_module('os')\n"
    assert CODE_C3 in [f["code"] for f in _run(tmp_path, "c3c.py", body)]


def test_c4_contract_module_with_class_must_be_static(tmp_path: Path):
    body = "class Foo:\n    pass\n"          # 有类、无 dataclass/pydantic
    codes = [f["code"] for f in _run(tmp_path, "contract/particle.py", body)]
    assert CODE_C4 in codes


def test_c4_dataclass_contract_is_clean(tmp_path: Path):
    body = "from dataclasses import dataclass\n\n\n@dataclass\nclass Foo:\n    a: int = 1\n"
    assert CODE_C4 not in [f["code"] for f in _run(tmp_path, "contract/ok.py", body)]


def test_c4_constants_only_module_is_exempt(tmp_path: Path):
    """纯常量模块比 dataclass 更静态 ⇒ 不得被判违规（否则 guard 天天误报被绕过）。"""
    body = 'ATTRS = ("a", "b")\n'
    assert CODE_C4 not in [f["code"] for f in _run(tmp_path, "contract/consts.py", body)]


def test_c4_reexport_module_is_exempt(tmp_path: Path):
    """纯 re-export 模块（contract/__init__.py 的形态）不得被判违规。"""
    body = "from .a import b\nfrom .c import d\n\n__all__ = ['b', 'd']\n"
    assert CODE_C4 not in [f["code"] for f in _run(tmp_path, "contract/__init__.py", body)]


def test_syntax_error_is_reported_not_crashed(tmp_path: Path):
    assert [f["code"] for f in _run(tmp_path, "broken.py", "def (:\n")] == ["SYNTAX"]
