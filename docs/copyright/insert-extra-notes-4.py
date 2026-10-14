#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""第五轮内容补充：针对仍差数行的图页与其相邻节补入内容。

幂等：以 `<!-- extra4:N -->` 注释为标记。

用法：
    python docs/copyright/insert-extra-notes-4.py [--dry-run]
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
<h3>7.4.3 界面与配置的对应关系</h3>
<p>
门户界面上的可见元素，均可追溯到某项配置，这使界面可以被逐项解释而不会出现「不知道为什么
这里显示这个」的情况。对应关系如下：
</p>
<ul>
  <li>业务方向来自租户画像的配置项；</li>
  <li>工作流与难度分级来自工作流配置；</li>
  <li>工作模式及其插件组合来自插件注册表与模式预设；</li>
  <li>能力面板中的原生工具与评分细则来自决策层的工具清单与评分量规。</li>
</ul>
<p>
理解这层对应关系之后，使用方在遇到界面显示与预期不符时，可以直接定位到相应配置去核查，
而不必从前端代码入手排查。这也是本软件把配置集中管理、把界面保持为纯呈现层的直接收益。
</p>
""",
    ),
    (
        2,
        r"<h2>E\.10 门户运行时</h2>",
        """
<h3>E.10.3 页面渲染的守卫机制</h3>
<p>
门户在把自然语言转为页面之前，先经过两道校验，这两道校验在界面与命令行上行为一致：
</p>
<ul>
  <li><b>输入守卫。</b>检查输入是否属于可解析的范围。若输入中包含明显不属于页面生成意图的内容，
      守卫会先行拦截，避免把无关文本送入解析环节。</li>
  <li><b>结构解析。</b>把通过守卫的自然语言解析为受控的页面结构，并给出解析置信度。
      置信度不足时会返回需要澄清的提示，而不是按最可能的猜测直接渲染。</li>
</ul>
<p>
两道校验的目的都是同一个：宁可多问一句，也不要产出一个看似合理但实际不符合意图的页面。
页面一旦被导出并用于交付，纠错成本远高于在生成前澄清一次。
</p>
""",
    ),
    (
        3,
        r"<h2>E\.14 质量保证与守卫工具链</h2>",
        """
<p>
守卫工具的运行方式为：在项目根目录直接以解释器执行对应脚本，脚本在检查完成后输出结论性文本，
并以退出码表示成败（零为通过，非零为未通过）。接入持续集成时，只需把脚本作为构建步骤调用，
无需额外解析输出文本。若某项检查出现警告级提示而非失败，脚本仍以零退出，
但会在输出中列出具体条目，供使用方按需处理。上述行为使守卫成为「可自动执行的纪律」，
而不是依赖人工逐项核对的检查表。
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
        key = f"<!-- extra4:{idx} -->"
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
