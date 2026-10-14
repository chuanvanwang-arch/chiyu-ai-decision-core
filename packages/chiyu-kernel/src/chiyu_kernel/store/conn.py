"""PG 连接、建表与向量编解码 —— 存储层**唯一入口**（内核通用版）。

⛔ 与 demo `db/conn.py` 的差异（零领域字面量原则 + 可配置性）
──────────────────────────────────────────────────────────────
demo 把 `bj12345`/`bj12345_app`/`bj_t_*`/`bj_t_ev_*` 的**前缀语义**焊进函数
（`register_ephemeral` 只认 `bj_t_`、`drop_test_schema` 只认 `bj_t_`）。内核**不得**
携带任意部署前缀字面量，故把"`<前缀>_t_*` 是测试/一次性 schema"这个约定改为
**由调用方在构造时声明**（`test_schema_prefix`、`ephemeral_prefix`），内核只校验
"该前缀白名单化 + 前缀→目标库一致性"，不写死 `bj`。

⛔ 保留的既有纪律（有可执行判据）：
  ① 禁 `close_all()` 全局核弹 → 提供 `close_schema`（按 schema 关闭）；\n  ② 禁 DELETE → 只允许删"已被调用方声明为可回收"的测试 schema（见 pg_store）；\n  ③ 向量不做隐式降级 → `vec_to_pg` 维度必须恰等 dim，短了必须显式 `pad_to_dim`；\n  ④ 单连接 + RLock 复用 + 建表幂等（advisory lock 串行化）；\n  ⑤ `_CREATED` 记"本进程建过的 schema"，供泄漏判据做"仍在"比对。
"""
from __future__ import annotations

import contextlib
import os
import threading
from typing import Any, Iterable, Iterator, Optional, Sequence

from . import dsn as _dsn
from .ddl import ddl_statements, vector_index_ddl

try:                                  # 只探测，不持有
    import psycopg2 as _pg
    _PG_ERR: Optional[str] = None
except Exception as _e:               # noqa: BLE001
    _pg = None
    _PG_ERR = f"{type(_e).__name__}: {_e}"

_ENSURED: set[tuple[str, str]] = set()
_REPORTS: dict[tuple[str, str], dict] = {}
_LOCK = threading.RLock()
_SHARED: dict[tuple[str, str], Any] = {}
_EPHEMERAL: set[str] = set()
_ATEXIT_HOOKED = False
_CREATED: set[str] = set()


def created_schemas() -> set[str]:
    """本进程创建过的 schema 名（只增不清，供泄漏判据做"仍在"比对）。"""
    with _LOCK:
        return set(_CREATED)


def _reclaim_at_exit() -> None:
    """进程退出时的兜底回收。**绝不让它把退出流程弄脏**。"""
    try:
        if not ephemeral_schemas():
            return
        failed = drop_ephemeral_schemas().get("failed") or {}
        if failed:
            print(f"[store] ⚠ 一次性 schema 退出回收失败：{failed}")
    except Exception as e:                            # noqa: BLE001
        print(f"[store] ⚠ 一次性 schema 退出回收异常：{type(e).__name__}: {e}")


def register_ephemeral(schema: str, ephemeral_prefix: str = "t_") -> None:
    """登记一个本进程创建的一次性 schema（供收尾统一回收）。

    ⛔ `ephemeral_prefix`（默认 `t_`）由调用方声明；内核校验 schema 名必须以
       `t_` 开头，但**不写死**领域前缀（demo 的 `bj_t_` 由上层拼）。
    """
    schema = _dsn.assert_safe_identifier(schema, what="schema")
    if not schema.startswith(ephemeral_prefix):
        raise _dsn.DBConfigError(
            f"只有 {ephemeral_prefix!r}* 可登记为一次性 schema：{schema!r}")
    global _ATEXIT_HOOKED
    with _LOCK:
        _EPHEMERAL.add(schema)
        _CREATED.add(schema)
        if not _ATEXIT_HOOKED:
            import atexit
            atexit.register(_reclaim_at_exit)
            _ATEXIT_HOOKED = True


