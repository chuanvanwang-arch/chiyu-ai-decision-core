"""J9-P3 双轨键形闸：TenantProfile.redline 只收结构化形态，词表 list 形态 fail-fast。

此前缺陷：profile_from_dict 对 list 形态的 redline 两个分支都不命中 → **静默丢弃**
（"配了却没生效"族）。守卫：词表轨（list[str] → run_spine redline_items）与
结构化轨（dict{mutex_top,sensitive} → TenantProfile.redline）不得混装。
"""
import pytest

from chiyu_kernel.api import profile_from_dict

# ParticleTypeSet 要求核心语义角色齐备（构造期闸）；与红线闸无关的合法夹具。
_PT = {"names": ["unstructured_asset", "entity", "decision", "memory", "knowledge"]}


def test_redline_dict_form_builds_spec():
    tp = profile_from_dict({
        "domain": "t", "particle_types": _PT,
        "redline": {"mutex_top": ["m1"], "sensitive": ["s1"]},
    })
    assert tp.redline.mutex_top == frozenset({"m1"})
    assert tp.redline.sensitive == frozenset({"s1"})


def test_redline_spec_instance_passthrough():
    from chiyu_kernel.contract.profile import RedlineSpec
    spec = RedlineSpec(mutex_top=frozenset({"m"}))
    tp = profile_from_dict({
        "domain": "t", "particle_types": _PT, "redline": spec,
    })
    assert tp.redline is spec


def test_redline_list_form_fails_loud():
    """词表形态塞进结构化轨 ⇒ TypeError 且提示改走 run_spine(redline_items)。"""
    with pytest.raises(TypeError, match="redline_items"):
        profile_from_dict({
            "domain": "t", "particle_types": _PT,
            "redline": ["未做小样确认即批量出货"],
        })


def test_redline_absent_defaults_empty():
    tp = profile_from_dict({"domain": "t", "particle_types": _PT})
    assert tp.redline.mutex_top == frozenset() and tp.redline.sensitive == frozenset()
