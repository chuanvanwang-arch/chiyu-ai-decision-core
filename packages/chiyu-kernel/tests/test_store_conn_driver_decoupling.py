"""R9 —— 存储层隔离机制的驱动解耦 + 两条硬知识兜底。

⛔ 为什么这条存在：内核把 `psycopg2` 焊死在 `conn.py`（import 期探测 + `connect`
   里直接调用），消费方若用 psycopg3 就**被迫整层重写**（实测 APS 为此重写约
   200 行）。这里用 `connect_factory` 注入把驱动变成可替换，不动既有调用。

两条硬知识（缺一不可）：
  ① `lock_timeout` —— `DROP SCHEMA` 撞上长事务会**无限等待**，测试/CI 表现为挂死
     而非失败。必须在 DROP 前设 lock_timeout，让冲突"快速失败"。
  ② `application_name` 精准摘连接 —— 清理时若按库无差别 `pg_terminate_backend`，
     会误杀并行会话/他人的连接。必须限定本进程 identity 且排除自身 backend。

⛔ 纯函数级 + fake conn，不连真 DB：真锁冲突判据会挂死，真 terminate 会误伤。
   这里用 fake conn 记录 SQL **执行序列**，从而把"顺序"与"作用域"变成可断言的判据。
"""
import os

import pytest

from chiyu_kernel.store import dsn as _dsn
from chiyu_kernel.store.conn import (
    connect,
    drop_test_schema,
    make_cursor,
    own_backend_identity,
    terminate_backends_sql,
    terminate_own_backends,
)

GOOD = "postgresql://chiyu@127.0.0.1:5432/chiyu_test"


# ── fake 驱动与连接：记录执行序列 ──────────────────────────────────────
class _FakeCursor:
    def __init__(self, log, rows=None, kw=None):
        self._log = log
        self._rows = rows or []
        self.kw = kw or {}

    def execute(self, sql, params=None):
        self._log.append((" ".join(str(sql).split()), params))

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


class _FakeConn:
    def __init__(self, log=None, rows=None):
        self.log = log if log is not None else []
        self._rows = rows or []
        self.autocommit = False
        self.closed = 0

    def cursor(self, *a, **kw):
        return _FakeCursor(self.log, self._rows, kw)

    def commit(self):
        self.log.append(("COMMIT", None))

    def close(self):
        self.closed = 1


class _FakeDriver:
    def __init__(self):
        self.seen = {}

    def connect(self, dsn, **kw):
        self.seen = {"dsn": dsn, "kw": kw}
        return _FakeConn()


