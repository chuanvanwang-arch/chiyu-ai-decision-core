#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""加大体量的定点补充，使图页文字行数跨过门槛。

幂等：以 `<!-- pin2:N -->` 注释为标记。

用法：
    python docs/copyright/insert-pin-notes-2.py [--dry-run]
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "user-manual.html"

PATCHES: list[tuple[int, str, str]] = [
    (
        1,
        "<!-- pin:1 -->",
        """
<!-- pin2:1 -->
<p><b>决策执行的三条纪律。</b>上述现象的解读方式，来自三条贯穿始终的纪律，
使用方在自行扩展功能时同样应遵守：</p>
<ul>
  <li><b>轨迹完整。</b>处理过程中的每一步都要在轨迹中留下记录，包括未执行的步骤。
      只记录成功步骤会让使用方无法区分「没做」与「做了但没输出」。</li>
  <li><b>缺口显式。</b>上下文不足时必须显式标注，而不能用默认值补位。
      默认值会让结论看起来完整，却掩盖了依据不足这一事实，使问题在更晚的阶段才暴露。</li>
  <li><b>结论可溯。</b>任一结论都应能沿轨迹回溯到具体的评分与事实依据；
      若某条结论无法从轨迹中还原，说明该结论的取得方式脱离了契约，需要修正实现。</li>
</ul>
<p>
这三条纪律与第六章所述的阶段契约是同一套约束在不同层面的表述：契约规定「按什么顺序做」，
纪律规定「做完之后留下什么」。两者共同保证了结论的可解释性。
</p>
""",
    ),
    (
        2,
        "<!-- pin:2 -->",
        """
<!-- pin2:2 -->
<p><b>会话数据的保存与清理。</b>会话记录属于使用方的业务数据，其保存周期由接入方的
数据保留策略决定，软件本身不自动清理。实践中的建议如下：</p>
<ul>
  <li>会话记录与决策落库记录互相独立：会话记录面向交互过程，决策落库记录面向治理留痕，
      两者的保留周期可以不同。</li>
  <li>导出为页面后的产物独立于会话存在，即使清理了会话，已交付的页面仍可访问。</li>
  <li>需要按人员或按租户隔离会话时，应在接入时确定隔离粒度，该粒度决定会话存储的键设计，
      后期变更需要数据迁移。</li>
</ul>
""",
    ),
    (
        3,
        "<!-- pin:3 -->",
        """
<!-- pin2:3 -->
<p><b>评分取值与阈值。</b>每个维度的取值含义为：0 表示该项依据缺失，1 表示较弱，
2 表示部分满足，3 表示良好，4 表示充分。九项评分的达成比例构成综合置信度，
默认情况下达成比例达到 0.75 视为良好、低于 0.5 视为需警示。阈值可按领域调整，
但调整的应是阈值本身，而不是评分的口径——把其他来源的分数混入置信度会让阈值失去可比性。
若某一维度确实不适用于某类决策，应当通过评分权重将该维度的作用调低，
并在场景定义中登记该决定，而不是在每次调用时临时跳过该维度。
</p>
""",
    ),
    (
        4,
        "<!-- extra2:4 -->",
        """
<!-- pin2:4 -->
<p><b>文档结束语。</b>本手册到此结束。全篇围绕一个目标展开：说明这套底座如何被正确地
使用、如何被接入到具体业务、以及在什么条件下它的结论可以被信任。文档中的图面与输出
均取自软件的真实运行，读者可按各节给出的操作步骤在本方环境复现。
若在复现过程中发现文档描述与软件行为不一致，请以软件的实际行为为准，并反馈至维护方，
以便在后续版本中修订。文档随软件版本迭代更新，版本对应关系见附录 D 的修订记录。
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
        key = f"<!-- pin2:{idx} -->"
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
