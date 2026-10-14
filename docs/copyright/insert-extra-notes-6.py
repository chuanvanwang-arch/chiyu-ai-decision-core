#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""收尾补充：补齐仍差数行的页面。

幂等：以 `<!-- extra6:N -->` 注释为标记。

用法：
    python docs/copyright/insert-extra-notes-6.py [--dry-run]
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
<h3>7.4.5 界面上文字的取值约定</h3>
<p>
界面上的文字分为三类，含义各不相同，阅读示例图时可按下列约定理解：
</p>
<ul>
  <li><b>固定文案。</b>按钮名称、分区标题等由软件内置，跨版本保持稳定；
      其中软件名、版本标识等在升级时随之更新。</li>
  <li><b>配置文案。</b>方向、工作流、模式的名称来自接入方的配置，随配置变化；
      同一套界面在不同接入方处会呈现不同的名称。</li>
  <li><b>运行数据。</b>决策阶段、评分取值、工具状态等来自本次运行的实际结果，
      每次执行都可能不同，示例图仅反映截图那一刻的真实状态。</li>
</ul>
""",
    ),
    (
        2,
        r"<h2>E\.10 门户运行时</h2>",
        """
<h3>E.10.5 门户相关命令速查</h3>
<p>除在界面上操作外，门户能力也可通过下列命令直接调用，便于脚本化验证：</p>
<pre>chiyu portal render --nl "显示本季度全部订单的列表，按金额排序" --title 季度订单 \\
    --entity-map 订单=order          # 自然语言 → 受控页面结构 → HTML
chiyu portal onboarding              # 生成引导式导航页
chiyu portal steps                   # 查询引导步骤定义</pre>
<p>
上述命令与界面操作调用同一套门户能力，输出可用浏览器打开后直接查看，
便于把界面上的观察结果与命令输出相互印证。
</p>
""",
    ),
    (
        3,
        r"<h2>E\.13 命令行与运维工具</h2>",
        """
<h3>E.13.1 常用命令组合</h3>
<p>下列组合覆盖了日常使用中最常见的三个场景，可直接复制执行：</p>
<pre>chiyu --version &amp;&amp; chiyu modes            # 交付前：确认版本与可用工作模式
chiyu selftest                            # 交付前：运行包内自测
chiyu decide --topic "…" --json           # 集成：以结构化方式取决策回执
chiyu evolution readiness                 # 巡检：自进化开闸条件自检</pre>
""",
    ),
    (
        4,
        r"<h2>E\.14 质量保证与守卫工具链</h2>",
        """
<h3>E.14.1 守卫失败时的处置</h3>
<p>
守卫失败时不应跳过检查继续交付，而应按失败类型处置：门面覆盖类失败通常意味着
新增能力未登记进公开门面，应补齐登记后重跑；导入方向类失败说明出现了跨层引用，
应调整引用方式而不是放宽检查规则；分发物同步类失败说明发布物与源码不一致，
应重新构建一致性分发物。处置完毕后再完整运行一次全部守卫，确认整体通过。
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
        key = f"<!-- extra6:{idx} -->"
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
