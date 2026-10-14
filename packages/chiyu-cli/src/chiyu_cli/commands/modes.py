"""chiyu modes —— 列出四种工作模式及其启用插件（从 PluginRegistry 动态生成）。

菜单内容完全来自 `chiyu_kernel.plugins` 的预设与 registry，不硬编码领域词。
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

from ._plugins import mode_summary_lines, resolve


def handler(args: argparse.Namespace) -> int:
    if args.mode:
        mode, enabled, disabled, warns = resolve(args.mode)
        if warns:
            for w in warns:
                print(f"[警告] {w}", file=sys.stderr)
        print(f"工作模式：{mode.id} —— {mode.label}")
        print(f"说明    ：{mode.description}")
        print(f"启用插件：{', '.join(enabled) or '（无）'}")
        if disabled:
            print(f"惰性关闭：{', '.join(disabled)}")
        print(f"Phase A 后端：{mode.llm_backend}"
              + (f"（Phase B → {mode.phase_b_backend}）" if mode.phase_b_backend else "（无需 LLM）"))
        return 0
    print("ChiYu 工作模式（对标 DeepSeek Harness 桌面版）：")
    print("=" * 56)
    for line in mode_summary_lines():
        print(line)
    return 0


def register(sub: Any) -> None:
    p = sub.add_parser("modes", help="列出四种工作模式及启用插件")
    p.add_argument("--mode", default=None,
                   help="查看单个模式详情：standard/ptc/minimal/creative")
    p.set_defaults(handler=handler)
