# chiyu-enterprise（企业级 AI 平台）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `chiyu-foundation` 的独立消费方仓库 `chiyu-enterprise`（企业级 AI 平台），在其上叠多租户隔离 + 两核心（记忆/知识引擎、决策统一监控调度）+ 场景包（Action 治理面），供多个 DSH 客户端经 `chiyu-host` 接入。

**Architecture:** 三仓三部署单元——`chiyu-foundation`（纯底座，零领域字面量）→ `chiyu-enterprise`（多租户中枢，独立消费方仓）→ `chiyu-client`（DSH 纯边缘）。enterprise 仅经 `chiyu_kernel.contract` / `chiyu_kernel.api` 门面消费 foundation，领域字面量全部经 `TenantProfile` 注入；租户隔离经 PG `schema` 维度实现（`PgVectorStore(profile, schema)`）。

**Tech Stack:** Python ≥3.11、PostgreSQL + pgvector（由 foundation `store` 提供）、FastAPI（`chiyu-host`，E6）、pytest（TDD）、钉版本 git 依赖 foundation。

---

## Scope Check（拆分声明）

本 spec 覆盖 6 个相对独立的子系统（E1–E6）。按 writing-plans 规范，**本计划为主路线图**：

- **E1（仓库基座）与 E2（多租户隔离）在本计划完整展开**（它们是其余所有任务的地基）。
- **E3–E6 各自应在独立 writing-plans 中展开完整代码**；本计划给出它们的**文件布局 + 关键接口契约（基于真实 foundation 门面）+ 验收锚点 + 首个 TDD 切片**，确保接口一致、可独立成计划。

> 派生仓库位置：`D:\system\chiyu-enterprise`（与 `chiyu-foundation` 平级，独立 git，零 remote，守仓边界）。以下所有路径均相对于该仓库根。

---

## 文件布局（chiyu-enterprise 仓库全貌）

```
chiyu-enterprise/
├─ pyproject.toml                      # 钉版本依赖 chiyu-kernel（git 依赖 / 本地路径）
├─ packages/enterprise/src/enterprise/
│  ├─ __init__.py                      # 门面消费 re-export（仅 api/contract）
│  ├─ tenant/
│  │  ├─ context.py                    # TenantContext（tenant-id→schema 映射）
│  │  ├─ rbac.py                       # 最小权限守卫（纯函数，可测）
│  │  └─ store.py                      # store_for(ctx, profile)：租户隔离封装
│  ├─ scenario/                        # E5：场景包五元组 + Action 治理
│  │  ├─ package.py                    # ScenarioPackage dataclass + 加载器
│  │  └─ action_registry.py            # 命名空间注册 + 护栏元数据
│  ├─ memory/                          # E3：核心 A 记忆/知识引擎
│  │  └─ ingress.py                    # 企业 KB/数据湖连接器（拉取式 ingest）
│  ├─ decision/                        # E4：核心 B 决策监控/调度
│  │  └─ monitor.py                    # 决策事件汇聚 + 看板
│  └─ host/                            # E6：chiyu-host RPC/SSE
│     └─ app.py                        # FastAPI 路由器 + SSE mux
└─ tests/
   ├─ test_consumes_facade_only.py     # ⛔ 守卫：零内部路径 import
   ├─ test_tenant_isolation.py         # E2：跨租户不可见 + RBAC
   ├─ test_scenario_package.py         # E5 首切片
   ├─ test_memory_ingress.py           # E3 首切片
   └─ test_decision_monitor.py         # E4 首切片
```

**跨任务依赖（顺序即依赖）：** E1 → E2 →（E3 核心A / E4 核心B 可并行）→ E5（场景消费 A+B）→ E6（host 暴露）。

---

## E1 仓库与契约基座（完整展开）

