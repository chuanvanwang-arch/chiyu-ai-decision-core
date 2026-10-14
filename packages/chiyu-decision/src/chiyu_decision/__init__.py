"""chiyu-decision —— 决策脊柱运行时（L2）。

顺序契约来自 L0 单一事实源，本包不得另写一份；门面经 `chiyu_decision.api` 暴露，
此处重导出以便 `from chiyu_decision import ...` 直接可用。
"""
from __future__ import annotations

__version__ = "0.1.0"

from .api import *                      # 重导出决策门面（唯一公开面）
from .api import __all__ as _API_ALL

__all__ = ["__version__", *_API_ALL]
