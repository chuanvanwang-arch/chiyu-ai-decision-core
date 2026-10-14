"""chiyu 命令派发入口。

⛔ 本模块只做派发与参数装配；业务一律下沉到 `commands/*`。
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from typing import Any, List, Optional

from . import __version__, shell
from .commands import decide, evolution, portal, selftest, modes


def build_parser() -> argparse.ArgumentParser:
    """构造顶层解析器并注册全部子命令。"""
    parser = argparse.ArgumentParser(
        prog="chiyu",
        description="ChiYu AI 原生决策平台 —— 终端运行入口",
    )
    parser.add_argument("--version", action="version", version=f"chiyu {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    decide.register(sub)
    portal.register(sub)
    evolution.register(sub)
    selftest.register(sub)
    modes.register(sub)
    shell.register(sub)

    # `dev`（完整 Python REPL）仅 full 版存在；external 构建不打包该模块。
    # ⛔ 这是构建形态探测（external 版无 dev.pyc），不是运行期动态派发。
    if importlib.util.find_spec("chiyu_cli.commands.dev") is not None:
        from .commands import dev

        dev.register(sub)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 主入口。返回进程退出码。"""
    parser = build_parser()
    args: Any = parser.parse_args(argv)   # required=True ⇒ 必有 handler
    return int(args.handler(args) or 0)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
