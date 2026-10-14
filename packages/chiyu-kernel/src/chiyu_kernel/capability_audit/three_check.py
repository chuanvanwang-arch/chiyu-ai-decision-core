"""三查法第①步：grep 定位（审计工具的 sanctioned IO 边界）。

上迁源：APS ``platform/capability_audit.py:three_check``。

⛔ 这是本能力**唯一**的 IO 面（读文件遍历）。判定/计数/装配全部纯函数
   （``grading`` / ``four_piece``）——IO 与裁决分离，裁决可单测、可对拍。

判据：grep 零命中 ≠ 不存在 X；本函数只负责「定位」，命中即给
``(relpath, lineno, line)`` 证据（行内容截断 160 字符防刷屏）。
"""
from __future__ import annotations

import os
import re
from typing import Iterable, List, Optional, Tuple

__all__ = ["three_check"]

Hit = Tuple[str, int, str]


def three_check(
    term: str, root: str = ".",
    *, ext: str = ".py", exclude: Optional[Iterable[str]] = None,
) -> List[Hit]:
    """在 ``root`` 下递归 grep ``term``（正则），返回 ``(relpath, lineno, line)``。

    ``exclude``：跳过含这些子串的路径（避免「检查自身定义」造成的假阳性，
    如审计模块检查自己的调用点时必须排除自身）。
    """
    hits: List[Hit] = []
    pat = re.compile(term)
    excl = tuple(exclude or ())
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(ext):
                continue
            full = os.path.join(dirpath, fn)
            # ★ 相对**扫描根**取相对路径并归一为 `/`：APS 原版对 cwd 取 relpath，
            #   扫描根与 cwd 跨盘符（Windows C:/D:）时 ValueError；且排除串
            #   （"tests/"）在 Windows 反斜杠路径下永不命中——两处均修正。
            rel = os.path.relpath(full, root).replace("\\", "/")
            if any(s in rel for s in excl):
                continue
            try:
                with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if pat.search(line):
                            hits.append((rel, i, line.strip()[:160]))
            except OSError:
                continue
    return hits
