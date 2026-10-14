"""CLI 派发与命令面测试。

⛔ 判别力要求：`--help` 断言不得写成恒真式（如 `== 0 or True`），
   否则「子命令漏注册」永远不会红。
"""
from __future__ import annotations

import pytest

from chiyu_cli.main import build_parser, main

EXPECTED_COMMANDS = ("decide", "portal", "evolution", "selftest", "shell", "dev")


def test_help_lists_all_commands():
    """六个子命令必须全部出现在 --help 中（漏注册 ⇒ 红）。"""
    help_text = build_parser().format_help()
    for cmd in EXPECTED_COMMANDS:
        assert cmd in help_text, f"--help 未列出子命令 {cmd}"


def test_main_help_exits_zero():
    """argparse 的 --help 走 SystemExit(0)。"""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_every_command_has_handler():
    """每个子命令都必须装配 handler（漏 set_defaults ⇒ 派发时 AttributeError）。"""
    parser = build_parser()
    cases = (
        ["decide", "--topic", "x"],
        ["portal", "render", "--nl", "x"],
        ["evolution", "readiness"],
        ["selftest", "--package", "portal"],
        ["shell"],
        ["dev"],
    )
    for argv in cases:
        args = parser.parse_args(argv)
        assert hasattr(args, "handler"), f"{argv[0]} 未装配 handler"
