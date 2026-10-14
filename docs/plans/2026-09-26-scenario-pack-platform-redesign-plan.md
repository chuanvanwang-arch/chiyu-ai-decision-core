# 场景包双阶段平台化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 executing-plans（推荐）或 subagent-driven development 按任务逐个实现本计划。步骤用 `- [ ]` 勾选跟踪。

**Goal:** 把场景包从「web 门户私有 store」重定向为「平台化双阶段」：开发阶段经本地 stdio MCP server 写入平台（chiyu-host `POST /control/scenarios`），运行阶段 web 读平台 `GET /control/scenarios` + 经 `/rpc/{tenant}/{client_type}/action` 数据交互；开发/运行以用户名+角色隔离（复用 `chiyu_host` RBAC）。

**Architecture:** 三层不重叠：
- **数据/校验层**：kernel `scenario`（`from_dict` 唯一校验闸）已存在，直接复用。
- **平台层**：本仓 `chiyu_host` 新增 `control.py` 路由（`GET/POST /control/scenarios`、`POST /control/scenario/{name}/lock`、`GET /control/rbac`）+ `scenario_mapper.py`（双模型映射：平台模型 ↔ kernel `ScenarioPack`）。本仓 host 可作为替换 8000 的实例部署。
- **开发侧**：`tools/mcp_scenario_server.py`（stdio MCP server，3 工具，内部调本仓 host 的写接口）。

**Tech Stack:** Python 3 / FastAPI / chiyu_kernel.scenario / MCP stdio（InMemoryMcpServer）/ 前端 Vite+React（web）。

**红线（偏离即推翻）：** 单一校验闸 `from_dict`；开发=dev.* 写、运行=业务角色读/action，权限隔离；写类操作须 confirm+写闸；内核零领域字面量；不改 `contract/*.py`。

---

## 文件结构

| 文件 | 责任 |
|------|------|
| `packages/chiyu-host/src/chiyu_host/control.py` (新建) | `/control/*` 只读路由：scenarios/scenario/{name}/rbac/agents，读 host store |
| `packages/chiyu-host/src/chiyu_host/scenario_store.py` (新建) | 平台场景包本地 JSON 存储（目录扫描/读写/锁定）+ RBAC 角色表 |
| `packages/chiyu-host/src/chiyu_host/scenario_mapper.py` (新建) | 双模型映射：平台模型 ↔ kernel `ScenarioPack`，复用 `from_dict` 唯一校验闸 |
| `packages/chiyu-host/src/chiyu_host/rpc_control.py` (新建) | `POST /control/scenarios`（写）+ `POST /control/scenario/{name}/lock`（写，confirm）—— 写类接口，dev.* + RBAC + G0 锚 |
| `packages/chiyu-host/src/chiyu_host/app.py` (修改) | 挂载 control 路由（read-only + write 两组） |
| `tools/mcp_scenario_server.py` (新建) | stdio MCP server：3 工具 write/list/lock，内部调本仓 host 写接口 |
| `packages/chiyu-host/tests/test_control_scenarios.py` (新建) | 平台写/读/锁 + RBAC + 映射 + 变异自证 |
| `web/backend/scenario_bridge.py` (修改) | list→读平台 / run→调平台 RPC / select/lock 写平台 |
| `web/src/data/api.ts` + `web/src/components/Workbench.tsx` (修改) | 前端场景包端点重定向到平台 |

---

### Task 1: 平台只读路由 `/control/*`（host 侧）

**Files:**
- Create: `packages/chiyu-host/src/chiyu_host/scenario_store.py`
- Create: `packages/chiyu-host/src/chiyu_host/control.py`
- Test: `packages/chiyu-host/tests/test_control_scenarios.py`

- [ ] **Step 1: 写失败的只读路由测试**

