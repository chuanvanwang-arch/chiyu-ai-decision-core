# 阶段五：workflow 真进程外并行调度（worker pool）· 设计文档

> 源偏差：phase4 计划 §4 登记「dsh `workflow` 是 JS 脚本执行引擎（Cordis+worker-thread），本仓无 JS 运行时 → 改用声明式 steps + 复用 SubagentPool.delegate；进程外执行非本阶段范围」。
> 本设计为该偏差的收口：把 `WorkflowRunner` 从串行 `await delegate` 升级为「每 run 一隔离子进程跑 DAG 调度 + 父进程并发池执行子智能体」，忠实吸收 dsh `parallel()` / `AGENT_CAP` / `WorkerRun` 生命周期。
> 设计批准：2026-09-25 用户批准（brainstorming P5）。

## 1. 架构（host/worker 分工，镜像 dsh host.ts ↔ worker）

```
┌─ 父进程 (host.py · WorkerRun) ──────────────────────────┐
│  spawn(multiprocessing.Process)  ← WorkerInit(JSON)      │
│  child-start{prompt} ──► SubagentPool.delegate()          │  ← 复用 AgentLoop / redline / 审批闸
│        ▲                      │ result(JSON)              │
│        └──── child-settled ───┘                            │
│  cancel() ──► grace timer ──► terminate()                 │  ← 有界生命周期（吸收 dsh WorkerRun）
│  result 永不 reject；第一 settle 赢                        │
└──────────────────────┬────────────────────────────────────┘
            双向 multiprocessing.Queue（协议镜像 dsh HostToWorker/WorkerToHost）
┌─ 子进程 (worker.py · 调度 realm) ───────────────────────┐
│  DAG 拓扑分层 → asyncio.Semaphore(max_concurrency)         │  ← 忠实 dsh parallel() + AGENT_CAP
│  独立 step 并发投 child-start；等 child-settled            │
│  组合子纪律：非 fatal→None / fatal→整 run error            │
│  cancel→停投新 step + 终止在途；grace→强制 exit            │
└──────────────────────────────────────────────────────────┘
```

- **子进程只做调度**：拓扑/并发/取消/清理，scrubbed env（无凭据、不 import `llm`/`tools`）。
- **父进程只做执行**：真正的 LLM 子智能体经 `SubagentPool.delegate()` → `AgentLoop`，复用全护栏。
- **R2 守住**：不新建平行 driver 框架；子进程经 Queue 把 `agent()` 子调用回传父进程执行，与 dsh worker-thread 把 `subagents.start()` 留在 host 完全一致。

## 2. 组件职责

| 组件 | 进程 | 职责 |
|------|------|------|
| `workflow/worker.py` | 子 | `run_worker(init, recv, send)`：吃 `WorkerInit`（steps/args/meta/max_concurrency/provider，纯 JSON）；跑 DAG；并发池派发；组合子纪律；生命周期（cancel/grace force-exit）；发 `result`。 |
| `workflow/host.py` | 父 | `WorkerRun`：spawn 子进程；`on_message` 分发 Queue；`child-start`→`SubagentPool.delegate()`→`child-settled`/`child-failed`；`cancel()`（grace→terminate）；`dispose()` 静默清理在途 child；`result` 永不 reject；边界值 JSON 校验。 |
| `workflow/runner.py` | 父 | `WorkflowRunner.run()` 改构造 `WorkerRun`（替代直接串行 delegate）；形状不变（`WorkflowResult`）；`register` 幂等注册子描述（父进程侧 `SubagentPool`）；`max_concurrency` 注入。 |
| `workflow/__init__.py` | — | 暴露 `WorkerRun` / `run_worker`（补门面 `__all__`）。 |

## 3. 并发与生命周期语义（忠实 dsh）

- **并发上限 `max_concurrency`**：默认 **4**，经 `WorkflowMeta.max_concurrency`（新增可选字段，向后兼容）或 `WorkflowRunner` 构造参数注入；对应 dsh `AGENT_CAP`。
- **组合子纪律（不变）**：非 fatal 子失败→该 step `None` 其余继续；fatal `WorkflowError`→整 run `error`；`signal.cancelled`→`cancelled`。
- **有界生命周期（新增，吸收 `WorkerRun`）**：`cancel()` 播 cancel + 启动 `dispose_grace_ms`（默认 5000）定时器，未 settle 强制 `terminate()`；worker 崩溃/exit→合成 `error`（未取消）或 `cancelled`（已取消）；`result` 永不 reject。
- **边界值**：child 结果必须经 JSON 可序列化校验，否则对应 dsh `RESULT_UNSERIALIZABLE` fatal（忠实）。

## 4. 测试计划（TDD + 变异自证，非假绿）

