"""平台模型 ↔ kernel ScenarioPack 双模型映射。

⛔ 单一校验闸：写入前必经 kernel scenario_from_dict 校验（平台模型 → 转 kernel
ScenarioPack → from_dict，任何非法输入抛 ScenarioPackError → 调用层转 422）。
适配器只做字段映射，不做重复校验。
"""
from __future__ import annotations

from typing import Any, Dict

try:  # noqa: C0412 — kernel 经 conftest 注入 sys.path，此处兜底
    from chiyu_kernel.api import ScenarioPackError, scenario_from_dict
except ImportError:  # pragma: no cover
    ScenarioPackError = Exception
    scenario_from_dict = None


# platform → kernel：平台 {pkg/namespace/tenant/actions/assets/integrations/status}
# 映射为 kernel ScenarioPack {id/name/level/mode/workflow/knowledge_needs}。
# ⚠️ 平台模型没有 level/mode 显式字段 ⇒ 由命名约定推断：
#    pkg 前缀 flow- → "flow"、end2end- → "end2end"，默认 "single"。
def platform_to_pack(platform: Dict[str, Any]) -> Dict[str, Any]:
    pkg: str = platform.get("pkg") or ""
    level = "single"
    if pkg.startswith("end2end-"):
        level = "end2end"
    elif pkg.startswith("flow-"):
        level = "flow"
    steps = []
    for i, a in enumerate(platform.get("actions") or []):
        steps.append({"name": f"step-{i}", "prompt": str(a), "depends_on": []})
    if not steps:  # 空 actions → 1 个占位 step 避免 from_dict 因空 workflow 拒绝
        steps = [{"name": "step-0", "prompt": "(no action)", "depends_on": []}]
    return {
        "id": pkg,
        "name": pkg,
        "level": level,
        "mode": "standard",
        "direction": platform.get("namespace") or "generic",
        "plugins": [str(i["name"]) for i in (platform.get("integrations") or [])
                    if isinstance(i, dict) and i.get("name")],
        "workflow": {"steps": steps},
        "knowledge_needs": [
            {"layer": str(a.get("layer")), "dims": list(a.get("dims") or [])}
            for a in (platform.get("assets") or [])
        ],
    }


def validate_platform(platform: Dict[str, Any]) -> None:
    """写入前唯一校验闸：平台模型 → kernel ScenarioPack → from_dict。抛异常即非法。"""
    if scenario_from_dict is None:  # pragma: no cover
        raise RuntimeError("kernel scenario_from_dict 不可用")
    kernel = platform_to_pack(platform)
    scenario_from_dict(kernel)  # 任何非法 → ScenarioPackError


# kernel → platform（读回/预览）
def pack_to_platform(kernel: Dict[str, Any], *, tenant: str = "t-default") -> Dict[str, Any]:
    return {
        "pkg": kernel["id"],
        "namespace": kernel.get("direction") or "generic",
        "tenant": tenant,
        "actions": [s["prompt"] for s in kernel["workflow"]["steps"]],
        "assets": kernel.get("knowledge_needs") or [],
        "integrations": [{"name": p} for p in (kernel.get("plugins") or [])],
        "status": "draft",
    }