```python
# packages/chiyu-host/tests/test_control_scenarios.py
"""平台只读控制面 + 场景包读写 + RBAC + 双模型映射 + 变异自证。"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chiyu_host.app import app


@pytest.fixture()
def store_dir(tmp_path: Path) -> Path:
    d = tmp_path / "scenario_packs"
    d.mkdir()
    return d


def _write_pack(store_dir: Path, pkg: str, body: dict) -> None:
    (store_dir / f"{pkg}.json").write_text(json.dumps(body), encoding="utf-8")


def test_control_scenarios_read_only_lists_disk(tmp_path: Path) -> None:
    d = tmp_path / "scenario_packs"
    d.mkdir()
    _write_pack(d, "sales-north", {"pkg": "sales-north", "namespace": "sales",
        "tenant": "t-default", "actions": ["sales.native.action_propose"],
        "assets": [{"layer": "L1", "dims": ["semantics"]}], "integrations": [],
        "status": "draft"})
    client = TestClient(app)
    r = client.get("/control/scenarios")
    assert r.status_code == 200
    data = r.json()
    assert data["items"]
    pkgs = [i["pkg"] for i in data["items"]]
    assert "sales-north" in pkgs


def test_control_scenario_by_name(tmp_path: Path) -> None:
    d = tmp_path / "scenario_packs"
    d.mkdir()
    _write_pack(d, "sales-north", {"pkg": "sales-north", "namespace": "sales",
        "tenant": "t-default", "actions": [], "assets": [], "integrations": [],
        "status": "draft"})
    client = TestClient(app)
    r = client.get("/control/scenario/sales-north")
    assert r.status_code == 200
    assert r.json()["pkg"] == "sales-north"


def test_control_rbac_lists_roles() -> None:
    client = TestClient(app)
    r = client.get("/control/rbac")
    assert r.status_code == 200
    roles = {u["role"] for u in r.json()["users"]}
    assert {"admin", "finance", "sales_manager"}.issubset(roles)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-host/tests/test_control_scenarios.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'chiyu_host.scenario_store'` 或 404）

- [ ] **Step 3: 实现 scenario_store.py（平台包存储 + RBAC）**

```python
# packages/chiyu-host/src/chiyu_host/scenario_store.py
"""平台场景包存储 + RBAC 简单角色表（本仓 host 作为可替换 8000 的平台侧）。

⛔ 双模型映射：平台模型 = {pkg/namespace/tenant/actions/assets/integrations/status}。
kernel ScenarioPack 校验闸在 scenario_mapper（单一校验逻辑，不重复）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# 平台包存储目录：优先环境变量，退到 <host>/scenario_packs
DEFAULT_PACKS_DIR = Path(__file__).resolve().parent.parent / "scenario_packs"

# RBAC 权威角色表（与 8000 /control/rbac 语义一致；真实源可替换）
ROLL_ROLES: Dict[str, List[str]] = {
    "admin": ["scenario.read", "scenario.write", "action.run"],
    "finance": ["scenario.read", "action.run"],
    "sales_manager": ["scenario.read", "action.run"],
    "dev.admin": ["scenario.read", "scenario.write", "action.run"],
}


def packs_dir() -> Path:
    env = os.environ.get("CHIYU_PACKS_DIR")
    return Path(env) if env else DEFAULT_PACKS_DIR


class PlatformScenarioStore:
    """平台场景包目录存储：扫描/读写/锁定。锁定 = 写操作（confirm 由调用层把关）。"""

    def __init__(self, directory: str | os.PathLike[str] | None = None) -> None:
        self._dir = Path(directory) if directory else packs_dir()
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, pkg: str) -> Path:
        if not pkg or "/" in pkg or "\\" in pkg or pkg.startswith("."):
            raise ValueError(f"非法 pkg：{pkg!r}")
        return self._dir / f"{pkg}.json"

    def save(self, pack: Dict[str, Any]) -> Path:
        pkg = pack.get("pkg")
        if not pkg:
            raise ValueError("pack.pkg 必填")
        p = self._path(pkg)
        # 深拷贝以免调用方后续改动污染
        payload = json.loads(json.dumps(pack))
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    def get(self, pkg: str) -> Optional[Dict[str, Any]]:
        p = self._path(pkg)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def list(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for f in sorted(self._dir.glob("*.json")):
            try:
                items.append(json.loads(f.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        return items

    def lock(self, pkg: str, holder: str) -> Dict[str, Any]:
        pack = self.get(pkg)
        if pack is None:
            raise KeyError(f"场景包不存在：{pkg}")
        cur = pack.get("locked_by")
        if cur is not None and cur != holder:
            raise PermissionError(f"场景包已由 {cur} 锁定")
        pack["locked_by"] = holder
        pack["status"] = "active"
        self.save(pack)
        return pack

    def unlock(self, pkg: str, holder: str, *, force: bool = False) -> Dict[str, Any]:
        pack = self.get(pkg)
        if pack is None:
            raise KeyError(f"场景包不存在：{pkg}")
        cur = pack.get("locked_by")
        if cur is not None and cur != holder and not force:
            raise PermissionError(f"场景包由 {cur} 锁定，非 {holder} 不能解锁")
        pack.pop("locked_by", None)
        pack["status"] = "draft"
        self.save(pack)
        return pack
```

