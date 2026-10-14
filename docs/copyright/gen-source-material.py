#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成软著「程序鉴别材料」（一般交存）。

规则：源程序**前连续 30 页** + **后连续 30 页**，每页 50 行；不足 60 页时全量提交。

收录范围（由用户 2026-10-09 拍板）：仅 ``packages/`` 四个在研包的主源码
    chiyu-kernel（L0 契约 + L1 基础设施）
    chiyu-decision（L2 决策脊柱）
    chiyu-portal（L3 门户运行时）
    chiyu-cli（命令行入口）
排除：tests/、build/、dist/、*.egg-info、__pycache__，以及**已弃用**的 chiyu-host
      （2026-09-26 已并入 chiyu-enterprise，不作为本软件源程序申报）。

产出：
    docs/copyright/source-lines.txt     打印用纯文本（前后 30 页拼接结果）
    docs/copyright/source-material.html 打印用 HTML（A4，页眉含软件名/版本/页码）

用法（仓库根目录）：
    python docs/copyright/gen-source-material.py
"""
from __future__ import annotations

import os
from pathlib import Path

SOFTWARE = "青羽 AI 原生底座软件（ChiYu-Foundation）"
VERSION = "V1.0"
LINES_PER_PAGE = 50
HEAD_PAGES = 30
TAIL_PAGES = 30

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent

# 收录顺序＝分层顺序（kernel → decision → portal → cli），保证材料前后连续可读
PACKAGES = [
    ("chiyu-kernel", "L0 契约 + L1 基础设施"),
    ("chiyu-decision", "L2 决策脊柱"),
    ("chiyu-portal", "L3 门户运行时"),
    ("chiyu-cli", "命令行入口"),
]

EXCLUDE_DIRS = {
    "tests", "build", "dist", "__pycache__", ".git", "node_modules",
    ".pytest_cache", ".ruff_cache", ".mypy_cache",
}
EXCLUDE_SUFFIXES = {".egg-info"}


def iter_source_files(pkg_dir: Path):
    """按目录序遍历包内主源码（.py）与包定义（pyproject.toml），跳过排除项。"""
    py_files, toml_files = [], []
    if not pkg_dir.exists():
        return py_files, toml_files
    for dirpath, dirnames, filenames in os.walk(pkg_dir):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in EXCLUDE_DIRS and not any(d.endswith(s) for s in EXCLUDE_SUFFIXES)
        )
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            if fn.endswith(".py"):
                py_files.append(p)
            elif fn == "pyproject.toml":
                toml_files.append(p)
    return sorted(py_files), sorted(toml_files)


def main() -> int:
    all_lines: list[str] = []
    stats: list[tuple[str, int, int]] = []

    for pkg, desc in PACKAGES:
        pkg_dir = ROOT / "packages" / pkg
        py_files, toml_files = iter_source_files(pkg_dir)
        n_lines = 0
        all_lines.append("")
        all_lines.append(f"# {'=' * 72}")
        all_lines.append(f"# PACKAGE: {pkg}  —— {desc}")
        all_lines.append(f"# {'=' * 72}")
        for f in toml_files + py_files:
            rel = f.relative_to(ROOT).as_posix()
            all_lines.append(f"# ----- FILE: {rel} -----")
            text = f.read_text(encoding="utf-8", errors="replace")
            body = text.split("\n")
            # 去掉文件末尾因换行产生的空尾行，避免材料里出现大片空行
            while body and body[-1] == "":
                body.pop()
            all_lines.extend(ln.replace("\t", "    ") for ln in body)
            n_lines += len(body)
        stats.append((pkg, len(py_files) + len(toml_files), n_lines))

    total = len(all_lines)
    head_n = LINES_PER_PAGE * HEAD_PAGES
    tail_n = LINES_PER_PAGE * TAIL_PAGES

    if total <= head_n + tail_n:
        selected = all_lines
        note = "源程序不足 60 页，按规则全量提交"
    else:
        selected = all_lines[:head_n] + all_lines[-tail_n:]
        note = f"前 {HEAD_PAGES} 页 + 后 {TAIL_PAGES} 页"

    pages = (len(selected) + LINES_PER_PAGE - 1) // LINES_PER_PAGE

    # ---- 纯文本产出 ----
    (OUT_DIR / "source-lines.txt").write_text("\n".join(selected), encoding="utf-8")

    # ---- HTML 产出 ----
    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    parts = []
    for i in range(pages):
        pg = i + 1
        chunk = selected[i * LINES_PER_PAGE:(i + 1) * LINES_PER_PAGE]
        code = "\n".join(esc(ln) for ln in chunk)
        parts.append(
            f'<div class="page">\n'
            f'  <div class="header">{SOFTWARE} {VERSION} — 源程序鉴别材料（一般交存）'
            f'　第 {pg} 页 / 共 {pages} 页</div>\n'
            f'  <pre class="codelines">{code}</pre>\n'
            f'  <div class="footer">{SOFTWARE} {VERSION}</div>\n'
            f'</div>'
        )

    html = (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">\n'
        "<style>\n"
        "@page { size: A4; margin: 0; }\n"
        "* { box-sizing: border-box; }\n"
        'body { font-family: Consolas, "Courier New", monospace; font-size: 7.5pt; '
        "color:#111; margin:0; }\n"
        ".page { page-break-before: always; height: 297mm; display:flex; flex-direction:column; }\n"
        ".page:first-child { page-break-before: auto; }\n"
        ".page:last-child { page-break-after: auto; }\n"
        ".header { flex:0 0 auto; border-bottom:1px solid #333; padding:2mm 3mm 1mm; font-size:7.5pt; }\n"
        ".footer { flex:0 0 auto; border-top:1px solid #ccc; padding:1mm 3mm; font-size:6.5pt; "
        "color:#555; text-align:right; }\n"
        ".codelines { flex:1 1 auto; overflow:hidden; white-space:pre; margin:0; padding:0 3mm; "
        "line-height:1.12; font-size:7.5pt; }\n"
        "</style></head><body>\n" + "\n".join(parts) + "\n</body></html>\n"
    )
    (OUT_DIR / "source-material.html").write_text(html, encoding="utf-8")

    print(f"软件：{SOFTWARE} {VERSION}")
    for pkg, n_files, n_lines in stats:
        print(f"  {pkg:<16} 文件 {n_files:>4}　代码行 {n_lines:>7}")
    print(f"源程序总行数（收录范围）：{total}")
    print(f"交存方式：{note}")
    print(f"提取页数：{pages}（每页 {LINES_PER_PAGE} 行）")
    print(f"输出：{OUT_DIR / 'source-lines.txt'}")
    print(f"输出：{OUT_DIR / 'source-material.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
