"""修复 Batch-7a 迁移兜底：把 `from chiyu_kernel.errors import KernelError` 复位到
模块文档串之后（避免文档串降级为普通字符串常量被领域词守卫扫到）。

仅作用于 4 个原本无 `from __future__ import annotations` 的契约文件。
"""
from __future__ import annotations

from pathlib import Path

BASE = Path("packages/chiyu-kernel/src/chiyu_kernel")
FILES = [
    "contract/scheduler.py",
    "contract/observability.py",
    "contract/nightly_report.py",
    "contract/agent_runtime.py",
]


def fix(text: str) -> str:
    lines = text.split("\n")
    assert lines[0].strip() == "from chiyu_kernel.errors import KernelError", lines[0]
    # 文档串从第 1 行开始，找到闭合的 """
    assert lines[1].lstrip().startswith('"""'), lines[1]
    j = 1
    while True:
        if lines[j].rstrip().endswith('"""'):
            break
        j += 1
        if j >= len(lines):
            raise RuntimeError("未找到文档串闭合")
    doc_lines = lines[1:j + 1]
    rest = lines[j + 1:]
    out = doc_lines + [
        "from __future__ import annotations",
        "from chiyu_kernel.errors import KernelError",
    ] + rest
    return "\n".join(out)


def main() -> None:
    for rel in FILES:
        p = BASE / rel
        new = fix(p.read_text(encoding="utf-8"))
        p.write_text(new, encoding="utf-8")
        print(f"  fixed {rel}")


if __name__ == "__main__":
    main()
