"""T4 — shell/terminal 工具（吸收 dsh `shell/bash-local` + `terminal/terminal` + `subprocess`）。

TDD：先红（chiyu_kernel.tools.shell 尚不存在）→ 绿。
"""
import os
import tempfile

from chiyu_kernel.tools import ToolRegistry
from chiyu_kernel.tools.shell import (
    CommandRejected, TerminalSession, register_shell_tools, run_command,
)


def test_run_command_echo():
    out = run_command("echo hello")
    assert "hello" in out
    assert "rc=0" in out


def test_allowlist_rejects_unlisted():
    raised = False
    try:
        run_command("rm -rf /", allowlist={"echo", "dir"})
    except CommandRejected:
        raised = True
    assert raised, "allowlist 未拒绝未列命令"


def test_terminal_session_persists_cwd():
    d = tempfile.mkdtemp()
    sub = os.path.join(d, "sub")
    os.mkdir(sub)
    sess = TerminalSession(cwd=d)
    sess.send("echo one")
    sess.send(f"cd sub")
    assert sess.cwd == sub, f"cwd 未持久：{sess.cwd}"
    sess.send("echo two")
    assert len(sess.history) == 3


def test_register_shell_tools_high_risk():
    reg = ToolRegistry()
    register_shell_tools(reg, allowlist={"echo"})
    assert reg.spec("shell_run").high_risk is True
    assert reg.spec("terminal_send").high_risk is True
    # 经 registry 调用（shell_run 高危险，scope 默认全局）
    out = reg.execute("shell_run", {"cmd": "echo via_reg"}, scope="")
    assert "via_reg" in out