def ephemeral_schemas() -> set[str]:
    with _LOCK:
        return set(_EPHEMERAL)


def drop_ephemeral_schemas(schemas: Optional[Iterable[str]] = None) -> dict:
    """回收本进程登记过的 schema（只动登记过的，绝不扫库按名字删）。"""
    targets = ephemeral_schemas() if schemas is None else {str(s) for s in schemas}
    targets &= ephemeral_schemas()
    out: dict[str, Any] = {"dropped": [], "absent": [], "failed": {}}
    for s in sorted(targets):
        try:
            existed = drop_test_schema(s)
        except Exception as e:                          # noqa: BLE001
            out["failed"][s] = f"{type(e).__name__}: {e}"
            continue
        (out["dropped"] if existed else out["absent"]).append(s)
    return out


def driver_available() -> bool:
    return _pg is not None


def driver_error() -> Optional[str]:
    return _PG_ERR


def vec_to_pg(vec: Sequence[float] | None, *, dim: int) -> Optional[str]:
    """float 序列 → pgvector 字面量。长度**必须恰好**等于 dim（不隐式补零/截断）。"""
    if vec is None:
        return None
    v = list(vec)
    if len(v) != dim:
        raise ValueError(f"向量维度 {len(v)} ≠ 期望 {dim}：请显式 pad_to_dim() 补零，"
                         f"不得隐式降级（会使 HNSW 索引静默失效）")
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


def pad_to_dim(vec: Sequence[float], dim: int) -> list[float]:
    """384 → 1024 尾部补零（余弦等价：补零不改变 L2 范数）。"""
    v = [float(x) for x in vec]
    if len(v) > dim:
        raise ValueError(f"向量维度 {len(v)} > 目标 {dim}，不可截断")
    return v + [0.0] * (dim - len(v))


def pg_to_vec(raw: Any) -> Optional[list[float]]:
    """pgvector 字面量（'[1,2,3]' 或 list）→ float 列表。"""
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        return [float(x) for x in raw]
    s = str(raw).strip()
    if not s:
        return None
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    return [float(x) for x in s.split(",") if x.strip()]


#: application_name 前缀。摘连接时按此**精确限定本进程**，绝不无差别 terminate。
BACKEND_APP_NAME_PREFIX = "chiyu-kernel"

#: DROP SCHEMA 前的默认锁等待上限（ms）。撞长事务要"快速失败"，不要挂死。
DEFAULT_LOCK_TIMEOUT_MS = 5000


def own_backend_identity() -> str:
    """本进程的连接标识（`application_name`）：`chiyu-kernel:pid=<pid>`。

    ⛔ 必须携带 pid：清理时按此串精确匹配，否则会误杀并行会话/他人的连接。
    """
    return f"{BACKEND_APP_NAME_PREFIX}:pid={os.getpid()}"


def terminate_backends_sql(identity: str) -> tuple[str, tuple]:
    """生成"按 identity 精准摘连接"的 SQL（参数化，不做字符串拼接）。

    ⛔ 两条硬约束（缺一即被判据判红）：
       ① 按 `application_name = identity` 限定 —— 否则无差别 terminate 会误杀他人；
       ② 排除 `pg_backend_pid()` —— 否则把自己也摘掉（自杀式清理）。
    """
    return (
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = current_database() "
        "AND application_name = %s "
        "AND pid <> pg_backend_pid()",
        (identity,),
    )


def terminate_own_backends(*, conn: Any = None) -> int:
    """摘掉本进程（同一 identity）的其余连接，返回摘除条数。

    `conn` 可注入（测试用 fake 记录 SQL）；不传走 `shared()`（既有路径不变）。
    """
    conn = conn if conn is not None else shared()
    sql, params = terminate_backends_sql(own_backend_identity())
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return len(rows or [])


