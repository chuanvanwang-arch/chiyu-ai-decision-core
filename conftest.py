"""仓库根 conftest：monorepo 兄弟包源码统一上 sys.path。

让 `chiyu_kernel` / `chiyu_decision` / `chiyu_portal` / `chiyu_cli` 在**任意调用目录**下都可导入，
使 `pytest packages` 从仓库根一次性跑通全平台（不再依赖各包 pyproject 的相对 pythonpath，
后者在从根目录调用时会因 rootdir 解析而逃逸仓库）。
路径基于本文件绝对位置计算，与 cwd 无关。
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

for _pkg in ("chiyu-kernel", "chiyu-decision", "chiyu-portal", "chiyu-cli"):
    _src = os.path.join(ROOT, "packages", _pkg, "src")
    if os.path.isdir(_src) and _src not in sys.path:
        sys.path.insert(0, _src)
