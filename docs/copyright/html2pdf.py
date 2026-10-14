#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用本机 Chromium 把打印用 HTML 转成 PDF（中文保真）。

为什么不用 reportlab：其内置 Courier/Helvetica 无中文字形，代码注释里的中文会成方块；
走浏览器打印可直接使用系统字体，且与 HTML 版式零偏差。

用法：
    python docs/copyright/html2pdf.py <html文件或URL> <输出pdf>
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser() -> str:
    for p in CHROME_CANDIDATES:
        if Path(p).exists():
            return p
    raise SystemExit("未找到 Chrome / Edge，无法生成 PDF")


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src = sys.argv[1]
    out = sys.argv[2]
    browser = find_browser()

    if "://" not in src:
        src = Path(src).resolve().as_uri()
    out_abs = str(Path(out).resolve())

    # 独立 profile：避免与用户已打开的浏览器实例争用（否则静默失败）
    profile = Path(out).resolve().parent / "_chrome-profile"
    profile.mkdir(parents=True, exist_ok=True)

    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-first-run",
        "--disable-extensions",
        f"--user-data-dir={profile}",
        "--no-pdf-header-footer",          # 去掉浏览器自带的页眉页脚（HTML 内已含）
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=60000",     # 图片较多时需更长的虚拟时间预算
        f"--print-to-pdf={out_abs}",
        src,
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True)
    if not Path(out_abs).exists():
        err = (proc.stderr or b"").decode("utf-8", "replace")[-800:]
        raise SystemExit(f"PDF 生成失败：{out_abs}\n{err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
