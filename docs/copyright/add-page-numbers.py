#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""为用户手册叠加页眉与页码。

为什么这样做：正文由 Chromium 排版（中文与版式保真），但浏览器打印无法自动生成中文页眉与"第 N 页 / 共 M 页"
页码。故用 reportlab 生成一份同尺寸的叠加层（只含页眉、页脚与分隔线），再与正文逐页合并。

用法（仓库根目录）：
    python docs/copyright/add-page-numbers.py 正文.pdf 输出.pdf

需在含 reportlab 的解释器下运行（本仓用隔离环境）：
    "C:/Users/wangchuan08/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
"""
from __future__ import annotations

import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

SOFTWARE = "青羽 AI 原生底座软件（ChiYu-Foundation）V1.0"
DOC_TITLE = "用户手册"

FONT_CANDIDATES = [
    (r"C:\Windows\Fonts\msyh.ttc", 0),
    (r"C:\Windows\Fonts\simhei.ttf", None),
    (r"C:\Windows\Fonts\simsun.ttc", 0),
]


def register_font() -> str:
    for path, idx in FONT_CANDIDATES:
        if not Path(path).exists():
            continue
        try:
            if idx is None:
                pdfmetrics.registerFont(TTFont("CJK", path))
            else:
                pdfmetrics.registerFont(TTFont("CJK", path, subfontIndex=idx))
            return "CJK"
        except Exception:                     # 该字体不可用时继续尝试下一个
            continue
    raise SystemExit("未找到可用中文字体，无法生成页眉页码")


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    font = register_font()

    reader = PdfReader(src)
    total = len(reader.pages)
    W, H = A4

    overlay_path = str(Path(out).with_suffix(".overlay.pdf"))
    c = canvas.Canvas(overlay_path, pagesize=A4)
    for pg in range(1, total + 1):
        # 页眉
        c.setFont(font, 7.5)
        c.setFillColorRGB(0.20, 0.31, 0.42)
        c.drawString(16 * mm, H - 11 * mm, f"{SOFTWARE}　{DOC_TITLE}")
        c.setStrokeColorRGB(0.70, 0.76, 0.82)
        c.setLineWidth(0.5)
        c.line(16 * mm, H - 13.2 * mm, W - 16 * mm, H - 13.2 * mm)

        # 页脚
        c.setFont(font, 7.5)
        c.setFillColorRGB(0.35, 0.42, 0.49)
        c.drawString(16 * mm, 10.5 * mm, SOFTWARE)
        c.drawRightString(W - 16 * mm, 10.5 * mm, f"第 {pg} 页 / 共 {total} 页")
        c.setStrokeColorRGB(0.85, 0.88, 0.91)
        c.line(16 * mm, 12.6 * mm, W - 16 * mm, 12.6 * mm)

        c.showPage()
    c.save()

    # 合并：正文在下，页眉页码在上
    writer = PdfWriter()
    ov = PdfReader(overlay_path)
    for i, page in enumerate(reader.pages):
        page.merge_page(ov.pages[i])
        writer.add_page(page)
    with open(out, "wb") as f:
        writer.write(f)

    Path(overlay_path).unlink(missing_ok=True)
    print(f"已生成带页眉页码的文档：{out}（共 {total} 页）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
