"""WS4 门面守卫模板 —— 判别力自证（该红则红、该绿则绿）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from check_facade_coverage import missing_names  # noqa: E402


def test_discriminates_a_missing_symbol():
    class _Stub:
        pass

    stub = _Stub()
    setattr(stub, "compute_coverage", None)   # 暴露一个
    # vector 层两个符号，门面只暴露一个 ⇒ 必须检出 cosine
    assert missing_names("vector", ("compute_coverage", "cosine"), stub, {}) == [
        "vector.cosine → api.cosine"
    ]


def test_honors_rename_table():
    class _Stub:
        pass

    stub = _Stub()
    renames = {("vector", "available"): "vector_available"}
    setattr(stub, "available", None)   # 裸名不算暴露（改名后才是 vector_available）
    assert missing_names("vector", ("available",), stub, renames) == [
        "vector.available → api.vector_available"
    ]
    setattr(stub, "vector_available", None)  # 改名后才算暴露
    assert missing_names("vector", ("available",), stub, renames) == []


def test_clean_layer_reports_nothing():
    class _Stub:
        pass

    stub = _Stub()
    for n in ("a", "b"):
        setattr(stub, n, None)
    assert missing_names("x", ("a", "b"), stub, {}) == []
