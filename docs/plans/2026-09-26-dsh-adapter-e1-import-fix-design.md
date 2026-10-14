# DSH 适配层 E1 违例修复（brainstorming 设计稿）

> 状态：**已批准 + 已落地 + 已验证**（E1 修复由并发会话实现，未走 writing-plans 闸门；本稿补作事实源收口，守「设计稿为唯一事实源」铁律）。仓边界：本稿落 `chiyu-foundation`（唯一事实源）；代码改动落 `chiyu-enterprise`。AI 不 commit。
> 触发：全量回归仅剩 1 失败 `test_consumes_facade_only::test_only_facade_imports`（E1 违例）。

## 0. 背景与约束

E1 守卫（分层铁律）：`enterprise` 包**只可** `import chiyu_kernel.api` / `chiyu_kernel.contract`，任何 `chiyu_kernel.<内部路径>` 即违约。门面存在的理由：`chiyu_kernel.api` 是唯一公开面，内部实现可重构而不破坏消费方（T9 Cython 编译会改模块布局）。

`tests/test_consumes_facade_only.py` 的 `_internal_imports()` 用 AST 扫描 `packages/enterprise/src/**/*.py`，收集所有 `chiyu_kernel.<非 api/contract>` import。当前违例：

- `host/dsh_adapter/bridge.py`：`from chiyu_kernel.session import SessionEvent`（1 处）
- `host/dsh_adapter/methods.py`：`session` / `skills` / `plugins` / `events` / `llm.client` / `tools` / `orchestration.subagent` / `orchestration.agent_loop` / `orchestration.agent_runtime` / `context` / `harness_native_tools`（11 处，共 12 违例）

## 1. 关键实测（trust-but-verify · P1 探索）

- `chiyu_kernel.api`（单一模块 `api.py`，非目录）**已 re-export 上述全部所需符号**：
  `SessionEvent/SessionLog/SessionManager`（api.py:257）、`SkillRegistry/load_catalog`（:268）、`MODE_PRESETS/DEFAULT_MODE_ID`（:386）、`EventBus`（:203）、`StubProvider/LlmResponse`（:233）、`ToolRegistry`（:364）、`SubagentDescriptor/SubagentPool`（:166）、`AgentLoop`（:164）、`Agent`（:163）、`assemble/KnowledgeNeed/KNOWLEDGE_NEEDS_DEFAULT_DIMS`（:316）、`register_native_tools/native_redline_guard`（:383）。
- `import chiyu_kernel.api` 实测**干净导入、零缺失符号、不触发 pg 连接**（api 的 `PgVectorStore` 仅 `open_store` 时惰性建连，模块级 `_store=None`）。
- `methods.py` 原注释称「api 门面会触发 pg 依赖」已**过时**——实测 import 安全。

**结论：E1 修复 = 纯 1:1 import 路径替换，无需改 `chiyu_kernel.api`（门面已全覆盖），无需 foundation 改动。**

## 2. 方案（P3 · 推荐 B，已排除 A/C）

| 方案 | 改动 | 优劣 |
|---|---|---|
| A 新增 `chiyu_kernel.runtime` 公共面 + 放宽 E1 白名单 | foundation 新模块 + 改测试白名单 | 过度设计；门面 `api` 已暴露所需符号，无需新面 |
| **B 1:1 import 替换为 `chiyu_kernel.api` ✅** | `bridge.py` 1 行 + `methods.py` 11 行改 import 源 | 最小、零行为变更（同符号）；门面已就绪；E1 即绿 |
| C 在 enterprise 内建 shim 重导出内部模块 | enterprise 加 `_shims.py` | **无效**——shim 自身仍 import 内部模块，E1 扫描仍红（无豁免机制） |

**选定 B**：`bridge.py` 与 `methods.py` 的所有内部 import 改为 `from chiyu_kernel.api import <符号>`；`methods.py` 既有 `from chiyu_kernel.contract import particle/decision/memory` **保留**（contract 属白名单）。

## 3. 设计（P4 · 任务分解）

### T1 bridge.py 单点替换
`from chiyu_kernel.session import SessionEvent` → `from chiyu_kernel.api import SessionEvent`。