- **T1 worker 调度单测**（注入 fake executor over Queue）：DAG 并发 / 依赖顺序 / 非 fatal→None / fatal→error / cancel→cancelled。
- **T2 host 生命周期单测**：cancel→grace→terminate / worker 崩溃合成 error / child 不可序列化→fatal。
- **T3 真 multiprocessing 集成 E2E**：独立 step 确并发（时延叠加 < 串行）；fatal 杀整 run；phase4 既有 25 测试形状不变（回归）。
- **T4 门面接线**：`workflow` 已在 `LAYERS`，补 `host`/`worker` 到 `api.py` `__all__`。
- **T5 变异自证**：T1 的 `if e.fatal:` 与 T2 的 grace `terminate` 分支中性化→对应测试转红→还原绿。

## 5. 风险与纪律

- ⛔ T3 用真子进程，单测用 Queue + fake executor 避免慢/flaky；grace 超时在测试里缩到百毫秒级（注入 `dispose_grace_ms`）。
- ⛔ 子进程不得 import `llm`/`tools`/凭据；`WorkerInit` 仅含 JSON 数据（steps/args/meta/max_concurrency/provider）。
- ⛔ 守卫自身的覆盖度也要被守卫：facade 守卫（`test_api_facade_covers_all_layers.py`）在新增 `host`/`worker` 符号后须仍绿。
- 提交纪律：分层提交、单行 `-m`、显式 `git add`、不 `-A`、AI 不 commit。
- 偏离已批准设计：仅经用户显式批准的设计变更才落地；本文件即 phase5 唯一依据。

## §A 生命契约（双轨）

```contract-yaml
- task: "实现子进程调度 realm worker.py（DAG 并发 + 组合子纪律 + 生命周期）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-multi-agent-orchestration]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "单测：独立 step 经 asyncio.Semaphore(max_concurrency) 并发派发；非fatal→None、fatal→整run error、cancel→cancelled"
- task: "实现父进程执行器+生命周期 host.py（WorkerRun：Queue 分发/cancel-grace-terminate/child 静默清理/边界值 JSON 校验）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-multi-agent-orchestration]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "单测：cancel→grace 超时→terminate；worker 崩溃合成 error；child 结果不可 JSON 序列化→fatal"
- task: "接线 WorkflowRunner→WorkerRun + 门面暴露 host/worker"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-multi-agent-orchestration]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "phase4 既有 25 测试形状不变全绿 + 真 multiprocessing E2E 证明独立 step 并发（时延叠加<串行）"
```

**契约说明（prose）：**
- 任务 1 由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），须调用 `ai-multi-agent-orchestration` SKILL、读本仓 `chiyu-foundation` 记忆（L1/L2，≤2 跳）；成功标准为子进程 DAG 并发调度单测全绿。
- 任务 2 同 agent/契约键，成功标准为父进程 `WorkerRun` 生命周期单测（取消/优雅退出/崩溃合成/边界值）全绿。
- 任务 3 同 agent/契约键，成功标准为门面接线后 phase4 回归不变 + 真进程外 E2E 证明独立 step 并发。

## 闭环回写

> 阶段五 Inline Execution 已全量收口（T1–T6），以下为执行期实测修正回填（非假绿）：

| task | agent | gap_type | observed | expected | ts | severity |
|------|-------|----------|----------|----------|----|----------|
| T3 host.start | kernel | 进程模型 | `queue.Queue` 在 Windows spawn 下 `TypeError: cannot pickle '_thread.lock'` | 真实进程路径必须用 `multiprocessing.Queue` | 2026-09-25 | P0-fixed |
| T3 host↔worker 接线 | kernel | 协议 | host pump 读空队列挂死（Queue 方向反了） | worker.recv=host._send / worker.send=host._recv；且 `W_READY→W_GO` 必须回 | 2026-09-25 | P0-fixed |
| T4 run() 取消语义 | kernel | 语义 | phase4 `test_cancel_signal_stops_run` 中途翻 signal 在进程外不保真 | 启动前 `signal.cancelled` 预检查；中途取消改由 `WorkerRun.cancel()`(grace→terminate) | 2026-09-25 | P1-fixed |
| T5 并发 E2E | kernel | 测试 | 绝对阈值 `dt<0.5` 在真机被 spawn 固定开销(~0.73s)淹没 | 同环境对照 `cap=1`(串行) vs `cap=4`(并发)，断言 `parallel<serial-0.1` | 2026-09-25 | P1-fixed |

提交：`0827dcb`(T1) `624bf4c`(T2) `fa73848`(T3) `23c4129`(T4) `633532c`(T5) `662f985`(host 修复+计划文档)。全量回归 kernel 373 + tools 11 = 384 passed，门面守卫 7 passed。
