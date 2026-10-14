"""版本与能力清单出口的守卫（N1 / R11 / R4）。

判据要点：
- 能力清单**机械覆盖磁盘真实子包** ⇒ 新增层忘登记即红（防"能力悄悄上线无人知"）；
- `memory` 的状态可机检（R4；T44 起 stable），不再靠读注释推断；
- 弃用别名（R10）双名同值，旧名不失效。
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import chiyu_kernel
from chiyu_kernel import api
from chiyu_kernel import version as V


def _disk_subpackages() -> list[str]:
    """机械枚举 `chiyu_kernel` 下的真实子包（不靠人记清单）。"""
    base = Path(chiyu_kernel.__file__).parent
    return sorted(
        p.name for p in base.iterdir()
        if p.is_dir() and (p / "__init__.py").exists()
        and not p.name.startswith("_")
    )


def test_api_version_is_semver_like() -> None:
    parts = V.api_version().split(".")
    assert len(parts) == 3, f"版本号须为三段语义化版本：{V.api_version()}"
    assert all(p.isdigit() for p in parts), f"版本段须为数字：{V.api_version()}"


def test_capabilities_cover_every_disk_subpackage() -> None:
    """新增子包未登记即红（判据机械推导，不由人枚举）。"""
    declared = {name for name, _ in V.capabilities()}
    on_disk = set(_disk_subpackages())
    assert on_disk, "磁盘子包枚举为空 ⇒ 判据失效"
    missing = sorted(on_disk - declared)
    assert not missing, f"下列子包已存在但未登记能力清单：{missing}"


def test_capability_statuses_are_legal() -> None:
    for name, status in V.capabilities():
        assert status in V.VALID_STATUSES, f"{name} 状态非法：{status}"


def test_memory_is_machine_checkably_stable() -> None:
    """R4：memory 状态可机检。T44（2026-10-10）毕业翻转：experimental → stable。"""
    assert V.capability_status("memory") == "stable"
    assert api.MEMORY_EXPERIMENTAL is False


def test_capability_status_is_bounded() -> None:
    with pytest.raises(KeyError):
        V.capability_status("no_such_capability")


def test_deprecated_aliases_still_resolve_and_equal() -> None:
    """R10：旧名仍可导入且与新名同值（严格加法，不破坏既有消费方）。"""
    for old, new in V.deprecations().items():
        assert hasattr(api, old), f"弃用旧名 {old} 不可导入 ⇒ 破坏既有消费方"
        assert getattr(api, old) == getattr(api, new), \
            f"{old} 与 {new} 不同值 ⇒ 分族失败"


def test_probe_capability_guard_discriminates() -> None:
    """探针：若把某真实子包从清单移除，守卫必须能检出（非恒绿）。"""
    on_disk = _disk_subpackages()
    declared = {name for name, _ in V.capabilities()}
    assert "graph" in declared, "样例层 graph 应在清单内"
    removed = declared - {"graph"}
    missing = sorted(set(on_disk) - removed)
    assert "graph" in missing, \
        "移除登记后判据未检出 ⇒ 守卫只是空跑（恒绿）"
