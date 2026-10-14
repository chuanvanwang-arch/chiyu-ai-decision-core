# 客户端—企业平台集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 DSH 前端客户端的协议接入企业平台唯一入口（`:8000`），复用其零信任治理，打通"客户端—企业平台"最小闭环。

**Architecture:** 以企业 host 为唯一后端；把本仓 `chiyu-host` 的 DSH 协议实现作为适配层（adapter）迁入企业 host，与企业 Action 路由共用同一治理中间件（token 认租户、读/写分流、写类两阶段 confirm、写闸 G0–G3）；补 action 执行体使写类 Action 真执行；以 headless 契约验证先行（绕过 DSH 构建受阻）。

**Tech Stack:** Python 3.13 / FastAPI / pytest（企业仓 `chiyu-enterprise`）；复用 `chiyu_kernel` 子模块（内存态，不连 pg）；本仓 `chiyu-host` 已验证的 handler/bridge 代码直接迁入。

---

## File Structure

**T1（chiyu-enterprise 仓）— 抽治理中间件**
- Create: `packages/enterprise/src/enterprise/host/governance.py`
- Modify: `packages/enterprise/src/enterprise/host/app.py`（改 import，逻辑不变）
- Test:   `tests/test_host_governance.py`

**T2（chiyu-enterprise 仓）— 迁入 DSH 适配层**
- Create: `packages/enterprise/src/enterprise/host/dsh_adapter/__init__.py`
- Create: `packages/enterprise/src/enterprise/host/dsh_adapter/methods.py`（迁入本仓 `chiyu-host/methods.py`）
- Create: `packages/enterprise/src/enterprise/host/dsh_adapter/bridge.py`（迁入本仓 `chiyu-host/bridge.py`）
- Modify: `packages/enterprise/src/enterprise/host/app.py`（新增 `POST /api/<method>` + `WS /api/events.mux`）
- Test:   `tests/test_dsh_adapter_schema.py`（含变异自证）

**T3（chiyu-enterprise 仓）— 补 Action executor**
- Create: `packages/enterprise/src/enterprise/action/executor.py`
- Modify: `packages/enterprise/src/enterprise/host/app.py`（`rpc_action` 写类 confirm 后调 executor）
- Test:   `tests/test_action_executor.py`

**T4（chiyu-enterprise 仓）— headless 契约验证**
- Create: `tests/test_headless_integration.py`（绕过 DSH 构建，直接打企业 host RPC/SSE/WS）

> 依赖前提（T2 第一步验证）：企业仓 `chiyu_kernel` 须可导入 `session/skills/plugins/events/llm.client/tools/orchestration.subagent/agent_loop/agent_runtime/context/harness_native_tools`——本仓 `chiyu-host` 已实测这些子模块不触发 pg 依赖。

---

## Task 1: 抽治理中间件（governance.py）

**Files:**
- Create: `packages/enterprise/src/enterprise/host/governance.py`
- Modify: `packages/enterprise/src/enterprise/host/app.py`
- Test:   `tests/test_host_governance.py`

- [ ] **Step 1: 写失败测试（验证治理中间件可被独立调用，且与企业 action 路由行为一致）**

```python
# tests/test_host_governance.py
from enterprise.host import governance as G


def test_auth_ctx_rejects_missing_token():
    ctx, schema, role, err = G.auth_ctx("", "t1")
    assert err == "missing_token" and ctx is None


def test_auth_ctx_rejects_invalid_token():
    ctx, schema, role, err = G.auth_ctx("Bearer not-a-real-token", "t1")
    assert err == "invalid_token"


def test_is_write_action_via_guard_mutating():
    # sales.native.* 中标记为 mutating 的动作应判为写类
    assert G.is_write_action("sales.integration.erp.sync_order") is True
    # session.list 等读类后缀/非 mutating → False
    assert G.is_write_action("session.list") is False


def test_run_write_gates_passes_zero_constraint_by_default():
    # 未注册场景包时默认零约束 → 放行
    res = G.run_write_gates("unknown.action.x", {"foo": 1}, "tenant-x", "admin")
    assert res.ok is True
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd D:/system/chiyu-enterprise && python -m pytest tests/test_host_governance.py -q`
Expected: FAIL（`enterprise.host.governance` 不存在）

- [ ] **Step 3: 抽取 governance.py（从 app.py 提取，逻辑逐字保留）**

