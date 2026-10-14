# 逐 WS cookbook（WS6 / WS2 / WS3 / WS8 / WS7）

> 日期：2026-10-13 ｜ 来源：`docs/plans/2026-10-09-foundation-maturity-blueprint.md` §7 执行记录（提炼为可运行样例 + 变异自证）
> 受众：消费方接入工程师 + foundation 底座团队
> 约定：每个 WS 收口须过**三件套**——① 测试绿 ② 反假绿探针绿（**变异自证**：删判据分支→转红→还原）③ 零领域字面量 grep=0。

---

## WS6 · 领域注入 SDK（关键石，I3，最高杠杆）

**用途**：把"领域字面量如何注入内核"做成官方三件套（`TenantProfile` + `inject_domain` + `ScenarioPack`），消费方照模板填，不再各仓重造领域注入。

**最小可运行样例**
```python
from chiyu_kernel.api import profile_from_dict, inject_domain, TenantProfile

profile = profile_from_dict({
    "tenant": "acme-auto",
    "particle_types": {"customer": {"layer": "L1", "serves_dims": ["decision_history"]}},
    "actions": {"follow_up": {"particle_type": "customer", "effects": []}},
    "predicates": {"EVALUATED": {}},
    "scenario": {"controlled_edges": [{"from": "customer", "predicate": "EVALUATED", "to": "customer"}]},
})
bundle = inject_domain(profile=profile, actions=(), scenarios=())   # → DomainBundle
# bundle.profile / bundle.actions(ActionRegistry) / bundle.scenarios
```

**变异自证**（`tests/test_domain_injection.py`，7 个，含 2 反假绿探针）
- 临时禁用 `inject_domain` 跨一致性闸 → 两探针转红（`DID NOT RAISE`）→ 还原。
- 探针覆盖：profile 缺核心角色 / R5 capability 冲突 / 边谓词不在 profile / 边类型不在 particle_types。

**锚点**：`tests/test_domain_injection.py` ｜ 验收 427 passed ｜ 零领域字面量 grep=0。

---

## WS2 · 标准 persister + 记忆网 writer（I3 落库侧，embody N/B/F/G）

**用途**：`SpineResult`→落库走 `event` + upsert `particle` + `write_decision_memory_net` 写 7 谓词边（单库多轨收口，禁另起可写存储）。

**最小可运行样例**
```python
from chiyu_kernel.api import PgVectorStorePersister, write_decision_memory_net, get_dsn, connect

store = open_store(get_dsn())                       # 见使用指南 §4
persister = PgVectorStorePersister(store, profile, onto=None, event_bus=None, materialize=True)

result = run_spine(context, profile, rubric_scores, elements,
                   redline_items=(), approval_gate=RedlinePriorityGate(),
                   persister=lambda r: persister.persist(r, subject_id="s1", tenant_id="t1"))
# 红线命中只落 event、不写 7 边（judge_worthiness 拦记忆网）
```

**变异自证**（`tests/test_persist_ws2.py`，7 个，含 2 处）
- ① 禁幂等闸（`content_hash`）→ 相同内容二次落库产生新 event 行断言**转红** → 还原。
- ② 禁 `judge_worthiness` 闸 → 红线决策也写 7 边断言**转红** → 还原。

**锚点**：`tests/test_persist_ws2.py` ｜ 验收 434 passed ｜ 零领域字面量守卫 13 passed。

---

## WS3 · 注入式 ApprovalGate（I1 红线闸，embody A + 金律26）

**用途**：硬约束先于置信度——红线命中即强制 HITL，屏蔽自主放行，不因置信度高豁免。

**最小可运行样例**
```python
from chiyu_kernel.api import run_spine, RedlinePriorityGate, resume_spine

result = run_spine(context, profile, rubric_scores, elements,
                   redline_items=("禁止向竞品披露",),
                   approval_gate=RedlinePriorityGate())   # 红线命中→pending/拒绝，persisted=False+audit
# PENDING 续跑（不重评）：
resume_spine(result, persister=persist_fn, audit_sink=audit_fn, approval_ref="单号-123")
# REJECTED 为终态：resume 抛 ValueError（红线硬拒不得复活）
```

