"""移除用户手册中此前以「第十四章」形式插入的旧块（已改为附录 E）。

旧块以 `<!-- CH14-INSERTED -->` 成对标记，位于附录 A 之前。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MANUAL = Path(__file__).resolve().parent / "user-manual.html"
MARK = "<!-- CH14-INSERTED -->"


def main() -> int:
    html = MANUAL.read_text(encoding="utf-8")
    if MARK not in html:
        print("未发现旧块标记，无需清理")
        return 0
    n = html.count(MARK)
    html = re.sub(re.escape(MARK) + r".*?" + re.escape(MARK), "", html, flags=re.S)
    html = html.replace(MARK, "")
    # 清理可能残留的多余空行
    html = re.sub(r"\n{3,}", "\n\n", html)
    MANUAL.write_text(html, encoding="utf-8")
    print(f"已移除旧块（标记 {n-1} 处配对）")
    left = html.count("第十四章")
    print(f"残留「第十四章」出现次数：{left}")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