```python
# packages/enterprise/src/enterprise/host/governance.py
"""治理中间件（从 host/app.py 抽取，供 DSH 适配层与企业 Action 路由共用）。

⛔ 守分层：只 import chiyu_kernel.api / chiyu_kernel.contract + 本包 auth/confirm/action.guard。
"""
from __future__ import annotations

import itertools
from typing import Optional, Tuple

from enterprise.action.guard import GateEnv, GuardSpec, check_write_gates
from enterprise.host.auth import (
    parse_bearer_token,
    resolve_role_from_token,
    resolve_tenant_from_token,
)
from enterprise.host.confirm import ConfirmSessionStore, merge_phase2_params
from enterprise.scenario import loader as scenario_loader

# 写动词后缀 fallback（guard.mutating 优先）
_WRITE_SUFFIXES = ("request_quote", "submit", "update", "create", "delete",
                   "approve", "reject", "sync", "advance", "write")

_confirms = ConfirmSessionStore()
_decision_seq = itertools.count(1)


def _default_guard_resolver(action: str) -> Optional[GuardSpec]:
    guard = scenario_loader.resolve_guard(action)
    return guard if guard is not None else GuardSpec()


guard_resolver = _default_guard_resolver
guard_resolver_entitlements = None


def is_write_action(action: str) -> bool:
    guard = guard_resolver(action)
    if guard is not None and guard.mutating:
        return True
    a = action.lower()
    return a.endswith(_WRITE_SUFFIXES)


def auth_ctx(authorization: str, tenant_id: str) -> Tuple[object, str, Optional[str], Optional[str]]:
    token = parse_bearer_token(authorization)
    if not token:
        return None, None, None, "missing_token"
    ctx = resolve_tenant_from_token(token)
    if ctx is None:
        return None, None, None, "invalid_token"
    role = resolve_role_from_token(token)
    return ctx, ctx.schema_name(), role, None


def _mint_decision(tenant_id: str, action: str) -> str:
    return f"d-{tenant_id}-{next(_decision_seq)}-{action.split('.')[-1]}"


def issue_confirm(action: str, payload: dict) -> str:
    return _confirms.issue(action, payload)


def consume_confirm(confirm_token: str, action: str, payload: dict):
    """返回 (merged_params, error_str)。merged=None 表示 confirm 失败。"""
    session = _confirms.get(confirm_token)
    if session is None:
        return None, "confirm_expired"
    if session.get("action") != action:
        return None, "confirm_action_mismatch"
    merged, conflict, _added = merge_phase2_params(session["params"], payload)
    if conflict is not None:
        return None, "confirm_params_conflict"
    if not _confirms.consume(confirm_token):
        return None, "confirm_expired"
    return merged, None


def run_write_gates(action: str, params: dict, tenant_schema: str,
                    actor_role) -> "GateEnv.__class__.__mro__[0] | object":
    _guard = guard_resolver(action)
    _env = GateEnv(
        actor_role=lambda: actor_role,
        resolve_entitlements=(guard_resolver_entitlements or (lambda tid: set())),
        trace=lambda kind, data: None,
    )
    return check_write_gates(
        guard=_guard, decision_id=params.get("decision_id"), params=params,
        tenant_id=tenant_schema, actor="system", channel="rpc",
        approval_passed=params.get("approval_passed") is True, env=_env,
    )


def mint_decision(tenant_id: str, action: str) -> str:
    return _mint_decision(tenant_id, action)


__all__ = [
    "is_write_action", "auth_ctx", "issue_confirm", "consume_confirm",
    "run_write_gates", "mint_decision", "guard_resolver", "guard_resolver_entitlements",
]
```

- [ ] **Step 4: 改写 app.py 改用 governance（逻辑不变，仅替换 import 与函数引用）**

把 `app.py` 顶部 `from enterprise.host.auth import ...` 等保留；删除本地的 `_WRITE_SUFFIXES` / `_default_guard_resolver` / `guard_resolver` / `guard_resolver_entitlements` / `_is_write_action` / `_auth_ctx` / `_mint_decision` / `_confirms` / `_decision_seq` 定义，改为：

```python
from enterprise.host import governance as G

# 保留模块级别名以最小化 diff
_confirms = G._confirms  # 仅测试 reset 用；或直接用 G.issue_confirm
guard_resolver = G.guard_resolver
guard_resolver_entitlements = G.guard_resolver_entitlements
```

并将 `rpc_action` / `rpc_events` 内的 `_auth_ctx(...)` → `G.auth_ctx(...)`、`_is_write_action(action)` → `G.is_write_action(action)`、`_mint_decision(...)` → `G.mint_decision(...)`。confirm 分支改用 `G.issue_confirm` / `G.consume_confirm`（保持返回结构一致）。

- [ ] **Step 5: 跑全量测试确认不破坏基线**

Run: `cd D:/system/chiyu-enterprise && python -m pytest tests/ -q`
Expected: PASS（既有的 host/routing/confirm/wiring 等约 106 测试全绿）；`tests/test_host_governance.py` 亦绿。

- [ ] **Step 6: Commit**

```bash
cd D:/system/chiyu-enterprise
git add packages/enterprise/src/enterprise/host/governance.py packages/enterprise/src/enterprise/host/app.py tests/test_host_governance.py
git commit -m "refactor(host): 抽取治理中间件 governance.py 供 DSH 适配层复用"
```

**成功标准（判定式）：** `pytest tests/ -q` 全绿（含 106 既有 + 新增 governance 4 项）；`app.py` 的 `rpc_action` 行为与原实现逐字节等价（既有 host 测试覆盖）。

> ### ✅ T1 执行记录（2026-09-26，inline execution）
> - 6 步全部完成：`governance.py` 抽取 + `app.py` 委托改写 + `tests/test_host_governance.py`（最终 6 项）。
> - **判定式达标但有 1 项遗留（非 T1 回归）**：全量 `315 passed / 1 failed / 4 skipped`。唯一红项 = `tests/test_consumes_facade_only.py::test_only_facade_imports`，因 `host/dsh_adapter/bridge.py`+`methods.py`（**T2 范围，mtime 12:32/12:36，非本会话所写**）import `chiyu_kernel.<internal>` 违 E1。该文件为并发会话预置的 T2 产物，不属 T1 回归，交由 T2 所有者修复（或将 chiyu_kernel 内部 import 改为经 `chiyu_kernel.api` 门面）。
> - **偏离计划之处（已追认）**：
>   1. 计划 Step5 预期「106 既有全绿」→ 实测基线非全绿；根因是 `confirm.py` 的 `PROTOCOL_KEYS` 含 `decision_id`，`merge_phase2_params` 把 phase2 的 `decision_id` 整体剥除 → `run_write_gates` 见 `decision_id=None` → G0 `decision_required` 永远触发（12 测试原本即红，属 confirm.py 既有缺陷，非抽取引入）。
>   2. 用户决策采用 **方案 C**：`run_write_gates` 增显式 `decision_id` 形参，`rpc_action` 从 raw phase2 payload 传 `decision_id=payload.get("decision_id")`（保留协议位不落 execParams 语义）。已实证：12 测试转绿。
>   3. 加项：8 个 `test_host_wiring_ext.py` 的 resolver 注入 patch 目标须从 `host_app.guard_resolver` 改为 `G.guard_resolver`（resolver 迁入 governance 后打错模块即写闸全放行）；已修正。
> - **git 环境**：企业仓 HEAD tree 损坏（`bad tree object HEAD`），`git stash/diff/show` 不可用；本会话仅改工作树，未 commit（commit 由用户在本地执行，遵循零 remote / 显式 add 纪律）。

