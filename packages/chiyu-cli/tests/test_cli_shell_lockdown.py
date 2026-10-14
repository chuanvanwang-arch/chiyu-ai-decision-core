"""受限命令壳的封锁测试（external 版防读源码的技术判据）。

⛔ 判别力自证：把 `shell._run` 的「未知命令」分支改成放行，
   下列测试必须全部转红；否则说明壳子只是摆设。
"""
from __future__ import annotations

import chiyu_cli.shell as sh


def _feed(monkeypatch, lines):
    seq = iter(lines)
    monkeypatch.setattr("builtins.input", lambda _="": next(seq))


def test_shell_rejects_raw_import(monkeypatch, capsys):
    """⛔ 核心：`import chiyu_kernel` 必须被拒（external 版靠此封死读源码）。"""
    _feed(monkeypatch, ["import chiyu_kernel", "exit"])
    sh.run_shell()
    err = capsys.readouterr().err
    assert "拒绝" in err
    assert "import" in err


def test_shell_rejects_arbitrary_python(monkeypatch, capsys):
    """任意 Python 语句（含 __import__ 逃逸写法）同样被拒。"""
    _feed(monkeypatch, ["__import__('os').system('echo hi')", "exit"])
    sh.run_shell()
    err = capsys.readouterr().err
    assert "拒绝" in err


def test_shell_help_lists_only_whitelist(monkeypatch, capsys):
    """help 输出不得出现 dev / import 等非白名单项。"""
    _feed(monkeypatch, ["help", "exit"])
    sh.run_shell()
    out = capsys.readouterr().out
    for allowed in ("decide", "render", "readiness", "selftest", "exit"):
        assert allowed in out
    assert "dev" not in out


def test_shell_exit_returns_zero(monkeypatch):
    _feed(monkeypatch, ["exit"])
    assert sh.run_shell() == 0
