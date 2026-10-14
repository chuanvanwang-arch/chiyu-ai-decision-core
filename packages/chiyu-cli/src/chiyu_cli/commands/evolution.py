"""chiyu evolution readiness —— 自主通道开闸前置认证（§12.3 七闸 + §12.4 G1/G2/G3）。

⛔ 本命令**只认证、不开闸**；夜批调度器上线前必须先过本闸。
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from chiyu_kernel.api import (
    ChannelNotReadyError,
    assert_channel_may_open,
    readiness_report,
)


def handler(args: argparse.Namespace) -> int:
    if args.assert_:
        try:
            report = assert_channel_may_open()
        except ChannelNotReadyError as exc:
            rep = exc.args[0]
            print("[拒绝开闸] 存在阻断闸 RED：", file=sys.stderr)
            for c in rep.blocking_red:
                print(f"  - {c.check_id} {c.title}: {c.detail}", file=sys.stderr)
            return 1
    else:
        report = readiness_report()

    if args.json:
        rows = [
            {
                "check_id": c.check_id,
                "title": c.title,
                "status": c.status,
                "detail": c.detail,
                "discriminating": c.discriminating,
            }
            for c in report.checks
        ]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print(f"{'ID':<28}{'状态':<8}{'有鉴别力':<10}标题")
    print("-" * 76)
    for c in report.checks:
        flag = "是" if c.discriminating else "否"
        print(f"{c.check_id:<28}{c.status:<8}{flag:<10}{c.title}")
        if c.detail:
            print(f"{'':<28}{c.detail}")
    print("-" * 76)
    print(report.summary())          # ⚠ summary 是方法，不是属性
    return 0


def register(sub: Any) -> None:
    p = sub.add_parser("evolution", help="平台自进化")
    sub2 = p.add_subparsers(dest="evolution_cmd", required=True)
    r = sub2.add_parser("readiness", help="开闸前置认证")
    r.add_argument("--assert", dest="assert_", action="store_true",
                   help="未全绿即抛 ChannelNotReadyError 并退 1")
    r.add_argument("--json", action="store_true", help="机器可读输出")
    r.set_defaults(handler=handler)