### T2 methods.py 11 处替换（逐符号对齐 api 导出名）
- `from chiyu_kernel.session import SessionManager, SessionLog` → `from chiyu_kernel.api import SessionManager, SessionLog`
- `from chiyu_kernel.skills import SkillRegistry, load_catalog` → `from chiyu_kernel.api import SkillRegistry, load_catalog`
- `from chiyu_kernel.plugins import MODE_PRESETS, DEFAULT_MODE_ID` → `from chiyu_kernel.api import MODE_PRESETS, DEFAULT_MODE_ID`
- `from chiyu_kernel.events import EventBus` → `from chiyu_kernel.api import EventBus`
- `from chiyu_kernel.llm.client import StubProvider, LlmResponse` → `from chiyu_kernel.api import StubProvider, LlmResponse`
- `from chiyu_kernel.tools import ToolRegistry` → `from chiyu_kernel.api import ToolRegistry`
- `from chiyu_kernel.orchestration.subagent import SubagentDescriptor, SubagentPool` → `from chiyu_kernel.api import SubagentDescriptor, SubagentPool`
- `from chiyu_kernel.orchestration.agent_loop import AgentLoop` → `from chiyu_kernel.api import AgentLoop`
- `from chiyu_kernel.orchestration.agent_runtime import Agent` → `from chiyu_kernel.api import Agent`
- `from chiyu_kernel.context import assemble, KnowledgeNeed, KNOWLEDGE_NEEDS_DEFAULT_DIMS` → `from chiyu_kernel.api import assemble, KnowledgeNeed, KNOWLEDGE_NEEDS_DEFAULT_DIMS`
- `from chiyu_kernel.harness_native_tools import register_native_tools, native_redline_guard`（模块底部） → `from chiyu_kernel.api import register_native_tools, native_redline_guard`

⛔ 守 T9 铁律：符号名与 api 门面**完全一致**（含 `vector_*` 前缀等已改名的 5 个；本任务不涉及）。改完须跑 `tests/test_api_facade_covers_all_layers.py` 确认门面未被破坏（守卫反向覆盖）。

### T3 验证（判别力自证，防假绿）
- `pytest tests/test_consumes_facade_only.py` → `test_only_facade_imports` 转绿（`_internal_imports()==[]`）。
- 全量 `pytest tests/` → 预期 **`316 passed, 4 skipped`**（原 1 failed 消失，零新失败）。
- 变异自证：临时把任一 `from chiyu_kernel.api` 改回 `from chiyu_kernel.session` → E1 测试转红；还原 → 绿；`grep MUTATION` 零残留。

## 4. 成功标准（判定式）
`test_consumes_facade_only::test_only_facade_imports` 通过；`enterprise` 包内 `chiyu_kernel.<非 api/contract>` import 计数 = 0；全量回归零失败（仅 `4 skipped`）。

## 5. 生命契约（living contract）

```contract-yaml
- task: "DSH 适配层 E1 违例修复（import 收敛到 chiyu_kernel.api）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2] }
  success: "bridge.py/methods.py 仅 import chiyu_kernel.api/contract；test_consumes_facade_only::test_only_facade_imports 转绿；全量 316 passed 零新失败"
```

## 6. 落地与验证（retrospective 收口）

### 6.1 纪律事件（并发会话先行落地）
本修复**由并发会话先行落地**，未走 brainstorming→writing-plans 闸门（同 G0 案例）。本会话在 P5 批准节点准备实现时，经 trust-but-verify 复核发现 live 源码已为收敛态：
- `bridge.py:17` → `from chiyu_kernel.api import SessionEvent`
- `methods.py:19-39` → 单一 `from chiyu_kernel.api import (...)`（含 `register_native_tools as _register_native_tools` / `native_redline_guard as _native_redline_guard` 别名保留；顶部一并导入，原底部 `harness_native_tools` 块删除）
- `methods.py:40` → `from chiyu_kernel.contract import particle as _particle, decision as _decision, memory as _memory`（白名单保留）
- 过时注释（原「api 门面会触发 pg 依赖」）已更新为 E1 收敛说明

⛔ 后续同类内核消费方 import 改动须先走 brainstorming（本仓多会话并发，源码改动可能由其他会话落地且无设计稿，以 live 复核为准）。

### 6.2 验证（trust-but-verify，本会话实测）
- `pytest tests/test_consumes_facade_only.py` → **`2 passed`**（E1 守卫 `test_only_facade_imports` 转绿，`_internal_imports()==[]`）。
- 全量 `pytest tests/`（repo 根 `D:/system/chiyu-enterprise`，PYTHONPATH 含两 src）→ **`338 passed, 4 skipped, 0 failed`**（E1 失败消失；设计稿预估 316 偏保守——并发会话期间测试集有增量，零失败为判定关键）。
- 全仓 `from chiyu_kernel.<非 api/contract>` import 扫描：`enterprise/src` 仅余 2 处注释提及（methods.py:72、decision/__init__.py:5），无实际 import 违约。
- **变异自证**：临时把 `bridge.py:17` 改回 `from chiyu_kernel.session import SessionEvent` → `test_only_facade_imports` 立即转红（`违约 import：[('bridge.py', 'chiyu_kernel.session')]`）；还原 → `2 passed`；`grep MUTATION` 零残留。判据具鉴别力，修复非假绿、为 load-bearing。

### 6.3 待办
- 用户本地先修 `git bad tree object HEAD` 再提交 E1 相关改动（`host/dsh_adapter/bridge.py`、`host/dsh_adapter/methods.py`）+ G0 相关改动。
- 禁 `git add -A`；显式 `git add` 指定文件。
