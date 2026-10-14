"""受限命令壳 —— ⛔ 白名单外一律拒绝（技术上封死 raw import 逃逸）。

external（外部顾问版）只提供本壳，不提供完整 Python REPL；
因此外部顾问**无法**借 `chiyu shell` 执行 `import chiyu_kernel` 读取源码。
"""
from __future__ import annotations

import argparse
import shlex
import sys
from typing import Any, List

from .commands.decide import handler as _decide
from .commands.evolution import handler as _readiness
from .commands.portal import handler as _render
from .commands.selftest import handler as _selftest
from .commands._plugins import resolve

HELP = """可用命令：
  decide "议题"                       跑决策脊柱
  render "页面描述" [--out p.html]     NL → HTML
  readiness [--assert]                开闸前置认证
  selftest [kernel|decision|portal|cli|all]
  help                                显示本帮助
  exit                                退出
⛔ 仅以上命令可用；不支持任意 Python 语句与 import。
"""

_EXIT = -1          # 哨兵：退出循环


def _run(argv: List[str]) -> int:
    """把壳内一行解析为受控调用。未知命令 ⇒ 拒绝并退 2。"""
    if not argv:
        return 0
    head, rest = argv[0], argv[1:]

    if head == "decide":
        topic = rest[0] if rest else ""
        if not topic:
            print('用法：decide "议题"', file=sys.stderr)
            return 2
        return int(_decide(argparse.Namespace(
            topic=topic, scores=None, threshold=0.79, decision_id=None, json=False)))

    if head == "render":
        nl = rest[0] if rest else ""
        if not nl:
            print('用法：render "页面描述" [--out p.html]', file=sys.stderr)
            return 2
        out = None
        if "--out" in rest:
            idx = rest.index("--out")
            out = rest[idx + 1] if idx + 1 < len(rest) else None
        return int(_render(argparse.Namespace(
            nl=nl, out=out, title=None, particle_types=None)))

    if head == "readiness":
        return int(_readiness(argparse.Namespace(
            assert_="--assert" in rest, json=False)))

    if head == "selftest":
        pkg = rest[0] if rest else "all"
        return int(_selftest(argparse.Namespace(package=pkg, keyword=None)))

    if head == "help":
        print(HELP)
        return 0

    if head == "exit":
        return _EXIT

    print(f"[拒绝] 不支持的命令 {head!r}；输入 help 查看可用命令。", file=sys.stderr)
    return 2


def run_shell(mode_id: str | None = None) -> int:
    """启动受限命令壳。返回 0（正常退出）。"""
    mode, enabled, disabled, mwarn = resolve(mode_id)
    if mwarn:
        for w in mwarn:
            print(f"[模式警告] {w}", file=sys.stderr)
    banner = (f"chiyu shell（受限命令壳）— 工作模式：{mode.id}（{mode.label}）；"
              f"启用插件：{', '.join(enabled) or '无'}。输入 help 查看命令，exit 退出。")
    if mode.orchestration.get("portal_hidden"):
        banner += "  极简模式：门户导航已隐藏。"
    print(banner)
    while True:
        try:
            line = input("chiyu> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        try:
            argv = shlex.split(line)
        except ValueError as exc:
            print(f"[拒绝] 无法解析：{exc}", file=sys.stderr)
            continue
        rc = _run(argv)
        if rc == _EXIT:
            return 0
    return 0


def handler(args: Any) -> int:
    return run_shell(getattr(args, "mode", None))


def register(sub: Any) -> None:
    p = sub.add_parser("shell", help="受限命令壳（两版共有）")
    p.add_argument("--mode", default=None,
                   help="工作模式：standard/ptc/minimal/creative（缺省=standard）")
    p.set_defaults(handler=handler)
