"""阶段二 Task 1：skill 技能注册表（dsh `skill` 能力吸收）。

忠实重写 dsh `packages/skill/skill/src/index.ts` 的注册表语义：
- `is_skill_name` 用 kebab-case 正则
- `SkillRegistry` register/get/list，rank 更低胜出，同名同 rank 抛 SkillConflict
- `load_catalog` 批量注册
"""
from __future__ import annotations

import pytest

from chiyu_kernel.skills import (
    SkillSpec, SkillRegistry, SkillConflict, is_skill_name, load_catalog,
)


def test_is_skill_name_grammar():
    assert is_skill_name("foo-bar")
    assert is_skill_name("summarizer")
    assert is_skill_name("a1-b2-c3")
    assert not is_skill_name("Foo_Bar")
    assert not is_skill_name("a b")
    assert not is_skill_name("")


def test_register_then_get_and_list():
    reg = SkillRegistry()
    reg.register(SkillSpec(name="summarizer", description="摘要", content="do summarize", rank=300))
    reg.register(SkillSpec(name="translator", description="翻译", content="do translate", rank=300))
    got = reg.get("summarizer")
    assert got.name == "summarizer"
    assert got.content == "do summarize"
    names = {s.name for s in reg.list()}
    assert names == {"summarizer", "translator"}


def test_get_missing_raises_keyerror():
    reg = SkillRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")


def test_lower_rank_wins_on_dup_name():
    reg = SkillRegistry()
    reg.register(SkillSpec(name="tool", description="v1", content="first", rank=300))
    reg.register(SkillSpec(name="tool", description="v2", content="second", rank=250))
    assert reg.get("tool").content == "second"  # 低 rank 胜出
    # 更高 rank 不得覆盖
    reg.register(SkillSpec(name="tool", description="v3", content="third", rank=400))
    assert reg.get("tool").content == "second"


def test_same_rank_dup_raises_conflict():
    reg = SkillRegistry()
    reg.register(SkillSpec(name="tool", description="v1", content="first", rank=250))
    with pytest.raises(SkillConflict):
        reg.register(SkillSpec(name="tool", description="v2", content="second", rank=250))


def test_load_catalog_bulk():
    reg = load_catalog({
        "summarizer": {"description": "摘要", "content": "c1", "when_to_use": "长文"},
        "translator": {"description": "翻译", "content": "c2"},
    })
    assert reg.get("summarizer").when_to_use == "长文"
    assert reg.get("translator").model_invocable is True
    assert len(reg.list()) == 2