def connect(*, dsn: Optional[str] = None, schema: Optional[str] = None,
            timeout: int = 5, autocommit: bool = False,
            connect_factory: Any = None,
            application_name: Optional[str] = None) -> Any:
    """新建一条连接（调用方负责关闭）。DSN/schema 走 env，红线校验在 dsn 模块完成。

    ⛔ 红线先于驱动校验：无论是否传入 dsn、驱动是否就绪，先过 `validate_dsn`
       （禁连生产机 FORBIDDEN_HOSTS、禁超级用户、scheme 必须为 postgresql）。
       否则 `connect(dsn="postgresql://...@81.70.184.198/...")` 会绕过红线直接试连。

    `connect_factory`（R9）：驱动**可注入**。内核此前把 psycopg2 焊死，消费方用
    psycopg3 就被迫整层重写隔离机制。传入 `connect_factory=psycopg` 即可跑通，
    ⛔ 不传即走模块默认驱动 —— 既有调用零影响（严格加法）。
    """
    dsn = dsn or _dsn.get_dsn()
    _dsn.validate_dsn(dsn)               # 红线在前：不依赖驱动，该拦则拦
    schema = _dsn.assert_safe_identifier(schema or _dsn.get_schema(), what="schema")
    factory = connect_factory if connect_factory is not None else _pg
    if factory is None:
        raise RuntimeError(
            f"数据库驱动不可用（{_PG_ERR}）；可注入 `connect_factory` 指定驱动")
    ident = application_name or own_backend_identity()
    # 兼容两种注入形态：模块式（`psycopg2` / `psycopg3`，有 `.connect`）与
    # 可调用式（包装函数 / partial）。两者签名一致，均按位置传 conninfo。
    if hasattr(factory, "connect"):
        conn = factory.connect(dsn, connect_timeout=timeout, application_name=ident)
    else:
        conn = factory(dsn, connect_timeout=timeout, application_name=ident)
    conn.autocommit = autocommit
    with conn.cursor() as cur:
        # search_path 逐连接显式设置（不依赖 ALTER ROLE 默认值）
        cur.execute(f"SET search_path TO {schema}, public")
    return conn


def shared(*, testing: bool | None = None,
           connect_factory: Any = None) -> Any:
    """进程内共享连接（单连接 + RLock）。

    `connect_factory`（N3）：与 `connect()` 同源的可注入驱动。此前 `shared()` 内部
    硬走内建 `_pg` 且不经 `connect_factory`，psycopg3 消费方在"进程级单连接"场景
    仍无法复用隔离机制 —— 与手动 `connect()` 的驱动注入**不一致**。传入
    `connect_factory` 时透传给 `connect()`，使单连接同样可由注入驱动建立。
    ⛔ 不传即走既有内建 `_pg` 路径（严格加法，既有调用零影响）。
    """
    if connect_factory is None and _pg is None:
        raise RuntimeError(f"psycopg2 不可用（{_PG_ERR}）")
    dsn = _dsn.get_dsn(testing=testing)
    schema = _dsn.assert_safe_identifier(_dsn.get_schema(), what="schema")
    key = (dsn, schema)
    with _LOCK:
        conn = _SHARED.get(key)
        if conn is None or getattr(conn, "closed", 1):
            conn = connect(dsn=dsn, schema=schema, connect_factory=connect_factory)
            _SHARED[key] = conn
    return conn


def make_cursor(conn: Any, *, dict_rows: bool = True, row_factory: Any = None) -> Any:
    """统一游标工厂（dict_rows=True 时返回 RealDictCursor——上层按 col 取值）。

    `row_factory`（R9）：psycopg3 的字典行是 `row_factory=dict_row`，与 psycopg2 的
    `cursor_factory=RealDictCursor` 不同名 —— 允许注入，psycopg3 才能复用本层。
    ⛔ 不传即走既有 psycopg2 路径（严格加法）。
    """
    if row_factory is not None:
        return conn.cursor(row_factory=row_factory)
    if not dict_rows:
        return conn.cursor()
    import psycopg2.extras as _ex
    return conn.cursor(cursor_factory=_ex.RealDictCursor)