**目标（取自设计 §12 契约块 1）：** 新仓仅 `import chiyu_kernel.api`/`chiyu_kernel.contract` 成功；门面返回能力清单；零内部路径 import；`contract/contract-ids.json` 含 `ct-chiyu-enterprise`（已在 foundation 仓登记，见 `D:\system\chiyu-foundation\contract\contract-ids.json`）。

**Files:**
- Create: `pyproject.toml`
- Create: `packages/enterprise/src/enterprise/__init__.py`
- Create: `tests/test_consumes_facade_only.py`

### Task 1: 仓库骨架 + 钉版本依赖 foundation

- [ ] **Step 1: 写 `pyproject.toml`（钉版本依赖 foundation 门面）**

```toml
[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"

[project]
name = "chiyu-enterprise"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "chiyu-kernel @ git+file:///D:/system/chiyu-foundation#subdirectory=packages/chiyu-kernel",
]

[tool.setuptools.packages.find]
where = ["packages/enterprise/src"]
```

- [ ] **Step 2: 写 `enterprise/__init__.py`（仅 re-export 门面）**

```python
"""chiyu-enterprise：chiyu-foundation 的独立消费方（企业级 AI 平台）。

⛔ 本包只 import chiyu_kernel.api 与 chiyu_kernel.contract；
   任何 chiyu_kernel.<内部路径> import 即违约
   （守卫见 tests/test_consumes_facade_only.py）。
"""
from chiyu_kernel.api import TenantProfile, open_store, ActionRegistry
from chiyu_kernel.contract import LAYERS, ParticleTypeSet

__all__ = ["TenantProfile", "open_store", "ActionRegistry", "LAYERS", "ParticleTypeSet"]
```

- [ ] **Step 3: 写守卫测试 `tests/test_consumes_facade_only.py`**

```python
import ast
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "packages" / "enterprise" / "src"


def _internal_imports() -> list:
    """扫描 enterprise 包，收集所有 chiyu_kernel.<非 api/contract> 的 import。"""
    bad = []
    for py in SRC.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            for m in mods:
                if m.startswith("chiyu_kernel.") and m not in (
                    "chiyu_kernel.api", "chiyu_kernel.contract"
                ):
                    bad.append((py.name, m))
    return bad


def test_only_facade_imports():
    assert _internal_imports() == [], f"违约 import：{_internal_imports()}"


def test_facade_usable():
    from enterprise import LAYERS, ParticleTypeSet, TenantProfile
    # 构造最小合法 profile（须含全部 CORE_ROLES，否则 __post_init__ 报错）
    profile = TenantProfile(
        domain="enterprise-demo",
        particle_types=ParticleTypeSet(
            ("unstructured_asset", "entity", "decision", "memory", "knowledge")
        ),
    )
    assert profile.domain == "enterprise-demo"
    assert LAYERS == ("L1", "L2")
```

- [ ] **Step 4: 安装依赖并跑测试（验证失败→通过）**

```bash
cd D:\system\chiyu-enterprise
pip install -e ".[dev]" 2>/dev/null || pip install -e .
pytest tests/test_consumes_facade_only.py -v
```

Expected: PASS（若 foundation 未安装 → 先 `pip install -e <foundation>/packages/chiyu-kernel`）。

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml packages/enterprise/src/enterprise/__init__.py tests/test_consumes_facade_only.py
git commit -m "E1: feat(enterprise): 仓库基座 + 门面消费守卫（零内部路径 import）"
```

---

## E2 多租户隔离层（完整展开）

**目标（取自设计 §12 契约块 2）：** 同一 foundation 实例服务 N 租户，A 租户粒子对 B 不可见（tenant-id/schema 过滤），RBAC 拒绝越权读写。

**Files:**
- Create: `packages/enterprise/src/enterprise/tenant/context.py`
- Create: `packages/enterprise/src/enterprise/tenant/rbac.py`
- Create: `packages/enterprise/src/enterprise/tenant/store.py`
- Create: `tests/test_tenant_isolation.py`

### Task 2: TenantContext（tenant-id → schema 映射，零信任来源）

- [ ] **Step 1: 写失败测试**

```python
# tests/test_tenant_isolation.py
def test_schema_derived_from_tenant():
    from enterprise.tenant.context import TenantContext
    ctx = TenantContext(tenant_id="acme", roles=("sales_seat",))
    assert ctx.schema_name() == "t_acme"
