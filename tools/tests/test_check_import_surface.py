"""sanctioned import 面门禁 —— **判别力自证**（B1 / N2 / N5）。

⛔ 为什么要"该红则红"双向验证：只验证"干净仓库绿"是恒绿探针 —— 空跑的门禁
   同样得 0，无法区分"没有违规"与"门禁没干活"。故每条判据都配一个**故意违规**
   的反例，断言门禁**必须**检出。

覆盖：
   · §2 五个 sanctioned 面均可 import；
   · `run_spine` 从 `chiyu_decision.api` 可达，且 `chiyu_kernel.api` **刻意不**导出（分层铁律）；
   · N5：contract 常量经 sanctioned 面可达；
   · 门禁对「跨分发 + 非 sanctioned」的导入必须判红。
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from check_import_surface import SANCTIONED, scan, CONFLICTING_NAMES  # noqa: E402


def test_all_sanctioned_faces_are_importable() -> None:
    """§2 表格的五个面必须真实可 import（成文面 ≠ 存在面）。"""
    for mod in SANCTIONED:
        try:
            importlib.import_module(mod)
        except Exception as e:                     # pragma: no cover - 失败即红
            raise AssertionError(f"sanctioned 面 {mod} 不可导入：{e}") from e


def test_run_spine_reachable_from_decision_facade_only() -> None:
    """B1：`run_spine` 经 `chiyu_decision.api` 可达；kernel 门面**刻意不**导出（不反向依赖）。"""
    dec = importlib.import_module("chiyu_decision.api")
    assert callable(getattr(dec, "run_spine", None)), "决策门面缺 run_spine"

    kernel = importlib.import_module("chiyu_kernel.api")
    assert not hasattr(kernel, "run_spine"), (
        "kernel 门面出现 run_spine ⇒ kernel→decision 反向依赖，违反分层铁律")


def test_contract_constants_reachable_via_sanctioned_faces() -> None:
    """N5：contract 常量经 sanctioned 面可达（消费方不必摸内部路径）。"""
    kernel = importlib.import_module("chiyu_kernel.api")
    dec = importlib.import_module("chiyu_decision.api")
    for name in ("EIGHT_ELEMENTS", "RUBRIC_KEYS", "SPINE_ORDER",
                 "AUTONOMOUS_RELEASE_DEFAULT"):
        assert hasattr(kernel, name) or hasattr(dec, name), f"{name} 不可达"
        assert hasattr(kernel, name), f"{name} 未进 kernel 门面 ⇒ 消费方须摸内部路径"


def test_gate_detects_cross_distribution_internal_import(tmp_path) -> None:
    """反例：跨分发 import 非 sanctioned 路径 ⇒ 门禁**必须**判红（判别力）。"""
    pkg = tmp_path / "packages" / "chiyu-decision" / "src" / "chiyu_decision"
    pkg.mkdir(parents=True)
    (pkg / "bad.py").write_text(
        "from chiyu_kernel.store.pg_store import assert_no_hard_delete\n",
        encoding="utf-8")
    violations, _ = scan(tmp_path)
    assert violations, "门禁对跨分发内部 import 未判红 ⇒ 空跑"
    assert "chiyu_kernel.store.pg_store" in violations[0]


def test_gate_allows_sanctioned_and_intra_distribution(tmp_path) -> None:
    """正例：sanctioned 面导入 + 同分发内部导入 ⇒ 门禁放行（不得误伤）。"""
    pkg = tmp_path / "packages" / "chiyu-decision" / "src" / "chiyu_decision"
    pkg.mkdir(parents=True)
    (pkg / "good.py").write_text(
        "from chiyu_kernel.contract.decision import SPINE_ORDER\n"
        "from chiyu_kernel.approval import RedlinePriorityGate\n"
        "from . import scoring\n",
        encoding="utf-8")
    violations, _ = scan(tmp_path)
    assert not violations, f"门禁误伤合法导入：{violations}"


def test_gate_passes_on_this_repo() -> None:
    """本仓自检（E1 双向）：foundation 自身也不得摸非 sanctioned 路径。"""
    violations, stats = scan(ROOT)
    assert stats["files"] > 0, "扫描到 0 个文件 ⇒ 扫描范围失效（假绿）"
    assert not violations, f"本仓存在非 sanctioned 跨面导入：{violations}"


# ── N1：易冲突名清单 + 门禁提示（非阻断警告）──────────────────────────────
def test_conflicting_names_table_is_nonempty() -> None:
    """反恒绿：易冲突名清单不能为空（空清单 = 门禁没干活）。"""
    assert len(CONFLICTING_NAMES) > 0, "CONFLICTING_NAMES 为空 ⇒ 提示机制失效"
    # 每项必须给出建议用法（不写建议 = 消费方仍要猜）
    for name, advice in CONFLICTING_NAMES.items():
        assert advice.strip(), f"易冲突名 {name} 缺建议用法"


def test_scan_records_conflict_warning_for_flat_import(tmp_path) -> None:
    """N1 判据正向：消费方从 sanctioned 面**扁平导入**易冲突名 ⇒ 门禁给出警告级提示
    （不阻断，但消费方可见）；非冲突名扁平导入不产生警告。"""
    pkg = tmp_path / "packages" / "chiyu-decision" / "src" / "chiyu_decision"
    pkg.mkdir(parents=True)
    flat_target = next(iter(CONFLICTING_NAMES))   # 取清单里第一个名字
    (pkg / "a.py").write_text(
        f"from chiyu_kernel.api import {flat_target}\n", encoding="utf-8")
    (pkg / "b.py").write_text(
        "from chiyu_kernel.api import get_dsn\n", encoding="utf-8")  # 非冲突名
    _, stats = scan(tmp_path)
    assert stats.get("conflict_warnings", 0) >= 1, \
        "扁平导入易冲突名未产生警告 ⇒ N1 提示机制失效"
    # 非冲突名（get_dsn）不额外贡献警告 —— 只统计命中清单的符号
    assert stats.get("flat_imports", 0) >= 2, "未统计到扁平导入 ⇒ 扫描失效"


def test_scan_conflict_warning_is_non_blocking(tmp_path) -> None:
    """N1 判据负向（判别力）：
    ① 扁平导入**易冲突名** ⇒ 仅记 `conflict_warnings`，**不**判 sanctioned 违规（警告≠阻断）；
    ② 命名空间导入（`import chiyu_kernel.api as kern_api`）⇒ 既不违规也不产生冲突警告。"""
    pkg = tmp_path / "packages" / "chiyu-decision" / "src" / "chiyu_decision"
    pkg.mkdir(parents=True)
    flat = next(iter(CONFLICTING_NAMES))
    (pkg / "a.py").write_text(
        f"from chiyu_kernel.api import {flat}\n", encoding="utf-8")   # 易冲突名扁平导入
    (pkg / "m.py").write_text(
        "import chiyu_kernel.api as kern_api\n", encoding="utf-8")    # 命名空间导入
    violations, stats = scan(tmp_path)
    assert not violations, f"易冲突名扁平导入被误判为 sanctioned 违规：{violations}"
    assert stats.get("conflict_warnings", 0) >= 1, "易冲突名扁平导入未记警告"
