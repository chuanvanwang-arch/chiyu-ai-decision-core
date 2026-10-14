"""让 examples 下的测试能 import 本包（与仓库其它测试同款纪律：只在缺失时插路径）。

⛔ 不加这个，pytest 的 rootdir/导入模式差异会让「单跑绿、组合跑崩」
   —— 本项目已踩过同族坑（见 docs/plans 蓝图 §7.4）。
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
