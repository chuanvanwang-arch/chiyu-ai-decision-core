"""store 存储内核 —— L1 基础设施：PG + pgvector 单一事实源。

⛔ 与 demo 的关键差异（设计 §0.3 的落地）
──────────────────────────────────────────
demo 的 `db/{dsn,conn,schema}.py` 把 `bj12345` / `bj12345_app` / `bj_t_*` /
7 类粒子枚举**硬编码**成模块常量，等于把群诉域的部署名焊进存储层。本包一律改为：

    DSN 库名 / 角色 / schema 前缀     → env 或调用方显式指定（内核不写死某域）
    粒子类型 CHECK / 谓词 CHECK      → 由 `TenantProfile` 生成（见 ddl.py）

⛔ 零领域字面量守卫只扫 `contract/`；store 同样遵守此精神 —— 本包**不出现**
    `bj`、`cluster`、`ticket` 等具体域名的硬编码取值（仅作占位参数名）。
"""
from __future__ import annotations

# ── sanctioned 面（单一事实源）─────────────────────────────────────────────
# 此前 `__all__` 为空 ⇒ store 的公共符号处于「门面未导出 + 守卫未登记」的
# 三不管状态，消费方只能 import 内部子模块。现在显式收敛为四个子模块
# `__all__` 的并集，由 `store` 统一再导出；门面覆盖守卫**从本清单机械推导**，
# 不再依赖人工枚举（`STORE_REQUIRED`）。
from .ddl import assert_no_free_jsonb, ddl_statements, vector_index_ddl
from .dsn import (
    DB_TESTING_ENV,
    DSN_ENV,
    DSN_TEST_ENV,
    FORBIDDEN_HOSTS,
    FORBIDDEN_ROLES,
    IDENT_MAX,
    SCHEMA_ENV,
    TESTING_FLAG_ENV,
    VALID_FORMS,
    DBConfigError,
    assert_safe_identifier,
    get_dsn,
    get_schema,
    in_testing_context,
    mask_dsn,
    parse_dsn,
    raw_dsn,
    validate_dsn,
)
from .conn import (
    close_all,
    close_schema,
    created_schemas,
    driver_available,
    driver_error,
    drop_ephemeral_schemas,
    drop_test_schema,
    ensure_schema,
    ephemeral_schemas,
    make_cursor,
    pad_to_dim,
    pg_to_vec,
    probe_schema_isolation,
    register_ephemeral,
    shared,
    vec_to_pg,
    connect,
    cursor,
    # R9：驱动解耦 + 两条硬知识
    BACKEND_APP_NAME_PREFIX,
    DEFAULT_LOCK_TIMEOUT_MS,
    own_backend_identity,
    terminate_backends_sql,
    terminate_own_backends,
)
from .pg_store import PgVectorStore, assert_no_hard_delete

__all__: list[str] = [
    # ddl
    "ddl_statements", "vector_index_ddl", "assert_no_free_jsonb",
    # dsn
    "DSN_ENV", "DSN_TEST_ENV", "SCHEMA_ENV", "DB_TESTING_ENV",
    "TESTING_FLAG_ENV", "FORBIDDEN_HOSTS", "FORBIDDEN_ROLES", "IDENT_MAX",
    "VALID_FORMS", "DBConfigError", "in_testing_context", "raw_dsn", "mask_dsn", "parse_dsn",
    "validate_dsn", "get_dsn", "get_schema", "assert_safe_identifier",
    # conn
    "driver_available", "driver_error", "vec_to_pg", "pad_to_dim", "pg_to_vec",
    "connect", "shared", "make_cursor", "cursor", "ensure_schema",
    "register_ephemeral", "ephemeral_schemas", "drop_ephemeral_schemas",
    "drop_test_schema", "probe_schema_isolation",
    "created_schemas", "close_schema", "close_all",
    # conn R9：驱动解耦 + 两条硬知识
    "BACKEND_APP_NAME_PREFIX", "DEFAULT_LOCK_TIMEOUT_MS",
    "own_backend_identity", "terminate_backends_sql", "terminate_own_backends",
    # pg_store
    "PgVectorStore", "assert_no_hard_delete",
]
