"""原生内核能力 → agent 工具（无缝集成桥）。

把本仓 L1–L4 能力（上下文装配 / 元红线）暴露为 dsh 式 agent 可调工具；
红线经 ``tools.execute`` 的 ``redline_guard`` 钩子拦截（被调用方硬闸门，非调用方）。

⛔ 内核零领域字面量：工具名/描述中性；领域取值来自注入的 ``TenantProfile``。
⚠ 与 `chiyu_kernel.evolution.meta_redline_hits` 的真实签名对齐：它接收
   ``Sequence[str]``（一批动作名），**无 profile 参数**，命中项取自 `META_REDLINES`
   冻结集（系统自进化红线，与业务无关）。
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from chiyu_kernel.context import assemble, KnowledgeNeed
from chiyu_kernel.evolution import meta_redline_hits
from chiyu_kernel.tools import ToolRegistry, ToolSpec


def register_native_tools(reg: ToolRegistry, *, profile) -> None:
    _ = profile  # 当前原生工具不依赖领域档案；profile 预留供未来领域注入

    def ctx_assemble(args: Mapping[str, Any]) -> Mapping[str, Any]:
        needs = [
            KnowledgeNeed(layer=n["layer"], dims=tuple(n.get("dims", ())),
                          key=n.get("key", ""))
            for n in args.get("needs", [])
        ]
        result = assemble(needs, args.get("provided", {}))
        return {"facts": result.facts,
                "missing": list(result.supply_report.missing)}

    reg.register(
        ToolSpec("native-context-assemble", "装配分层上下文（L1–L4）", scope="",
                 high_risk=False),
        ctx_assemble,
    )

    def redline_check(args: Mapping[str, Any]) -> Mapping[str, Any]:
        actions = args.get("actions") or []
        hits = list(meta_redline_hits(list(actions)))
        return {"redline_hit": bool(hits), "hits": hits}

    reg.register(
        ToolSpec("native-redline-check", "元红线命中检查", scope="", high_risk=True),
        redline_check,
    )


def native_redline_guard(*, profile) -> Callable[[str, Any], Optional[str]]:
    """返回 ``redline_guard(name, args) -> 命中原因|None``。

    仅当工具入参携带元红线动作（``args["actions"]`` 命中 ``META_REDLINES``）时返回
    原因串 ⇒ ``tools.execute`` 抛 ``GuardDenied``。非红线工具（无 actions 字段）永不误拦。
    """
    _ = profile  # 元红线集与领域档案无关；profile 预留供未来领域红线扩展

    def _guard(name: str, args: Any) -> Optional[str]:
        if not isinstance(args, dict):
            return None
        actions = args.get("actions")
        if not isinstance(actions, (list, tuple)):
            return None
        hits = list(meta_redline_hits(list(actions)))
        return ("redline:" + ", ".join(str(h) for h in hits)) if hits else None

    return _guard


__all__ = ["register_native_tools", "native_redline_guard"]