---

## Task 2: 迁入 DSH 适配层（adapter）

**Files:**
- Create: `packages/enterprise/src/enterprise/host/dsh_adapter/__init__.py`
- Create: `packages/enterprise/src/enterprise/host/dsh_adapter/methods.py`
- Create: `packages/enterprise/src/enterprise/host/dsh_adapter/bridge.py`
- Modify: `packages/enterprise/src/enterprise/host/app.py`
- Test:   `tests/test_dsh_adapter_schema.py`

- [ ] **Step 1: 验证企业仓可导入 chiyu_kernel 所需子模块（信任但验证，避免假绿）**

```python
# tests/test_dsh_adapter_schema.py （前置 sanity）
def test_chiyu_kernel_submodules_importable_in_enterprise():
    import chiyu_kernel.session, chiyu_kernel.skills, chiyu_kernel.plugins
    import chiyu_kernel.events, chiyu_kernel.llm.client, chiyu_kernel.tools
    import chiyu_kernel.orchestration.subagent, chiyu_kernel.orchestration.agent_loop
    import chiyu_kernel.orchestration.agent_runtime, chiyu_kernel.context
    from chiyu_kernel.harness_native_tools import register_native_tools, native_redline_guard
    assert register_native_tools and native_redline_guard
```

Run: `cd D:/system/chiyu-enterprise && python -m pytest tests/test_dsh_adapter_schema.py::test_chiyu_kernel_submodules_importable_in_enterprise -q`
Expected: PASS。若 `harness_native_tools` 缺失，改用 `chiyu_kernel.tools.ToolRegistry` + 中性 redline guard 等价入口（见 Task 2 注释），先在此步定位并修正。

- [ ] **Step 2: 复制 bridge.py（线格式映射，逐字迁入）**

将 `D:\system\chiyu-foundation\packages\chiyu-host\src\chiyu_host\bridge.py` 复制到 `packages/enterprise/src/enterprise/host/dsh_adapter/bridge.py`，顶部加模块 doc「迁入自 chiyu-host，供企业 host 适配层复用」。内容不变（`to_wire_session_event` / `build_mux_frame` / `MuxBroadcaster` 已在原仓验证）。

- [ ] **Step 3: 复制 methods.py（29 handler，逐字迁入 + 包内 import 改前缀）**

将 `D:\system\chiyu-foundation\packages\chiyu-host\src\chiyu_host\methods.py` 复制到 `packages/enterprise/src/enterprise/host/dsh_adapter/methods.py`，唯一改动：把 `from .bridge import ...` 改为 `from enterprise.host.dsh_adapter.bridge import to_wire_session_event, MuxBroadcaster`。其余（29 个 HANDLERS、`_session_manager` / `_mux` 单例、`session_prompt` 真调 LLM、goal/subagent 等）保持不变。

- [ ] **Step 4: 写失败测试（adapter 经治理后返回 ServerResponse 全形，字段对齐 DSH schema）**

```python
# tests/test_dsh_adapter_schema.py
from fastapi.testclient import TestClient
from enterprise.host.app import app
import enterprise.host.dsh_adapter.methods as m


def _post(method, payload=None, auth=""):
    c = TestClient(app)
    body = {"type": "client-request", "rpcId": "r1", "method": method, "payload": payload or {}}
    return c.post(f"/api/{method}", json=body, headers={"Authorization": auth})


def _dev_auth():
    # 本仓 dev token 形态（含 tenant+role）；若企业 auth 解析器不同，在此补 fixture
    return "Bearer t-default-desktop-dev"


def test_session_list_shape_and_fields():
    m._session_index["s1"] = m._session_manager.get_or_create("s1")
    r = _post("session.list", {}, _dev_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "server-response" and body["rpcId"] == "r1"
    assert body["result"]["ok"] is True
    items = body["result"]["value"]["items"]
    assert set(["sessionId", "updatedAt", "running", "blank"]).issubset(items[0].keys())


def test_llm_models_static_deepseek():
    r = _post("llm.models", {}, _dev_auth())
    groups = r.json()["result"]["value"]["groups"]
    assert groups[0]["id"] == "deepseek" and groups[0]["models"][0]["id"] == "deepseek-v4-flash"


def test_skill_list_ok():
    assert _post("skill.list", {}, _dev_auth()).json()["result"]["ok"] is True


def test_unknown_method_error():
    r = _post("no.such.method", {}, _dev_auth())
    assert r.json()["result"]["ok"] is False
    assert r.json()["result"]["error"]["code"] == "bad-request"
```

