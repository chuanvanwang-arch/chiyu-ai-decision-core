# G0 决策锚修复（设计稿 + 计划 ·  retrospective 收口）

> 状态：**已落地 + 已验证**（由并发会话实现，未走 brainstorming 闸门；本稿补作事实源收口，守「设计稿为唯一事实源」铁律）。
> 仓边界：本稿落 `chiyu-foundation`（唯一事实源）；代码改动落 `chiyu-enterprise`。AI 不 commit。

## 0. 问题（根因）

写闸 G0（R4 决策强制）要求 `mutating` 写动作必须携带 `decision_id`（`guard.py:check_write_gates`，`guard.mutating and not decision_id → deny`）。但 host 写链路存在**协议位被剥离**的缺陷：

- `host/confirm.py` 的 `PROTOCOL_KEYS` 含 `decision_id`；`merge_phase2_params` 对协议位**整体跳过**（不并入 `merged`）。
- host 写分支：`merged, _ = G.consume_confirm(...)` 后 `G.run_write_gates(action, merged, ...)`，`run_write_gates` 取 `params.get("decision_id")` —— 而 `merged` 已被剥离 `decision_id` → 永远 `None`。
- `G.mint_decision(...)` 在 `run_write_gates` **之后**才签发 → G0 永远看不到任何决策锚 → 永远 `decision_required` 拦截。

结果：所有 `mutating=True` 动作（如 `sales.integration.erp.sync_order` / `sales.native.feedback_capture`）经 host 写链路时必被 G0 卡死，**12 项既有测试红**（`test_host_wiring_ext` ×7 + `test_sales_scenario` ×5）。

## 1. 决策（D1 修复路线选型）

三方案对比：

| 方案 | 改动 | 优劣 |
|---|---|---|
| A 移出 PROTOCOL_KEYS | `confirm.py` 删 `decision_id` | 最小（1 行）；但 `decision_id` 由协议位降级为业务参数，**落入 execParams**，违反 confirm.py 注释约定「不落 execParams」；响应仍 mint 新 id 与请求锚不一致 |
| **B 显式提升（Fix C）✅** | `app.py` 从 raw phase2 提 `decision_id` 传 `run_write_gates`；`governance.run_write_gates` 加 `decision_id` 入参；`PROTOCOL_KEYS` 不动 | 语义最纯：`decision_id` 仍是协议位、不落 execParams；G0 见客户端锚；响应锚一致。**落地即此方案** |
| C 改 12 测试放 phase1 | 测试重写 | 协议位语义偏；改动面大；不修复根因 |

**选定 Fix C**（与实现落地一致，亦为推荐方案）：保留 `decision_id` 为协议位，由调用方从 raw phase2 payload 显式传入 `run_write_gates`，仅供 G0 验证、不并入 `merged`。

## 2. 落地改动（已在 `chiyu-enterprise`，待用户本地 commit）

- `enterprise/host/app.py` 写分支（约 73–78）：
  ```python
  _gate = G.run_write_gates(
      action, merged, tenant_schema, actor_role,
      decision_id=payload.get("decision_id"),   # 从 raw phase2 显式提升，不落 merged
  )
  ```
- `enterprise/host/governance.py` `run_write_gates`（101–124）：新增 `decision_id: Optional[str] = None` 入参；`_decision_id = decision_id if decision_id is not None else params.get("decision_id")`；传 `check_write_gates`。
- `enterprise/host/confirm.py`：`PROTOCOL_KEYS` **未改**。

⛔ 纪律事件：本改动由并发会话先行落地、无设计稿。本稿补作事实源；后续同类内核写链路改动须先走 brainstorming。

## 3. 验证（trust-but-verify，本会话实测）

- 全量 `pytest tests/`：`13 failed / 303 passed`（修复前）→ **`1 failed / 315 passed / 4 skipped`**（修复后）。**12 项 G0 相关测试全部转绿**，零新失败。
- 变异自证：临时把 `decision_id=payload.get("decision_id")` 改为 `decision_id=None` → `test_phase2_mutating_with_decision_allowed` 与 `test_host_allows_write_when_gates_satisfied` 立即转红（400 `decision_required`）；还原 → 28 passed；`grep MUTATION` 零残留。
- 唯一剩余失败 `test_consumes_facade_only`（E1 违例，另立项）。

## 4. 待办

- 用户本地先修 `git bad tree object HEAD` 再提交 G0 相关改动。
- `sales.native.feedback_capture` 仍「mutating 未接 handler」占位：G0 已通，理论可接 handler 真执行，非阻塞，留作后续。

## 5. 生命契约（retrospective）

```contract-yaml
- task: "G0 决策锚修复（decision_id 经 raw phase2 提升供写闸 G0 验证）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-native-action-design]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2] }
  success: "mutating 写动作携 decision_id 过 G0→executor；test_host_wiring_ext + test_sales_scenario 全绿（12 项转绿），变异自证通过"
```
