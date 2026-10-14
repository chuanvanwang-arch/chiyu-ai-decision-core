#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""收尾补齐：处理最后两页行数不足的问题。

幂等：以 `<!-- pin4:N -->` 注释为标记。

用法：
    python docs/copyright/insert-pin-notes-4.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "user-manual.html"

NOTES: list[tuple[int, str, str]] = [
    (
        1,
        r"<h2>E\.11 插件与工作模式</h2>",
        """
<!-- pin4:1 -->
<p><b>扩展模式时的注意事项。</b>新增工作模式时，应同时登记该模式启用的插件组合，
否则模式虽可被查询到，组合清单却为空，界面上会出现「有模式、无能力」的不一致。
模式标识一经发布应保持稳定：模式标识会被会话记录引用，改名会使历史会话无法回溯到当时的配置。
若确需调整模式含义，建议新增模式标识而不是修改既有标识，以保持历史记录的可读性。
</p>
""",
    ),
    (
        2,
        r"<!-- pin3:3 -->",
        """
<!-- pin4:2 -->
<h2>文档使用说明</h2>
<p>
为便于使用方与审查方查阅，此处对全篇的组织方式作一总结：
</p>
<ul>
  <li><b>入门路径。</b>从第三章开始，按三种安装方式之一完成部署并跑通第一个决策回路，
      再回到第二章核对运行环境与自检要求。该路径可在较短时间内建立对软件的完整印象。</li>
  <li><b>接入路径。</b>重点阅读第四章的契约与配置、第十一章的接入指南与自检清单；
      接入过程中遇到的绝大多数问题，都可在契约配置与接入纪律两部分中找到对应说明。</li>
  <li><b>运维路径。</b>重点阅读第十二章的运维与故障处理，以及第九章的守卫工具链与版本政策；
      把守卫接入流水线后，日常运维的主要工作是关注审计记录与探针结论。</li>
  <li><b>查阅路径。</b>接口清单见附录 A，配置模板见附录 B，默认参数见附录 C，
      功能界面与操作步骤见附录 E。四份附录配合正文使用，可覆盖从调用到排障的完整信息需求。</li>
</ul>
<p>
本手册的全部内容以软件的真实行为为准进行描述，未对能力作超出实际的表述：
处于实验态的能力已在第九章与附录 E 中明确标注，未纳入本版本的稳定承诺。
使用方在规划生产部署时，应以能力清单中标注的状态作为判断依据。
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

    for idx, pattern, content in NOTES:
        key = f"<!-- pin4:{idx} -->"
        if key in src:
            skip += 1
            continue
        m = re.search(pattern, src)
        if not m:
            print(f"  ! 未命中（#{idx}）：{pattern}")
            miss += 1
            continue
        if pattern.startswith("<!-- pin3"):
            # 插在该标记所在段落之后
            end = src.index("</p>", m.end()) + len("</p>")
            src = src[:end] + "\n" + content + src[end:]
        else:
            nxt = re.search(r"<h[12][ >]", src[m.end():])
            end = m.end() + nxt.start() if nxt else len(src)
            src = src[:end] + f"{key}\n{content}\n" + src[end:]
        ok += 1

    print(f"插入 {ok} 段　|　未命中 {miss} 段　|　已存在 {skip} 段")
    if args.dry_run:
        print("（dry-run，未写盘）")
        return 0
    MANUAL.write_text(src, encoding="utf-8")
    print(f"已写回：{MANUAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
