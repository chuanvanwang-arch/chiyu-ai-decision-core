#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""定点补充：在指定图注说明之后插入内容，使其留在本页的空隙中。

幂等：以 `<!-- pin:N -->` 注释为标记。

用法：
    python docs/copyright/insert-pin-notes.py [--dry-run]
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "user-manual.html"

PATCHES: list[tuple[int, str, str]] = [
    (
        1,
        "<!-- ui2:7 -->",
        """
<!-- pin:1 -->
<p><b>决策执行中的常见现象与解释。</b>使用方在观察处理轨迹时，可能遇到下列情形，
均可由轨迹本身解释，无需解读为异常：</p>
<ul>
  <li>某项工具显示「未执行」——说明本次请求的处理路径未经过该工具，
      通常与当前工作模式所启用的插件组合有关，而非工具故障。</li>
  <li>上下文装配标注了缺口项——说明该层供给不足，处理按降级路径继续，
      结论仍然有效，但依据的充分性低于无缺口的情形。</li>
  <li>红线校验命中数为零——说明本次动作未触及红线目录中的任一事项，
      属于正常结果；命中数非零时才涉及强制改判。</li>
</ul>
""",
    ),
    (
        2,
        "<!-- ui2:11 -->",
        """
<!-- pin:2 -->
<p><b>会话级隔离的实现要点。</b>会话隔离不是简单的界面分组，而是上下文层面的隔离，
其要点包括：</p>
<ul>
  <li>每个会话持有独立的方向、工作流、工作模式三项配置，互不继承；</li>
  <li>每个会话持有独立的上下文，包括本次会话内已装配的实体、召回结果与先例；</li>
  <li>会话之间不共享推理中间状态，因此在一个会话中的尝试不会影响另一个会话的结论；</li>
  <li>会话记录可长期保留，便于按会话回溯某次决策的完整经过。</li>
</ul>
""",
    ),
    (
        3,
        "<!-- ui2:13 -->",
        """
<!-- pin:3 -->
<p><b>九项评分维度对照表。</b>决策脊柱的评分量规由下列九个维度组成，每项取值 0 至 4 分
（0 为缺失、4 为充分）。置信度取九项评分的达成比例，不采用任何其他来源的分数：</p>
<table>
  <thead><tr><th style="width:18%">英文键</th><th style="width:16%">中文名</th><th>评价内容</th></tr></thead>
  <tbody>
    <tr><td><code>clarity</code></td><td>清晰性</td><td>决策目标与依据的表述是否清晰可理解。</td></tr>
    <tr><td><code>accuracy</code></td><td>准确性</td><td>所依据的事实是否准确无误。</td></tr>
    <tr><td><code>precision</code></td><td>精确性</td><td>结论的表述是否足够具体、可执行。</td></tr>
    <tr><td><code>relevance</code></td><td>相关性</td><td>所依据的内容与决策目标是否直接相关。</td></tr>
    <tr><td><code>depth</code></td><td>深度</td><td>是否触及问题的关键层面，而非停留于表面。</td></tr>
    <tr><td><code>breadth</code></td><td>广度</td><td>是否考虑了必要的其他方面与影响。</td></tr>
    <tr><td><code>logic</code></td><td>逻辑性</td><td>从依据到结论的推导是否成立。</td></tr>
    <tr><td><code>importance</code></td><td>重要性</td><td>所处理事项的重要程度是否与投入相匹配。</td></tr>
    <tr><td><code>fairness</code></td><td>公平性</td><td>结论是否对不同相关方保持一致的尺度。</td></tr>
  </tbody>
</table>
""",
    ),
    (
        4,
        "成为「可自动执行的纪律」，",
        """
<!-- pin:4 -->
<p>
把守卫接入持续集成时，建议的编排顺序为：先跑分发物同步与零残留检查（最快的两项），
再跑导入方向与门面覆盖检查，最后运行包内自测。该顺序使明显且廉价的问题尽早暴露，
避免在耗时较长的自测之后才发现分发物不一致。全部检查通过后，再把构建产物作为交付物归档。
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
        key = f"<!-- pin:{idx} -->"
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
