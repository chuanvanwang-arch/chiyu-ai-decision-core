"""TenantProfile 往返一致性 —— β5「demo 域可表达」的构造级实证。

⛔ 本测试不连 DB。它验证「profile JSON 能无损载入契约对象」，
   是存储层 zero 领域字面量 + 消费方注入语义的落地判据之一。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from chiyu_kernel.contract import (
    CORE_ROLES,
    ParticleTypeSet,
    PredicateSet,
    PredicateSpec,
    RedlineSpec,
    TenantProfile,
)

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
_GROUP_APPEAL = _EXAMPLES / "group-appeal.profile.json"


def _load_example() -> dict:
    assert _GROUP_APPEAL.exists(), f"示例 profile 缺失：{_GROUP_APPEAL}"
    with open(_GROUP_APPEAL, encoding="utf-8") as f:
        return json.load(f)


def test_example_profile_roundtrip() -> None:
    """examples/group-appeal.profile.json —— 反抽 demo 群诉域。"""
    data = _load_example()
    pts = ParticleTypeSet(names=tuple(data["particle_types"]))
    # 5 个核心语义角色必须被覆盖
    for role in CORE_ROLES:
        assert pts.covers(role), f"缺少核心角色 {role}"
    # 群诉域自有角色可扩展表达
    for own in ("group", "respondent", "claim"):
        assert pts.covers(own), f"缺少领域自有角色 {own}"

    pred = PredicateSet(knowledge=tuple(
        PredicateSpec(**p) for p in data["predicates"]["knowledge"]
    ))
    red = RedlineSpec(
        mutex_top=frozenset(data["redline"]["mutex_top"]),
        sensitive=frozenset(data["redline"]["sensitive"]),
    )
    profile = TenantProfile(
        domain=data["domain"],
        particle_types=pts,
        predicates=pred,
        redline=red,
        rubric_thresholds=dict(data["rubric_thresholds"]),
        autonomous_threshold=data["autonomous_threshold"],
    )
    assert profile.domain == "group_appeal"
    assert "group" in profile.particle_types.names
    # 谓词端点必须落在粒子类型集内（__post_init__ 构造期校验，能过即证明两端合法）
    assert len(profile.predicates.knowledge) == 4
    assert profile.autonomous_threshold == 0.79


def test_kernel_refuses_domain_literals_default() -> None:
    """⛔ 内核不提供领域默认：空 domain / 空粒子类型集必须抛（防止默认域漂移）。"""
    with pytest.raises(ValueError, match="domain 必填"):
        TenantProfile(domain="", particle_types=ParticleTypeSet(names=CORE_ROLES))
    with pytest.raises(ValueError, match="不得为空"):
        ParticleTypeSet(names=())


def test_autonomous_threshold_bounds() -> None:
    with pytest.raises(ValueError, match="autonomous_threshold"):
        TenantProfile(
            domain="x",
            particle_types=ParticleTypeSet(names=CORE_ROLES),
            autonomous_threshold=1.5,
        )


def test_predicate_endpoint_must_be_in_particle_types() -> None:
    """谓词 to_type 指向未声明的粒子类型 ⇒ 构造期拒绝（该边永远建不起来）。"""
    pts = ParticleTypeSet(names=CORE_ROLES)  # 无 "ghost"
    with pytest.raises(ValueError, match="不在"):
        TenantProfile(
            domain="x",
            particle_types=pts,
            predicates=PredicateSet(knowledge=(
                PredicateSpec(predicate="links_to", from_type="entity",
                              to_type="ghost", layer="K", source="rule"),
            )),
        )
