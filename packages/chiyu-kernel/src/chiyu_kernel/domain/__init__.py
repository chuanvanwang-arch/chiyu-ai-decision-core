"""领域注入 SDK（WS6 关键石）—— 把 TenantProfile + ActionRegistry + ScenarioPack
三件套统一校验、聚合成一个 DomainBundle。

⛔ 机制非清单：本模块只承载「校验机制 + 聚合」；具体粒子类型 / Action 清单 /
场景内容都是 L4 消费方域内容，经 TenantProfile / ActionSpec / ScenarioPack 注入。
⛔ 内核不提供任何默认领域值；domain 空 / particle_types 缺核心角色 ⇒ 构造期即红。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from chiyu_kernel.actions import ActionRegistry, ActionSpec
from chiyu_kernel.contract import (
    ParticleTypeSet,
    PredicateSet,
    PredicateSpec,
    RedlineSpec,
    TenantProfile,
)
from chiyu_kernel.scenario.model import ScenarioPack, from_dict as scenario_from_dict


class DomainInjectionError(Exception):
    """领域注入失败（聚合所有校验错误，机器可路由）。"""

    def __init__(self, message: str, errors: Sequence[str]) -> None:
        super().__init__(message)
        self.name = "DomainInjectionError"
        self.errors = tuple(errors)


@dataclass(frozen=True)
class DomainBundle:
    """注入成功后的聚合体：消费方可直接拿去 open_store / run_spine / 注册 Action。"""

    profile: TenantProfile
    actions: ActionRegistry
    scenarios: Tuple[ScenarioPack, ...]


def profile_from_dict(d: Mapping[str, Any]) -> TenantProfile:
    """dict → TenantProfile（L4 域内容经此进入内核唯一通道）。

    particle_types / predicates / redline 接受 dict 或已构造对象（机制非清单：
    具体取值由消费方提供）。profile.predicates 省略时 memory 默认用内核常量
    MEMORY_PREDICATES（7 记忆谓词），consumer 只补 knowledge 部分。
    """

    if not isinstance(d, Mapping):
        raise TypeError(f"profile 必须为对象：{d!r}")
    kwargs: Dict[str, Any] = {"domain": d["domain"]}

    pt = d.get("particle_types")
    if isinstance(pt, ParticleTypeSet):
        kwargs["particle_types"] = pt
    elif isinstance(pt, Mapping):
        kwargs["particle_types"] = ParticleTypeSet(names=tuple(pt["names"]))
    else:
        kwargs["particle_types"] = ParticleTypeSet(names=tuple(pt))

    pred = d.get("predicates")
    if pred is not None:
        if isinstance(pred, PredicateSet):
            kwargs["predicates"] = pred
        elif isinstance(pred, Mapping):
            kspecs = tuple(PredicateSpec(**k) for k in pred.get("knowledge", ()))
            kwargs["predicates"] = PredicateSet(knowledge=kspecs)

    rl = d.get("redline")
    if rl is not None:
        if isinstance(rl, RedlineSpec):
            kwargs["redline"] = rl
        elif isinstance(rl, Mapping):
            kwargs["redline"] = RedlineSpec(
                mutex_top=frozenset(rl.get("mutex_top", ()) or ()),
                sensitive=frozenset(rl.get("sensitive", ()) or ()),
            )
        else:
            # J9-P3 双轨键形闸（此前 list 形态静默丢弃 = "配了却没生效"族缺陷）：
            # TenantProfile.redline 是结构化轨（dict{mutex_top,sensitive}）；
            # 决策红线词表（list[str]）属词表轨，走 run_spine(redline_items=...)。
            raise TypeError(
                f"profile.redline 须为 RedlineSpec 或 dict(mutex_top/sensitive)，"
                f"实为 {type(rl).__name__}。list/tuple 形态是决策红线词表"
                "（词表轨），不得塞进 TenantProfile.redline —— "
                "请改走 run_spine(redline_items=...)。")

    if "rubric_thresholds" in d:
        kwargs["rubric_thresholds"] = dict(d["rubric_thresholds"])
    if "autonomous_threshold" in d:
        kwargs["autonomous_threshold"] = float(d["autonomous_threshold"])
    if "extras" in d:
        kwargs["extras"] = dict(d["extras"])
    return TenantProfile(**kwargs)


def inject_domain(
    *,
    profile: Mapping[str, Any],
    actions: Sequence[Mapping[str, Any]] = (),
    scenarios: Sequence[Mapping[str, Any]] = (),
    plugin_registry: Any = None,
) -> DomainBundle:
    """唯一注入闸：dict → DomainBundle（三件套统一校验 + 跨一致性闸）。

    闸：
    1. TenantProfile 构造（domain 必填 / autonomous_threshold ∈ [0,1] /
       谓词端类型 ∈ particle_types / particle_types 含全部核心角色）
    2. ActionRegistry 注册 + audit（R1–R6：重复名 / R5 capability 冲突 / R6 force）
    3. ScenarioPack from_dict（level/mode/插件/工作流环/知识层/受控边形状）
    4. 跨一致性：场景声明的受控边（controlled_edges）的 predicate 必须 ∈
       profile 谓词集，且 from_type / to_type 必须 ∈ profile.particle_types ——
       否则该边永远建不起来（"配了却没生效"族缺陷，构造期即红）。
    """

    errors: List[str] = []

    # 1. profile
    try:
        tp = profile_from_dict(profile)
    except Exception as e:  # noqa: BLE001
        errors.append(f"TenantProfile 校验失败：{e}")
        raise DomainInjectionError("领域注入失败（profile）", errors)

    # 2. actions
    reg = ActionRegistry()
    for a in actions:
        try:
            reg.register(ActionSpec(**a))
        except Exception as e:  # noqa: BLE001
            errors.append(f"Action 注册失败 {a.get('name')!r}：{e}")
    audit_errs, _ = reg.audit()
    errors.extend(audit_errs)

    # 3. scenarios
    packs: List[ScenarioPack] = []
    for s in scenarios:
        try:
            packs.append(scenario_from_dict(s, plugin_registry=plugin_registry))
        except Exception as e:  # noqa: BLE001
            errors.append(f"ScenarioPack 校验失败 {s.get('id')!r}：{e}")

    # 4. 跨一致性闸
    declared = set(tp.predicates.names())
    types = set(tp.particle_types.names)
    for pack in packs:
        for edge in pack.controlled_edges:
            pred = edge["predicate"]
            if pred not in declared:
                errors.append(
                    f"场景 {pack.id!r} 受控边 {pred!r} 不在 profile 谓词集 "
                    f"⇒ 该边永远无法建立")
            ft = edge["from_type"]
            if ft not in types:
                errors.append(
                    f"场景 {pack.id!r} 受控边 {pred!r} from_type {ft!r} "
                    f"不在 particle_types ⇒ 该边永远无法建立")
            tt = edge["to_type"]
            if tt is not None and tt not in types:
                errors.append(
                    f"场景 {pack.id!r} 受控边 {pred!r} to_type {tt!r} "
                    f"不在 particle_types ⇒ 该边永远无法建立")

    if errors:
        raise DomainInjectionError("领域注入失败（见 errors 聚合）", errors)
    return DomainBundle(profile=tp, actions=reg, scenarios=tuple(packs))


__all__ = [
    "DomainBundle",
    "DomainInjectionError",
    "profile_from_dict",
    "inject_domain",
]
