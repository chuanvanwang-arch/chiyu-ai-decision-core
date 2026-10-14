"""chiyu-cli：ChiYu AI 原生决策平台终端运行入口（CLI + 受限命令壳 / REPL）。

⛔ 分层纪律：本包只消费 `chiyu_kernel.api` / `chiyu_kernel.contract.*`
   与兄弟包的 `*.api` 门面，**禁止** import 内部子模块。
"""
from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
