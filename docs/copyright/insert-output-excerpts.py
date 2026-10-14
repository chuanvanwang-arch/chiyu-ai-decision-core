#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把终端真实输出摘录插入用户手册附录 E 的对应图前。

目的：软著文档要求「每页不少于 30 行」。纯截图页的文字行数不足，
故在每张终端截图前插入该次真实执行的标准输出节选（一手证据，
与截图内容一致，原始全文留存于 terminal-output/ 可逐行复核）。

幂等：以 `<!-- excerpt:KEY -->` 注释为标记，重复执行不会重复插入。

用法：
    python docs/copyright/insert-output-excerpts.py [--max-lines 10] [--dry-run]
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "user-manual.html"
TXT_DIR = ROOT / "terminal-output"

FIG_RE = re.compile(
    r"[ \t]*<figure>\s*<img\s+src=\"screenshots/(?P<name>[^\"]+)\.png\"[^>]*>\s*"
    r"<figcaption>(?P<cap>.*?)</figcaption>\s*</figure>",
    re.S,
)


def pick_lines(text: str, max_lines: int, width: int) -> list[str]:
    """从原始输出中挑出有信息量的行，去掉分隔线与空行。"""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if set(line.strip()) <= {"=", "-", "*"}:  # 纯分隔线
            continue
        if len(line) > width:
            line = line[: width - 1] + "…"
        out.append(line)
        if len(out) >= max_lines:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-lines", type=int, default=10, help="每段摘录的行数，默认 10")
    ap.add_argument("--width", type=int, default=92, help="单行截断宽度，默认 92")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = MANUAL.read_text(encoding="utf-8")

    inserted = 0
    skipped_exist = 0
    skipped_notxt = 0

    def repl(m: re.Match) -> str:
        nonlocal inserted, skipped_exist, skipped_notxt
        name = m.group("name")
        key = f"<!-- excerpt:{name} -->"
        if key in src:
            skipped_exist += 1
            return m.group(0)
        txt = TXT_DIR / f"{name}.txt"
        if not txt.exists():
            skipped_notxt += 1
            return m.group(0)
        lines = pick_lines(txt.read_text(encoding="utf-8", errors="replace"),
                           args.max_lines, args.width)
        if not lines:
            skipped_notxt += 1
            return m.group(0)
        body = html.escape("\n".join(lines))
        block = (
            f"{key}\n"
            f'<p><b>关键输出摘录。</b>以下为该次运行的真实标准输出节选'
            f"（完整文本见 <code>terminal-output/{name}.txt</code>）：</p>\n"
            f"<pre>{body}</pre>\n\n"
        )
        inserted += 1
        return block + m.group(0)

    new = FIG_RE.sub(repl, src)

    print(f"匹配 figure：{len(FIG_RE.findall(src))} 处")
    print(f"本次插入摘录：{inserted} 处")
    print(f"已存在跳过：{skipped_exist} 处　|　无对应输出文本（门户界面图）：{skipped_notxt} 处")

    if args.dry_run:
        print("（dry-run，未写盘）")
        return 0

    MANUAL.write_text(new, encoding="utf-8")
    print(f"已写回：{MANUAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
