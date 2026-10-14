"""测试路径装配 —— 让 `import chiyu_kernel` 与 rootdir 的选取**无关**。

⛔ 为什么需要它（本文件的存在理由，已实测）
──────────────────────────────────────────
pytest 的 `pythonpath` ini 是**相对 rootdir** 解析的，而 rootdir 取决于调用方式。
实测：从仓库根跑 `pytest packages/chiyu-kernel/tests`，rootdir 落在
`packages/chiyu-kernel`（因为那里的 `pyproject.toml` 含 `[tool.pytest.ini_options]`），
于是 `-o pythonpath="packages/chiyu-kernel/src"` 被解析成
`packages/chiyu-kernel/packages/chiyu-kernel/src`（不存在）⇒ 导入失败。
靠"调用方每次都传对相对路径"不可靠 —— 那正是假 A/B 的来源。

⛔ 只在**尚未可导入**时插入：若调用方用 `-o pythonpath=<副本>` 指定了别的副本，
   这里必须**不覆盖**，否则 A/B 实验会把对照组也指到主源码上。
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import chiyu_kernel  # noqa: F401
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# 跨包 E2E（harness 移植）需要 chiyu_portal；同样仅在不冲突时插入，
# 不覆盖调用方指定的 A/B 副本路径。
try:
    import chiyu_portal  # noqa: F401
except ImportError:
    _portal_src = str(Path(__file__).resolve().parents[1].parent / "chiyu-portal" / "src")
    if _portal_src not in sys.path:
        sys.path.insert(0, _portal_src)

# 跨包契约守卫（test_contract_eight_elements_pin.py 等）需要 chiyu_decision；
# test_canary_probe / test_consumer_facade_stability 同样顶层 import 决策面，
# 单包直跑此前只能靠组合跑（根 conftest）才可达。同样仅在不可导入时插入，
# 不覆盖调用方指定的 A/B 副本路径。
try:
    import chiyu_decision  # noqa: F401
except ImportError:
    _decision_src = str(Path(__file__).resolve().parents[1].parent / "chiyu-decision" / "src")
    if _decision_src not in sys.path:
        sys.path.insert(0, _decision_src)


def pytest_configure(config):
    # 注册真库 E2E 标记（单包直跑时 rootdir 落本包 pyproject，根 pytest.ini
    # 的 markers 不可达 —— 此处与两处配置解耦，双重注册幂等）。
    config.addinivalue_line(
        "markers",
        "pg: 真库 E2E（本地便携 PG chiyu_test；无库自动跳过，见 test_pg_e2e.py 头注红线）")
