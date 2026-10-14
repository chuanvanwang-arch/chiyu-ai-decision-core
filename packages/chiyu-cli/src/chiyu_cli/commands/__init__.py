"""chiyu 子命令实现。

每个子模块对外只暴露 `register(subparsers)` 与 `handler(args)` 两个契约函数。
"""
from __future__ import annotations

__all__ = ["decide", "dev", "evolution", "portal", "selftest"]