- [ ] **Step 5: 在 app.py 新增 `/api/<method>` + `WS /api/events.mux`（复用 governance 鉴权）**

在 `app.py` 末尾追加（保留既有 `/rpc/...` 路由）：

```python
from enterprise.host import governance as G
from enterprise.host.dsh_adapter import methods as dsh_methods
import asyncio
from fastapi import WebSocket, WebSocketDisconnect


@app.post("/api/{method:path}")
def dsh_rpc(method: str, request: Request):
    auth = request.headers.get("authorization", "")
    _ctx, _schema, _role, err = G.auth_ctx(auth, "")
    if err is not None:
        raise HTTPException(status_code=401, detail=f"{err}: valid Bearer token required")
    body = request.json()
    rpc_id = body.get("rpcId")
    method_name = body.get("method") or method
    payload = body.get("payload") or {}
    handler = dsh_methods.HANDLERS.get(method_name)
    if handler is None:
        result = {"ok": False, "error": {"code": "bad-request",
                                          "message": f"未知方法：{method_name}", "details": {}}}
    else:
        try:
            value = handler(payload)
            result = {"ok": True, "value": value}
        except dsh_methods.RpcError as e:
            result = {"ok": False, "error": {"code": e.code, "message": e.message, "details": e.details}}
        except Exception as e:  # noqa: BLE001
            result = {"ok": False, "error": {"code": "internal", "message": str(e), "details": {}}}
    return {"type": "server-response", "rpcId": rpc_id, "result": result}


@app.websocket("/api/events.mux")
async def dsh_mux_ws(websocket: WebSocket):
    await websocket.accept()
    queue: "asyncio.Queue[str]" = asyncio.Queue()
    dsh_methods._mux.add_connection(queue.put_nowait)
    try:
        while True:
            receive_task = asyncio.create_task(websocket.receive_text())
            send_task = asyncio.create_task(queue.get())
            done, pending = await asyncio.wait(
                {receive_task, send_task}, return_when=asyncio.FIRST_COMPLETED)
            if send_task in done:
                await websocket.send_text(send_task.result())
            if receive_task in done:
                try:
                    receive_task.result()
                except WebSocketDisconnect:
                    break
            for t in pending:
                t.cancel()
    finally:
        dsh_methods._mux.remove_connection(queue.put_nowait)
```

- [ ] **Step 6: 跑 adapter 测试确认通过**

Run: `cd D:/system/chiyu-enterprise && python -m pytest tests/test_dsh_adapter_schema.py -q`
Expected: PASS（import sanity + 4 schema 断言）。

- [ ] **Step 7: 变异自证（防止假绿）**

临时把 `dsh_adapter/methods.py` 的 `session_list` 返回 `"sessionId"` 改为 `"id"`，重跑 `test_session_list_shape_and_fields`：
Expected: FAIL（`items[0]` 缺 `sessionId`）。还原后重跑：PASS。

- [ ] **Step 8: 跑全量确认不破坏基线**

Run: `cd D:/system/chiyu-enterprise && python -m pytest tests/ -q`
Expected: PASS。

- [ ] **Step 9: Commit**

```bash
cd D:/system/chiyu-enterprise
git add packages/enterprise/src/enterprise/host/dsh_adapter/ packages/enterprise/src/enterprise/host/app.py tests/test_dsh_adapter_schema.py
git commit -m "feat(host): 迁入 DSH 适配层（/api/<method> + WS mux），复用治理中间件"
```

**成功标准（判定式）：** 14 类 DSH 方法（session.* / llm.* / agentPreset.* / skill.list / subagent.* / host.describe / goal.*）经 `TestClient` 返回 `ServerResponse` 全形且字段对齐 DSH schema；`session.prompt` 已在本仓验证真调 LLM（同 handler 迁入，行为不变）；变异自证红→还原→绿；既有 106 测试不破坏。

> ### ✅ T2 执行记录（2026-09-26, inline execution）
> - **E1 收口（本会话核心交付）**：`host/dsh_adapter/bridge.py` + `methods.py` 全部 `chiyu_kernel.<内部>` import 改经 `chiyu_kernel.api` 门面（L18–L28 合并为单一名字导入块；模块底部 `harness_native_tools` import 删除，符号改由顶部 api 导入；`chiyu_kernel.contract` 导入保留）。`test_consumes_facade_only::test_only_facade_imports` 由红转绿。
> - **关键澄清（推翻方法.py 原 doc 误判）**：原 doc 称「api 门面会触发 `store.pg_store` 的 pg 依赖，M0 不连库故不能走 api」。实测 `import chiyu_kernel.api` 仅 import `store.pg_store` 模块（1.86s），**加载期不连库**（PgVectorStore 仅在 `open_store()` 实例化时连）；故 E1 与「内存态不连库」策略无冲突。doc 已更正，避免后人误信。
> - **门面覆盖核验**：`chiyu_kernel.api` 重导出 dsh_adapter 全部所需符号（SessionManager/SessionLog/SkillRegistry/load_catalog/MODE_PRESETS/DEFAULT_MODE_ID/EventBus/StubProvider/LlmResponse/ToolRegistry/SubagentDescriptor/SubagentPool/AgentLoop/Agent/assemble/KnowledgeNeed/KNOWLEDGE_NEEDS_DEFAULT_DIMS/register_native_tools/native_redline_guard/SessionEvent），零符号缺口。
> - **变异自证（防假绿）**：临时把 `session_list` 返回 `"sessionId"` → `"id"`，`test_session_list_shape_and_fields` 转红（items[0] 缺 sessionId）；还原 → 绿。`grep` 零残留。判据具鉴别力。
> - **全量回归（信任但验证）**：`pytest tests/`（排除并发会话新建的 `test_control_panel_api.py`） = **333 passed / 4 skipped / 0 failed**；T2 相关 11 测试（schema + headless + E1）全绿。
> - **并发会话产物（非本会话回归，已取证）**：`tests/test_control_panel_api.py`（mtime 2026-09-26 13:51:05）引用尚不存在的 `enterprise/control_panel` 源模块，3 测试红（test_health / test_tenants_scenarios_connectors_shapes / test_sales_scenario_connectors_resolvable）。该文件不在本会话基线 `tests/` 列表，交其所有者处理，不计入 T2 验收。
> - **git 环境**：企业仓 HEAD tree 仍损坏（`bad tree object HEAD`），AI 不 commit；变更文件待用户本地修树后按显式 `git add` 路径提交（禁 `git add -A`）。