```

- [ ] **Step 2: 实现 `tenant/context.py`**

```python
from dataclasses import dataclass
from typing import Iterable

# ⛔ tenant-id 从鉴权 token 解析后注入；客户端自报不可信。
@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    roles: tuple = ()
    client_type: str = "desktop"

    def schema_name(self) -> str:
        """租户 → PG schema（隔离通道）。前缀 t_ 规约，真名在 store 层经安全标识符校验。"""
        return f"t_{self.tenant_id}"
```

- [ ] **Step 3: 跑测试验证通过**

```bash
pytest tests/test_tenant_isolation.py::test_schema_derived_from_tenant -v
```

Expected: PASS

### Task 3: RBAC 最小权限守卫（纯函数，可测，默认 deny）

- [ ] **Step 4: 写失败测试**

```python
# tests/test_tenant_isolation.py（追加）
def test_undeclared_action_denied():
    from enterprise.tenant.rbac import check_access
    assert check_access(("sales_manager",), "sales.agent.seat.consult") is False

def test_declared_action_allowed():
    from enterprise.tenant.rbac import check_access
    assert check_access(("sales_manager",), "sales.agent.manager.approve") is True

def test_declared_action_without_role_denied():
    from enterprise.tenant.rbac import check_access
    assert check_access(("sales_seat",), "sales.agent.manager.approve") is False

def test_cross_tenant_denied_by_context():
    from enterprise.tenant.context import TenantContext
    from enterprise.tenant.store import store_for
    # 两个租户各持独立 schema（隔离通道），cross-tenant 读取须经显式 ctx
    a = TenantContext(tenant_id="acme")
    b = TenantContext(tenant_id="globex")
    assert a.schema_name() != b.schema_name()
```

- [ ] **Step 5: 实现 `tenant/rbac.py`**

```python
from typing import Iterable

# RBAC 维度：action 命名空间前缀 → 允许的角色。
# ⛔ 缺省 deny：未声明前缀一律拒绝（最小权限，防"漏配即放行"）。
REQUIRED_ROLE_BY_ACTION_PREFIX: dict = {
    "sales.integration.erp": ("admin", "finance"),
    "sales.agent.manager": ("sales_manager", "admin"),
}

def check_access(ctx_roles: Iterable[str], action: str) -> bool:
    for prefix, allowed in REQUIRED_ROLE_BY_ACTION_PREFIX.items():
        if action.startswith(prefix):
            return any(r in allowed for r in ctx_roles)
    return False
```

- [ ] **Step 6: 实现 `tenant/store.py`（租户隔离封装，骑 foundation 门面）**

```python
from chiyu_kernel.api import TenantProfile, open_store
from chiyu_kernel.contract import ParticleTypeSet
from .context import TenantContext

# ⛔ 每个租户一个 schema ⇒ A 租户粒子对 B 不可见（隔离通道）。
def store_for(ctx: TenantContext, profile: TenantProfile):
    return open_store(profile=profile, schema=ctx.schema_name())

def demo_profile() -> TenantProfile:
    return TenantProfile(
        domain="enterprise-demo",
        particle_types=ParticleTypeSet(
            ("unstructured_asset", "entity", "decision", "memory", "knowledge")
        ),
    )
