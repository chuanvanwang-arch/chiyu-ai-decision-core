"""WS4 §13 零残留 —— 判别力自证（注入禁用标记必须判红）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from check_zero_residue import scan  # noqa: E402


def test_internal_marker_is_detected(tmp_path: Path):
    f = tmp_path / "deck.md"
    f.write_text("这是一页展示 # ⛔ 内部标记不应出现\n", encoding="utf-8")
    hits = scan(tmp_path, ["⛔"])
    assert hits, "注入 ⛔ 必须判红"
    assert hits[0][0] == f


def test_overclaim_phrase_is_detected(tmp_path: Path):
    f = tmp_path / "doc.md"
    f.write_text("决策记忆网已落地，全链路跑通\n", encoding="utf-8")
    assert scan(tmp_path, ["决策记忆网已落地"])


def test_clean_file_passes(tmp_path: Path):
    f = tmp_path / "doc.md"
    f.write_text("稳定的底座能力清单\n", encoding="utf-8")
    assert scan(tmp_path, ["⛔", "决策记忆网已落地"]) == []
