"""内存 store 替身（fake adapter）—— 让样板**零外部依赖**即可跑通与自检。

⛔ 这不是生产存储：它只实现 `PgVectorStore` 的**调用面**
   （`schema` / `execute` / `execute_fetch` / `upsert_particle` / `query`），
   把写入记在内存里，供探针断言「真落库 / 真物化 / 真派生」。

生产替换：把 `InMemoryStore()` 换成 `PgVectorStore(profile, schema=...)` 即可，
上层（persister / 图 / MCP 工具）代码一行不用改 —— 这就是「单源」接缝的价值。

⚠️ 语义说明：本替身按 SQL 中的表名路由（`event` / `graph_edge`），与内核
   persister 生成的 SQL 形状绑定。改 persister 的 SQL 形状时须同步此处。
"""
from __future__ import annotations

import json
from typing import Any, Iterable, List, Mapping, Optional


class InMemoryStore:
    """store 替身：记录 event / particle / graph_edge 写入，暴露为可读事实。"""

    def __init__(self, schema: str = "public") -> None:
        self.schema = schema
        self.events: dict = {}          # event_id -> payload dict（真实环境在 jsonb 列）
        self.particles: dict = {}       # particle_id -> 粒子属性 dict
        self.edges: List[dict] = []     # 每条受控边（与 graph_edge 表列对齐）
        self.executes: List[tuple] = []  # 全量 SQL 审计（供「是否真执行」类探针）

    # ── PgVectorStore 调用面 ────────────────────────────────────────────────
    def execute(self, sql: str, params: Any = None) -> None:
        self.executes.append((sql, params))
        lowered = sql.lower()
        if "graph_edge" in lowered:
            p = list(params or ())
            self.edges.append({
                "from_id": p[0], "to_id": p[1], "predicate": p[2],
                "layer": p[3], "serves_dims": tuple(p[4] or ()),
                "edge_source": p[5],
            })
        elif "insert into" in lowered and "event" in lowered:
            eid = params[0]
            payload = json.loads(params[-1])   # 末参是 jsonb 字符串
            self.events[eid] = payload

    def execute_fetch(self, sql: str, params: Any = None) -> Any:
        """仅实现 persister 用到的幂等查询（content_hash 比对）。"""
        if "content_hash" in sql.lower():
            eid = (params or (None,))[0]
            if eid in self.events:
                return {"ch": self.events[eid].get("content_hash")}
        return None

    def upsert_particle(self, particle_id: str, ptype: str, layer: str = "L1", *,
                        label: Any = None, status: Any = None, provider: Any = None,
                        ai_generated: bool = False, dim: int = 1024,
                        vec: Any = None, **_: Any) -> None:
        self.particles[particle_id] = {
            "particle_id": particle_id, "type": ptype, "layer": layer,
            "label": label, "status": status, "provider": provider,
            "ai_generated": ai_generated, "dim": dim,
        }

    def query(self, table: str, *, where: str = "", params: Any = None,
              limit: int = 100) -> List[Mapping[str, Any]]:
        if table == "event":
            return list(self.events.values())[:limit]
        if table == "graph_edge":
            return list(self.edges)[:limit]
        return []

    def count(self, table: str) -> int:
        return len(self.events) if table == "event" else len(self.edges)

    def close(self) -> int:
        return 0

    def created_schemas(self) -> set:
        return {self.schema}

    # ── 事实视图（供探针 / canary 只读消费）────────────────────────────────
    def edge_triples(self) -> set:
        return {(e["from_id"], e["to_id"], e["predicate"]) for e in self.edges}

    def decision_events(self) -> dict:
        return {k: v for k, v in self.events.items()
                if v.get("event_type", "decision") == "decision"}


__all__ = ["InMemoryStore"]
