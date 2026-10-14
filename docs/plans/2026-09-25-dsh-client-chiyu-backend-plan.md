# 实施计划：DSH 前端 + 本平台后端 桌面客户端（M0 → M4）

> 阶段：writing-plans（待批准 → executing-plans）
> 关联设计稿：`docs/plans/2026-09-25-dsh-client-chiyu-backend-design.md`
> 已锁定决策：交付=Electron 桌面安装包；前端=复用 DSH `packages/client` 的 `ui-*` 模块；后端=换 `chiyu_kernel`；集成=路线 A 协议桥接；语音=暂缓。
> 契约事实（实读 `D:/system/reference/deepseek-harness-master`）：DSH client 经 `packages/client/connection/src/client/{web-api-client,rpc}.ts` 对接 host `packages/host/apiproxy/src/api/*.ts` 的 **REST+SSE 契约**，共 **37 个 api 域**（含 `events` SSE mux、`sessions`、`llm`、`skills`、`subagents`、`agent-presets`、`approvals`、`jobs`、`goals`、`workspace`、`settings`、`credentials`、`questions`、`host` 等，由 `rpc-map.ts`/`rpc.ts` 的 `RpcMethodMap` 分发）。

---

## 0. 全局技术约束（已核实，必须遵守）

- **后端语言 = Python**：`chiyu_kernel` 是 Python 库（phase1-4 已收口，361 passed）。桥接层 `chiyu-host` 必须用 Python 实现 HTTP/SSE 契约，DSH client（TS）语言无关，零改对接。
- **前端启动依赖 `window.__DSH_BOOT__`**：`apps/web` 非独立 vite（其 `vite.config.ts` 显式 `rejectStandaloneServe`），必须经 `pnpm dsh web` 启动器注入 boot manifest。M0 有两种接法：
  - (i) **复用 DSH 完整启动链**：把 `dsh web` 的 webserver 换成我们的 `chiyu-host`，保留 boot 注入；
  - (ii) **自建最小 boot 注入**：M0 先用一个 thin launcher 注入 `__DSH_BOOT__`，把 client 的 connection base URL 指向 `chiyu-host`。
  - M0 选 **(ii)** 降低耦合，验证桥接后再推进 (i)。
- **R4 提醒**：`chiyu_kernel` 的 `llm` 抽象已就位但 **provider 尚未接（Phase B）**。M0 的 `llm` 域可先返回静态/默认模型列表（deepseek-v4-flash），真实多 LLM 切换待 Phase B 接 provider 后激活。

---

## M0 — 接入验证 + R3 耦合探针（本计划核心交付）

**目标**：① 产出 `ui-*` 对 host api 域的耦合矩阵（R3 去风险）；② 跑通 `ui-conversation` + `ui-model-selection` 经桥接连 `chiyu_kernel` 的最小闭环。

### M0-T1 R3 耦合探针（先读后写，不允许凭空）
- 对 `packages/client/**` 全量 grep 各 `ui-*` 模块实际 import/call 的 apiproxy 域（特征：`from '@deepseek-ai/dsh-host-apiproxy/...'`、`rpc.agentPreset.*`、`rpc.session.*`、`rpc.llm.*`、`rpc.skill.*`、`rpc.subagent.*`、`events.mux` 等）。
- 产出 **耦合矩阵表**：行=`ui-*` 模块，列=依赖的 api 域，标注「强依赖(缺失即崩溃)/弱依赖(降级可用)」。
- 判定 M0 最小桥接必须覆盖的域（预期=`events`+`sessions`+`llm`+`skills`+`subagents`）。
- 输出文件：`docs/plans/2026-09-25-dsh-client-r3-coupling.md`。

### M0-T2 `chiyu-host` 桥接骨架（Python，FastAPI/Starlette）
> 契约修正（见 R3 探针 `2026-09-25-dsh-client-r3-coupling.md`）：`connection` 只消费**单一 RPC 端点 + SSE mux**，37 域 = 52 个 `RpcMethodMap` 方法的归属，非独立 REST 控制器。故 `chiyu-host` 实现**一个 RPC 路由器 + 一个 SSE 流 + boot 注入**，而非 37 个 REST 控制器。

- 新建 `packages/chiyu-host/`（参考本仓 `pyproject` 布局；复用 `chiyu_kernel.api` 门面）。
- **RPC 路由器**：`POST /api/<method>` 按 `RpcMethodMap` 分发到 chiyu_kernel 处理函数。M0 实现子集（≈14 方法）：
  - 对话：`session.list/create/history/prompt/cancel/models/selectModel`
  - 模型：`llm.providers/models`、`agentPreset.list`
  - 插件清单（集中封装后台插件首落地）：`skill.list`、`subagent.list`、`host.describe`
  - 每个方法响应形状须与 `apiproxy/src/api/<domain>.ts` 的 `XxxApi` 接口逐字段对齐（防假绿）。
