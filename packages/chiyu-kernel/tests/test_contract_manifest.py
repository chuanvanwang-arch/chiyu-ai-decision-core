"""契约清单守卫：manifest.json 必须与磁盘实际内容一致。

为什么：双轨构建（T9）靠这份清单判"两轨是否同源"。若清单可过期，
同源校验就变成"比对一个陈旧数字"——假绿。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / "src" / "chiyu_kernel" / "contract"


def _actual() -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(CONTRACT.glob("*.py"))
        if p.name != "_gen_manifest.py"
    }


def test_manifest_matches_disk():
    manifest_path = CONTRACT / "manifest.json"
    assert manifest_path.exists(), "缺少 contract/manifest.json（先跑 _gen_manifest.py）"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = _actual()
    assert data["algo"] == "sha256"
    assert set(data["files"]) == set(actual), (
        f"清单文件集与磁盘不一致：清单独有 {set(data['files']) - set(actual)}，"
        f"磁盘独有 {set(actual) - set(data['files'])}"
    )
    drifted = [n for n, h in actual.items() if data["files"][n] != h]
    assert not drifted, f"契约已改但清单未重生成：{drifted}"


def test_manifest_covers_all_six_contract_modules():
    """六类契约齐备（设计 §2.1：粒子/属性/谓词/记忆/决策/审计）。"""
    names = set(_actual())
    for required in ("particle.py", "decision.py", "memory.py", "audit.py",
                     "profile.py", "__init__.py"):
        assert required in names, f"缺少契约模块 {required}"
