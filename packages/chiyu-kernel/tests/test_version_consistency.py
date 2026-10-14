"""N1 版本钉一致性 + deprecation 政策可机检（守 CHANGELOG 与政策文档不漂移）。

⛔ 为什么连"文档是否存在"都要断言：N1 的四件交付物中三件是文档/策略类
   （CHANGELOG / deprecation 政策 / 版本出口）。文档缺失**不产生任何报错**，
   而消费方做版本钉时会发现"没有可依据的东西" —— 与本项目反复踩的
   "判据存在但无人跑 = 不存在"同族。故此处把交付物存在性写成判据。

⛔ 反假绿：`__version__` 若写成硬编码常量，pyproject 升版后它仍绿（静默漂移）。
   本测试直接比对 `pyproject.toml` ⇒ 漂移即红。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from chiyu_kernel import api

ROOT = Path(__file__).resolve().parents[3]      # tests/ -> chiyu-kernel/ -> packages/ -> 仓库根


def _pyproject_version() -> str:
    text = (ROOT / "packages" / "chiyu-kernel" / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    assert m, "pyproject.toml 未声明 version"
    return m.group(1)


def test_version_exported_and_matches_pyproject() -> None:
    """`__version__` 可从门面取到，且与分发包声明一致（不做版本钉漂移）。"""
    assert hasattr(api, "__version__"), "门面无 __version__ ⇒ 消费方无法版本钉"
    assert "__version__" in api.__all__
    assert api.__version__ == _pyproject_version(), (
        f"__version__={api.__version__} 与 pyproject={_pyproject_version()} 不一致")


def test_version_is_dynamic_not_hardcoded() -> None:
    """反假绿：版本号须来自分发元数据（或兜底常量），不得是另一套硬编码字面量。"""
    from chiyu_kernel import version as vmod
    src = Path(vmod.__file__).read_text(encoding="utf-8")
    assert "importlib.metadata" in src, "`__version__` 未走分发元数据 ⇒ 升版会静默漂移"
    assert vmod.PACKAGE_VERSION == _pyproject_version(), "兜底常量与 pyproject 不一致"


def test_deprecated_aliases_still_importable() -> None:
    """deprecation 政策第 1 条：标记期内旧名**必须**仍可用（禁止标记即移除）。"""
    for old in api.deprecations():
        assert hasattr(api, old), f"弃用旧名 {old} 已被移除 ⇒ 违反先 warn 一版的政策"


def test_deprecation_map_points_to_existing_new_names() -> None:
    """`DEPRECATIONS` 的新名必须真实存在（否则消费方按图索骥撞空）。"""
    for old, new in api.deprecations().items():
        assert hasattr(api, new), f"{old} 指向的新名 {new} 不存在"


@pytest.mark.parametrize("rel", [
    "CHANGELOG.md",
    "docs/versioning-and-deprecation.md",
    "docs/sanctioned-import-surface.md",
])
def test_n1_deliverables_exist(rel: str) -> None:
    """N1/N2 的文档类交付物存在（缺失零报错，故须显式断言）。"""
    p = ROOT / rel
    assert p.is_file(), f"缺交付物 {rel}"
    assert p.stat().st_size > 200, f"{rel} 内容过短 ⇒ 疑似空壳"