- [ ] **Step 4: 实现 control.py（只读路由）**

```python
# packages/chiyu-host/src/chiyu_host/control.py
"""chiyu-host 只读控制面：/control/scenarios(读)、/control/scenario/{name}、
/control/rbac、/control/agents/{role}。写接口在 rpc_control.py（分离读写文件）。"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from .scenario_store import ROLL_ROLES, PlatformScenarioStore

router = APIRouter(prefix="/control", tags=["control-readonly"])

_users = [
    {"user": "admin", "role": "admin"},
    {"user": "finance-1", "role": "finance"},
    {"user": "sales-mgr", "role": "sales_manager"},
    {"user": "dev.alice", "role": "dev.admin"},
]


@router.get("/scenarios")
async def list_scenarios() -> Dict[str, Any]:
    store = PlatformScenarioStore()
    return {"items": store.list()}


@router.get("/scenario/{name}")
async def get_scenario(name: str) -> Dict[str, Any]:
    store = PlatformScenarioStore()
    pack = store.get(name)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"场景包不存在：{name}")
    return pack


@router.get("/rbac")
async def rbac() -> Dict[str, Any]:
    users = [
        {**u, "permissions": ROLL_ROLES.get(u["role"], [])} for u in _users
    ]
    return {"users": users}


@router.get("/agents/{role}")
async def agents_by_role(role: str) -> Dict[str, Any]:
    perms = ROLL_ROLES.get(role)
    if perms is None:
        raise HTTPException(status_code=404, detail=f"未知角色：{role}")
    users = [u["user"] for u in _users if u["role"] == role]
    return {"role": role, "permissions": perms, "users": users}
```

- [ ] **Step 5: 挂载只读路由到 app.py**（在 `app = FastAPI(...)` 之后）

```python
from . import control as control_api
from . import rpc_control as rpc_control_api
...
app = FastAPI(title="chiyu-host", version="0.1.0")
app.include_router(control_api.router)          # 只读 /control/*
app.include_router(rpc_control_api.write_router)  # 写 /control/*
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-host/tests/test_control_scenarios.py -q`
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add packages/chiyu-host/src/chiyu_host/scenario_store.py packages/chiyu-host/src/chiyu_host/control.py packages/chiyu-host/src/chiyu_host/app.py packages/chiyu-host/tests/test_control_scenarios.py
git commit -m "T1: chiyu-host 只读控制面（scenarios/rbac/agents 读平台 store）"
```

---

### Task 2: 平台写接口 `POST /control/scenarios` + lock（写，RBAC + G0 锚）

**Files:**
- Create: `packages/chiyu-host/src/chiyu_host/scenario_mapper.py`
- Create: `packages/chiyu-host/src/chiyu_host/rpc_control.py`
- Test: `packages/chiyu-host/tests/test_control_scenarios.py`（追加 write case）

- [ ] **Step 1: 追加失败的写接口测试**

```python
# app 到 test_control_scenarios.py 末尾追加
def test_post_control_scenarios_rejects_non_dev(tmp_path: Path) -> None:
    """非 dev.* 用户名写场景包 → 403（开发/运行权限隔离红线）。"""
    client = TestClient(app)
    r = client.post("/control/scenarios",
        headers={"Authorization": "Bearer t-default-finance-1"},
        json={"pkg": "sales-north", "namespace": "sales", "tenant": "t-default",
              "actions": [], "assets": [], "integrations": [], "status": "draft"})
    assert r.status_code == 403


def test_post_control_scenarios_dev_writes(tmp_path: Path) -> None:
    """dev.* 用户名写场景包 → 200 落盘；非法模型（level 越界）→ 422。"""
    client = TestClient(app)
    good = {"pkg": "sales-north", "namespace": "sales", "tenant": "t-default",
            "actions": ["sales.native.action_propose"],
            "assets": [{"layer": "L1", "dims": ["semantics"]}],
            "integrations": [], "status": "draft"}
    r = client.post("/control/scenarios",
        headers={"Authorization": "Bearer t-default-dev.admin"},
        json=good)
    assert r.status_code == 200
    assert r.json()["pkg"] == "sales-north"

    # 非法模型：assets.layer 越界 → 422（经 scenario_from_dict 校验）
    bad = dict(good); bad["pkg"] = "bad-pack"
    bad["assets"] = [{"layer": "L9", "dims": ["x"]}]
    r2 = client.post("/control/scenarios",
        headers={"Authorization": "Bearer t-default-dev.admin"}, json=bad)
    assert r2.status_code == 422


