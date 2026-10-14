#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""最终定点补充：在仍差数行的页面末尾元素之后插入内容。

幂等：以 `<!-- pin3:N -->` 注释为标记。

用法：
    python docs/copyright/insert-pin-notes-3.py [--dry-run]
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "user-manual.html"

PATCHES: list[tuple[int, str, str]] = [
    (
        1,
        "<!-- pin2:1 -->",
        """
<!-- pin3:1 -->
<p><b>导出页面的前置条件。</b>对话可被导出为页面，前提是本次对话已经产生可渲染的内容。
若对话尚未包含任何工具调用回执或阶段轨迹，导出入口会提示内容不足，而不是产出一个空页面。
导出过程不修改原对话记录，导出产物是对话内容在该时刻的一份快照：
后续对原对话的继续操作不会改变已导出的页面，这一点便于将导出结果作为交付材料固定下来。
</p>
""",
    ),
    (
        2,
        "<!-- ui4:11 -->",
        """
<!-- pin3:2 -->
<p><b>会话与工作区的关系。</b>工作区是比会话更高一层的组织单位：一个工作区下可以建立多个会话，
同一工作区内的会话共享工作区的插件与工作模式范围，但各自持有独立的对话上下文。
界面上，工作区选择位于会话列表之上，先确定工作区、再建立会话。该层次划分使
「同一业务方向下并行推进多个任务」成为自然的用法，而不必反复调整配置。
</p>
""",
    ),
    (
        3,
        "<!-- pin2:4 -->",
        """
<!-- pin3:3 -->
<p><b>关于材料的一致性。</b>本手册与同目录下的其他材料保持同一口径：软件全称、版本号、
源程序量与功能项名称均与申请表填报稿一致；附录 E 的功能顺序与申请表所列功能项顺序一一对应；
本手册中的截图与命令行输出，均可与同目录 <code>terminal-output/</code> 下的原始文本逐份核对。
若日后软件版本升级导致行为变化，应同步修订本手册与相应材料，保持各份材料之间的一致性。
</p>
""",
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = MANUAL.read_text(encoding="utf-8")
    ok = skip = miss = 0

    for idx, anchor, content in PATCHES:
        key = f"<!-- pin3:{idx} -->"
        if key in src:
            skip += 1
            continue
        if anchor not in src:
            print(f"  ! 锚点未命中（#{idx}）：{anchor}")
            miss += 1
            continue
        i = src.index(anchor)
        end = src.index("</p>", i) + len("</p>")
        src = src[:end] + "\n" + content + src[end:]
        ok += 1

    print(f"插入 {ok} 处　|　未命中 {miss} 处　|　已存在 {skip} 处")
    if args.dry_run:
        print("（dry-run，未写盘）")
        return 0
    MANUAL.write_text(src, encoding="utf-8")
    print(f"已写回：{MANUAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