@contextlib.contextmanager
def cursor(*, testing: bool | None = None, dict_rows: bool = True) -> Iterator[Any]:
    """共享连接上的游标（自动 commit/rollback；异常回滚后重抛，不吞错）。"""
    conn = shared(testing=testing)
    with _LOCK:
        cur = make_cursor(conn, dict_rows=dict_rows)
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def ensure_schema(*, profile, testing: bool | None = None,
                  create_vector_index: bool = True,
                  schema: Optional[str] = None) -> dict:
    """建 schema + 全部表 + 受控词表种子（幂等；同 (dsn,schema) 会话内只跑一次）。

    ⛔ `profile` 必传：DDL 的粒子/谓词 CHECK 由 `TenantProfile` 生成（零领域字面量）。
    """
    from . import dsn as _d
    dsn = _d.get_dsn(testing=testing)
    schema = _d.assert_safe_identifier(schema or _d.get_schema(), what="schema")
    if schema.startswith("t_"):
        with _LOCK:
            _CREATED.add(schema)
    key = (dsn, schema)
    with _LOCK:
        if key in _ENSURED:
            base = dict(_REPORTS.get(key) or {})
            base.update({"schema": schema, "skipped": True})
            base.setdefault("vector_index", None)
            base.setdefault("ext_vector", None)
            base.setdefault("spec_keys", [])
            base.setdefault("notes", [])
            return base
        conn = shared(testing=testing)
        report: dict = {"schema": schema, "skipped": False,
                        "vector_index": None, "ext_vector": None, "notes": []}
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()
            report["ext_vector"] = "ensured"
        except Exception as e:                               # noqa: BLE001
            conn.rollback()
            report["ext_vector"] = f"skip({type(e).__name__})"
        with conn.cursor() as cur:
            cur.execute("SELECT extversion FROM pg_extension WHERE extname='vector'")
            row = cur.fetchone()
        if not row:
            report["notes"].append("pgvector 扩展不存在：vector 列建不出来，请先安装扩展")
            raise RuntimeError("pgvector 未安装（CREATE EXTENSION vector 失败且查无扩展）")
        report["ext_vector"] = row[0]
        with conn.cursor() as cur:
            # 建表串行化：并发启动时后到者等前者提交完再判 IF NOT EXISTS
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                        (f"chiyu_schema:{schema}",))
            for stmt in ddl_statements(profile, schema):
                cur.execute(stmt)
        conn.commit()
        if create_vector_index:
            try:
                with conn.cursor() as cur:
                    for stmt in vector_index_ddl(schema):
                        cur.execute(stmt)
                conn.commit()
                report["vector_index"] = "hnsw(vector_cosine_ops)"
            except Exception as e:                           # noqa: BLE001
                conn.rollback()
                report["vector_index"] = f"FAILED: {type(e).__name__}: {e}"
                report["notes"].append("HNSW 索引未建成，向量检索将退化为顺序扫描")
        _ENSURED.add(key)
        report["tables"] = _list_tables(schema, testing=testing)
        _REPORTS[key] = dict(report)
        return report


def _list_tables(schema: str, *, testing: bool | None = None) -> list[str]:
    with cursor(testing=testing) as cur:
        cur.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname=%s ORDER BY tablename",
            (schema,))
        return [r["tablename"] for r in cur.fetchall()]


def close_schema(schema: Optional[str] = None, *, testing: bool | None = None) -> int:
    """关闭**指定 schema** 的共享连接（只关它），返回关掉了几条。⛔ 不是全局核弹。"""
    from . import dsn as _d
    target = _d.assert_safe_identifier(_d.get_schema() if schema is None else schema,
                                       what="schema")
    dsn = _d.get_dsn(testing=testing)
    n = 0
    with _LOCK:
        for key in [k for k in list(_SHARED) if k[1] == target and k[0] == dsn]:
            with contextlib.suppress(Exception):
                _SHARED.pop(key).close()
            n += 1
    return n