- **SSE 流**：`GET /api/events/mux` → 推送 `session/*` 事件帧（来自 `chiyu_kernel.session` + `render_conversation` 渲染意图）。
- **boot 注入**：thin launcher 注入 `window.__DSH_BOOT__`（`modules` 插件扫描 client 树生成），base URL 指向 `chiyu-host`。
- 单元测试（`packages/chiyu-host/tests`）：RPC 方法响应形状 + SSE 帧对照 apiproxy schema 一致；`TestClient` 跑绿。
- ⚠️ 守卫：契约字段不得私自删减；M0 只做子集，但每个实现方法须与对应 `*.schema.ts` 逐字段对齐。

### M0-T3 DSH client 接线（thin launcher）
- 在 DSH 仓库侧（或本仓 `vendor/` 引用）准备一个 **boot-injection launcher**：注入 `window.__DSH_BOOT__`，将 `web-api-client` 的 base URL 指向 `chiyu-host` 本地端口。
- 启动 `chiyu-host` + client，验证：
  - `ui-conversation` 显示一条来自 `chiyu_kernel` 的会话事件（哪怕静态/回显）；
  - `ui-model-selection` 列出 `chiyu-host` 返回的模型；
  - `ui-settings-plugin-inventory` / `ui-settings-plugins` 列出 `skills`+`subagents`（若 M0 接入了这两个域）。
- 记录阻断点（哪些 `ui-*` 因未实现域而降级），回填 R3 矩阵。

### M0 完成判据
- R3 耦合矩阵已落盘；`chiyu-host` 子集端点单测绿；DSH client 经桥接在 Electron/本地 dev 下跑通 `ui-conversation`+`ui-model-selection` 最小闭环；阻断点清单已记录。

---

## M1 — 插件清单 + 选插件 UI 接 `chiyu_kernel`
- 扩展 `chiyu-host` 覆盖 `skills`/`subagents`/`agent-presets` 全量；`ui-settings-plugin-inventory`+`ui-settings-plugins` 可浏览/启停本平台插件。
- 接 `chiyu_kernel` 的 `skill` 注册表（phase2）+ `subagent` 委派（phase2）+ `plan`/`todo`/`workflow`（phase4）作为「后台插件」呈现。

## M2 — agent/subagent/workflow 调度 UI
- `chiyu-host` 覆盖 `subagents`/`jobs`/`goals`/`workflow` 域；前端 `ui-subagent`+`ui-workflow-run`+`ui-plan`+`ui-goal`+`ui-jobs` 接 phase2/4 运行时，可视化委派/编排链路。

## M3 — 决策/记忆/库表面板（本平台独有）
- 新增本平台专属域（非 DSH 所有）：`decision`/`memory`/`tables` 经 `chiyu-decision` + 本仓记忆/存储层暴露；前端新增对应面板（DSH 无此部分，需新 `ui-*` 或嵌入 `chiyu_portal` 渲染产物）。

## M4 — Electron 桌面打包 + 安装器
- Electron 外壳：内嵌/连接本地 `chiyu-host` 进程（或远程），加载 DSH client 构建产物，原生菜单/托盘/文件访问。
- 打包：electron-builder → exe/dmg；首版可先 dev 模式验证，再补安装包。

## 语音
- 后续 phase（DSH 源码无语音，必为 net-new；浏览器 Web Speech API 或后端 STT/TTS 待 M4 后评估）。

---

## 风险登记（继承设计稿 §7）
- **R1** Electron（已定）。
- **R2** 协议复刻成本：M0-T2 逐字段对齐 apiproxy schema，降低。
- **R3** `ui-*` 对 dsh-* host 耦合：M0-T1 探针解决。
- **R4** llm provider 待接（Phase B）：M0 静态模型列表占位。
- **R5** 进程模型：M0 先本地 dev 双进程（chiyu-host + client），M4 再内嵌。

## 提交纪律
- 每 Task 一 commit；显式 `git add` 路径，禁 `git add -A`；AI 不 commit。
- `chiyu-host` 为新增包，独立提交；DSH 侧 launcher 改动若落 DSH 仓库须另议（建议以 `vendor/` 引用 + 本仓 thin launcher 为主，不改 DSH 源码）。