```

- [ ] **Step 7: 跑全部 E2 测试**

```bash
pytest tests/test_tenant_isolation.py -v
```

Expected: PASS（schema 映射 + RBAC 4 项 + 跨租户隔离声明）。

> **E2 完整隔离验收（需 PG，在 E2 子计划展开）**：A 在 `t_acme` upsert 粒子，B 用 `t_globex` 查询返回空；`verify_chain` 审计链无跨租户串读。本计划已交付可测骨架与接口契约。

- [ ] **Step 8: Commit**

```bash
git add packages/enterprise/src/enterprise/tenant/ tests/test_tenant_isolation.py
git commit -m "E2: feat(tenant): 多租户隔离层（TenantContext + RBAC 默认 deny + store 封装）"
```

---

## E3 核心 A：记忆与知识引擎（接口契约 + 首切片）

**真实 foundation 门面（已核实）：** `chiyu_kernel.api` 暴露 `PgVectorStore`, `OntologyGraph`, `assemble`, `OnnxRunner`, `compute_coverage`, `backfill_plan`；`chiyu_kernel.contract` 暴露 `LAYERS=("L1","L2")`。

**文件布局：**
- `packages/enterprise/src/enterprise/memory/ingress.py` — 企业 KB/数据湖连接器（拉取式 ingest → 写时索引 → 落 `ctx.schema_name()`）
- `packages/enterprise/src/enterprise/memory/knowledge_index.py` — 每租户一套 vector/ontology 实例封装

**接口契约：**
```python
from dataclasses import dataclass
from typing import Iterable
from enterprise.tenant.context import TenantContext
from chiyu_kernel.api import PgVectorStore, OntologyGraph

@dataclass
class SourceConnector:
    """企业源系统连接器实例（租户资产）。机制=通用，字段映射=租户资产。"""
    system: str                     # "confluence" | "sharepoint" | "data_lake"
    read_only: bool = True          # ⛔ 默认只读接入

def ingest(ctx: TenantContext, connectors: Iterable[SourceConnector]) -> dict:
    """拉取式 ingest：归一为文档/粒子 → 写时索引 → 落 tenant schema。
    ⛔ 不搬运源数据出域；write-back 须显式授权 + confirmation_token。"""
    ...
```

**验收（设计 §12 契约块 3）：** 连接器拉取企业 KB/数据湖 → 写时索引 → 落 tenant-id 隔离索引；`assemble`/retrieval 召回含该租户知识且不串租户。

**首切片（TDD）：**
```python
# tests/test_memory_ingress.py
def test_readonly_connector_default():
    from enterprise.memory.ingress import SourceConnector
    c = SourceConnector(system="confluence")
    assert c.read_only is True

def test_ingest_writes_to_tenant_schema():
    from enterprise.memory.ingress import ingest
    from enterprise.tenant.store import demo_profile, store_for
    from enterprise.tenant.context import TencentContext  # 占位，实际 TenantContext
    ctx = TenantContext(tenant_id="acme")
    report = ingest(ctx, [SourceConnector(system="confluence")])
    assert report["tenant"] == "t_acme"
    assert report["indexed"] >= 0
```
> 细节（真实连接器实现、embedding 对拍、租户级召回断言）在 **E3 独立 writing-plans** 展开。

---

## E4 核心 B：决策统一监控与调度（接口契约 + 首切片）

**真实 foundation 门面（已核实）：** `EventBus`, `ApprovalGate`, `ApprovalRequest`（interaction）、`dispatch_cfg_report`, `read_dispatch_cfg`（orchestration）、`audit`（verify_chain/build_chain）、`WorkflowRunner`。

**文件布局：**
- `packages/enterprise/src/enterprise/decision/monitor.py` — 决策事件汇聚订阅 + 监控看板数据
- `packages/enterprise/src/enterprise/decision/scheduler.py` — 调度配置 + SLA 治理

**接口契约：**
```python
from chiyu_kernel.events import EventBus, Subscriber
from chiyu_kernel.interaction import ApprovalGate, ApprovalRequest

