"""支持 `python -m chiyu_cli`（零安装运行）。"""
from __future__ import annotations

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())
