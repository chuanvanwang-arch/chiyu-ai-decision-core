"""chiyu selftest —— 调 pytest 跑指定包测试（退出码透传）。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, List

# 本文件位于 <仓库根>/packages/chiyu-cli/src/chiyu_cli/commands/selftest.py
# parents: [0]=commands [1]=chiyu_cli [2]=src [3]=chiyu-cli [4]=packages [5]=仓库根
_ROOT = Path(__file__).resolve().parents[5]

_PACKAGES: dict = {
    "kernel": ("packages/chiyu-kernel/tests",),
    "decision": ("packages/chiyu-decision",),
    "portal": ("packages/chiyu-portal",),
    "cli": ("packages/chiyu-cli",),
}


def _targets(name: str) -> List[str]:
    if name == "all":
        return ["packages"]
    return [str(_ROOT / p) for p in _PACKAGES[name]]


def handler(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
        *_targets(args.package),
    ]
    if args.keyword:
        cmd += ["-k", args.keyword]
    print("$ " + " ".join(cmd))
    completed = subprocess.run(cmd, cwd=str(_ROOT))
    return int(completed.returncode)


def register(sub: Any) -> None:
    p = sub.add_parser("selftest", help="跑包测试")
    p.add_argument("--package", default="all",
                   choices=("all", "kernel", "decision", "portal", "cli"), help="目标包")
    p.add_argument("-k", dest="keyword", default=None, help="pytest -k 过滤")
    p.set_defaults(handler=handler)