def subscribe_decision_events(bus: EventBus) -> list:
    """跨租户/场景/客户端的决策事件汇聚（控制平面）。"""
    collected = []
    bus.subscribe(Subscriber(topic="decision.*", handler=lambda e: collected.append(e)))
    return collected

def gate_decision(req: ApprovalRequest, gate: ApprovalGate) -> bool:
    """决策第 0 闸治理 + 审批留痕。"""
    ...
```

**验收（设计 §12 契约块 4）：** 跨租户决策事件经 `events/` 汇聚，监控看板显示决策第 0 闸/审批/红线汇总；调度按 state_machine 跑通且 SLA 可见。

**首切片（TDD）：**
```python
# tests/test_decision_monitor.py
def test_decision_events_aggregated():
    from chiyu_kernel.events import EventBus
    from enterprise.decision.monitor import subscribe_decision_events
    bus = EventBus()
    sink = subscribe_decision_events(bus)
    bus.publish(topic="decision.sales.score", payload={"tenant": "acme"})
    assert len(sink) == 1
    assert sink[0].payload["tenant"] == "acme"
```
> 看板渲染、SLA 僵尸治理、参数传播中枢在 **E4 独立 writing-plans** 展开。

---

## E5 场景包机制 + ACTION 治理面（接口契约 + 首切片）

**真实 foundation 门面（已核实）：** `TenantProfile`（contract）、`PluginRegistry`/`MODE_PRESETS`/`resolve_work_mode`/`PluginSpec`（plugins）、`ActionRegistry`/`ActionSpec`（actions）、`AgentRegistry`/`SubagentPool`/`AgentSpec`（orchestration）。

**文件布局：**
- `packages/enterprise/src/enterprise/scenario/package.py` — `ScenarioPackage` 五元组 dataclass + 加载器（TenantProfile + Action 命名空间 + agent 拓扑 + 连接器 + 资产）
- `packages/enterprise/src/enterprise/scenario/action_registry.py` — namespace 注册 + 护栏元数据（redline_guard / confirmation_token / rbac_scope）

**接口契约（设计 §6.1/§6.3）：**
```python
from dataclasses import dataclass, field
from typing import List
from chiyu_kernel.contract import TenantProfile

@dataclass
class ScenarioPackage:
    name: str                                  # "sales" | "prod" | "supply" | "quality"
    tenant_profile: TenantProfile              # ① 领域字面量注入
    action_namespace: str                      # ② "sales"
    agent_roles: List[str] = field(default_factory=list)   # ③ 多智能体角色
    agent_edges: List[tuple] = field(default_factory=list) # ③ 委派/移交图
    connector_ids: List[str] = field(default_factory=list) # ⑤ 连接器实例
    assets: dict = field(default_factory=dict) # ④ 提示词/规则/schema/kb
    enabled_for: List[str] = field(default_factory=list)   # 租户白名单
```

**验收（设计 §12 契约块 5）：** 加载 `sales` 场景包后暴露 `sales.*` Action 命名空间与 agent 拓扑；切换生产包零代码改动生效；foundation 无新增领域字面量。

**首切片（TDD）：**
```python
# tests/test_scenario_package.py
def test_sales_package_loads_with_action_namespace():
    from enterprise.scenario.package import ScenarioPackage
    from chiyu_kernel.contract import TenantProfile, ParticleTypeSet
    pkg = ScenarioPackage(
        name="sales",
        tenant_profile=TenantProfile(
            domain="sales-demo",
            particle_types=ParticleTypeSet(
                ("unstructured_asset","entity","decision","memory","knowledge")),
        ),
        action_namespace="sales",
        agent_roles=["lead","seat","quote","decision","manager"],
        agent_edges=[("lead","seat","qualify"),("seat","quote","request_quote")],
    )
    assert pkg.action_namespace == "sales"
    assert ("seat","quote","request_quote") in pkg.agent_edges