> ### ✅ T3 执行记录（2026-09-26, inline verification + 收口）
> - **状态**：T3 全部交付物已落盘且全绿（前序/并发会话预置源码 + 测试，本会话以「信任但验证」核验并补强判别力）。
> - **交付物核验**：
>   - `action/executor.py`：`execute_action` 按 fqn 遍历 `loader._REGISTRY`，命中包后查 `pkg.handler_of(fqn)`；三种返回结构 `{ok,wired,result|error}` 齐备（命中真执行 / 命中无 handler→接线缺口显式 / 未命中包→未注册显式，均不静默）。
>   - `scenario/package.py`：`ScenarioAction` 增 `handler: Optional[Callable]` 字段；`ScenarioPackage.handler_of(fqn)` 仅在显式 `self.actions` 上查找，派生动作默认无 handler。
>   - `scenario/sales.py`：`build_sales_scenario` 为 `sales.native.action_propose` 与 `sales.native.action_submit` 各接最小 handler（`_handle_action_propose` / `_handle_action_submit`）。
>   - `host/app.py`：`rpc_action` 写类写闸放行后调用 `execute_action`，已接 handler→返回真 `result`（含 `decision_id`），未接→显式 `wiring_gap`（不静默假装执行）。
>   - 测试：`tests/test_action_executor.py`（2）、`tests/test_headless_integration.py`（3，含 401→confirm→200 含 result→400 一次性消费 全链路 + WS mux 收帧）。
> - **变异自证（防假绿）**：临时把 `_handle_action_propose` 返回 `{"proposed":[...]}` → `{"mutated_probe":True}`，`test_execute_sales_native_action_returns_result` 转红（`'proposed' in result` 失败）；还原 → 绿；`grep` 零残留。判据具鉴别力。
> - **偏离计划（已记录于测试 docstring，追认）**：
>   ① 计划 T3 端到端写链路原定用 `sales.native.action_propose`，但该 Action `mutating=False`（读类，`GuardSpec()`）→ 经 app.py 走读类直连、不返回 result。实际端到端写链路改用 `sales.native.action_submit`（后缀写 `submit` + 零约束护栏，与 `request_quote` 同模式，可不触发 G0 决策锚即放行）→ 真实走 confirm+写闸+executor→result。`test_headless_integration.py` 头部「偏离计划说明」已注明。
>   ② G0 决策锚限制：`sales.native.feedback_capture` 等真 `mutating=True` 动作尚不能经完整 /rpc 链路（decision_id 被 `confirm.PROTOCOL_KEYS` 剥离，G0 先于 `mint_decision` 运行），故端到端验证改用零约束后缀写 `action_submit`。此项为独立待修（非 T3 阻塞），G0 决策锚注入修复后真 mutating 动作亦可端到端。
> - **全量回归**：`pytest tests/ --ignore=tests/test_control_panel_api.py` = **333 passed / 4 skipped / 0 failed**（T3 测试已含入该计数；`test_control_panel_api.py` 为并发会话 WIP，交其所有者）。
> - **提交**：git HEAD tree 仍损坏，AI 不 commit。建议提交范围（用户本地修树后显式 add）：
>   `action/executor.py`、`scenario/package.py`、`scenario/sales.py`、`host/app.py`、`tests/test_action_executor.py`（及既有 `tests/test_headless_integration.py` 若未提交）。

