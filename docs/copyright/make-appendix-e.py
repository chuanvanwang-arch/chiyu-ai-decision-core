"""把「第十四章　全功能运行界面与操作说明」改写为「附录 E」，并统一节号与图号。

为什么：软著文档鉴别材料按「前 30 页 + 后 30 页」交存。该章若作为第十四章位于
附录之前，其前 6 页会落在交存窗口之外；调整为附录 E 并置于附录 A–D 之后，
该章即可完整落入交存版的后 30 页，全部功能界面图均可见。

用法：python docs/copyright/make-appendix-e.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "chapter14.html"


def main() -> int:
    text = SRC.read_text(encoding="utf-8")

    # 0) 章注释
    text = text.replace("<!-- ══════════════ 第十四章 ══════════════ -->",
                        "<!-- ══════════════ 附录 E ══════════════ -->")
    # 1) 章标题
    text = text.replace(
        '<h1 class="nobreak">第十四章　全功能运行界面与操作说明</h1>',
        '<h1>附录 E　全功能运行界面与操作说明</h1>',
    )
    # 2) 节号 14.x → E.x
    text = re.sub(r"<h2>14\.(\d+)", lambda m: f"<h2>E.{m.group(1)}", text)
    # 3) 图号 图 14-N → 图 E-N
    text = re.sub(r"图 14-(\d+)", lambda m: f"图 E-{m.group(1)}", text)
    # 4) 正文开头对"本章"的表述改为"本附录"
    text = text.replace("<p>本章按申请表", "<p>本附录按申请表")
    text = text.replace("本章说明", "本附录说明")

    SRC.write_text(text, encoding="utf-8")

    n_sec = len(re.findall(r"<h2>E\.", text))
    n_fig = len(re.findall(r"图 E-\d+", text))
    print(f"已转换为附录 E：{n_sec} 节 · {n_fig} 处图号引用")
    if "第十四章" in text or re.search(r"<h2>14\.", text):
        print("!! 仍存在未替换的第十四章痕迹")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
