"""图写 store 工厂（foundation 补 store 交付）单测。

验证 `make_graph_write_profile` / `open_graph_write_store` 正确封装
foundation 内核不变量（CORE_ROLES），消费方无需猜测领域建模即可取得
可注入 `build_graph_write_server` 的 store。

⛔ 不连库：两个工厂仅构造对象，连接惰性发生于首次 `execute`；
   本测试无 DSN 即可验证结构与契约。
"""
from __future__ import annotations

from chiyu_kernel.contract.particle import CORE_ROLES, MEMORY_PREDICATES
from chiyu_kernel.graph import (
    build_graph_write_server,
    make_graph_write_profile,
    open_graph_write_store,
)
from chiyu_kernel.store import PgVectorStore


def test_make_graph_write_profile_invariant():
    profile = make_graph_write_profile("crm-a1")
    # 内核不变量：particle_types 必须 = CORE_ROLES（跨域五角色）
    assert profile.particle_types.names == CORE_ROLES
    # 谓词默认 M 层七边，且端点类型均落在 particle_types 内（构造期不红）
    assert set(profile.predicates.names()) == {p.predicate for p in MEMORY_PREDICATES}
    # domain 透传（内核不提供默认域，须由部署侧注入）
    assert profile.domain == "crm-a1"


def test_open_graph_write_store_returns_pg_store_without_dsn():
    # 无 DSN env：仅构造，不发起连接
    store = open_graph_write_store("crm-a1", schema="graph")
    assert isinstance(store, PgVectorStore)
    assert store.schema == "graph"
    # 具备 write_controlled_edges 所需的三个方法（契约）
    assert hasattr(store, "schema")
    assert hasattr(store, "execute")
    assert hasattr(store, "execute_fetch")


def test_factory_compose_with_build_graph_write_server():
    # 端到端组合：工厂 store 可直接喂给 build_graph_write_server（闭环自证）
    store = open_graph_write_store("crm-a1", schema="graph")
    srv = build_graph_write_server(store, auth=lambda ctx: True, secret="s")
    tools = srv.list_tools()
    assert any(t.name == "write_controlled_edges" and t.risk == "write" for t in tools)