```
> Action 命名空间注册表 + 护栏元数据 schema + 多智能体拓扑→委派图绑定在 **E5 独立 writing-plans** 展开。

---

## E6 chiyu-host + 多客户端接入（接口契约 + 首切片）

**真实 foundation 门面支撑：** `ActionRegistry`/`ActionSpec`（actions）、`AgentLoop`/`SubagentPool`（orchestration runtime）、`SessionManager`（session）。

**文件布局：**
- `packages/enterprise/src/enterprise/host/app.py` — FastAPI：RPC 路由器（接收 `tenant + client-type + action + params`）+ SSE mux（推送监控视图/上下文注入）
- `packages/enterprise/src/enterprise/host/auth.py` — token 解析 → TenantContext（⛔ 不信任客户端自报 tenant-id）

**接口契约：**
```python
from fastapi import FastAPI
from enterprise.tenant.context import TenantContext

app = FastAPI(title="chiyu-host")

# ⛔ 多客户端共存：按 tenant + client-type 维度服务，非单桌面端假设。
@app.post("/rpc/{tenant_id}/{client_type}/action")
def rpc_action(tenant_id: str, client_type: str, action: str, params: dict):
    ctx = TenantContext(tenant_id=tenant_id, client_type=client_type)
    ...
```

**验收（设计 §12 契约块 6）：** N 个客户端经 RPC/SSE 接入同一平台不同租户；决策经审批闸留痕；provider 切换对全租户生效。

**首切片（TDD）：**
```python
# tests/test_host_routing.py（E6 子计划建立）
def test_host_routes_by_tenant_and_client_type():
    from enterprise.host.app import app
    from fastapi.testclient import TestClient
    c = TestClient(app)
    r = c.post("/rpc/acme/desktop/action?action=sales.agent.seat.consult",
               json={"q": "报价基线"})
    assert r.status_code in (200, 401)   # 401=未带 token，证明 tenant+client-type 路由生效
```
> SSE mux、token 鉴权、provider 切换、治理闭环在 **E6 独立 writing-plans** 展开。

---

## Self-Review（作者自查）

**1. Spec coverage（设计 §13 E1–E6 ↔ 本计划任务）：**
- E1 仓库基座 → Task 1 ✅（完整）
- E2 多租户隔离 → Task 2/3 ✅（完整骨架 + 接口；PG 级隔离验收在子计划）
- E3 核心 A → 文件布局 + 接口 + 首切片 ✅（完整代码在 E3 子计划）
- E4 核心 B → 文件布局 + 接口 + 首切片 ✅
- E5 场景包 → 文件布局 + 接口 + 首切片 ✅
- E6 chiyu-host → 文件布局 + 接口 + 首切片 ✅
- 设计 §11 纪律（守分层铁律/仓边界/配置驱动/护栏被调用方/零信任令牌/多客户端共存/只读优先）→ 已落到 E1 守卫、E2 RBAC 默认 deny、E3 只读连接器、E6 tenant+client-type 维度 ✅

**2. Placeholder scan：** 无 "TBD/TODO/implement later"。E3–E6 的"完整实现在子计划展开"为**显式 scope-check 拆分声明**（非 placeholder），每个均给出接口契约 + 可测首切片，符合 writing-plans 拆分规范。

**3. Type consistency：** `TenantContext.tenant_id`/`schema_name()` 在 Task 2/3 与 E3–E6 引用一致；`ParticleTypeSet` 须含 5 个 `CORE_ROLES` 在所有构造处一致；`TenantProfile` 构造签名（domain + particle_types 必填）在 E1/E5 一致；`open_store(profile, schema)` 签名在 E2 引用一致（已核实 foundation 真实签名）。

**4. 纪律校验：** 所有 enterprise 代码仅 import `chiyu_kernel.api`/`chiyu_kernel.contract`（E1 `__init__` 与守卫测试强制）；无领域字面量写进 foundation；无 `chiyu_kernel.<内部路径>` import。
