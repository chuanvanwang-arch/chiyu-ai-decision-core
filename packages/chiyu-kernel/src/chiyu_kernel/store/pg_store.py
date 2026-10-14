"""PgVectorStore —— 存储层门面实现（内核通用版）。

⛔ 禁 DELETE 红线（可执行，不靠自觉）
──────────────────────────────
`execute()` 前拦截 `DELETE FROM`（含 `TRUNCATE`）。删除一律走墓碑语义：
`UPDATE ... SET status='deleted', updated_at=now()`。硬删除在 store 层被拒，
文档条款拦不住，这条拦截能。

⛔ 构造时保存 `profile`：DDL / 谓词 / 粒子全部由 profile 注入，源码零领域字面量。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union, overload

from chiyu_kernel.contract import TenantProfile, VECTOR_DIM

from . import conn as _conn
from . import dsn as _dsn

# 禁 DELETE：拒绝执行这些语句的开头（含空白/注释前缀后的第一个词）
_FORBIDDEN_STATEMENTS = (re.compile(r"^\s*delete\s+from", re.IGNORECASE),
                         re.compile(r"^\s*truncate\s+", re.IGNORECASE))


def assert_no_hard_delete(sql: str) -> None:
    """⛔ 硬删除拦截。命中 ⇒ 抛 ValueError（不是静默忽略）。"""
    s = sql.strip()
    if any(p.match(s) for p in _FORBIDDEN_STATEMENTS):
        raise ValueError(
            f"禁 DELETE（硬删除拦截）：{sql[:80]!r}。删除请用墓碑语义 "
            "UPDATE ... SET status='deleted', updated_at=now()")


class PgVectorStore:
    """单实例 + 跨进程锁语义的存储门面（与 demo 同纪律）。

    构造参数：
        profile   TenantProfile（DDL/谓词/粒子取值来源，必传）
        schema    目标 schema（默认取 env 或 \"\"）
    """

    def __init__(self, profile: TenantProfile, schema: str = "") -> None:
        self.profile = profile
        self.schema = _dsn.assert_safe_identifier(schema or _dsn.get_schema(),
                                                  what="schema")

    # ── DDL ──────────────────────────────────────────────────────────
    def ensure_schema(self, *, create_vector_index: bool = True) -> dict:
        """建 schema + 全部表 + 词表种子（幂等）。"""
        return _conn.ensure_schema(profile=self.profile,
                                   schema=self.schema,
                                   create_vector_index=create_vector_index)

    # ── 写（全部走墓碑语义，禁硬删除）────────────────────────────────
    def execute(self, sql: str, params: Any = None) -> None:
        """统一执行入口（**只写**）。⛔ 硬删除语句在**这里**被拦。

        ⛔ N3 返回契约：本方法**只写不读**，返回 `None` —— 此前返回一个已随
           context 关闭的 cursor（死对象），调用方误用它 fetch 会得到空结果或
           报错，且类型标注 `Any` 把这个坑藏住了。需要读结果请用 `execute_fetch`
           （执行+取值同事务原子完成）。
        """
        assert_no_hard_delete(sql)
        with _conn.cursor() as cur:
            cur.execute(sql, params)

    # ⛔ N3/G2 返回契约（enterprise 2026-10-09 复测指出 `-> Any` 未跟上）：
    #   `fetch_all=True`  ⇒ `list[dict]`（恒为 list，无行时 `[]`，不是 None）
    #   `fetch_all=False` ⇒ `dict | None`（首行，无行时 None）
    # 用 @overload 让消费方**从类型上**区分单/多行返回，不再靠读 docstring。
    @overload
    def execute_fetch(self, sql: str, params: Any = None, *,
                      fetch_all: bool = True) -> List[Dict[str, Any]]: ...
    @overload
    def execute_fetch(self, sql: str, params: Any = None, *,
                      fetch_all: bool = False) -> Optional[Dict[str, Any]]: ...
    def execute_fetch(self, sql: str, params: Any = None,
                      *, fetch_all: bool = False
                      ) -> Union[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """原子\"执行+取值\"：同事务内完成 SELECT 并取数（供加密/读侧消费）。

        ⛔ N3 返回契约：`fetch_all=True` ⇒ `list[dict]`（**恒为 list**，无行时
           `[]`，不是 None）；`fetch_all=False` ⇒ `dict | None`（首行，无行时 None）。
        ⛔ 与 execute 的区别：execute 只写不读（返回 None），本方法在事务内
           直接取数返回。
        ⛔ 同样先过禁 DELETE 守卫（含读路径的 DROP 拦截）。
        """
        assert_no_hard_delete(sql)
        if re.match(r"^\s*drop\s+", sql, re.IGNORECASE):
            raise ValueError(f"禁 DROP（读路径拦截）：{sql[:80]!r}")
        with _conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch_all:
                return list(cur.fetchall()) if cur.description else []
            row = cur.fetchone()
            return row if row is not None else None

    def upsert_particle(self, particle_id: str, ptype: str, layer: str = "L1",
                        *, label: Optional[str] = None, status: Optional[str] = None,
                        vec: Optional[list] = None, provider: Optional[str] = None,
                        ai_generated: bool = False, dim: int = VECTOR_DIM) -> None:
        # vec None ⇒ 存 NULL（不补零不隐式降级）；非 None ⇒ 调用方已显式 pad_to_dim
        # dim 由调用方注入（默认 VECTOR_DIM），不再焊死 1024，避免与 DDL 维度不一致
        if vec is not None:
            vec_expr = _conn.vec_to_pg(vec, dim=dim) + "::vector"
        else:
            vec_expr = "NULL"
        self.execute(
            f"INSERT INTO {_q(self.schema, 'particle')} "
            f"(particle_id, type, layer, label, status, vec, provider, ai_generated) "
            f"VALUES (%s, %s, %s, %s, %s, {vec_expr}, %s, %s) "
            f"ON CONFLICT (particle_id) DO UPDATE SET "
            f"label=EXCLUDED.label, status=EXCLUDED.status, "
            f"vec=EXCLUDED.vec, provider=EXCLUDED.provider, "
            f"ai_generated=EXCLUDED.ai_generated, updated_at=now()",
            (particle_id, ptype, layer, label, status, provider, ai_generated))

    # ── 读 ───────────────────────────────────────────────────────────
    def query(self, table: str, *, where: str = "", params: Any = None,
              limit: int = 100) -> list:
        table = _dsn.assert_safe_identifier(table, what="table")
        sql = f"SELECT * FROM {_q(self.schema, table)}"
        if where:
            sql += f" WHERE {where}"
        sql += f" LIMIT {int(limit)}"
        self.assert_safe_read(sql)
        with _conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())

    @staticmethod
    def assert_safe_read(sql: str) -> None:
        """⛔ 读路径也禁 DELETE/TRUNCATE/DROP（防拼接逃逸）。"""
        assert_no_hard_delete(sql)
        if re.match(r"^\s*drop\s+", sql, re.IGNORECASE):
            raise ValueError(f"禁 DROP（读路径拦截）：{sql[:80]!r}")

    # ── 探针 ─────────────────────────────────────────────────────────
    def count(self, table: str) -> int:
        table = _dsn.assert_safe_identifier(table, what="table")
        with _conn.cursor() as cur:
            cur.execute(f"SELECT count(*) AS n FROM {_q(self.schema, table)}")
            return int(cur.fetchone()["n"])

    def close(self) -> int:
        return _conn.close_schema(self.schema)

    def created_schemas(self) -> set:
        return _conn.created_schemas()


def _q(schema: str, table: str) -> str:
    return f"{schema}.{table}"


__all__ = ["PgVectorStore", "assert_no_hard_delete"]