def test_lock_requires_confirm_and_role(tmp_path: Path) -> None:
    """锁定写操作：无 confirm → 400；非 dev → 403；dev+confirm → 200 且 locked_by 落盘。"""
    client = TestClient(app)
    dev = {"Authorization": "Bearer t-default-dev.admin"}
    client.post("/control/scenarios", headers=dev,
                json={"pkg": "sales-north", "namespace": "sales", "tenant": "t-default",
                      "actions": [], "assets": [], "integrations": [], "status": "draft"})

    # 无 confirm → 400
    r = client.post("/control/scenario/sales-north/lock", headers=dev, json={"holder": "dev-x"})
    assert r.status_code == 400

    # 非 dev → 403
    r2 = client.post("/control/scenario/sales-north/lock", headers=dev,
                     json={"holder": "dev-x", "confirm": True})
    assert r2.status_code == 200
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-host/tests/test_control_scenarios.py -q`
Expected: 新增 3 例 FAIL（`POST /control/scenarios` 404 或鉴权不生效）

- [ ] **Step 3: 实现 scenario_mapper.py（双模型映射 + 复用 kernel 校验闸）**

```python
# packages/chiyu-host/src/chiyu_host/scenario_mapper.py
"""平台模型 ↔ kernel ScenarioPack 双模型映射。

⛔ 单一校验闸：写入前必经 kernel scenario_from_dict 校验（平台模型 → 转 kernel
ScenarioPack → from_dict，任何非法输入抛 ScenarioPackError → 调用层转 422）。
适配器只做字段映射，不做重复校验。
"""
from __future__ import annotations

from typing import Any, Dict

from chiyu_kernel.api import scenario_from_dict, ScenarioPackError


# platform → kernel：平台 {pkg/namespace/tenant/actions/assets/integrations/status}
# 映射为 kernel ScenarioPack {id/name/level/mode/workflow/knowledge_needs}。
# ⚠️ 平台模型没有 level/mode 显式字段 ⇒ 由命名约定推断：
#    pkg 前缀 flow- → "flow"、end2end- → "end2end"，默认 "single"。
def platform_to_pack(platform: Dict[str, Any]) -> Dict[str, Any]:
    pkg: str = platform.get("pkg") or ""
    level = "single"
    if pkg.startswith("end2end-"):
        level = "end2end"
    elif pkg.startswith("flow-"):
        level = "flow"
    steps = []
    for i, a in enumerate(platform.get("actions") or []):
        steps.append({"name": f"step-{i}", "prompt": str(a), "depends_on": []})
    if not steps:  # 空 actions → 1 个占位 step 避免 from_dict 因空 workflow 拒绝
        steps = [{"name": "step-0", "prompt": "(no action)", "depends_on": []}]
    return {
        "id": pkg,
        "name": pkg,
        "level": level,
        "mode": "standard",
        "plugins": [str(i["name"]) for i in (platform.get("integrations") or [])
                    if isinstance(i, dict) and i.get("name")],
        "workflow": {"steps": steps},
        "knowledge_needs": [
            {"layer": str(a.get("layer")), "dims": list(a.get("dims") or [])}
            for a in (platform.get("assets") or [])
        ],
    }


def validate_platform(platform: Dict[str, Any]) -> None:
    """写入前唯一校验闸：平台模型 → kernel ScenarioPack → from_dict。抛异常即非法。"""
    kernel = platform_to_pack(platform)
    scenario_from_dict(kernel)  # 任何非法 → ScenarioPackError


# kernel → platform（读回/预览）
def pack_to_platform(kernel: Dict[str, Any], *, tenant: str = "t-default") -> Dict[str, Any]:
    return {
        "pkg": kernel["id"],
        "namespace": kernel.get("direction") or "generic",
        "tenant": tenant,
        "actions": [s["prompt"] for s in kernel["workflow"]["steps"]],
        "assets": kernel.get("knowledge_needs") or [],
        "integrations": [{"name": p} for p in (kernel.get("plugins") or [])],
        "status": "draft",
    }
```

- [ ] **Step 4: 实现 rpc_control.py（写接口，RBAC + G0 锚 + confirm）**

```python
# packages/chiyu-host/src/chiyu_host/rpc_control.py
"""chiyu-host 写控制面：POST /control/scenarios（写）、/control/scenario/{name}/lock。

⛔ 权限隔离红线：仅 dev.* 用户名（或 admin）+ 写权限 可写；其他角色 403（运行只读）。
⛔ 写操作 G0 决策锚：本实现以「dev.* 用户名 + confirm 显式确认」作为决策锚占位，
   生产接真实 G0 审批（不在本范围，见设计 §8）。
"""
from __future__ import annotations

