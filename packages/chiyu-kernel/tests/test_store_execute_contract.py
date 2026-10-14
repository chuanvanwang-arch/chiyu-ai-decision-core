"""N3 execute / execute_fetch 返回契约 —— 纯函数级，不连真 DB。

⛔ 背景：`execute` 此前返回一个已随 context 关闭的 cursor（死对象）且标注 `Any`
   ⇒ "只写方法看似可读"，消费方误 fetch 得到空结果且无类型提示。
   N3 契约：`execute` **只写返回 None**；`execute_fetch` 读（fetch_all=True ⇒
   list[dict] 恒 list；否则 dict | None）。

⛔ 判别力：用假 cursor 走一遍真调用路径，断言返回值是 None 而非 cursor 对象
   —— 只查签名挡不住"实现里偷偷 return"的回归。
"""
from __future__ import annotations

import contextlib
import inspect
from typing import Any, List, Tuple

import pytest

from chiyu_kernel.contract import TenantProfile
from chiyu_kernel.contract.particle import CORE_ROLES, ParticleTypeSet
from chiyu_kernel.store import pg_store as pg_store_mod
from chiyu_kernel.store.pg_store import PgVectorStore


class _FakeCursor:
    def __init__(self, sink: List[Tuple[str, Any]]) -> None:
        self._sink = sink

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self._sink.append((sql, params))


@pytest.fixture()
def store(monkeypatch) -> PgVectorStore:
    profile = TenantProfile(domain="demo",
                            particle_types=ParticleTypeSet(set(CORE_ROLES)))
    monkeypatch.setattr(pg_store_mod._conn, "cursor",
                        lambda **kw: contextlib.nullcontext(_FakeCursor([])))
    return PgVectorStore(profile, schema="t_x")


def test_execute_returns_none(store) -> None:
    """行为判据：execute 返回 None（不是死 cursor）。"""
    assert store.execute("INSERT INTO t_x.particle VALUES (1)") is None


def test_execute_signature_and_doc() -> None:
    sig = inspect.signature(PgVectorStore.execute)
    assert sig.return_annotation in (None, "None", type(None)), \
        f"execute 返回标注须为 None，实为 {sig.return_annotation}"
    doc = inspect.getdoc(PgVectorStore.execute) or ""
    assert "只写" in doc, "docstring 未声明只写语义"
    assert "execute_fetch" in doc, "docstring 未指引读路径"


def test_execute_fetch_documented_shapes() -> None:
    doc = inspect.getdoc(PgVectorStore.execute_fetch) or ""
    assert "list" in doc and "None" in doc, "execute_fetch 未写明两种返回形态"


def test_execute_still_blocks_hard_delete(store) -> None:
    """返回契约收紧不得削弱既有红线：硬删除仍被拦。"""
    with pytest.raises(ValueError):
        store.execute("DELETE FROM t_x.particle")