> ### ✅ T4 执行记录（2026-09-26, inline verification + 判别力补强）
> - **状态**：`tests/test_headless_integration.py` 已由前序/并发会话预置且全绿；本会话以「信任但验证」实跑核验、**收紧一处弱断言**、做两轮变异自证后收口。
> - **三条 headless 判据全绿**（`test_headless_integration.py` 3 passed）：
>   ① `test_dsh_14_method_classes_all_200`：15 个代表方法类（session.*/llm.*/agentPreset.*/skill.list/subagent.list/host.describe）经 `POST /api/{method}` 全部返回 200（路由到结构化 ServerResponse，无 500 崩溃）。
>   ② `test_write_action_full_chain_with_token`：`sales.native.action_submit` 端到端 401（无 token）→ 200 confirm（confirm_required + token）→ 200 执行含真 `result`（`submitted`）→ 400（一次性消费，重复 token 拒绝）。
>   ③ `test_ws_mux_receives_frame`：WS `/api/events.mux` 订阅 MuxBroadcaster，`_bus.publish` 后收到 `server-request` 全形帧（`payload.type=session/event`）。
> - **实证 8/15 方法返回 ok=False 属预期（非缺陷）**：直接对企业 host 打载荷实测，`session.history/models/selectModel/prompt/cancel` + `agentPreset.select` 因 smoke 测试未带 `sessionId` 返回结构化 error（`{"code":"internal","message":"'sessionId'"}`）；`agentPreset.read` 未带 mode 返回 `agent-preset-not-found`。均为合法入参校验错误，非崩溃；HTTP 均为 200。**契约意图成立**：`/api/{method}` 保证「路由到结构化 ServerResponse、永不 500」，而非业务必成功。
> - **判别力补强（本会话改动）**：原断言 `res["ok"] is True or "error" in res` 过弱（裸 `{"error":"任意串"}` 也过）。已收紧为：`result` 必须是 dict、`ok` 必须是 bool、非 ok 时 `error` 必须是含 `code`/`message` 的**结构化 dict**。合法入参校验错误仍通过，但畸形响应/裸串 error 会转红。
> - **变异自证（两轮，防假绿）**：
>   ① 写链路：`_handle_action_submit` 返回 `{"submitted":[...]}`→`{"mutated":True}`，`test_write_action_full_chain_with_token` 转红（`'submitted' in result` 失败）——证明 executor 确被端到端真执行。
>   ② 方法类：`app.py` 路由 wrapper 的 `result={"ok":True,"value":value}`→去掉 `ok`，`test_dsh_14_method_classes_all_200` 转红（`result.ok` 非 bool）——证明收紧后的结构断言具鉴别力。
>   两处均还原 → 绿；`grep MUTATION` 零残留。
> - **全量回归**：`pytest tests/ --ignore=tests/test_control_panel_api.py` = **333 passed / 4 skipped / 0 failed**（T4 已含入；`test_control_panel_api.py` 并发 WIP 交其所有者）。
> - **提交**：git HEAD tree 仍损坏，AI 不 commit。本次本会话仅有 1 处文件变更：`tests/test_headless_integration.py`（收紧断言 + 注释）。建议用户本地显式 add 提交。

---

## Task 3: 补 Action executor（写类 Action 真执行）

**Files:**
- Create: `packages/enterprise/src/enterprise/action/executor.py`
- Modify: `packages/enterprise/src/enterprise/host/app.py`（`rpc_action` 写类分支调 executor）
- Test:   `tests/test_action_executor.py`

- [ ] **Step 1: 写失败测试（写类 Action 经 confirm+写闸后真执行并返回结果，而非仅 decision_id）**

```python
# tests/test_action_executor.py
from enterprise.action.executor import execute_action
from enterprise.scenario import loader as scenario_loader
from enterprise.scenario.sales import build_sales_package


def setup_module():
    scenario_loader.register_scenario("sales", build_sales_package)


def test_execute_sales_native_action_returns_result():
    # 选一个声明了 handler 的 sales.native.* Action（如 action_propose）
    res = execute_action("sales.native.action_propose",
                         {"tenant": "t1", "draft": "请建议下一步动作"},
                         tenant_id="t1", actor_role="admin")
    assert res["ok"] is True
    assert "result" in res  # 真执行结果，而非仅 decision_id
```

- [ ] **Step 2: 实现 executor.py（最小可运行，路由 Action FQN 到场景包 handler）**

```python
# packages/enterprise/src/enterprise/action/executor.py
"""Action 执行分发（最小实现）。

⛔ 守分层：通用层不持领域字面量；Action → handler 映射由已注册场景包提供。
写类 Action 已在 host 层经 confirm + 写闸，此处只执行「已放行」的动作。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from enterprise.scenario import loader as scenario_loader


def execute_action(action_fqn: str, params: Dict[str, Any], *,
                   tenant_id: str, actor_role: Optional[str] = None) -> Dict[str, Any]:
    """执行一个已通过治理闸的 Action，返回 {ok, result|error}。

    路由：按 fqn 在已注册场景包中查找 handler（ScenarioAction.handler）；
    未命中 handler → ok=False（声明了 Action 但未接 handler，属接线缺口，显式报错不静默）。
    """
    pkg = None
    for _name, factory in _registries():
        p = factory()
        if action_fqn in p.action_fqns() or any(a.fqn == action_fqn for a in p.actions):
            pkg = p
            break
    if pkg is None:
        return {"ok": False, "error": f"未注册场景包承载 {action_fqn}"}
    handler = pkg.handler_of(action_fqn)
    if handler is None:
        return {"ok": False, "error": f"Action {action_fqn} 已声明但未接 handler（接线缺口）"}
    try:
        result = handler(params, tenant_id=tenant_id, actor_role=actor_role)
        return {"ok": True, "result": result}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def _registries():
    # 复用 loader 的注册表迭代（避免重复实现）
    return [(n, scenario_loader._REGISTRY[n]) for n in scenario_loader._REGISTRY]
```

> 注：`ScenarioPackage` 需新增 `handler_of(fqn)` 方法（在 `scenario/package.py` 中按 `actions` 列表的 `handler` 字段查找）。若 `ScenarioAction` 当前无 `handler` 字段，先在 `package.py` 给 `ScenarioAction` 增加 `handler: Optional[Callable]` 字段，`sales.py` 为 `sales.native.action_propose` 提供一个最小 handler（返回 `{"proposed": [...]}` 占位即可，证明链路通）。

- [ ] **Step 3: 改写 app.py `rpc_action` 写类分支接入 executor**

在 `rpc_action` 写类 confirm 通过、写闸放行后（约原 `app.py:166` 之后），把仅返回 `decision_id` 改为：