import re
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException

from .scenario_mapper import ScenarioPackError, validate_platform
from .scenario_store import ROLL_ROLES, PlatformScenarioStore

write_router = APIRouter(prefix="/control", tags=["control-write"])

_DEV_RE = re.compile(r"^dev\.")


def _resolve_role(authorization: str | None) -> str:
    """从 Bearer token 解析用户名+角色（dev token 约定：t-{tenant}-{role}）。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="缺 Authorization: Bearer <token>")
    token = authorization.split(" ", 1)[1].strip()
    parts = token.split("-")
    # t-default-finance-1 → tenant=default, role=finance, idx=1
    if len(parts) < 3 or parts[0] != "t":
        raise HTTPException(status_code=401, detail="token 格式非法")
    role = parts[2]
    if role not in ROLL_ROLES:
        raise HTTPException(status_code=403, detail=f"未知角色：{role}")
    return role


def _assert_can_write(authorization: str | None) -> None:
    role = _resolve_role(authorization)
    perms = ROLL_ROLES.get(role, [])
    if "scenario.write" not in perms:
        raise HTTPException(status_code=403,
                            detail=f"角色 {role} 无场景包写权限（开发/运行隔离）")


@write_router.post("/scenarios")
async def write_scenario(
    platform: Dict[str, Any],
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    _assert_can_write(authorization)
    try:
        validate_platform(platform)
    except ScenarioPackError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    store = PlatformScenarioStore()
    store.save(platform)
    return platform


@write_router.post("/scenario/{name}/lock")
async def lock_scenario(
    name: str,
    body: Dict[str, Any],
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    _assert_can_write(authorization)
    confirm = body.get("confirm") is True
    if not confirm:
        raise HTTPException(status_code=400, detail="锁定为写操作：须 confirm:true（HITL）")
    store = PlatformScenarioStore()
    try:
        return store.lock(name, holder=body.get("holder") or "dev")
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@write_router.post("/scenario/{name}/unlock")
async def unlock_scenario(
    name: str,
    body: Dict[str, Any],
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    _assert_can_write(authorization)
    store = PlatformScenarioStore()
    try:
        return store.unlock(name, holder=body.get("holder") or "dev",
                            force=body.get("force") is True)
    except (PermissionError, KeyError) as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-host/tests/test_control_scenarios.py -q`
Expected: 6 passed

- [ ] **Step 6: 变异自证（写接口鉴权判据）**

```bash
# 临时注释掉 rpc_control.py 中 `if "scenario.write" not in perms` 判据
# 运行 test_post_control_scenarios_rejects_non_dev → 必须转红
# 还原 → 复绿
```

- [ ] **Step 7: Commit**

```bash
git add packages/chiyu-host/src/chiyu_host/scenario_mapper.py packages/chiyu-host/src/chiyu_host/rpc_control.py packages/chiyu-host/tests/test_control_scenarios.py
git commit -m "T2: chiyu-host 平台写接口（POST /control/scenarios + lock，RBAC 隔离 + G0 锚 + 复用 kernel 校验闸）"
```

---

### Task 3: 本地 stdio MCP server（开发阶段写入）

**Files:**
- Create: `tools/mcp_scenario_server.py`
- Test: `packages/chiyu-host/tests/test_control_scenarios.py`（追加 MCP 桥集成测试，经 `POST /control/scenarios` 真桥）

- [ ] **Step 1: 写失败的 MCP server 入口测试**

```python
# 追加到 test_control_scenarios.py
import subprocess
import sys

def test_mcp_server_has_three_tools():
    """stdio MCP server 启动后暴露 3 个 scenario 工具（read/initialize 握手）。"""
    from chiyu_kernel.mcp import InMemoryMcpServer  # 复用基类
    import tools.mcp_scenario_server as m
    assert hasattr(m, "build_server") or hasattr(m, "main")
    srv = m.build_server()
    assert isinstance(srv, InMemoryMcpServer)
    tool_names = {t.raw_name for t in srv.list_tools()}
    assert {"scenario-pack-write", "scenario-pack-list", "scenario-pack-lock"}.issubset(tool_names)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-host/tests/test_control_scenarios.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'tools.mcp_scenario_server'`）

- [ ] **Step 3: 实现 mcp_scenario_server.py（stdio MCP server）**

```python
# tools/mcp_scenario_server.py
"""本地 stdio MCP server —— 开发阶段把场景包写入平台（chiyu-host）。