def drop_test_schema(schema: str, test_prefix: str = "t_", *,
                     conn: Any = None,
                     lock_timeout_ms: int = DEFAULT_LOCK_TIMEOUT_MS) -> bool:
    """删除一次性 schema。**返回\"是否真的删掉了一个存在的 schema\"**。

    ⛔ `test_prefix`（默认 `t_`）由调用方声明，内核不写死领域前缀（demo 的 `bj_t_`）。
    ⛔ 返回值语义是\"存在过\"而非\"执行过\"：`DROP SCHEMA IF EXISTS` 在 schema 不存在时
       也\"成功\"，于是在**指错的库**上执行会伪装成清理成功。调用方拿 False 应当警觉。

    ⛔ `lock_timeout_ms`（R9 硬知识①）：`DROP SCHEMA` 撞上长事务会**无限等待**，
       在 CI 上表现为挂死而非失败。故 DROP 前必设 lock_timeout 让冲突快速失败，
       DROP 后立即 RESET（不污染复用连接上的后续语句）。
    """
    if not schema.startswith(test_prefix):
        raise _dsn.DBConfigError(
            f"拒绝删除 schema {schema!r}：只允许 {test_prefix!r}* 一次性测试 schema")
    schema = _dsn.assert_safe_identifier(schema, what="schema")
    conn = conn if conn is not None else shared()
    with conn.cursor() as cur:
        cur.execute(f"SET lock_timeout = {int(lock_timeout_ms)}")
        cur.execute("SELECT 1 FROM pg_namespace WHERE nspname=%s", (schema,))
        existed = cur.fetchone() is not None
        cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        cur.execute("RESET lock_timeout")
    conn.commit()
    _ENSURED.discard((_dsn.get_dsn(), schema))
    _REPORTS.pop((_dsn.get_dsn(), schema), None)
    with _LOCK:
        _EPHEMERAL.discard(schema)
    return existed


def probe_schema_isolation(*, testing: bool | None = None) -> dict:
    """泄漏判据：本进程 `created_schemas()` 中\"现在还存在于库\"的 schema 名。

    ⛔ 为什么单独列函数而不是\"扫库\"：只按名字扫库会把并行会话/历史遗留的 schema
       算到本进程头上（demo 首版判据就是这么红的）。这里只比对\"本进程建过\"与
       \"当前仍在\"的交集。
    """
    from . import dsn as _d
    alive: list[str] = []
    for s in sorted(created_schemas()):
        try:
            conn = shared(testing=testing)
            with conn.cursor() as c:
                c.execute("SELECT 1 FROM pg_namespace WHERE nspname=%s", (s,))
                if c.fetchone() is not None:
                    alive.append(s)
        except Exception:                                   # noqa: BLE001
            continue
    return {"registered": sorted(created_schemas()), "alive": alive,
            "leaked": alive}


def close_all() -> None:
    with _LOCK:
        for conn in _SHARED.values():
            with contextlib.suppress(Exception):
                conn.close()
        _SHARED.clear()
        _ENSURED.clear()
        _REPORTS.clear()


__all__ = ["driver_available", "driver_error", "vec_to_pg", "pad_to_dim", "pg_to_vec",
           "connect", "shared", "make_cursor", "cursor", "ensure_schema",
           "register_ephemeral", "ephemeral_schemas", "drop_ephemeral_schemas",
           "drop_test_schema", "probe_schema_isolation",
           "created_schemas", "close_schema", "close_all",
           # R9：驱动解耦 + 两条硬知识
           "BACKEND_APP_NAME_PREFIX", "DEFAULT_LOCK_TIMEOUT_MS",
           "own_backend_identity", "terminate_backends_sql", "terminate_own_backends"]
