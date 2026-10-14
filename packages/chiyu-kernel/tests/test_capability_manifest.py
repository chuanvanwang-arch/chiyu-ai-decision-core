"""CRM R1 —— capability manifest 守卫（机器可读能力清单，跨仓引用稳定 ID）。

CRM 回信 R1（2026-10-09）：跨仓引用一律用 capability_id，取代 `file:line` 锚点；
字段至少 capability_id / package / status / semantics / verify_entry / since_version。

本守卫保证 `contract/capability-manifest.json` 与 `chiyu_kernel.version.CAPABILITIES`
**单一事实源一致**：新增能力不登记（语义/验证入口缺失、状态越界、ID 不齐）即红。
判别力自证：删除一项 manifest 的 capability_id → 立即转红。
"""
from __future__ import annotations

import io
import json
import os

import pytest

from chiyu_kernel.version import CAPABILITIES, VALID_STATUSES

# tests/ -> chiyu-kernel/ -> packages/ -> 仓库根（向上 3 级）
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
MANIFEST_PATH = os.path.join(ROOT, "contract", "capability-manifest.json")


def _load_manifest() -> dict:
    with io.open(MANIFEST_PATH, encoding="utf-8") as fp:
        return json.load(fp)


def test_manifest_exists_and_schema():
    d = _load_manifest()
    assert d["schema"] == "capability-manifest/1"
    caps = d["capabilities"]
    assert isinstance(caps, list) and caps


def test_manifest_capability_ids_exactly_equal_capabilities():
    """与 `chiyu_kernel.version.CAPABILITIES` 完全一致（少/多/改名即红）。"""
    expected = {name for name, _ in CAPABILITIES}
    got = {e["capability_id"] for e in _load_manifest()["capabilities"]}
    assert got == expected, f"缺失/多余：{expected ^ got}"


def test_manifest_status_matches_capabilities():
    """每项 status 与 CAPABILITIES 同一来源（漂移即红）。"""
    status_of = {name: status for name, status in CAPABILITIES}
    for e in _load_manifest()["capabilities"]:
        assert e["capability_id"] in status_of
        assert e["status"] == status_of[e["capability_id"]]
        assert e["status"] in VALID_STATUSES


def test_manifest_required_fields_present():
    """CRM R1 六字段齐全（缺任一字段/空值即红）。"""
    for e in _load_manifest()["capabilities"]:
        assert e["capability_id"]
        assert e["package"] in ("chiyu-kernel", "chiyu-decision")
        assert e["semantics"]
        assert e["verify_entry"]
        assert e["since_version"]


def test_manifest_mutation_discrimination():
    """变异自证：删一项 capability_id 立即转红（守卫非空跑恒绿）。"""
    d = _load_manifest()
    d["capabilities"] = d["capabilities"][1:]  # 删掉第一项
    with pytest.raises(AssertionError):
        expected = {name for name, _ in CAPABILITIES}
        got = {e["capability_id"] for e in d["capabilities"]}
        assert got == expected