```python
    decision_id = G.mint_decision(ctx.tenant_id, action)
    exec_res = execute_action(action, merged, tenant_id=tenant_schema, actor_role=role)
    return {
        "tenant": tenant_schema, "client_type": client_type, "action": action,
        "ok": exec_res["ok"], "decision_id": decision_id,
        "result": exec_res.get("result"), "error": exec_res.get("error"),
    }
```

- [ ] **Step 4: 跑 executor 测试 + 全量**

Run: `cd D:/system/chiyu-enterprise && python -m pytest tests/test_action_executor.py tests/ -q`
Expected: PASS；写类 Action 返回 `result` 而非仅 `decision_id`。

- [ ] **Step 5: Commit**

```bash
cd D:/system/chiyu-enterprise
git add packages/enterprise/src/enterprise/action/executor.py packages/enterprise/src/enterprise/scenario/package.py packages/enterprise/src/enterprise/scenario/sales.py packages/enterprise/src/enterprise/host/app.py tests/test_action_executor.py
git commit -m "feat(action): 补 executor 使写类 Action 真执行（sales.native.* 最小 handler）"
```

**成功标准（判定式）：** `execute_action("sales.native.action_propose", ...)` 返回 `ok=True` 且含 `result`；`/rpc/{t}/{c}/action` 写类 Action 端到端（401 无 token → 200 confirm → 400 重复 confirm → 200 执行含 result）；反 CRUD 爆炸检测仍有效。

---

## Task 4: headless 契约验证（绕过 DSH 构建）

**Files:**
- Create: `tests/test_headless_integration.py`

- [ ] **Step 1: 写 headless 验证（不依赖 DSH 前端打包，直接对企业 host 打 RPC/SSE/WS）**

```python
# tests/test_headless_integration.py
from fastapi.testclient import TestClient
from enterprise.host.app import app
import enterprise.host.dsh_adapter.methods as dsh_methods


def _client():
    return TestClient(app)


def _auth():
    return {"Authorization": "Bearer t-default-desktop-dev"}


def test_dsh_14_method_classes_all_200():
    c = _client()
    methods = ["session.list", "session.create", "session.history", "session.models",
               "session.selectModel", "session.prompt", "session.cancel", "llm.providers",
               "llm.models", "agentPreset.list", "agentPreset.select", "agentPreset.read",
               "skill.list", "subagent.list", "host.describe"]
    for m in methods:
        body = {"type": "client-request", "rpcId": "x", "method": m, "payload": {}}
        r = c.post(f"/api/{m}", json=body, headers=_auth())
        assert r.status_code == 200, f"{m} -> {r.status_code}"
        assert r.json()["result"]["ok"] is True or "error" in r.json()["result"]


def test_write_action_full_chain_with_token():
    c = _client()
    # 401 无 token
    r0 = c.post("/rpc/t1/desktop/action?action=sales.native.action_propose", json={})
    assert r0.status_code == 401
    # 200 confirm
    r1 = c.post("/rpc/t1/desktop/action?action=sales.native.action_propose",
                json={"draft": "x"}, headers=_auth())
    assert r1.json().get("gate") == "confirm_required"
    token = r1.json()["confirm_token"]
    # 400 重复 confirm（一次性消费）
    r2 = c.post("/rpc/t1/desktop/action?action=sales.native.action_propose",
                json={"draft": "x", "confirm_token": token}, headers=_auth())
    assert r2.status_code == 200 and r2.json()["ok"] is True and "result" in r2.json()


def test_ws_mux_receives_frame():
    # 用 TestClient.websocket_connect 起 WS，触发一次 session.prompt 广播，断言收到 MuxFrame
    from fastapi.testclient import TestClient
    c = TestClient(app)
    with c.websocket_connect("/api/events.mux") as ws:
        dsh_methods._bus.publish(
            {"id": "e1", "event_type": "session/event", "sessionId": "s9",
             "event": {"kind": "assistant/message", "seq": 1, "ts": 0.0, "payload": {}}},
            persist=lambda e: None)
        frame = ws.receive_json()
        assert frame["type"] == "server-request"
        assert frame["payload"]["type"] == "session/event"
```

- [ ] **Step 2: 跑 headless 验证**

Run: `cd D:/system/chiyu-enterprise && python -m pytest tests/test_headless_integration.py -q`
Expected: PASS（14 方法全 200 + 写类全链路 + WS 收帧）。

- [ ] **Step 3: 跑全量确认整体绿**

Run: `cd D:/system/chiyu-enterprise && python -m pytest tests/ -q`
Expected: PASS（含 106 既有 + T1/T2/T3/T4 新增）。

- [ ] **Step 4: Commit**

```bash
cd D:/system/chiyu-enterprise
git add tests/test_headless_integration.py
git commit -m "test(host): headless 契约验证（客户端—企业平台最小闭环，绕过 DSH 构建）"
```

**成功标准（判定式）：** 三条 headless 测试全绿，证明「DSH 前端协议 + 企业治理 + 真执行 + WS 事件」闭环成立；DSH 构建受阻不影响此判据。

---

## 执行后收尾

### ✅ 收尾执行记录（2026-09-26 本会话）

