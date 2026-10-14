"""sanctioned import 面守卫（B1 + N2 + N5 的机械判据）。

守三条：
  1. 五个 sanctioned 面**可 import**（正向：能力确实可达，防"面定义了却摸不到"）；
  2. `run_spine` 从 `chiyu_decision.api` 可达，且 `chiyu_kernel.api` **确无** `run_spine`
     （反向：防 kernel 反向依赖 decision 回潮，守 D3 分层 + 授权分级）；
  3. 门禁**有判别力**（变异自证）：注入违规 import 必判红、注入合规 import 必判绿。
     ⛔ 无判别力的门禁 = 假绿（本项目已多次踩同族）。

对应文档：docs/sanctioned-import-surface.md §4
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
TOOLS = REPO / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

# ⛔ 兄弟包 src 装配：本测试断言 chiyu_decision.api / chiyu_portal.api 可达，
#    而单跑 kernel 测试时它们不在 sys.path（组合跑才由根 conftest 装配）。
#    与 packages/chiyu-decision/src/chiyu_decision/tests/conftest.py 同款纪律：
#    **只在尚未可导入时插入**，绝不覆盖调用方用 -o pythonpath 指定的别处副本（防假 A/B）。
for _pkg in ("chiyu-decision", "chiyu-portal", "chiyu-kernel"):
    _src = REPO / "packages" / _pkg / "src"
    _mod = _pkg.replace("chiyu-", "chiyu_")
    try:
        importlib.import_module(_mod)
    except ImportError:
        if _src.is_dir() and str(_src) not in sys.path:
            sys.path.insert(0, str(_src))

import check_import_surface as cis  # noqa: E402


# ── 1. 五个 sanctioned 面可达（正向）──────────────────────────────────────
@pytest.mark.parametrize("mod", [
    "chiyu_kernel.api",
    "chiyu_kernel.contract",
    "chiyu_kernel.approval",
    "chiyu_decision.api",
    "chiyu_portal.api",
])
def test_sanctioned_faces_importable(mod):
    assert importlib.import_module(mod) is not None


def test_run_spine_reachable_from_decision_api():
    """B1 正解：`run_spine` 走决策脊柱自己的门面。"""
    api = importlib.import_module("chiyu_decision.api")
    assert hasattr(api, "run_spine"), "run_spine 必须从 chiyu_decision.api 可达"


def test_run_spine_absent_from_kernel_api():
    """⛔ 反向：kernel 不得收 decision（D3 分层 + 授权分级），故不得出现 run_spine。"""
    api = importlib.import_module("chiyu_kernel.api")
    assert not hasattr(api, "run_spine"), (
        "chiyu_kernel.api 出现 run_spine ⇒ kernel 反向依赖 decision，违反分层铁律"
    )


def test_contract_constants_in_sanctioned_face():
    """N5：八要素/九尺子键名的权威源必须经 contract 面可达。"""
    d = importlib.import_module("chiyu_kernel.contract.decision")
    for name in ("EIGHT_ELEMENTS", "RUBRIC_KEYS", "SPINE_ORDER"):
        assert hasattr(d, name), f"{name} 必须经 contract 面可达"


# ── 2. 门禁判别力（变异自证）──────────────────────────────────────────────
def _probe(tmp_path: Path, monkeypatch, code: str) -> int:
    """把 code 写入临时扫描根，返回门禁退出码。"""
    root = tmp_path / "repo"
    src = root / "packages" / "chiyu-portal" / "src"
    src.mkdir(parents=True)
    (src / "probe.py").write_text(code, encoding="utf-8")
    monkeypatch.setattr(cis, "SCAN_ROOTS", ("packages/chiyu-portal/src",))
    return cis.main(["--root", str(root)])


def test_gate_rejects_internal_path(tmp_path, monkeypatch):
    """变异自证 ①：跨分发 import 内部路径（store.pg_store）⇒ 必须判红。"""
    code = "from chiyu_kernel.store.pg_store import PgVectorStore\n"
    assert _probe(tmp_path, monkeypatch, code) == 1, "违规 import 未判红 ⇒ 门禁无判别力"


def test_gate_rejects_decision_internals(tmp_path, monkeypatch):
    """变异自证 ②：直连 chiyu_decision.spine（非 .api）⇒ 必须判红。"""
    code = "from chiyu_decision.spine import run_spine\n"
    assert _probe(tmp_path, monkeypatch, code) == 1, "直连决策内部路径未判红"


def test_gate_accepts_sanctioned(tmp_path, monkeypatch):
    """变异自证 ③：走 sanctioned 面 ⇒ 必须判绿（防门禁误杀合法 import）。"""
    code = (
        "from chiyu_kernel.api import PgVectorStore\n"
        "from chiyu_decision.api import run_spine\n"
        "from chiyu_kernel.contract.decision import RUBRIC_KEYS\n"
    )
    assert _probe(tmp_path, monkeypatch, code) == 0, "合规 import 被误杀 ⇒ 门禁过严"


def test_gate_allows_same_dist_imports(tmp_path, monkeypatch):
    """同分发内 import 属实现细节，不受约束（防门禁越权）。"""
    root = tmp_path / "repo"
    src = root / "packages" / "chiyu-kernel" / "src"
    src.mkdir(parents=True)
    (src / "probe.py").write_text("from chiyu_kernel.store.pg_store import PgVectorStore\n",
                                  encoding="utf-8")
    monkeypatch.setattr(cis, "SCAN_ROOTS", ("packages/chiyu-kernel/src",))
    assert cis.main(["--root", str(root)]) == 0, "同分发内 import 被误判"


# ── 3. 全仓实况：当前零违规（回归闸门）────────────────────────────────────
def test_repo_has_no_violation():
    violations, stats = cis.scan(REPO)
    assert not violations, "全仓存在 sanctioned 面违规：\n" + "\n".join(violations)
    assert stats["files"] > 0, "扫描文件数为 0 ⇒ 门禁空跑（假绿）"
