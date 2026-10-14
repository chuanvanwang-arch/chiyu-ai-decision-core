#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按软著一般交存规则截取交存版：前连续 30 页 + 后连续 30 页。

适用对象：页数超过 60 页的材料（如用户手册 65 页）。
页数不超过 60 页的材料（如源程序材料 60 页）无需截取，直接交存全文。

用法：
    python docs/copyright/gen-submission.py 全文.pdf 交存版.pdf [--head=30 --tail=30]
"""
from __future__ import annotations

import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        raise SystemExit(__doc__)
    head = tail = 30
    for a in sys.argv[1:]:
        if a.startswith("--head="):
            head = int(a.split("=", 1)[1])
        if a.startswith("--tail="):
            tail = int(a.split("=", 1)[1])

    src, out = args[0], args[1]
    reader = PdfReader(src)
    total = len(reader.pages)

    if total <= head + tail:
        print(f"全文 {total} 页，未超过 {head + tail} 页，按规则全量交存（无需截取）")
        return 0

    indices = list(range(head)) + list(range(total - tail, total))
    writer = PdfWriter()
    for i in indices:
        writer.add_page(reader.pages[i])
    with open(out, "wb") as f:
        writer.write(f)
    print(f"全文 {total} 页 → 交存版 {len(indices)} 页"
          f"（前 {head} 页 + 后 {tail} 页，含第 {total - tail + 1} 至 {total} 页）")
    print(f"输出：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
