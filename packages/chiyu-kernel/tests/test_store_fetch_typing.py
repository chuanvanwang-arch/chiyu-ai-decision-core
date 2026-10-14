"""G2 `execute_fetch` 返回类型契约 —— 从类型上区分单/多行（去 `Any`）。

enterprise 2026-10-09 复测（G2）：`execute` 已改 `-> None` 但 `execute_fetch`
仍 `-> Any`。本文件钉死：实现返回类型为 Union 且**不含 Any**；@overload 两条
签名分别给出 `list[dict]` 与 `dict | None`。
"""
from __future__ import annotations

import typing

from chiyu_kernel.store.pg_store import PgVectorStore


def _resolved_return():
    hints = typing.get_type_hints(PgVectorStore.execute_fetch)
    return hints["return"]


def test_impl_return_type_has_no_any():
    ret = _resolved_return()
    assert ret is not typing.Any, "execute_fetch 返回仍是裸 Any ⇒ G2 未修"
    args = typing.get_args(ret)
    assert typing.Any not in args, f"返回 Union 里仍藏着 Any：{args}"


def test_overloads_distinguish_single_and_multi_row():
    overloads = typing.get_overloads(PgVectorStore.execute_fetch)
    assert len(overloads) == 2, f"应恰有两条 @overload 签名，实际 {len(overloads)}"
    returns = [typing.get_type_hints(o)["return"] for o in overloads]
    list_first = [r for r in returns
                  if typing.get_origin(r) is list
                  or (typing.get_origin(r) is typing.Union
                      and any(typing.get_origin(a) is list
                              for a in typing.get_args(r)))]
    assert len(list_first) == 1, "应有且仅有一条 fetch_all=True ⇒ list 形态的 overload"
