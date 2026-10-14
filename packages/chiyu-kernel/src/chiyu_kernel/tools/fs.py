"""沙箱文件系统工具（吸收 dsh `fs/fs` + `fs/fs-local`）。

`SandboxedFs` 把所有路径解析限制在 `root` 内（真实路径 + 不逃离 root 守卫）；越界即拒。
`register_fs_tools` 注册 `fs_read` / `fs_write`（高危险）/ `fs_list` 进 `ToolRegistry`，
统一 `scope="fs"`。写入属高危险动作，须配合审批闸门（见 `chiyu_kernel.interaction`）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

from chiyu_kernel.tools import ToolRegistry, ToolSpec


class PathEscapeError(PermissionError):
    """路径试图逃离沙箱 root。"""


class SandboxedFs:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    def _resolve(self, path: str) -> Path:
        target = (self.root / path).resolve()
        if target != self.root and self.root not in target.parents:
            raise PathEscapeError(f"路径逃离沙箱：{path}")
        return target

    def read(self, path: str) -> str:
        return self._resolve(path).read_text(encoding="utf-8")

    def write(self, path: str, content: str) -> int:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return len(content)

    def list(self, path: str = ".") -> List[str]:
        d = self._resolve(path)
        return [str(p.relative_to(self.root)) for p in d.iterdir()]


def register_fs_tools(registry: ToolRegistry, root: str) -> None:
    """注册 fs_read / fs_write（高危险）/ fs_list 到 registry（scope=fs）。"""
    fs = SandboxedFs(root)

    def _read(args: Any) -> str:
        return fs.read(_as_str(args, "path"))

    def _write(args: Any) -> int:
        return fs.write(_as_str(args, "path"), _as_str(args, "content"))

    def _list(args: Any) -> List[str]:
        return fs.list(_as_str(args, "path", default="."))

    registry.register(
        ToolSpec(name="fs_read", description="读取沙箱内文件内容", scope="fs", high_risk=False),
        _read,
    )
    registry.register(
        ToolSpec(name="fs_write", description="写入沙箱内文件（高危险）", scope="fs", high_risk=True),
        _write,
    )
    registry.register(
        ToolSpec(name="fs_list", description="列出沙箱内目录", scope="fs", high_risk=False),
        _list,
    )


def _as_str(args: Any, key: str, default: str = "") -> str:
    if isinstance(args, dict):
        return str(args.get(key, default))
    return default


__all__ = ["SandboxedFs", "PathEscapeError", "register_fs_tools"]
