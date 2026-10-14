#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""最后一批内容补充，使全文每页行数达标。

幂等：以 `<!-- extra5:N -->` 注释为标记。

用法：
    python docs/copyright/insert-extra-notes-5.py [--dry-run]
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
        r"<h2>7\.4 界面示例</h2>",
        """
<h3>7.4.4 界面示例与操作手册的关系</h3>
<p>
本章的界面示例与第三章的快速上手、附录 E 的功能说明构成互补关系：第三章说明「怎样跑通一遍」，
本章说明「界面由哪些部分构成」，附录 E 则按功能项逐项给出操作步骤与真实输出。
三者描述的软件行为完全一致，区别只在于组织方式，使用方可按需选择入口。
</p>
""",
    ),
    (
        2,
        r"<h2>E\.10 门户运行时</h2>",
        """
<h3>E.10.4 门户能力的边界</h3>
<p>
门户层承担的是交互与呈现，不承担业务判断。具体而言，门户不决定某个动作是否应当放行，
也不参与评分计算，这些判断全部由决策层完成；门户也不保存业务实体的权威数据，
页面上的数据均来自内核与决策层的实时返回。明确这条边界，可以避免把治理逻辑写进界面层，
从而使治理规则集中在一处、便于审计与变更。
</p>
""",
    ),
    (
        3,
        r"<h2>E\.14 质量保证与守卫工具链</h2>",
        """
<p><b>守卫工具清单与检查范围。</b>各守卫的检查范围互不重叠，合起来覆盖了交付质量的主要风险面：</p>
<ul>
  <li><b>导入方向守卫。</b>检查是否存在跨分发引用面的非法引用，确保分层架构不被破坏。</li>
  <li><b>门面覆盖守卫。</b>检查公开门面是否完整覆盖各层能力，避免出现「能力存在但无法被正常引用」的情况。</li>
  <li><b>零残留守卫。</b>检查交付物中是否遗留开发过程的临时标记，确保交付内容干净。</li>
  <li><b>分发物同步守卫。</b>检查分发包内容与源码是否一致，避免发布与源码脱节。</li>
  <li><b>能力清单生成。</b>由能力定义生成机器可读清单，作为使用方做能力断言的依据。</li>
</ul>
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
        key = f"<!-- extra5:{idx} -->"
        if key in src:
            skip += 1
            continue
        m = re.search(pattern, src)
        if not m:
            print(f"  ! 未命中（#{idx}）")
            miss += 1
            continue
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
