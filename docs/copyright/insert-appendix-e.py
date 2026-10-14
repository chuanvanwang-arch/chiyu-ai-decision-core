"""把附录 E「全功能运行界面与操作说明」插入用户手册。

位置：附录 D 之后（文末），目录中紧随附录 D 之后。

动作：
  1) 目录：在「附录 D」条目之后插入附录 E 条目；
  2) 正文：在 </body> 之前插入 chapter14.html 全文；
  3) 校验：所有引用的截图文件均须存在，否则报错退出（防止交付缺图）。

可重复执行：以标记 `<!-- APPENDIX-E -->` 判定，已插入则先移除再重插。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANUAL = HERE / "user-manual.html"
CHAPTER = HERE / "chapter14.html"
SHOTS = HERE / "screenshots"

MARK = "<!-- APPENDIX-E -->"
TOC_ANCHOR = "    <li>附录 D　文档说明与修订记录</li>"
TOC_ENTRY = """    <li>附录 E　全功能运行界面与操作说明</li>
    <li class="l2">E.1 本附录说明　E.2 契约与配置载体　E.3 粒子与本体管理</li>
    <li class="l2">E.4 向量与语义检索　E.5 情境装配与降级召回　E.6 图存储与关系视图</li>
    <li class="l2">E.7 决策脊柱　E.8 审批治理与续跑　E.9 事件、审计与探针</li>
    <li class="l2">E.10 门户运行时　E.11 插件与工作模式　E.12 模型接入与协议适配</li>
    <li class="l2">E.13 命令行与运维工具　E.14 质量保证与守卫工具链　E.15 版本化与兼容承诺</li>
"""


def main() -> int:
    html = MANUAL.read_text(encoding="utf-8")
    chapter = CHAPTER.read_text(encoding="utf-8")

    # 幂等：先移除旧块（含此前误插的第十四章版本与目录条目）
    if MARK in html:
        html = re.sub(re.escape(MARK) + r".*?" + re.escape(MARK), "", html, flags=re.S)
        html = html.replace(MARK, "")
    html = re.sub(
        r"    <li>第十四章　全功能运行界面与操作说明</li>\n"
        r"(    <li class=\"l2\">14\.[^\n]*\n){0,5}", "", html)
    html = re.sub(
        r"    <li>附录 E　全功能运行界面与操作说明</li>\n"
        r"(    <li class=\"l2\">E\.[^\n]*\n){0,5}", "", html)

    refs = re.findall(r'src="screenshots/([^"]+)"', chapter)
    missing = [r for r in refs if not (SHOTS / r).exists()]
    if missing:
        print("缺少截图文件：")
        for m in missing:
            print("  -", m)
        return 1
    print(f"截图引用校验通过：{len(refs)} 处，文件齐全")

    if TOC_ANCHOR not in html:
        print("未找到目录锚点（附录 D 条目）")
        return 1
    html = html.replace(TOC_ANCHOR, TOC_ANCHOR + "\n" + TOC_ENTRY.rstrip("\n"), 1)

    if "</body>" not in html:
        print("未找到正文锚点（</body>）")
        return 1
    html = html.replace("</body>", f"{MARK}\n{chapter}\n{MARK}\n\n</body>", 1)

    MANUAL.write_text(html, encoding="utf-8")
    print(f"已插入附录 E：{len(chapter)} 字符，含 {len(refs)} 张截图引用")
    return 0


if __name__ == "__main__":
    sys.exit(main())