**变异自证**（`test` 等价 464 / `test-all` 等价 476，含 2 处）
- ① 禁闸内红线分支 → 内核探针**转红** → 还原。
- ② 禁脊柱接线分支 `if not gate_verdict.approved` → 脊柱探针**转红**（`persisted=True` 暴露闸门被绕过）→ 还原。
- 教训：脊柱探针须用全 8 要素 + 满分使红线成为**唯一**拦截点（否则 missing 分支与红线分支同时拦截，无法鉴别）。

**锚点**：`chiyu_kernel/approval/` + `chiyu_decision` 接线测试 ｜ 验收 464/476 passed。

---

## WS8 · GraphStore 图存储（I1，embody H 单源双视图）

**用途**：只读派生面——数据来自 `particle`+`decision`+`graph_edge` 同库，**禁另起可写图库**。

**最小可运行样例**
```python
from chiyu_kernel.api import relation_view, timeline_view, decision_backlinks, PgCteGraphStore

store = PgCteGraphStore(connect_factory=connect)    # 纯 PG 递归 CTE，零新扩展依赖（=AGE 等价）
view = relation_view(store, root="customer:1", max_hops=2)   # 受控边多跳 + truncated 诚实标记
tl   = timeline_view(store, decision_id="d-1")                # 四源只读聚合
bl   = decision_backlinks(store, decision_id="d-1")           # 审计回链四问
```

**变异自证**（`tests/test_graph_*`，含 3 处，均转红后还原）
- ① 禁受控谓词闸 → 2 条**转红** → 还原。
- ② 禁深度上界闸 → 越界不再抛 → 还原。
- ③ 删 CTE `w.depth < %s` → 2 条**转红** → 还原。
- 协议守：`test_protocol_has_no_write_methods` 守 GraphStore 无任何写方法。

**锚点**：`chiyu_kernel/graph/` ｜ 验收 488 passed ｜ 两后端对拍（同输入须同结果）。

---

## WS7 · MCP 服务骨架（I2，embody 零信任 + v0.2 双输出）

**用途**：把底座能力稳定输出为 MCP 工具面——统一 auth + 工具注册守卫 + 两阶段确认零信任写入。

**最小可运行样例**
```python
from chiyu_kernel.api import McpServer, issue_confirm_token, verify_confirm_token, AuthDenied

srv = McpServer(name="chiyu-foundation")
srv.expose("decide", risk="write", handler=my_handler)   # 名式 ^[a-z][a-z0-9_]{0,63}$ / 重名禁静默覆盖
resp = srv.handle_request({"tool": "decide", "args": {...}, "principal": "p"},
                          auth=lambda ctx: ctx.principal == "p")   # auth=None 一律拒绝
# 写类工具首次返回 confirmation_required+token；二次带 token 才执行（HMAC 绑定 工具名+参数+主体）
```

**变异自证**（`tests/test_mcpserver_*`，含 3 处，均转红后还原）
- ① 禁鉴权闸 → 探针报 `leaked`（默认放行即泄密）→ 还原。
- ② 禁两阶段闸 → 写操作无确认即执行 → 还原。
- ③ token 解绑参数 → `amount 100→999999` 被放行（重放攻击）→ 还原。
- 自查：首版 `test_probe_duplicate_guard_discriminates` 含 `if False else None` 死代码（断言空转=假绿），已改实质断言。

**锚点**：`chiyu_kernel/mcpserver/` ｜ 验收 508 passed。

---

## WS9 · 参考消费层（端到端样板 + 常驻 canary）—— ⏳ 唯一未 ship

`maturity-blueprint.md §7.7` 明示为下一步：端到端样板须带**反假绿探针**（证决策真落库、记忆真物化、图真派生，非"表有行即判已接通"）。本 cookbook 暂列占位，待 WS9 收口后补最小样例。

---

**收口计数汇总**：WS6 427 → WS2 434 → WS3 464/476 → WS8 488 → WS7 508（组合回归，均含变异自证 + 零领域字面量 grep=0）。

— foundation（chiyu-foundation 仓），2026-10-13
