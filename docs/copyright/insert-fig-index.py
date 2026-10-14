#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""在目录后补「本手册图索引」，并在附录 E 末尾补结语。

用途：目录末页与全文末页容易留白，补入与正文一致的索引与结语内容。

幂等：以 `<!-- fig-index -->` / `<!-- epilogue -->` 注释为标记。

用法：
    python docs/copyright/insert-fig-index.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "user-manual.html"

EPILOGUE = """
<!-- epilogue -->
<h2>E.16 本附录小结与复核方式</h2>
<p>
本附录按申请表所列十四项功能，逐项给出了运行界面、操作步骤、真实输出摘录与可核对要点。
为使材料可被独立复核，此处再次说明全部图面的产生方式与复核路径：
</p>
<ul>
  <li><b>图形界面截图。</b>由软件自带的前后端在本地真实启动后，通过浏览器自动化操作截取。
      页面上的数据（工作模式、插件注册表、原生工具、评分细则、决策轨迹）均由底层能力实时返回，
      不是静态样例，也不存在为截图而预置的结果。</li>
  <li><b>终端运行截图。</b>在项目根目录真实执行软件自带的命令行入口与门面调用演示脚本后截取。
      对应命令的标准输出原文完整留存于同目录 <code>terminal-output/</code> 下，
      可逐份与本附录中的摘录核对。</li>
  <li><b>演示脚本的边界。</b>演示脚本只调用软件公开门面中提供的能力，
      不对结论作任何预置或修饰；凡涉及评分的演示，评分输入均由脚本显式给出，
      结论由软件计算得出。</li>
  <li><b>能力状态。</b>本附录所展示的能力中，涉及记忆网的部分处于实验态，
      未纳入本版本稳定承诺，相关状态在能力清单中有明确标注。</li>
</ul>
<p>
使用方如需在本方环境复现上述任一界面，可按本附录各节给出的操作步骤执行；
复现过程中若出现与本文档描述不一致的结果，应优先核对软件版本与能力清单，
再对照《第十一章 接入方集成指南》中的接入自检清单逐项检查。
</p>

<h2>E.17 功能与源程序量的对应说明</h2>
<p>
本附录所展示的十四项功能，对应的源程序量见申请表填报稿：交存口径为四个在研包的主源码，
共 13,590 行（不含测试代码与构建产物）。功能与代码的对应关系如下：
</p>
<table>
  <thead>
  <tr><th style="width:30%">功能范围</th><th style="width:22%">所在软件包</th><th>说明</th></tr>
  </thead>
  <tbody>
  <tr><td>契约与配置载体、粒子与本体、数据存储</td><td>内核包</td>
      <td>承载业务实体模型、受控谓词、契约常量与存储协议，是全部上层能力的基础。</td></tr>
  <tr><td>向量与语义检索、情境装配与降级召回、图存储与关系视图</td><td>内核包</td>
      <td>承载离线向量通道、分层上下文组织与图关系查询，为决策提供上下文供给。</td></tr>
  <tr><td>决策脊柱、审批治理与续跑</td><td>决策包</td>
      <td>承载阶段顺序契约、评分聚合、红线判定与三态审批，是结论可信度的核心。</td></tr>
  <tr><td>门户运行时</td><td>门户包</td>
      <td>承载自然语言到页面的解析、渲染与引导式导航生成。</td></tr>
  <tr><td>命令行与运维工具</td><td>命令行包</td>
      <td>承载命令行入口与日常运维命令，使软件可脱离图形界面使用。</td></tr>
  <tr><td>质量保证与守卫工具链</td><td>工具集</td>
      <td>承载导入方向、门面覆盖、零残留与分发物同步等构建期门禁。</td></tr>
  </tbody>
</table>
<p>
上述功能划分与申请表「软件主要功能」十四项一一对应，本附录的节次顺序与申请表功能项的
顺序保持一致，便于逐项比对查阅。
</p>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = MANUAL.read_text(encoding="utf-8")
    changed = []

    # ① 图索引：插在目录块结束前
    if "<!-- fig-index -->" not in src:
        caps = re.findall(r"<figcaption>(图 [^<]+)</figcaption>", src)
        items = "\n".join(f"  <li>{c.strip()}</li>" for c in caps)
        block = (
            "<!-- fig-index -->\n"
            "<h3>本手册图索引</h3>\n"
            "<ul class=\"fig-index\">\n"
            f"{items}\n"
            "</ul>\n"
        )
        toc_end = src.index("</ul>\n</div>", src.index('<div class="toc">'))
        insert_at = toc_end + len("</ul>\n")
        src = src[:insert_at] + block + src[insert_at:]
        changed.append(f"图索引 {len(caps)} 条")

    # ② 结语：插在正文结束前
    if "<!-- epilogue -->" not in src:
        src = src.replace("</body>", EPILOGUE + "\n</body>", 1)
        changed.append("附录 E 小结与对应说明")

    if not changed:
        print("已存在，无需插入")
        return 0
    print("插入：" + "　|　".join(changed))
    if args.dry_run:
        print("（dry-run，未写盘）")
        return 0
    MANUAL.write_text(src, encoding="utf-8")
    print(f"已写回：{MANUAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
