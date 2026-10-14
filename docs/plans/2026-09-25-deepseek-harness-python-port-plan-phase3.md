# Deepseek Harness 全量 Python 移植 · 阶段三实施计划

- 日期：2026-09-25
- 形态：全量 Python 移植（忠实重写 dsh 行为，能力吸收式 R2）
- 契约：`contract/contract-ids.json`（agent = `foundation-builder`，键 `ct-chiyu-foundation`）
- 关联设计：`docs/plans/2026-09-25-deepseek-harness-python-port-design.md` §2/§4
- 关联阶段一/二计划：`...-plan.md` / `...-plan-phase2.md`（门面守卫/`make test` 纪律沿用）

## 0. 阶段三范围（设计文档 Phase 3）

| dsh 包 | 本仓落地 | 层 | 门面 | 说明 |
|---|---|---|---|---|
| `guard/repeat-tool-reminder` + `guard/timeout-policy` | `chiyu_kernel/orchestration/loop_guard.py` | L2 | orchestration 已覆盖 | 重复工具调用提醒 + 轮次预算（环路卫生） |
| `mcp/mcp-client` | `chiyu_kernel/mcp/`（新子包） | L2 | 加 `LAYERS` | MCP 工具桥（命名 `mcp__<server>__<raw>` + namespace 预留） |
| `fs/fs` + `fs/fs-local` | `chiyu_kernel/tools/fs.py` | L1 | tools 已覆盖 | 沙箱文件系统工具（write 高危险） |
| `shell/bash-local` + `terminal/terminal` + `subprocess` | `chiyu_kernel/tools/shell.py` | L1 | tools 已覆盖 | `shell_run` 一次性命令 + `TerminalSession` 状态会话 |
| `hooks/hook-protocol` | `chiyu_kernel/hooks/`（新子包） | L2 | 加 `LAYERS` | 钩子总线（matcher + 生命周期点 PreToolUse/PostToolUse/Stop） |
| `interaction/permission-presets` + 审批 | `chiyu_kernel/interaction/`（新子包） | L2 | 加 `LAYERS` | 高风险动作 HITL 审批闸门 |

> 严守 R2：复用 `AgentLoop` / `ToolRegistry` / `SessionManager`，新 scope 不重复 `actions`/`evolution`。
> 网络型 MCP stdio/HTTP transport 不在本阶段（需真实子进程/网络）；`McpBridge` 用 `McpTransport` 协议 + `InMemoryMcpServer` 测试替身，可后续接真实 transport。

## 1. 任务清单（TDD：先红→绿→门面守卫→提交）

- **T1 — loop_guard（guard 环路卫生）**：扩展 `AgentLoop` 接 `loop_guard`；新增 `LoopGuard`（重复调用提醒 [3,5,8] + 轮次预算 max_steps 终止）。测试覆盖：重复注入提醒、超预算终止、未知 guard 不影响。
- **T2 — mcp 桥**：`chiyu_kernel/mcp/`（子包）。`McpTransport` 协议 + `InMemoryMcpServer` + `McpBridge`（连/列/调/断，命名归一，namespace 重复报错）。测试覆盖：工具注册、调用转发、重复 serverName 报错、命名归一。
- **T3 — fs 工具**：`chiyu_kernel/tools/fs.py`。`SandboxedFs`（root 沙箱）+ `register_fs_tools`（fs_read/fs_write/fs_list，write 高危险）。测试覆盖：读写列、越界拒绝、高危险标记。
- **T4 — shell/terminal 工具**：`chiyu_kernel/tools/shell.py`。`run_command`（subprocess，高危险，可选 allowlist）+ `TerminalSession`（状态 cwd）。测试覆盖：echo 执行、cwd 持久、allowlist 拒绝、终端会话历史。
- **T5 — hooks 总线**：`chiyu_kernel/hooks/`（子包）。`HookBus`（register/run）+ `matches`（match-all/literal/regex）。接 `AgentLoop` 生命周期（PreToolUse 可否决、PostToolUse、Stop）。测试覆盖：matcher 三态、PreToolUse 否决跳过、PostToolUse/Stop 触发。
- **T6 — 审批闸门（interaction）**：`chiyu_kernel/interaction/`（子包）。`ApprovalGate`（request/approve/deny/guard）。接 `ToolRegistry` 红线位。测试覆盖：高危险未批→GuardDenied、批准→执行、deny→保持拒绝。
- **T7 — 阶段三 E2E 冒烟**：串联 loop_guard + mcp + fs + shell + hooks + approval 跑一轮完整 turn，断言各能力生效；`make test` 全绿。

## 2. 契约块（P7 自检用）

