"""测试路径装配 —— 让 `import chiyu_host` / `import chiyu_kernel` 与 rootdir 无关。

⛔ 存在理由（对齐内核 conftest）：pytest 的 `pythonpath` ini 相对 rootdir 解析，
rootdir 取决于调用方式；从仓库根跑 `pytest packages/chiyu-host/tests` 时 rootdir
落在 `packages/chiyu-host`，`pythonpath=["src"]` 只覆盖 host 自身的 src，
`chiyu_kernel`（在 `packages/chiyu-kernel/src`）不在此路径 ⇒ 导入失败。
这里显式把 `packages/chiyu-kernel/src` 与 `packages/chiyu-host/src` 插入 sys.path，
仅在**尚未可导入**时插入，不覆盖调用方 `-o pythonpath=<副本>` 指定的 A/B 副本。
"""
from __future__ import annotations

import sys
from pathlib import Path

_HOST_SRC = str(Path(__file__).resolve().parents[1] / "src")
_KERNEL_SRC = str(Path(__file__).resolve().parents[2] / "chiyu-kernel" / "src")

try:
    import chiyu_host  # noqa: F401
except ImportError:
    if _HOST_SRC not in sys.path:
        sys.path.insert(0, _HOST_SRC)

try:
    import chiyu_kernel  # noqa: F401
except ImportError:
    if _KERNEL_SRC not in sys.path:
        sys.path.insert(0, _KERNEL_SRC)
