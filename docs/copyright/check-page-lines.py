#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按「视觉行」统计 PDF 每页行数，用于核验软著文档「每页不少于 30 行」要求。

与文本提取计数的差别：文本提取会把表格单元格内的换行合并成一行，
而视觉行以版面上的实际文本行为准（表格换行、代码块换行均按行计），
与人工翻页点数的口径一致。

用法：
    python docs/copyright/check-page-lines.py 手册.pdf [--min 30] [--head 30 --tail 30]

退出码：0 = 全部达标；1 = 存在未达标页。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fitz  # PyMuPDF


def visual_lines(page: fitz.Page) -> list[str]:
    """返回该页的视觉行文本列表（自上而下、自左而右）。"""
    rows: list[tuple[float, float, str]] = []
    data = page.get_text("dict")
    for block in data.get("blocks", []):
        if block.get("type") != 0:  # 0 = 文本块，1 = 图像块
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text:
                continue
            x0, y0 = line["bbox"][0], line["bbox"][1]
            rows.append((round(y0, 1), x0, text))
    # 先按纵向位置、再按横向位置排序，保证与阅读顺序一致
    rows.sort(key=lambda r: (r[0], r[1]))
    return [r[2] for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser(description="核验 PDF 每页视觉行数")
    ap.add_argument("pdf", help="待核验的 PDF 路径")
    ap.add_argument("--min", type=int, default=30, help="每行最少行数要求，默认 30")
    ap.add_argument("--head", type=int, default=0, help="仅看前 N 页（交存口径）")
    ap.add_argument("--tail", type=int, default=0, help="仅看后 N 页（交存口径）")
    ap.add_argument("--verbose", action="store_true", help="打印全部页的行数")
    args = ap.parse_args()

    path = Path(args.pdf)
    if not path.exists():
        raise SystemExit(f"文件不存在：{path}")

    doc = fitz.open(str(path))
    total = len(doc)
    if args.head or args.tail:
        head = args.head or 0
        tail = args.tail or 0
        idxs = list(range(min(head, total))) + list(range(max(0, total - tail), total))
        scope = f"交存口径（前 {head} 页 + 后 {tail} 页）"
    else:
        idxs = list(range(total))
        scope = "全文"

    print(f"文件：{path.name}　|　总页数：{total}　|　核验范围：{scope}　|　要求：每页 ≥ {args.min} 行")

    bad: list[tuple[int, int, str]] = []
    counts: list[int] = []
    for i in idxs:
        lines = visual_lines(doc[i])
        counts.append(len(lines))
        head_txt = lines[0][:40] if lines else "(空页)"
        if len(lines) < args.min:
            bad.append((i + 1, len(lines), head_txt))
        if args.verbose:
            mark = "" if len(lines) >= args.min else "  <<< 不足"
            print(f"  p{i + 1:>4}: {len(lines):>3} 行   {head_txt}{mark}")

    if not args.verbose:
        for b in bad:
            print(f"  未达标  p{b[0]:>4}: {b[1]:>3} 行   {b[2]}")

    print("-" * 60)
    if counts:
        print(f"行数区间：{min(counts)} – {max(counts)}　|　平均：{sum(counts) / len(counts):.1f}")
    if bad:
        print(f"结论：{len(bad)} / {len(idxs)} 页未达标 —— 需整改")
        return 1
    print(f"结论：全部 {len(idxs)} 页达标")
    return 0


if __name__ == "__main__":
    sys.exit(main())
