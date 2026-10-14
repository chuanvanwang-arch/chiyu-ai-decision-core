"""存储层隔离红线守卫 —— **纯函数级，不连真 DB**。

G1-β 判据落地：
  β3  禁 DELETE 可执行  —— `assert_no_hard_delete`/`assert_safe_read` 命中即抛
  β2  禁自由 jsonb 有判别力 —— `assert_no_free_jsonb` 命中即列违规
  β4  契约通信守卫       —— store 层只 `from chiyu_kernel.contract import ...`
  β5  demo 域可表达       —— `TenantProfile` 能承载群诉域（见 examples/ round-trip）

⛔ 为什么纯函数：真 DB 判据（建表/向量索引/隔离）会因环境无 PG/pgvector 而假红，
   且污染进程级 `created_schemas()`。这里只测**内核自身承诺**的红线拦截逻辑，
   保证"该红则红"在无外接依赖时也能自证。
"""
import pytest

from chiyu_kernel.contract import (
    CORE_ROLES,
    ParticleTypeSet,
    PredicateSet,
    TenantProfile,
    VECTOR_DIM,
)
from chiyu_kernel.store.conn import pad_to_dim, vec_to_pg
from chiyu_kernel.store.ddl import assert_no_free_jsonb as no_free_jsonb
from chiyu_kernel.store.dsn import DBConfigError, assert_safe_identifier
from chiyu_kernel.store.pg_store import assert_no_hard_delete


# ── β3 禁 DELETE：纯函数可执行，命中即抛 ──────────────────────────────
@pytest.mark.parametrize("sql", [
    "DELETE FROM particle",
    "delete from particle where type='x'",
    "  DELETE   FROM graph_edge;",
    "TRUNCATE particle",
    "truncate   graph_edge",
])
def test_hard_delete_is_blocked(sql: str) -> None:
    """任何 DELETE/TRUNCATE 开头的语句必须被拦（含大小写/空白/换行前缀）。"""
    with pytest.raises(ValueError, match="禁 DELETE"):
        assert_no_hard_delete(sql)


@pytest.mark.parametrize("sql", [
    "SELECT * FROM particle",
    "UPDATE particle SET status='deleted', updated_at=now() WHERE particle_id=%s",
    "INSERT INTO particle (particle_id) VALUES (%s)",
    "SELECT count(*) FROM graph_edge",
])
def test_non_delete_sql_not_blocked(sql: str) -> None:
    """墓碑 UPDATE / 读路径 / INSERT 不得被误伤（防止过拦导致功能瘫痪）。"""
    assert_no_hard_delete(sql)  # 不抛即过


def test_safe_read_blocks_drop_too() -> None:
    """读路径的 assert_safe_read 除 DELETE 外还拦 DROP（防拼接逃逸）。"""
    from chiyu_kernel.store.pg_store import PgVectorStore
    with pytest.raises(ValueError, match="禁 DROP"):
        PgVectorStore.assert_safe_read("DROP TABLE particle")


# ── β2 禁自由 jsonb：业务粒子表/边表零 jsonb，例外仅 event/spec ────────
def test_no_free_jsonb_has_discriminative_power() -> None:
    """该红则红：业务表混入 jsonb 必须被列违规。"""
    bad = {
        "particle": ["particle_id:text", "meta:jsonb"],
        "graph_edge": ["edge_id:bigint", "payload:json"],
    }
    violations = no_free_jsonb(bad)
    assert violations, "业务表含 jsonb 必须被列为违规"
    assert any(".meta" in v for v in violations)
    assert any(".payload" in v for v in violations)


def test_allowed_jsonb_exceptions_are_ok() -> None:
    """唯独 event / spec 允许 jsonb（语义上异构，设计 §0.3 授权）。"""
    ok = {
        "event": ["payload:jsonb", "context_facts:jsonb"],
        "spec": ["definition:jsonb"],
        "particle_attribute": ["value_set:text[]"],  # 数组列不是 jsonb
    }
    assert no_free_jsonb(ok) == []


# ── 向量不隐式降级：维度必须恰等 dim，短了必须显式补零 ─────────────────
def test_vec_to_pg_rejects_wrong_dim() -> None:
    with pytest.raises(ValueError, match="维度"):
        vec_to_pg([0.1, 0.2], dim=VECTOR_DIM)  # 2 ≠ 1024


def test_pad_to_dim_pads_tail_with_zeros() -> None:
    import math
    short = [0.5, -0.5]
    padded = pad_to_dim(short, dim=VECTOR_DIM)
    assert len(padded) == VECTOR_DIM
    # 余弦等价：补零不改变方向（内积比例不变）
    n1 = math.sqrt(sum(x * x for x in short))
    n2 = math.sqrt(sum(x * x for x in padded))
    assert abs(n1 - n2) < 1e-9


def test_pad_to_dim_rejects_shrink() -> None:
    with pytest.raises(ValueError, match="不可截断"):
        pad_to_dim([0.0] * (VECTOR_DIM + 1), dim=VECTOR_DIM)


# ── schema 名白名单：禁注入 ────────────────────────────────────────────
@pytest.mark.parametrize("bad", [
    "bj; DROP TABLE particle",
    "a b",
    "1abc",
    "a-b",
    "x" * 64,
])
def test_schema_identifier_rejects_injection(bad: str) -> None:
    with pytest.raises(DBConfigError):
        assert_safe_identifier(bad, what="schema")


@pytest.mark.parametrize("good", ["bj", "bj12345", "t_demo_schema", "a1_b2"])
def test_schema_identifier_accepts_safe(good: str) -> None:
    assert assert_safe_identifier(good, what="schema") == good


# ── β5 demo 域可表达 + 粒子类型集形态约束 ──────────────────────────────
def test_demo_domain_expressible_via_core_roles() -> None:
    """群诉域（demo）只需扩展 CORE_ROLES 之外的自有类型即可表达。"""
    names = CORE_ROLES + ("group", "respondent", "claim")
    pts = ParticleTypeSet(names=names)
    # 5 个核心语义角色必须被覆盖
    for role in CORE_ROLES:
        assert pts.covers(role)
    sql = pts.sql_check()
    assert "'group'" in sql and "'claim'" in sql and "'entity'" in sql


def test_particle_type_set_rejects_missing_core_role() -> None:
    with pytest.raises(ValueError, match="核心语义角色"):
        ParticleTypeSet(names=("entity", "decision"))


# ── R2 安全项：connect 必须先过 validate_dsn（生产机/超级用户红线）──────
def test_connect_rejects_forbidden_host_before_driver() -> None:
    """R2 安全项：黑名单主机红线必须在驱动校验之前拦截。

    变异自证：若 `connect()` 未先调 `validate_dsn`，传入生产机 DSN 会绕过红线
    直接试连（或仅因缺驱动抛 RuntimeError），而非按预期抛 DBConfigError。
    """
    from chiyu_kernel.store.conn import connect
    with pytest.raises(DBConfigError, match="被禁主机"):
        connect(dsn="postgresql://app@81.70.184.198/crm_native")


def test_connect_rejects_superuser_role() -> None:
    """R2 安全项：禁止以超级用户连接（不依赖驱动是否就绪）。"""
    from chiyu_kernel.store.conn import connect
    with pytest.raises(DBConfigError, match="超级用户"):
        connect(dsn="postgresql://postgres@127.0.0.1/chiyu_test")
