"""shell / terminal 工具（吸收 dsh `shell/bash-local` + `terminal/terminal` + `subprocess`）。

- `run_command`：一次性子进程执行（subprocess），高危险，可选 allowlist（前缀白名单）。
- `TerminalSession`：状态化 shell 会话，持久 `cwd` 跨多次 `send`（吸收 terminal/subprocess）。
- `register_shell_tools`：注册 `shell_run`（高危险）+ `terminal_send`（高危险）到 `ToolRegistry`。

> shell 执行为高危险动作，须配合审批闸门（见 `chiyu_kernel.interaction`）。
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, List, Optional, Tuple

from chiyu_kernel.tools import ToolRegistry, ToolSpec


class CommandRejected(PermissionError):
    """命令不在 allowlist 内。"""


def _check_allowlist(cmd: str, allowlist: Optional[set]) -> None:
    if allowlist is None:
        return
    first = cmd.strip().split()
    if not first:
        raise CommandRejected("空命令")
    if first[0] in allowlist:
        return
    raise CommandRejected(f"命令不在白名单：{first[0]}")


def _run(cmd: str, *, cwd: Optional[str], allowlist: Optional[set],
         timeout: float = 30) -> str:
    _check_allowlist(cmd, allowlist)
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise
    return f"rc={r.returncode}\n{r.stdout}{r.stderr}"


def run_command(cmd: str, *, cwd: Optional[str] = None,
                allowlist: Optional[set] = None, timeout: float = 30) -> str:
    return _run(cmd, cwd=cwd, allowlist=allowlist, timeout=timeout)


class TerminalSession:
    """状态化 shell 会话：持久 `cwd` 跨多次 `send`（吸收 terminal/subprocess）。"""
    def __init__(self, cwd: Optional[str] = None, allowlist: Optional[set] = None) -> None:
        self.cwd = cwd
        self.allowlist = allowlist
        self.history: List[Tuple[str, str]] = []

    def send(self, cmd: str) -> str:
        # cd 为内部导航命令，跳过 allowlist
        is_cd = cmd.strip().lower().startswith("cd ")
        if not is_cd:
            _check_allowlist(cmd, self.allowlist)
        prefix = f"cd /d {self.cwd} && " if self.cwd else ""
        try:
            r = subprocess.run(
                prefix + cmd, shell=True, cwd=self.cwd,
                capture_output=True, text=True, timeout=30,
            )
        except subprocess.TimeoutExpired:
            raise
        out = f"rc={r.returncode}\n{r.stdout}{r.stderr}"
        self.history.append((cmd, out))
        if is_cd:
            self._apply_cd(cmd.strip()[3:].strip())
        return out

    def _apply_cd(self, target: str) -> None:
        if not target:
            return
        new = Path(target)
        if not new.is_absolute() and self.cwd is not None:
            new = Path(self.cwd) / target
        self.cwd = str(new)


def register_shell_tools(registry: ToolRegistry, *, allowlist: Optional[set] = None,
                         cwd: Optional[str] = None) -> None:
    """注册 shell_run + terminal_send（均高危险）到 registry。"""

    def _shell_run(args: Any) -> str:
        cmd = _as_str(args, "cmd")
        return run_command(cmd, cwd=cwd, allowlist=allowlist)

    def _terminal_send(args: Any) -> str:
        cmd = _as_str(args, "cmd")
        sess = TerminalSession(cwd=cwd, allowlist=allowlist)
        return sess.send(cmd)

    registry.register(
        ToolSpec(name="shell_run", description="执行一次性 shell 命令（高危险）",
                 scope="", high_risk=True),
        _shell_run,
    )
    registry.register(
        ToolSpec(name="terminal_send", description="在状态终端会话发送命令（高危险）",
                 scope="", high_risk=True),
        _terminal_send,
    )


def _as_str(args: Any, key: str, default: str = "") -> str:
    if isinstance(args, dict):
        return str(args.get(key, default))
    return default


__all__ = [
    "CommandRejected", "run_command", "TerminalSession", "register_shell_tools",
]