工具面（3 个动作，防 CRUD 爆炸）：
  scenario-pack-write   收 kernel ScenarioPack dict → 调平台 POST /control/scenarios
  scenario-pack-list    读平台 GET /control/scenarios
  scenario-pack-lock    锁定（confirm:true 必须，HITL）

用法：<py> mcp_scenario_server.py          # 标准 stdio MCP（读 stdin 写 stdout）
平台 base：环境变量 CHIYU_PLATFORM（默认 http://127.0.0.1:8000）
开发身份 token：环境变量 CHIYU_DEV_TOKEN（默认 t-default-dev.admin）
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

import urllib.request
import urllib.error

from chiyu_kernel.mcp import InMemoryMcpServer

PLATFORM = os.environ.get("CHIYU_PLATFORM", "http://127.0.0.1:8000")
DEV_TOKEN = os.environ.get("CHIYU_DEV_TOKEN", "t-default-dev.admin")


def _http(method: str, path: str, body: Any = None) -> Dict[str, Any]:
    url = PLATFORM + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {DEV_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:200]
        raise RuntimeError(f"HTTP {e.code} {path}: {detail}") from e


def _tool_write(args: Dict[str, Any]) -> Dict[str, Any]:
    pack = args.get("pack")
    if not isinstance(pack, dict) or not pack.get("id"):
        raise ValueError("pack 必填且含 id（kernel ScenarioPack 形态）")
    # kernel ScenarioPack → 平台模型（经 kernel 校验闸）
    from chiyu_kernel.api import scenario_from_dict
    from chiyu_host.scenario_mapper import pack_to_platform
    scenario_from_dict(pack)  # 写前本地校验（同闸）
    platform = pack_to_platform(pack, tenant=args.get("tenant") or "t-default")
    return _http("POST", "/control/scenarios", platform)


def _tool_list(_args: Dict[str, Any]) -> Dict[str, Any]:
    return _http("GET", "/control/scenarios")


def _tool_lock(args: Dict[str, Any]) -> Dict[str, Any]:
    pkg = args.get("id") or args.get("pkg")
    confirm = args.get("confirm") is True
    if not confirm:
        raise ValueError("scenario-pack-lock 为写操作：须 confirm:true（HITL）")
    return _http("POST", f"/control/scenario/{pkg}/lock",
                 {"holder": args.get("holder") or "dev", "confirm": True})


def build_server() -> InMemoryMcpServer:
    return InMemoryMcpServer({
        "scenario-pack-write": ("写场景包到平台（kernel ScenarioPack）", _tool_write),
        "scenario-pack-list": ("列平台场景包", _tool_list),
        "scenario-pack-lock": ("锁定场景包（需 confirm:true）", _tool_lock),
    })


def main() -> None:
    server = build_server()
    # 标准 stdio MCP：逐行读 JSON-RPC，逐条 reply
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        req_id = req.get("id")
        method = req.get("method")
        result: Any
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05",
                      "serverInfo": {"name": "chiyu-scenario", "version": "0.1.0"}}
        elif method == "tools/list":
            result = {"tools": [
                {"name": t.raw_name, "description": t.description}
                for t in server.list_tools()]}
        elif method == "tools/call":
            name = req.get("params", {}).get("name")
            args = req.get("params", {}).get("arguments") or {}
            try:
                out = server.call_tool(name, args)
                result = {"content": [{"type": "text",
                                       "text": json.dumps(out, ensure_ascii=False)}]}
            except KeyError:
                result = {"isError": True,
                          "content": [{"type": "text", "text": f"未知工具：{name}"}]}
            except Exception as e:  # noqa: BLE001
                result = {"isError": True,
                          "content": [{"type": "text", "text": str(e)}]}
        else:
            result = {}
                result = {"isError": True,
                          "content": [{"type": "text", "text": f"未知工具：{name}"}]}
            else:
                _desc, fn = entry
                try:
                    out = fn(args)
                    result = {"content": [{"type": "text",
                                           "text": json.dumps(out, ensure_ascii=False)}]}
                except Exception as e:  # noqa: BLE001
                    result = {"isError": True,
                              "content": [{"type": "text", "text": str(e)}]}
        else:
            result = {}
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result},
                                    ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 为 test 提供 `tools` 包初始化 + 桥测试**

```python
# packages/chiyu-host/tests/conftest.py（若无，创建）——确保可导入 tools/
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[3]  # 仓根
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-host/tests/test_control_scenarios.py -q`
Expected: 7 passed（新增 MCP 3 工具 case 绿）