**① G0 决策锚注入修复（真 mutating 动作端到端）——已完成**
- 根因确认：`feedback_capture` 等真 `mutating=True` 动作此前无法经 host 写链路，因 G0 在 `mint_decision` 之前运行，且 `decision_id` 为 `confirm.PROTOCOL_KEYS` 协议位、被 `merge_phase2_params` 剥离。T2 方案 C（`app.py` 显式传 `decision_id=payload.get("decision_id")` 入 `run_write_gates`）已修 G0 校验，但 `feedback_capture` 仍无 handler 且注释标注「暂无法真执行」。
- 本会话收口：① 新增 `_handle_action_feedback_capture` 最小 handler 并接入 `sales.native.feedback_capture`（G0 前置已满足）；② 更新 `sales.py` 过时注释；③ `test_sales_scenario.py` 新增 `test_real_mutating_action_full_chain_with_decision_id` e2e：401（无 token）→ confirm → G0 拦截（无 decision_id → 400 `decision_required`）→ 携 decision_id 200 真执行含 `result.captured` → 重复 token 400（一次性消费）。
- 连带更新：`tests/test_action_executor.py::test_execute_unwired_declared_action_is_explicit_gap` 改用仍无 handler 的 `sales.integration.crm.update_opportunity`（原 `feedback_capture` 已接 handler，不再是接线缺口样例）。
- 变异自证：临时摘除 `feedback_capture` 的 handler → e2e 测试转红（`assert result is not None` 失败）；还原 → 绿；`grep MUTATION` 零残留。
- 全量：**334 passed / 4 skipped / 0 failed**（排除并发 `test_control_panel_api.py`）。

**② 并发会话 `test_control_panel_api.py` 排查——已解决（非本会话回归）**
- 初始取证：13:52 该测试文件出现在 `tests/` 时，`enterprise/host/control.py` 尚未存在 → 3 红。
- 复查发现：并发会话在 13:53 已建 `enterprise/host/control.py`（+`control_plane.py`），且 `app.py` 已挂 `/control/*` 路由 + `bootstrap_control_state()`。当前实跑 5 passed。
- **全量含该文件 = 339 passed / 4 skipped / 0 failed**。无需本会话处理，交其所有者自行提交。

**③ `chiyu-host` 弃用标记——已完成**
- `packages/chiyu-host/src/chiyu_host/__init__.py`：模块 docstring 顶注「⚠️ 已弃用（2026-09-26）」+ 迁移指向（`chiyu-enterprise` 企业 host `enterprise.host.dsh_adapter`）；新增 `DEPRECATED=True` 与 `SUPERSEDED_BY="chiyu-enterprise enterprise.host.dsh_adapter"` 常量。
- `README.md` 包结构表新增 `chiyu-host` 行，状态标「已弃用（并入 chiyu-enterprise）」。
- 保留代码不删（作为历史快照/参考实现）；本仓内核+host 测试 426 passed 不受影响。
- ⛔ 清理（删包）不在本计划范围，待用户另行确认。

### ✅ 补测记录（2026-09-26 本会话，加深 headless 覆盖）

**背景**：集成验证体系唯一已知缺口＝DSH 前端**真渲染**（浏览器验证）。经核查，`web/` 是 ChiYu 门户 demo（React+Vite，已构建）而非 DSH 客户端；DSH 客户端源码/构建产物**不在本机可枚举位置**（reference 树仅含 `subagent-dsh-sdk` 工具），真浏览器渲染需其构建产物回传，本机无法自主完成。经用户确认，补测方向＝**加深 headless 覆盖**，把闭环证据从「结构合法」提升到「数据真实流通」。

**新增 `tests/test_headless_deep.py`（4 条硬判据，全绿）：**
1. **session 生命周期闭环**：`session.create` → 拿真实 `sessionId` → `session.history/selectModel/cancel` 携该 id 返回 `ok=True`（证明参数真被消费，非仅路由通）。
2. **agentPreset 切换闭环**：`agentPreset.list` 取真实 preset → `agentPreset.select` 用其 id → `ok=True`（`sessionId` 为 `standard/ptc/minimal/creative` 之一）。
3. **session.prompt 真执行落库**：真调 LLM（StubProvider stream_chat）→ `_session_manager` 写入 `user/message` + `assistant/message` 两帧。
4. **WS mux 收真实帧（反假绿关键）**：**双 TestClient 方案**——WS 连接持有者与 HTTP 触发者分离，先 `add_connection` 再触发真实 `session.prompt`，收到 `payload.type=="session/event"` + `event.type ∈ {user/message, assistant/message}` 的真实帧（区别于既有测试手动 `_bus.publish` 假帧）。

**关键实证（信任但验证）：**
- **时序竞态根因**：TestClient 的 HTTP 与 WS 是同步串行——若先 `c.post(prompt)` 再 `websocket_connect`，帧在 `add_connection` 注册前已广播丢失 → `receive_json` 永久阻塞（SIGTERM 根因）。修正＝双 client / 先建 WS 再触发。**这是真实行为差异，非测试 bug**。
- **帧结构澄清**：MuxFrame 外壳 `payload.type=="session/event"`，真实事件类型在**内层 `payload.event.type`**（`user/message`/`assistant/message`），非 `payload.type` 亦非 `event.kind`。
- **变异自证**：`session_create` 临时不注册 `_session_index` → 4 条全红（证明全部真实依赖「会话被正确索引」）；还原 → 绿；`grep MUTATION` 零残留。

**回归基线（补测后）：** 全 headless（deep 4 + integration 3）+ sales 22 + executor = **29 passed**；企业仓全量 **369 passed / 4 skipped / 0 failed**（339→369）。

**提交建议（git HEAD 树已修复，本会话不 commit）：**
```bash
cd D:/system/chiyu-enterprise
git add tests/test_headless_deep.py
git commit -m "test(host): 加深 headless 覆盖——session生命周期/agentPreset切换/prompt真执行/WS真实帧（369 passed）"
```
