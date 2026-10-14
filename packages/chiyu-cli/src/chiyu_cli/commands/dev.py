"""chiyu dev —— 完整 Python REPL（⚠ 仅 full 全代码版；external 构建不打包本模块）。

预置三门面与常用快捷函数，供内部开发现场试跑。
"""
from __future__ import annotations

import argparse
import code
from pathlib import Path
from typing import Any, Dict

BANNER = """chiyu dev —— 完整 Python REPL（仅全代码版）
预置：K = chiyu_kernel.api   C = chiyu_kernel.contract
      D = chiyu_decision.api P = chiyu_portal.api
      render(nl, out=None) · readiness() · decide(topic)
Ctrl-D 退出。"""


def _namespace() -> Dict[str, Any]:
    import chiyu_kernel.api as K
    import chiyu_kernel.contract as C
    import chiyu_decision.api as D
    import chiyu_portal.api as P
    from chiyu_kernel.contract.particle import CORE_ROLES, ParticleTypeSet

    def render(nl: str, out: str | None = None) -> str:
        guard = P.guard_nl_input(nl)
        if not guard.ok:
            return f"护栏拒绝：{guard.reason}"
        parsed = P.parse_nl_to_schema(nl)
        res = P.render_page(parsed.schema, particle_types=ParticleTypeSet(names=CORE_ROLES))
        if not res.ok:
            return "渲染拒绝：" + "; ".join(str(e) for e in res.errors)
        if out:
            Path(out).write_text(res.html, encoding="utf-8")
            return f"已写出 {out}"
        return res.html

    def readiness() -> str:
        return K.readiness_report().summary

    def decide(topic: str) -> Any:
        return D.run_spine(
            context={"topic": topic}, profile=None,
            rubric_scores={}, elements={"intent": topic}, persister=None,
        )

    return {
        "K": K, "C": C, "D": D, "P": P,
        "render": render, "readiness": readiness, "decide": decide,
    }


def handler(args: argparse.Namespace) -> int:
    code.interact(banner=BANNER, local=_namespace())
    return 0


def register(sub: Any) -> None:
    p = sub.add_parser("dev", help="完整 Python REPL（仅全代码版）")
    p.set_defaults(handler=handler)