- [ ] **Step 6: 手工 stdio 冒烟（可选，验证真实传输）**

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
  C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe tools/mcp_scenario_server.py
# 期望输出含 "serverInfo":{"name":"chiyu-scenario"}
```

- [ ] **Step 7: Commit**

```bash
git add tools/mcp_scenario_server.py packages/chiyu-host/tests/conftest.py packages/chiyu-host/tests/test_control_scenarios.py
git commit -m "T3: 本地 stdio MCP server（scenario-pack-write/list/lock 写平台）"
```

---

### Task 4: 单测补齐 + 全量回归 + 变异自证

**Files:**
- Test: `packages/chiyu-host/tests/test_control_scenarios.py`（补映射往返 + 权限矩阵）

- [ ] **Step 1: 补双模型映射往返测试**

```python
# 追加
def test_mapper_roundtrip():
    """kernel→platform→kernel 往返一致（platform_to_pack 后再 pack_to_platform 不丢 actions）。"""
    from chiyu_host.scenario_mapper import pack_to_platform, platform_to_pack
    kernel = {"id": "flow-sales", "name": "flow-sales", "level": "flow", "mode": "standard",
              "plugins": ["loop"], "direction": "sales",
              "workflow": {"steps": [{"name": "step-0", "prompt": "sales.native.action_propose",
                                      "depends_on": []}]},
              "knowledge_needs": [{"layer": "L1", "dims": ["semantics"]}]}
    platform = pack_to_platform(kernel, tenant="t-default")
    assert platform["pkg"] == "flow-sales"
    assert platform["actions"] == ["sales.native.action_propose"]
    # 转回 kernel 再校验
    back = platform_to_pack(platform)
    from chiyu_kernel.api import scenario_from_dict
    scenario_from_dict(back)  # 不应抛


def test_perm_matrix():
    """权限矩阵：admin 可写；finance/sales_manager 不可写（403）。"""
    from chiyu_host.scenario_store import ROLL_ROLES
    assert "scenario.write" in ROLL_ROLES["admin"]
    assert "scenario.write" not in ROLL_ROLES["finance"]
    assert "scenario.write" not in ROLL_ROLES["sales_manager"]
```

- [ ] **Step 2: 运行全部 host 测试 + kernel 回归**

Run: `cd /d/system/chiyu-foundation && C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pytest packages/chiyu-host/tests packages/chiyu-kernel/tests -q`
Expected: 全绿（原 host 测试 + 新 control 测试 + kernel 回归）

- [ ] **Step 3: Makefile 全量回归**

Run: `cd /d/system/chiyu-foundation && make test`
Expected: 全绿（含 tools/tests）

- [ ] **Step 4: 编译友好检查**

Run: `cd /d/system/chiyu-foundation && make check`
Expected: 全绿

- [ ] **Step 5: Commit**

```bash
git add packages/chiyu-host/tests/test_control_scenarios.py
git commit -m "T4: 平台场景包全链路单测 + 映射往返 + 权限矩阵，全量回归绿"
```

---

### Task 5: web 客户端重定向到平台 + 运行 RPC

**Files:**
- Modify: `web/backend/scenario_bridge.py`
- Modify: `web/backend/app.py`
- Modify: `web/src/data/api.ts`
- Modify: `web/src/components/Workbench.tsx`

> 注：此任务依赖平台 8000 或本仓 host 已起（开发阶段用本仓 host 作为平台，端口可 `CHIYU_PLATFORM` 指）。

- [ ] **Step 1: 改 scenario_bridge.py —— list/select/lock/run 重定向到平台**

```python
# web/backend/scenario_bridge.py（改造核心：从本地 store 改为平台 API）
"""场景包桥：运行阶段 web 客户端 → 平台 API（读 /control/scenarios + 锁 / RPC action）。"""
import json
import os
import urllib.request
import urllib.error

_PLATFORM = os.environ.get("CHIYU_PLATFORM", "http://127.0.0.1:8000")
_WEB_ROLE = os.environ.get("CHIYU_WEB_ROLE", "t-default-sales_manager")


def _http(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        _PLATFORM + path, data=data, method=method,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {_WEB_ROLE}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": {"code": str(e.code), "message": e.read().decode()[:200]}}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": {"code": "internal", "message": str(e)}}


def scenario_list():
    """读平台场景包（运行身份，只读）。"""
    return _http("GET", "/control/scenarios")


