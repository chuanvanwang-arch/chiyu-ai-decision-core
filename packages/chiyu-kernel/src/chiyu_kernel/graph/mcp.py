"""图写 MCP 服务端工具面（R9 方案 A 的**可消费通道**；补 T48 §2.1 纸面缺口）。

设计约束（docs/2026-10-10-答复-CRM-方案A实现稿交付与A1A3a解锁路径.md §2）：
- foundation 把 `write_controlled_edges` 经 `McpServer.expose(risk="write")` 暴露为
  写类工具 `write_controlled_edges`，走 WS7 两阶段确认（与 A9 契约同构）。
- CRM 镜像写 foundation `graph_edge` 的**唯一合法通道** = 经此 MCP 端点调用；
  不得直连 foundation 库写 `graph_edge` SQL（绕过闭集校验与悬空边拒绝 = 无守卫双写）。
- 本文件只做**服务端工具注册**：不发明传输层（R5：http/stdio transport 由消费方
  自实现，把请求喂给 `McpServer.handle_request` 即可）。

参照先例：`chiyu_kernel.scenario.mcp.build_in_memory_server` 同构（能力包自带工具面）。
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from chiyu_kernel.contract import TenantProfile
from chiyu_kernel.contract.particle import CORE_ROLES, ParticleTypeSet, PredicateSet
from chiyu_kernel.mcpserver import McpServer, McpServerError
from chiyu_kernel.persist.graph_edges import EdgeWrite, write_controlled_edges

__all__ = [
    "WRITE_CONTROLLED_EDGES_TOOL", "build_graph_write_server",
    "make_graph_write_profile", "open_graph_write_store",
]

# 工具名（MCP 命名归一：小写+下划线，≤64）
WRITE_CONTROLLED_EDGES_TOOL = "write_controlled_edges"


def build_graph_write_server(store: Any, *, profile: Any = None,
                              auth: Optional[Any] = None,
                              secret: Optional[str] = None) -> McpServer:
    """构造 foundation 图写 MCP 服务端：暴露 `write_controlled_edges`（risk="write"）。

    这是把 R9 方案 A 的"图写能力"从**库函数**升级为**可消费通道**的关键一步：
    CRM 侧拿到 `McpServer` 实例（注入自己的 `auth` + 自选 transport）后，
    即可经 `write_controlled_edges` 两阶段确认地写入 foundation `graph_edge`。

    参数：
        store   图写落库 store（PgVectorStorePersister 等；须实现 schema/execute/execute_fetch）
        profile 受控谓词闭集来源；缺省 = `PredicateSet()`（M 层七边）。
                消费方可注入含 K 层知识的 `PredicateSet` 扩展受控谓词（M∪K 合并视图）。
        auth    可插拔鉴权（零信任：未注入 ⇒ 默认拒绝一切）。
        secret  两阶段令牌密钥；缺省进程内随机（重启即失效，不跨进程重放）。
    """
    if profile is None:
        profile = _DefaultProfile()

    server = McpServer(auth=auth, secret=secret)

    def _write_controlled_edges(args: Mapping[str, Any],
                           ctx: Optional[Mapping[str, Any]] = None) -> Any:
        try:
            edges = [EdgeWrite(**_coerce_edge(e))
                     for e in (args or {}).get("edges", [])]
            report = write_controlled_edges(store, edges, profile=profile)
        except ValueError as e:
            # 闭集 / 悬空等边写校验异常 ⇒ 转结构化 MCP 错误（禁把未处理异常
            # 抛给消费方；与 WS7 handle_request 的 McpServerError 捕获路径一致）。
            raise McpServerError(f"受控边写校验失败：{e}") from e
        return {
            "written": report.written,
            "skipped": [
                {"from_id": f, "to_id": t, "predicate": p, "reason": r}
                for (f, t, p, r) in report.skipped
            ],
        }

    server.expose(
        WRITE_CONTROLLED_EDGES_TOOL, _write_controlled_edges,
        description=(
            "Write controlled graph edges into foundation graph_edge (R9 Plan A). "
            "Predicates must be in profile.predicates; layer/edge_source must be in "
            "closed sets. Dangling edges (missing particle) are rejected (no implicit "
            "vertex creation). Write op requires two-phase confirmation. "
            "Args: {edges: [ {from_id, to_id, predicate, layer?, serves_dims?, "
            "edge_source?, evidence_ref?, valid_from?, valid_until?, weight?, "
            "confidence?} ]}"),
        risk="write",
    )
    return server


class _DefaultProfile:
    """最小 profile 桩：predicates = M 层七边（与 test_graph_edges.Profile 同构）。"""

    def __init__(self) -> None:
        self.predicates = PredicateSet()


# EdgeWrite 允许字段白名单（MCP 入参越界键丢弃，禁注入未知列）
_EDGE_FIELDS = frozenset({
    "from_id", "to_id", "predicate", "layer", "serves_dims",
    "edge_source", "evidence_ref", "valid_from", "valid_until",
    "weight", "confidence",
})


def _coerce_edge(e: Mapping[str, Any]) -> dict:
    """MCP 入参 → EdgeWrite 字段；白名单过滤，必填判据下放到 write_controlled_edges。"""
    return {k: v for k, v in (e or {}).items() if k in _EDGE_FIELDS}


def make_graph_write_profile(domain: str) -> TenantProfile:
    """构造图写租户画像（**foundation 内核不变量，消费方不得自行猜测**）。

    ⛔ 为何必须由 foundation 提供而非消费方手写：
        `TenantProfile.particle_types` 须含全部 `CORE_ROLES`（跨域恒定五角色），
        且须覆盖 M 层七边的端点类型——这是 `ParticleTypeSet` / `TenantProfile`
        的构造期硬约束（`contract/particle.py:86`、`contract/profile.py:52`）。
        消费方若自行填 `ParticleTypeSet(...)`，要么漏核心角色直接构造期红，
        要么把 foundation 领域建模猜错 ⇒ 边写运行期缺锚。本工厂把该不变量收口为
        单一事实源，消费方只传 `domain`（部署侧经 env 注入，内核不提供默认域）。

    - particle_types = `CORE_ROLES`（unstructured_asset/entity/decision/memory/knowledge）
    - predicates     = `PredicateSet()`（默认 M 层七边，与 CRM 镜像写对齐）
    """
    return TenantProfile(
        domain=domain,
        particle_types=ParticleTypeSet(CORE_ROLES),
        predicates=PredicateSet(),
    )


def open_graph_write_store(domain: str, *, schema: str = "graph") -> Any:
    """构造图写租户 store（底层 `PgVectorStore`，实现 `schema/execute/execute_fetch`）。

    消费方（CRM）启动 stdio transport 前调用本函数取得 store，再喂给
    `build_graph_write_server(store, ...)`——这是「等 foundation 补 store」的精确交付：
    foundation 把 `TenantProfile` 构造不变量封装好，消费方零领域猜测。

    ⛔ 惰性 import `open_store`：避免 `graph` ↔ `api` 顶层环依赖
       （`api.py` 在 import 阶段已 `from chiyu_kernel.graph import ...`）。
    PG DSN 由 foundation 标准 env 注入；本函数仅构造对象，不发起连接
    （连接惰性发生于首次 `execute`，单测可无 DSN 验证结构）。

    参数：
        domain  本部署域（消费方经 env 传入；必填，内核不提供默认）。
        schema  目标 schema（默认 "graph"）。
    """
    from chiyu_kernel.api import open_store
    return open_store(make_graph_write_profile(domain), schema=schema)

