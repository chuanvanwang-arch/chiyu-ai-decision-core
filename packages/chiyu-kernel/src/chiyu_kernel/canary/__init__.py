"""canary 探针件（N7）—— 决策落库三判据的**统一判定式**（foundation 单一事实源）。

⛔ 为什么要在基座 ship 这个：三个消费方各自自造探针 ⇒ 判据口径漂移
   （"count>0 就算落库"这类恒绿探针曾是本仓真实事故）。本模块把三判据
   的**判定式**收归基座维护，消费方只注入接线（store + 决策回调）。

三判据（缺一不可，任一不满足即探针失败）：
  1. **决策真落库**：event 行存在 **且** particle 行存在（只查 event 不查
     particle 挡不住"半写"—— 两张表须同事务成对出现）；
  2. **记忆网真物化**：`graph_edge` 中该决策的 `edge_source='engine'` 边数
     **恰好等于**注入 references 的非空谓词数（多写=幻影边，少写=漏物化）；
  3. **红线挡落库**：红线决策回调的结果不落库且被审批闸拦下
     （REJECTED 或 PENDING；注入了红线回调才可判定，否则该判据为 False）。

接口说明（与 enterprise 反馈 #N7 原案 `canary_probe(dsn, profile)` 的差异，诚实标注）：
  取 `store`（鸭子类型：`execute` / `execute_fetch` / `schema`）而非 `dsn` ——
  消费方（如 APS 用 psycopg3）已持有自己的连接层，注入 store 免内核绑死驱动
  （与 R9 驱动解耦同一取向）；dsn 场景由消费方先 `PgVectorStore(profile)` 自建。
  `run_decision` / `run_redline_decision` 为消费方接线的决策回调
  （内核不得反向依赖 chiyu_decision，分层铁律）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence

__all__ = ["CanaryReport", "canary_probe"]


@dataclass(frozen=True)
class CanaryReport:
    """探针结论：三判据逐项布尔 + 细节（排障用，不含敏感值）。"""

    decision_persisted: bool
    memory_net_materialized: bool
    redline_blocked: bool
    details: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """三判据全绿才算通过（部分绿 = 未通过，禁"主要判据绿"式放水）。"""
        return self.decision_persisted and self.memory_net_materialized \
            and self.redline_blocked


def _q(schema: str, table: str) -> str:
    return f"{schema}.{table}" if schema else table


def _table_of(sql: str, schema: str, table: str) -> bool:
    """判定 SQL 是否查询 `<schema>.<table>`（供打桩 store 路由读请求）。"""
    pat = re.compile(rf"FROM\s+{re.escape(_q(schema, table))}\b", re.IGNORECASE)
    return bool(pat.search(sql))


def canary_probe(*, store: Any,
                 run_decision: Callable[[], Any],
                 decision_id: str = "canary-dec-1",
                 references: Optional[Mapping[str, Sequence[str]]] = None,
                 run_redline_decision: Optional[Callable[[], Any]] = None) -> CanaryReport:
    """对已接线的决策链路执行三判据。**只读核验**，自身不写库。

    参数：
      store               消费方 store（PgVectorStore 或同鸭子类型；须有
                          `schema` / `execute_fetch`）
      run_decision        消费方决策回调：执行一次**正常**决策
                          （run_spine + persister 已接到同一 store），返回
                          SpineResult 同形对象（须有 `persisted` 属性）
      decision_id         本轮回调使用的 decision_id（须与回调内一致）
      references          记忆网供给（键=谓词、值=端点列表）；None/空 ⇒
                          判据 2 不可判定（False，禁静默放行）
      run_redline_decision 红线决策回调：执行一次**红线命中**的决策；
                          None ⇒ 判据 3 不可判定（False）
    """
    schema = getattr(store, "schema", "")
    details: dict = {}

    # ── 判据 1：决策真落库（event + particle 成对）────────────────────
    result = run_decision()
    details["run_persisted"] = bool(getattr(result, "persisted", False))
    event_row = store.execute_fetch(
        f"SELECT id FROM {_q(schema, 'event')} WHERE id=%s", (decision_id,))
    particle_row = store.execute_fetch(
        f"SELECT particle_id FROM {_q(schema, 'particle')} WHERE particle_id=%s",
        (decision_id,))
    details["event_row"] = event_row is not None
    details["particle_row"] = particle_row is not None
    decision_persisted = (details["run_persisted"] and details["event_row"]
                          and details["particle_row"])

    # ── 判据 2：记忆网真物化（engine 边数 == 非空谓词数，恰好相等）──────
    expected_edges = sum(1 for v in (references or {}).values() if v) \
        if references else 0
    if expected_edges == 0:
        details["memory_net"] = "未提供 references ⇒ 判据 2 不可判定"
        memory_net_materialized = False
    else:
        row = store.execute_fetch(
            f"SELECT count(*) AS n FROM {_q(schema, 'graph_edge')} "
            f"WHERE from_id=%s AND edge_source='engine'", (decision_id,))
        actual = int(row["n"]) if isinstance(row, dict) else int(row[0])
        details["memory_net"] = f"engine 边 {actual} / 期望 {expected_edges}"
        memory_net_materialized = (actual == expected_edges)

    # ── 判据 3：红线挡落库 ────────────────────────────────────────────
    if run_redline_decision is None:
        details["redline"] = "未注入红线决策回调 ⇒ 判据 3 不可判定"
        redline_blocked = False
    else:
        r2 = run_redline_decision()
        rejected = getattr(r2, "approval_rejected", None) is not None
        pending = bool(getattr(r2, "pending", False))
        not_persisted = not getattr(r2, "persisted", False)
        details["redline"] = (f"persisted={getattr(r2, 'persisted', None)}, "
                              f"rejected={rejected}, pending={pending}")
        redline_blocked = not_persisted and (rejected or pending)

    return CanaryReport(
        decision_persisted=decision_persisted,
        memory_net_materialized=memory_net_materialized,
        redline_blocked=redline_blocked,
        details=details,
    )
