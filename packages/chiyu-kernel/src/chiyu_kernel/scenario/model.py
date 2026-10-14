"""ScenarioPack 数据模型 —— 可运行场景包（机制层，零领域字面量）。

场景包 = **模式 + 插件 + 声明式工作流 DAG + 知识需求**的可复用资产：
向导四元组与客户端 MCP 文件调用**双入口**都经本模块唯一的 `from_dict` 校验闸
落盘，不存在第二套写包逻辑（设计 docs/2026-09-26-scenario-pack-design.md §3）。

错误码族对齐 `workflow.WorkflowError` 风格（机器可路由，非自由文本）：
- PACK_META_INVALID      id 非 kebab-case / name 空 / level ∉ LEVEL_IDS / mode ∉ MODE_PRESETS
- PACK_PLUGIN_UNKNOWN    plugins 含插件注册表外插件（传入 registry 时校验）
- PACK_WORKFLOW_INVALID  steps 空 / 步骤名重复 / depends_on 指向不存在步骤 / DAG 成环
- PACK_NEEDS_INVALID     knowledge_needs 的 layer ∉ {L1,L2,L3,L4}

`to_workflow()` 复用 `chiyu_kernel.workflow.Workflow`（其 `topo_order` 作为环检测
的二次兜底——本模块校验闸先行，Workflow 构造再兜底，双保险非重复实现）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from chiyu_kernel.plugins.modes import MODE_PRESETS
from chiyu_kernel.workflow import Workflow, WorkflowMeta, WorkflowStep

LEVEL_IDS = ("single", "flow", "end2end")

KNOWLEDGE_LAYERS = ("L1", "L2", "L3", "L4")

_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

__all__ = [
    "LEVEL_IDS",
    "KNOWLEDGE_LAYERS",
    "ScenarioPackError",
    "ScenarioStep",
    "ScenarioPack",
    "from_dict",
]


class ScenarioPackError(Exception):
    """机器可路由的场景包失败（对齐 WorkflowError 风格）。"""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.name = "ScenarioPackError"
        self.code = code


@dataclass
class ScenarioStep:
    """包内一个声明式步骤（语义与 workflow.WorkflowStep 对齐，独立持有便于校验）。"""

    name: str
    prompt: str
    depends_on: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "prompt": self.prompt, "depends_on": list(self.depends_on)}


@dataclass
class ScenarioPack:
    """可运行场景包（机制层中性：level/mode 为机制枚举，领域内容走消费方注入）。"""

    id: str
    name: str
    level: str
    direction: str
    mode: str
    plugins: Tuple[str, ...] = ()
    workflow_steps: Tuple[ScenarioStep, ...] = ()
    knowledge_needs: Tuple[Dict[str, Any], ...] = ()
    controlled_edges: Tuple[Dict[str, Any], ...] = ()
    locked_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "direction": self.direction,
            "mode": self.mode,
            "plugins": list(self.plugins),
            "workflow": {"steps": [s.to_dict() for s in self.workflow_steps]},
            "knowledge_needs": [dict(n) for n in self.knowledge_needs],
            "controlled_edges": [dict(e) for e in self.controlled_edges],
            "locked_by": self.locked_by,
        }

    def to_workflow(self) -> Workflow:
        """pack → `chiyu_kernel.workflow.Workflow`（Workflow.topo_order 二次兜底环检测）。"""
        meta = WorkflowMeta(name=self.id, description=self.name)
        steps = [
            WorkflowStep(name=s.name, prompt=s.prompt, depends_on=list(s.depends_on))
            for s in self.workflow_steps
        ]
        return Workflow(meta=meta, steps=steps)


def _validate_meta(data: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    pack_id = data.get("id")
    if not isinstance(pack_id, str) or not _KEBAB_RE.match(pack_id):
        raise ScenarioPackError(f"id 必须为 kebab-case：{pack_id!r}", "PACK_META_INVALID")
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ScenarioPackError(f"name 必须为非空字符串：{name!r}", "PACK_META_INVALID")
    level = data.get("level")
    if level not in LEVEL_IDS:
        raise ScenarioPackError(f"level 必须属于 {LEVEL_IDS}：{level!r}", "PACK_META_INVALID")
    direction = data.get("direction")
    if not isinstance(direction, str) or not direction.strip():
        raise ScenarioPackError(f"direction 必须为非空字符串：{direction!r}", "PACK_META_INVALID")
    mode = data.get("mode")
    if mode not in MODE_PRESETS:
        raise ScenarioPackError(
            f"mode 必须属于 {tuple(sorted(MODE_PRESETS))}：{mode!r}", "PACK_META_INVALID")
    return pack_id, name, level, direction, mode  # type: ignore[return-value]


def _validate_plugins(data: Mapping[str, Any], registry: Any) -> Tuple[str, ...]:
    raw = data.get("plugins") or []
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        raise ScenarioPackError(f"plugins 必须为字符串序列：{raw!r}", "PACK_META_INVALID")
    plugins = tuple(raw)
    if registry is not None:
        unknown = [p for p in plugins if not registry.has(p)]
        if unknown:
            raise ScenarioPackError(
                f"plugins 含注册表外插件：{unknown}", "PACK_PLUGIN_UNKNOWN")
    return plugins


def _validate_workflow(data: Mapping[str, Any]) -> Tuple[ScenarioStep, ...]:
    wf = data.get("workflow")
    if not isinstance(wf, Mapping):
        raise ScenarioPackError(f"workflow 必须为对象：{wf!r}", "PACK_WORKFLOW_INVALID")
    raw_steps = wf.get("steps")
    if not isinstance(raw_steps, Sequence) or not raw_steps:
        raise ScenarioPackError(f"workflow.steps 必须为非空序列：{raw_steps!r}",
                                "PACK_WORKFLOW_INVALID")
    steps: List[ScenarioStep] = []
    seen: set = set()
    for s in raw_steps:
        if not isinstance(s, Mapping):
            raise ScenarioPackError(f"步骤必须为对象：{s!r}", "PACK_WORKFLOW_INVALID")
        sname = s.get("name")
        if not isinstance(sname, str) or not sname.strip():
            raise ScenarioPackError(f"步骤名必须为非空字符串：{sname!r}",
                                    "PACK_WORKFLOW_INVALID")
        if sname in seen:
            raise ScenarioPackError(f"步骤名重复：{sname!r}", "PACK_WORKFLOW_INVALID")
        seen.add(sname)
        prompt = s.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ScenarioPackError(f"步骤 {sname!r} 缺 prompt", "PACK_WORKFLOW_INVALID")
        deps = s.get("depends_on") or []
        if not isinstance(deps, Sequence) or isinstance(deps, str):
            raise ScenarioPackError(
                f"步骤 {sname!r} depends_on 必须为字符串序列：{deps!r}",
                "PACK_WORKFLOW_INVALID")
        steps.append(ScenarioStep(name=sname, prompt=prompt, depends_on=tuple(deps)))

    names = seen
    for s in steps:
        for d in s.depends_on:
            if d not in names:
                raise ScenarioPackError(
                    f"步骤 {s.name!r} 依赖不存在的步骤 {d!r}", "PACK_WORKFLOW_INVALID")

    # Kahn 环检测（自校验闸先跑；to_workflow 的 Workflow.topo_order 二次兜底）
    indeg = {s.name: 0 for s in steps}
    adj: Dict[str, List[str]] = {s.name: [] for s in steps}
    for s in steps:
        for d in s.depends_on:
            adj[d].append(s.name)
            indeg[s.name] += 1
    queue = [n for n, deg in indeg.items() if deg == 0]
    visited = 0
    while queue:
        n = queue.pop()
        visited += 1
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    if visited != len(steps):
        raise ScenarioPackError("workflow 存在循环依赖（cycle detected）",
                                "PACK_WORKFLOW_INVALID")
    return tuple(steps)


def _validate_needs(data: Mapping[str, Any]) -> Tuple[Dict[str, Any], ...]:
    raw = data.get("knowledge_needs") or []
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        raise ScenarioPackError(f"knowledge_needs 必须为序列：{raw!r}", "PACK_NEEDS_INVALID")
    needs: List[Dict[str, Any]] = []
    for n in raw:
        if not isinstance(n, Mapping):
            raise ScenarioPackError(f"knowledge_needs 项必须为对象：{n!r}",
                                    "PACK_NEEDS_INVALID")
        layer = n.get("layer")
        if layer not in KNOWLEDGE_LAYERS:
            raise ScenarioPackError(
                f"knowledge_needs.layer 必须属于 {KNOWLEDGE_LAYERS}：{layer!r}",
                "PACK_NEEDS_INVALID")
        needs.append({"layer": layer, "dims": list(n.get("dims") or [])})
    return tuple(needs)


def _validate_edges(data: Mapping[str, Any]) -> Tuple[Dict[str, Any], ...]:
    """受控谓词边声明（机制；取值由 profile 提供）。

    仅做形状校验（predicate 名 + from_type 必填、to_type 可选）；
    「边名 ∈ profile 谓词集 / 端类型 ∈ particle_types」的跨一致性闸在
    `chiyu_kernel.domain.inject_domain` 统一校验（from_dict 拿不到 profile）。
    """

    raw = data.get("controlled_edges") or []
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        raise ScenarioPackError(f"controlled_edges 必须为序列：{raw!r}",
                                "PACK_NEEDS_INVALID")
    edges: List[Dict[str, Any]] = []
    for e in raw:
        if not isinstance(e, Mapping):
            raise ScenarioPackError(f"controlled_edges 项必须为对象：{e!r}",
                                    "PACK_NEEDS_INVALID")
        pred = e.get("predicate")
        if not isinstance(pred, str) or not pred.strip():
            raise ScenarioPackError(f"边 predicate 必须为非空字符串：{pred!r}",
                                    "PACK_NEEDS_INVALID")
        ft = e.get("from_type")
        if not isinstance(ft, str) or not ft.strip():
            raise ScenarioPackError(
                f"边 {pred!r} from_type 必须为非空字符串：{ft!r}",
                "PACK_NEEDS_INVALID")
        tt = e.get("to_type")
        if tt is not None and not isinstance(tt, str):
            raise ScenarioPackError(
                f"边 {pred!r} to_type 必须为字符串或空：{tt!r}",
                "PACK_NEEDS_INVALID")
        edges.append({"predicate": pred, "from_type": ft, "to_type": tt})
    return tuple(edges)


def from_dict(data: Mapping[str, Any], *, plugin_registry: Any = None) -> ScenarioPack:
    """唯一写包校验闸：dict → `ScenarioPack`（双入口共用，无第二套逻辑）。"""
    if not isinstance(data, Mapping):
        raise ScenarioPackError(f"场景包必须为对象：{data!r}", "PACK_META_INVALID")
    pack_id, name, level, direction, mode = _validate_meta(data)
    plugins = _validate_plugins(data, plugin_registry)
    steps = _validate_workflow(data)
    needs = _validate_needs(data)
    edges = _validate_edges(data)
    return ScenarioPack(
        id=pack_id,
        name=name,
        level=level,
        direction=direction,
        mode=mode,
        plugins=plugins,
        workflow_steps=steps,
        knowledge_needs=needs,
        controlled_edges=edges,
    )
