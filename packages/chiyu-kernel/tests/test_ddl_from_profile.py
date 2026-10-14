"""DDL 由 profile 驱动 —— 结构证明「同一内核、两个领域」可行。

⛔ 判据不是"DDL 里有 'cluster'"（那是某域），而是：
   用两个**互不相交**的粒子类型集生成 DDL，两者 CHECK 内容不同，
   且**共享同一条内核代码路径**（同一个 ddl_statements 函数）。
"""
from __future__ import annotations

import pytest

from chiyu_kernel.contract import ParticleTypeSet, PredicateSet, TenantProfile
from chiyu_kernel.store.ddl import assert_no_free_jsonb, ddl_statements

CORE = ("unstructured_asset", "entity", "decision", "memory", "knowledge")


def _profile(domain: str, extra: tuple) -> TenantProfile:
    return TenantProfile(
        domain=domain,
        particle_types=ParticleTypeSet(names=CORE + extra),
        predicates=PredicateSet(),
    )


def test_two_domains_share_one_code_path():
    a = "\n".join(ddl_statements(_profile("domain-a", ("alpha_obj",)), "s_a"))
    b = "\n".join(ddl_statements(_profile("domain-b", ("beta_obj",)), "s_b"))
    assert "'alpha_obj'" in a and "'beta_obj'" not in a
    assert "'beta_obj'" in b and "'alpha_obj'" not in b
    # 除枚举值与 schema 名外，其余 DDL 完全同构
    norm = lambda s: (s.replace("'alpha_obj'", "X").replace("'beta_obj'", "X")
                      .replace("s_a", "S").replace("s_b", "S"))
    assert norm(a) == norm(b), "两域 DDL 结构应当一致（只有枚举值不同）"


def test_ddl_contains_all_core_roles():
    sql = "\n".join(ddl_statements(_profile("d", ("x_obj",)), "s"))
    for role in CORE:
        assert f"'{role}'" in sql


def test_particle_typeset_rejects_missing_core_role():
    with pytest.raises(ValueError, match="缺少核心语义角色"):
        ParticleTypeSet(names=("entity", "decision"))


def test_business_tables_have_no_jsonb():
    tables = {
        "particle": ["particle_id:text", "vec:vector", "label:text"],
        "particle_attribute": ["value_text:text"],
        "graph_edge": ["from_id:text"],
        "edge_attribute": ["attr:text"],
        "event": ["payload:jsonb", "context_facts:jsonb"],
        "spec": ["definition:jsonb"],
    }
    assert assert_no_free_jsonb(tables) == []


def test_free_jsonb_is_caught():
    """判别力自证：给业务表塞 jsonb 必须被检出。"""
    tables = {"particle": ["particle_id:text", "payload:jsonb"]}
    assert assert_no_free_jsonb(tables) == ["particle.payload:jsonb"]