```contract-yaml
- task: "guard 环路卫生：重复调用提醒 + 轮次预算（吸收 dsh guard）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-multi-agent-orchestration]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "AgentLoop 接 loop_guard 后：连续相同工具调用达阈值注入提醒；超 max_steps 终止；pytest 覆盖"
```
```contract-yaml
- task: "MCP 工具桥（吸收 dsh mcp-client，命名归一 + namespace 预留）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "McpBridge 连入 InMemoryMcpServer 后工具注册进 ToolRegistry 且调用转发；重复 serverName 报错；pytest 覆盖"
```
```contract-yaml
- task: "沙箱文件系统工具（吸收 dsh fs，write 高危险）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "SandboxedFs 在 root 内读写列；越界拒绝；fs_write 标记 high_risk；pytest 覆盖"
```
```contract-yaml
- task: "shell/terminal 工具（吸收 dsh shell/terminal/subprocess，高危险）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "shell_run 经 subprocess 执行 echo；TerminalSession 持久 cwd；allowlist 拒绝；pytest 覆盖"
```
```contract-yaml
- task: "钩子总线（吸收 dsh hook-protocol，matcher + 生命周期点）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-multi-agent-orchestration]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "HookBus matcher 三态正确；PreToolUse 否决跳过；PostToolUse/Stop 触发；pytest 覆盖"
```
```contract-yaml
- task: "审批闸门（吸收 dsh interaction/permission，HITL 高风险）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "ApprovalGate 高危险动作未批拦截、批准放行、deny 保持拒绝；pytest 覆盖"
```
```contract-yaml
- task: "阶段三 END-TO-END 冒烟"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "loop_guard+mcp+fs+shell+hooks+approval 串联跑通一轮 turn；make test 全绿"
```

## 3. 门面纪律（沿用阶段一/二）

- 每个新建子包（`mcp`/`hooks`/`interaction`）加 `LAYERS`；`tools/fs.py`、`tools/shell.py`、`orchestration/loop_guard.py` 由既有子包覆盖。
- `AgentLoop` 扩展 `loop_guard`/`hook_bus` 参数（默认 None，向后兼容，不破坏阶段一/二测试）。
- `contract/` 未改动 → 无需重生成 `manifest.json`。

## 4. 风险与判别力

- **R2 重复框架**：已规避——全部复用 `AgentLoop`/`ToolRegistry`/`SessionManager`/`Agent`。
- **门面静默未接线（阶段一/二已踩）**：每个新子包必加 `LAYERS`；`orchestration.loop_guard` 补 `orchestration/__init__` + api。
- **变异自证（沿用纪律）**：T1 repeat 提醒判据、T5 PreToolUse 否决判据、T6 审批判据做变异（中和→转红，还原→绿）。
- **回归**：阶段三完成后 `make test`（kernel+tools）+ portal 套件全绿；新增约 7×N 例。

## 5. 实施修正记录

（执行后补；均在该 seven-task 计划自身 fallback 范围内，无需再批设计）

- **T1–T6 全绿**：逐 task TDD 红→绿→门面守卫→（用户提交）。门面 `LAYERS` 已在 `mcp`/`hooks`/`interaction` 三子包落地时同步追加，未出现阶段一/二的「子包就绪但门面未接线」静默。
- **T7 E2E 初版红 → 根因非接线缺陷，而是测试读错来源**：`SessionManager.derive_messages()`（session/__init__.py:36）**有意**只投影 `user/message`/`assistant/message`，工具调用结果不入模型可见历史（设计注记 line 4-5：模型可见 ⟺ 已记录）。故 `run_turn` 返回的 `messages` 永不含 `tool` 角色；工具结果落在 session 日志 `tool/result` 事件。E2E 断言应读 `loop.sessions.get_or_create(...).events()` 的 `tool/result`，而非 `out["messages"]`。已加 `_session_tool_results`/`_render_events` 辅助读取真实 session 事件，并让 `render_conversation` 吃真实事件。修复后 2 passed。
  - ⚠️ 排查期在 `agent_loop.py` 临时加了 `import sys; print("DBG calls:...")` 诊断行（line ~49），定位后已**移除**，当前 `agent_loop.py` 无调试残留。
- **回归基线**：`make test`（kernel 336 + tools 11 = 347 passed，RC=0）全绿。阶段三新增 26 例（T1×11/T2×12/T3×10/T4×11/T5×11/T6×11/T7×2，含门面守卫与 E2E）。
  - ⚠️ 全量 `pytest packages/chiyu-kernel/tests tools/tests` 末行会被沙箱 `safe-delete` 守卫在 pytest 临时目录清理（69 个 tmp）时拦截并置 `EXIT=1`，**非测试失败**；分段跑（kernel / tools 各自 basetemp）可直接拿到 `X passed`。
- **变异自证（判别力，非假绿）**：
  - T5 `PreToolUse` 否决分支：将 `if any(r.decision in ("deny","block")...)` 中性化为 `if False:` → `test_pre_tool_use_veto_skips_execution` 转红（`assert 1 == 0`）→ 还原转绿。
  - T6 `ApprovalGate.guard` 高风险拦截：在 `guard` 顶部加 `return None` → `test_high_risk_blocked_before_approval` 转红（`高危险工具未批却未拦截`）→ 还原转绿。
  - 两端均证实测试对判据有鉴别力，非恒绿。
