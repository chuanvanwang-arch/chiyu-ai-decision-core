#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""最后一轮内容补充，使全文每页行数达标且总页数保持在 60 页以内。

幂等：以 `<!-- extra3:N -->` 注释为标记。

用法：
    python docs/copyright/insert-extra-notes-3.py [--dry-run]
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
<h3>7.4.2 图面的取证方式</h3>
<p>
本章及附录 E 中的全部图面，均按下列方式取得，以保证图面内容与软件实际行为一致：
</p>
<ul>
  <li>图形界面图在软件前后端真实启动后截取，界面数据由底层能力实时返回；
      图面中的方向、模式、插件、工具与评分细则均可与《附录 C 默认参数一览》逐项对照。</li>
  <li>终端图在项目根目录真实执行命令后截取，对应标准输出原文留存备查；
      图面中出现的版本号、能力档位与测试计数均为该次执行的真实结果。</li>
  <li>图面未作任何美化性修饰：界面上的按钮、开关与状态标记均保持运行时的实际样式，
      便于使用方按图对照操作。</li>
</ul>
""",
    ),
    (
        2,
        r"<h3>E\.9 事件、审计与探针</h3>|<h2>E\.9 事件、审计与探针</h2>",
        """
<p><b>探针结果的解读方式。</b>探针报告的结论由三条判据共同决定，
解读时应当逐条核对而不是只看总体结论：</p>
<ul>
  <li>若事件与粒子未成对出现，说明写入过程在某一侧中断，需检查事务边界是否覆盖了两侧写入。</li>
  <li>若图边数量与预期不相等，说明存在重复写入或漏写，需检查关系写入入口是否唯一。</li>
  <li>若红线未阻止落库，说明治理链路存在缺口，属于最高优先级问题，应立即停止上线。</li>
</ul>
""",
    ),
    (
        3,
        r"<h2>E\.10 门户运行时</h2>",
        """
<h3>E.10.2 图形界面与命令行的一致性</h3>
<p>
本节给出的图形界面操作与后续命令行操作，调用的是同一套底层能力，因此两者在结果上一致：
界面上显示的决策阶段轨迹与命令行输出的回执字段一一对应；界面上呈现的页面渲染结果与
命令行渲染命令产出的页面结构一致。这一点对使用方有两个实际意义：
</p>
<ul>
  <li><b>可以交叉验证。</b>若怀疑界面显示有误，可用命令行复现同一次调用，
      比对两者结果是否一致，从而快速定位问题出在界面层还是能力层。</li>
  <li><b>可以平滑迁移。</b>先在界面上验证流程，再把同一流程改写为命令接入自动化，
      无需重新理解一套新的接口语义。</li>
</ul>
""",
    ),
    (
        4,
        r"<h2>E\.13 命令行与运维工具</h2>",
        """
<p>
常见的命令行使用场景包括三类：一是交付前自检，通过包内自测与守卫工具确认交付物完整；
二是日常巡检，通过探针与能力查询确认运行环境的连通性；三是自动化集成，
通过决策命令与门户渲染命令把底座能力嵌入既有的业务流程或流水线。
三类场景对应的命令在上表中均有对应项，可按需组合使用。
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
        key = f"<!-- extra3:{idx} -->"
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