@pytest.fixture(autouse=True)
def _clean_dsn_env(monkeypatch):
    for k in (_dsn.DSN_ENV, _dsn.DSN_TEST_ENV, _dsn.SCHEMA_ENV,
              "CHIYU_DB_TESTING", "CHIYU_TEST"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv(_dsn.DSN_ENV, GOOD)
    monkeypatch.setenv(_dsn.SCHEMA_ENV, "public")


# ── 判据一：驱动可注入 ────────────────────────────────────────────────
def test_connect_uses_injected_factory():
    seen = {}

    def factory(dsn, **kw):
        seen.update({"dsn": dsn, "kw": kw})
        return _FakeConn()

    connect(connect_factory=factory)
    assert seen["dsn"] == GOOD, "注入工厂未拿到 DSN"
    assert seen["kw"].get("application_name"), "连接未带 application_name 标识"


def test_connect_default_factory_unchanged(monkeypatch):
    """严格加法：不传 factory 时仍走模块级驱动 —— 既有调用零影响。"""
    from chiyu_kernel.store import conn as c
    drv = _FakeDriver()
    monkeypatch.setattr(c, "_pg", drv)
    out = connect()
    assert isinstance(out, _FakeConn)
    assert drv.seen["dsn"] == GOOD


def test_make_cursor_accepts_row_factory():
    """psycopg3 的 dict 行工厂是 `row_factory=dict_row`，须可注入。"""
    cur = make_cursor(_FakeConn(), dict_rows=True, row_factory="DICT_ROW")
    assert cur.kw.get("row_factory") == "DICT_ROW"


def test_make_cursor_default_unchanged():
    """不传 row_factory 时仍是 psycopg2 路径（Regress 保护）。"""
    cur = make_cursor(_FakeConn(), dict_rows=False)
    assert cur.kw == {}


# ── 判据二：lock_timeout 必须在 DROP 之前 ─────────────────────────────
def _idx_of(log, needle):
    for i, (sql, _p) in enumerate(log):
        if needle in sql.lower():
            return i
    return -1


def test_drop_test_schema_sets_lock_timeout_before_drop(monkeypatch):
    from chiyu_kernel.store import conn as c
    monkeypatch.setattr(c, "shared", lambda **kw: _FakeConn())
    conn = _FakeConn()
    drop_test_schema("t_demo", conn=conn)
    lt = _idx_of(conn.log, "lock_timeout")
    dr = _idx_of(conn.log, "drop schema")
    assert lt >= 0, f"未设置 lock_timeout：{conn.log}"
    assert dr >= 0, f"未执行 DROP SCHEMA：{conn.log}"
    assert lt < dr, f"lock_timeout 必须在 DROP 之前：{conn.log}"


def test_lock_timeout_value_is_injected(monkeypatch):
    from chiyu_kernel.store import conn as c
    monkeypatch.setattr(c, "shared", lambda **kw: _FakeConn())
    conn = _FakeConn()
    drop_test_schema("t_demo", conn=conn, lock_timeout_ms=1500)
    assert any("1500" in sql for sql, _p in conn.log), f"lock_timeout 值未注入：{conn.log}"


# ── 判据三：摘连接按 identity 精准命中，且不自杀 ───────────────────────
def test_identity_carries_pid():
    ident = own_backend_identity()
    assert str(os.getpid()) in ident, f"identity 未携带本进程 pid：{ident}"


def test_terminate_sql_scoped_to_identity_and_excludes_self():
    ident = own_backend_identity()
    sql, params = terminate_backends_sql(ident)
    low = sql.lower()
    assert "pg_terminate_backend" in low
    assert "application_name" in low, "未按 application_name 限定 ⇒ 会误杀他人连接"
    assert "pg_backend_pid()" in low, "未排除自身 backend ⇒ 会自杀"
    assert ident in params


def test_terminate_own_backends_executes_scoped_sql():
    conn = _FakeConn()
    terminate_own_backends(conn=conn)
    assert any("pg_terminate_backend" in s.lower() for s, _p in conn.log), \
        f"未执行摘连接：{conn.log}"


# ── 判据四：shared() 进程级单连接同样透传 connect_factory（N3）──────────
def test_shared_passes_connect_factory_through(monkeypatch):
    """N3：注入 connect_factory 时，shared() 的进程级单连接由该 factory 建立，
    而非内建 _pg。psycopg3 下进程级单连接才能复用隔离机制。"""
    from chiyu_kernel.store import conn as c
    seen = {}

    def factory(dsn, **kw):
        seen.update({"dsn": dsn, "kw": kw})
        return _FakeConn()

    # 清掉既有缓存，确保真正走新建路径
    monkeypatch.setattr(c, "_SHARED", {})
    monkeypatch.setattr(c, "_pg", None)   # 内建驱动不可用也不应阻塞 factory 注入
    out = c.shared(connect_factory=factory)
    assert isinstance(out, _FakeConn)
    assert seen["dsn"] == GOOD, "shared() 未把 DSN 传给注入工厂"
    assert seen.get("kw", {}).get("application_name"), "shared() 经 factory 建的连接未带 identity"


def test_shared_skips_builtin_guard_when_factory_injected(monkeypatch):
    """N3：传 connect_factory 时，即使 `_pg` 为 None 也不抛『驱动不可用』。"""
    from chiyu_kernel.store import conn as c
    monkeypatch.setattr(c, "_SHARED", {})
    monkeypatch.setattr(c, "_pg", None)
    out = c.shared(connect_factory=lambda dsn, **kw: _FakeConn())
    assert isinstance(out, _FakeConn), "传入 factory 仍被 _pg=None 阻塞 ⇒ 未跳过内建可用性检查"


def test_shared_default_unchanged(monkeypatch):
    """严格加法：不传 connect_factory 时仍走内建 _pg（既有调用零影响）。"""
    from chiyu_kernel.store import conn as c
    drv = _FakeDriver()
    monkeypatch.setattr(c, "_SHARED", {})
    monkeypatch.setattr(c, "_pg", drv)
    out = c.shared()
    assert isinstance(out, _FakeConn)
    assert drv.seen["dsn"] == GOOD