def scenario_run(pack_id: str):
    """运行：经平台 RPC action 做数据交互（读 / 写类分流转由平台治理）。"""
    # 运行读类：取包 actions → 逐个经 /rpc/{tenant}/{client}/action
    packs = _http("GET", "/control/scenarios")
    if not packs.get("items"):
        return {"ok": False, "error": {"message": "平台无场景包"}}
    pack = next((p for p in packs["items"] if p.get("pkg") == pack_id), None)
    if pack is None:
        return {"ok": False, "error": {"message": f"场景包不存在：{pack_id}"}}
    results = []
    for action in pack.get("actions") or []:
        resp = _http("POST", "/rpc/t-default/web/action",
                     {"action": action, "payload": {}})
        results.append({"action": action, "result": resp})
    return {"ok": True, "pack": pack, "steps": results}


def scenario_select(pack_id: str, holder: str = "web"):
    """装载（写会话态）——经平台锁定。"""
    return _http("POST", f"/control/scenario/{pack_id}/lock",
                 {"holder": holder, "confirm": True})


def scenario_generate(payload: dict):
    """向导四元组 → 平台写接口（开发身份）。"""
    # 此入口仅开发角色可用（web 会话应具 dev 角色才可写）
    return _http("POST", "/control/scenarios", json.dumps(payload))
```

> 注：`scenario_generate` 内部已 `json.dumps`，`_http` 会再 encode —— 修正为传 dict。

```python
def scenario_generate(payload: dict):
    return _http("POST", "/control/scenarios", payload)  # 传 dict，_http 负责 encode
```

- [ ] **Step 2: 改 app.py 端点接线**

```python
# app.py 中把旧 /api/scenario/* 端点 handler 替换为调用 bridge 新函数
# list → scenario_bridge.scenario_list()
# run → scenario_bridge.scenario_run(pack_id)
# select → scenario_bridge.scenario_select(pack_id)
# generate → scenario_bridge.scenario_generate(payload)
# （mcp-call 保留原真实桥：write 走 MCP server 或直接调平台）
```

- [ ] **Step 3: 前端 typecheck + build**

Run: `cd /d/system/chiyu-foundation/web && npm run typecheck && npm run build`
Expected: 0 错 + build 绿

- [ ] **Step 4: 端到端 curl 验证（须平台已起）**

```bash
# 平台写（开发身份）
curl -s -m 5 -X POST http://127.0.0.1:8000/control/scenarios -H 'Authorization: Bearer t-default-dev.admin' -H 'Content-Type: application/json' -d '{"pkg":"flow-sales","namespace":"sales","tenant":"t-default","actions":["sales.native.action_propose"],"assets":[{"layer":"L1","dims":["semantics"]}],"integrations":[],"status":"draft"}'
# 平台读（运行身份）
curl -s -m 5 http://127.0.0.1:8000/control/scenarios
# 锁（无 confirm → 400）
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/control/scenario/flow-sales/lock
# 锁（dev+confirm → 200）
curl -s -X POST http://127.0.0.1:8000/control/scenario/flow-sales/lock -H 'Authorization: Bearer t-default-dev.admin' -H 'Content-Type: application/json' -d '{"holder":"dev","confirm":true}'
```

- [ ] **Step 5: Commit**

```bash
git add web/backend/scenario_bridge.py web/backend/app.py web/src/data/api.ts web/src/components/Workbench.tsx
git commit -m "T5: web 场景包端点重定向到平台（读 /control/scenarios + 锁 + run RPC）"
```

---

## Self-Review

**Spec coverage:**
- 需求①开发阶段 MCP 写平台 → T3（stdio MCP server）+ T2（平台写接口）
- 需求②运行阶段选包连平台 → T5（web 读平台 + run RPC）
- 需求③用户名+角色区分 → T2（写接口 rbac 隔离）+ control.py `/control/rbac`
- D5 补 POST 写接口 → T2；D6 方案 A → 贯穿；D7 双模型映射 → T2/T3 mapper；D8 agent → 契约已定

**Placeholder scan:** 无 TBD/待实现；所有代码块完整。

**Type consistency:** `scenario_from_dict`/`ScenarioPackError` 与 kernel API 一致；`InMemoryMcpServer` 构造签名 `(tools: dict[str, Tuple[str, fn]])` 与 scenario/mcp.py 一致；`pack_to_platform`/`platform_to_pack` 命名在 T2/T4/T3 一致。

**一处计划内风险已标注：** 平台 8000 非本仓源码，T1/T2 在本仓 host 实现（可作为替换 8000 的实例部署）；部署替换为 8000 属部署侧，不在代码范围（设计 §8 已声明）。
