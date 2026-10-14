"""决策脊柱测试的路径装配 —— 让 `import chiyu_decision` / `chiyu_kernel` 与 rootdir 无关。

⛔ 为什么需要它（本文件的存在理由，已实测 2026-10-08）
──────────────────────────────────────────
pytest 的 `pythonpath` ini **相对 rootdir** 解析，而 rootdir 取决于调用方式：

- 单跑 `pytest packages/chiyu-decision/src/chiyu_decision/tests`
  ⇒ rootdir 命中 `packages/chiyu-decision/pyproject.toml`（含 `[tool.pytest.ini_options]`）
  ⇒ 其 `pythonpath = ["src", "../chiyu-kernel/src"]` 恰好生效 ⇒ 能导入。
- 组合跑 `pytest packages/chiyu-kernel/tests tools/tests packages/chiyu-decision/...`
  ⇒ 仓库根**无** `pyproject.toml`/`pytest.ini`，rootdir 退化为 `packages/`；
  根 `conftest.py` 落在 `confcutdir` 之上**不被 pytest 加载**
  ⇒ `chiyu_decision` / `chiyu_kernel` 均不在 `sys.path`
  ⇒ 5 个本目录测试全部 `ModuleNotFoundError` 收集失败。

⛔ 与 `packages/chiyu-kernel/tests/conftest.py` 同款纪律：**只在尚未可导入时插入**。
   若调用方用 `-o pythonpath=<副本>` 指定了别处副本（如 A/B 实验的对照组），
   这里必须**不覆盖**，否则会把对照组也指回主源码 ⇒ 假 A/B。
   本仓当前为纯本地 git、零 remote，`chiyu_kernel` 只有 `packages/chiyu-kernel/src`
   一份源码，故此处不存在副本冲突；纪律保留以防未来引入副本。
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()

# 本包源码：.../packages/chiyu-decision/src
_CHIYU_DECISION_SRC = _HERE.parents[2] / "src"
# 兄弟包内核源码：.../packages/chiyu-kernel/src（脊柱 import chiyu_kernel.contract.*）
_CHIYU_KERNEL_SRC = _HERE.parents[3] / "chiyu-kernel" / "src"

try:
    import chiyu_decision  # noqa: F401
except ImportError:
    if _CHIYU_DECISION_SRC.is_dir() and str(_CHIYU_DECISION_SRC) not in sys.path:
        sys.path.insert(0, str(_CHIYU_DECISION_SRC))

try:
    import chiyu_kernel  # noqa: F401
except ImportError:
    if _CHIYU_KERNEL_SRC.is_dir() and str(_CHIYU_KERNEL_SRC) not in sys.path:
        sys.path.insert(0, str(_CHIYU_KERNEL_SRC))
