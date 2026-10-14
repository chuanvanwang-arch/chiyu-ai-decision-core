"""§13 零残留 lint（WS4 / CRM F-08 / enterprise #4）。

扫描对外产物（默认 `ppt` 展示页）中的禁用标记与「已落地」类越权表述，
命中即非零残留（退出 1，并打印 file:line 便于定位）。

用法：
  python tools/check_zero_residue.py [PATHS...] [--tokens FILE]
  - PATHS 默认 `ppt`（仓库相对）；可追加 `docs` 等。
  - --tokens 默认 `tools/zero_residue.tokens`（一行一词，`#` 注释）。
  - 命中即退出 1。

判别力：测试向临时文件注入令牌并断言判红（详见 tools/tests/test_check_zero_residue.py）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCAN_SUFFIXES = {".md", ".py", ".txt", ".json", ".slide", ".html"}
DEFAULT_TOKENS = "tools/zero_residue.tokens"
DEFAULT_PATHS = ["ppt"]


def load_tokens(path: Path) -> list:
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


def scan(root: Path, tokens: list) -> list:
    """返回 [(path, lineno, token), ...] 命中列表。"""
    hits = []
    if root.is_file():
        files = [root]
    else:
        files = [p for p in root.rglob("*") if p.suffix in SCAN_SUFFIXES]
    for f in files:
        try:
            lines = f.read_text(encoding="utf-8", errors="strict").splitlines()
        except Exception:  # noqa: BLE001
            continue
        for i, line in enumerate(lines, 1):
            for tok in tokens:
                if tok and tok in line:
                    hits.append((f, i, tok))
                    break
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="§13 零残留 lint")
    ap.add_argument("paths", nargs="*", default=DEFAULT_PATHS)
    ap.add_argument("--tokens", default=DEFAULT_TOKENS)
    args = ap.parse_args(argv)
    repo = Path(__file__).resolve().parents[1]
    tokens = load_tokens(repo / args.tokens)
    if not tokens:
        print(f"[warn] tokens 文件为空或缺失：{args.tokens}", file=sys.stderr)
    hits = []
    for p in args.paths:
        hits.extend(scan(repo / p, tokens))
    if hits:
        for f, i, tok in hits:
            print(f"{f}:{i}: 命中禁用标记 {tok!r}")
        print(f"\n§13 零残留：{len(hits)} 处非零残留", file=sys.stderr)
        return 1
    print("§13 零残留：通过（0 处）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
