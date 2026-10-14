#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""为门户界面图补「操作步骤」，使图页文字行数达标。

幂等：以 `<!-- ui3:N -->` 注释为标记。

用法：
    python docs/copyright/insert-ui-notes-3.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "user-manual.html"

FIG_RE = re.compile(
    r"[ \t]*<figure>\s*<img\s+src=\"screenshots/(?P<name>A[^\"]+)\.png\"[^>]*>\s*"
    r"<figcaption>(?P<cap>.*?)</figcaption>\s*</figure>",
    re.S,
)

STEPS: list[str] = [
    """<p><b>操作步骤。</b>① 启动门户后端与前端服务，在浏览器中打开门户地址，等待引导页加载完成；
② 在方向选择区点击目标方向卡片；③ 观察页面进入下一步，且后续可选项已按所选方向过滤。</p>""",
    """<p><b>操作步骤。</b>① 在方向选定后进入本步；② 阅读各工作流的难度分级说明，
点击符合任务复杂度的工作流；③ 进入下一步，确认所选工作流已随会话提交。</p>""",
    """<p><b>操作步骤。</b>① 在工作流选定后进入本步；② 对照各模式右侧的插件组合，
点击目标工作模式卡片；③ 进入确认页，核对所选模式与插件组合。</p>""",
    """<p><b>操作步骤。</b>① 核对确认页汇总的三项选择（方向、工作流、工作模式）；
② 如需修改，点击返回并重新选择；③ 确认无误后提交，进入对话工作台。</p>""",
    """<p><b>操作步骤。</b>① 在底部输入区描述决策目标或调用指令；② 按需切换检索增强、深度思考等开关
并选择模型档位；③ 提交后观察对话主区依次呈现处理过程与结论。</p>""",
    """<p><b>操作步骤。</b>① 点击工作台右侧的能力面板入口；② 自上而下查看当前工作模式、
插件注册表、原生工具与决策脊柱评分细则；③ 核对完毕后关闭面板返回对话。</p>""",
    """<p><b>操作步骤。</b>① 发起一次决策；② 阅读工具调用卡片，确认各工具的执行状态；
③ 沿阶段轨迹逐项核对关键取值，并与最终结论对照。</p>""",
    """<p><b>操作步骤。</b>① 观察引导首屏的方向选项，确认其与画像配置一致；
② 点击方向卡片；③ 确认页面不出现任何具体行业的业务用语。</p>""",
    """<p><b>操作步骤。</b>① 进入工作模式选择步骤；② 比较不同模式右侧的插件组合差异；
③ 选择目标模式并进入确认页。</p>""",
    """<p><b>操作步骤。</b>① 在工作台输入区提交一条决策目标；② 观察主区按时间顺序追加处理结果；
③ 通过顶部信息确认当前方向与工作流。</p>""",
    """<p><b>操作步骤。</b>① 点击左栏「新会话」开启新会话；② 在新会话中发起一轮对话；
③ 切回原会话，确认原会话内容与上下文未丢失。</p>""",
    """<p><b>操作步骤。</b>① 打开能力面板；② 查看上半部的当前工作模式与插件注册表，
逐项核对启用状态；③ 与引导阶段所选模式对照。</p>""",
    """<p><b>操作步骤。</b>① 在能力面板中向下查看原生工具清单，确认红线硬闸工具在列；
② 查看决策脊柱评分细则的九个维度；③ 与第六章所述评分量规对照。</p>""",
    """<p><b>操作步骤。</b>① 发起一次决策；② 查看工具调用卡片与阶段轨迹；
③ 逐项核对轨迹中的状态与关键取值，确认结论可被轨迹解释。</p>""",
    """<p><b>操作步骤。</b>① 在目标消息上点击导出按钮；② 等待系统完成守卫校验与结构解析；
③ 查看导出的页面内容，确认包含工具调用回执与阶段轨迹。</p>""",
    """<p><b>操作步骤。</b>① 打开设置面板并切换到「模型」页；② 按层填写模型端点与凭据；
③ 保存后发起一次请求，在处理轨迹中确认所采用的层与回退情况。</p>""",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = MANUAL.read_text(encoding="utf-8")
    counter = {"n": 0}

    def repl(m: re.Match) -> str:
        idx = counter["n"]
        counter["n"] += 1
        if idx >= len(STEPS):
            return m.group(0)
        key = f"<!-- ui3:{idx + 1} -->"
        if key in src:
            return m.group(0)
        return m.group(0) + f"\n{key}\n{STEPS[idx]}"

    new = FIG_RE.sub(repl, src)
    print(f"门户界面图 {counter['n']} 张，步骤文案 {len(STEPS)} 条")
    if args.dry_run:
        print("（dry-run，未写盘）")
        return 0
    MANUAL.write_text(new, encoding="utf-8")
    print(f"已写回：{MANUAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
