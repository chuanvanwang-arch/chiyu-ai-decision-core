# 设计稿：DSH 前端 + 本平台后端的桌面客户端

> 状态：brainstorming（待批准）→ writing-plans → 实现
> 关联：DeepSeek Harness Python 移植 phase1-4（已收口，361 passed）
> 约束来源：用户 2026-09-25 决策 —— 交付形态=桌面安装包；前端=复用 DSH client UI 换后端；语音=暂缓

---

## 1. 决策基线（已确认）

| 项 | 决策 |
|---|---|
| 交付形态 | 桌面安装包（Electron / Tauri 待二选一，见 §7 R1） |
| 前端来源 | **复用 DSH `packages/client` 的 `ui-*` 模块**，替换通信层接 `chiyu_kernel` |
| 语音 | **暂缓**（DSH 源码无语音实现，首版不做，留后续 phase） |
| 后端 | 本平台 `chiyu_kernel`（phase1-4 已吸收 skill/subagent/plan·todo/workflow/mcp/fs/shell/hooks/interaction）+ `chiyu-decision`/记忆/库表（本平台独有，DSH 无） |
| 目标能力 | DSH 前端观感（对话/选插件/多模型/agent 调度/workflow 编排）+ 本平台后端（决策、记忆、库表） |

---

## 2. DSH 客户端架构（实读 `packages/bundle/*/cordis.patch.yml` 结论）

- **插件 = Cordis Loader entry**；`profile = base + (web-app | headless)`。
- **首启动地基 `dsh-base` = 78 插件**（全 profile 共有）；`dsh-web-app` 在其上**净新增 ≈52**（host 传输层 + 51 个 `ui-*` 浏览器插件 + `agent-presets`）；`dsh-headless` 仅 +3。
- **客户端运行时栈**（web profile）：
  `modules`（shell kernel 构造 module table → `window.__DSH_BOOT__`）
  → `connection`（fetch/SSE 双端）
  → `api-remotes`（Typert RPC 客户端）
  → `client-runtime` / `cordis-client-runner`（Cordis client 实例）
  → `ui-*` 插件（消费 host 经 Typert 暴露的 Remote 服务）
- **host 侧**（本仓要替换的部分）：`webserver` + `api-gateway`（Typert）+ `plugin-inventory` + `agent`/`session`/`llm` 服务。
- **前端 UI 模块（复用对象）**：`ui-conversation`、`ui-settings-plugins`、`ui-settings-plugin-inventory`、`ui-model-selection`、`ui-subagent`、`ui-workflow-run`、`ui-plan`、`ui-goal`、`ui-jobs`、`ui-tool`、`ui-sidebar`、`ui-layout`、`ui-input-trigger`、`ui-commands`、`ui-skill`、`ui-message-feedback`、`ui-theme`、`ui-agent-preset` 等。

---

## 3. 集成接缝（核心难点）

DSH client 的 `ui-*` 通过 **Cordis client runtime** 消费 host 经 **Typert Remote** 暴露的服务。换后端为 `chiyu_kernel` 有两条路线：

- **路线 A（推荐，最贴合「复用 DSH client 换后端」）—— 协议桥接**：
  在 `chiyu_kernel` 侧新增 `chiyu-host`（或扩展 `chiyu_kernel.api`）暴露**与 DSH client 期望同构的 Remote 服务**（conversation / model-selection / plugin-inventory / agent / subagent / workflow / session），前端 `connection`/`api-remotes` 指向本桥。
  代价：须复刻 DSH client 的 Typert 协议契约（方法名/参数/错误码）。
- **路线 B —— 自研薄通信层**：
  不复用 DSH 的 `connection`/`api-remotes`，改 `chiyu_kernel` 暴露 REST/SSE，前端写新 transport；DSH 的 `ui-*` 需解耦其 Cordis 依赖（工作量最大，DSH 观感保留度低）。

→ **路线 A** 与「复用 DSH client UI」一致，优先。

---

## 4. 后端需补齐的能力面（chiyu_kernel 侧，对照 DSH client 期望）

| DSH client 期望服务 | chiyu_kernel 现状 | 需补齐 |
|---|---|---|
| conversation 事件流 | `render_conversation` 是纯函数；无会话事件推送服务 | 新增会话事件服务 + SSE 推送 |
| model-selection / 多 LLM | `llm` 抽象有，但 provider 注册（deepseek/pi-ai）待接（Phase B） | 暴露 model 列表 + 切换 + 接 provider |
| plugin-inventory | `api.py` 的 `LAYERS` + 各子包 `__all__` = 插件清单（含 enable 语义） | 暴露为 inventory 服务（list/enable/disable） |
| agent 调度可视化 | `subagent`/`workflow` 运行时已有（phase2/4） | 暴露 run/trace 给前端 |
| 决策/记忆/库表 | `chiyu-decision` + 本仓记忆/存储层 | **本平台独有优势**，需面板 UI + 服务 |

---

## 5. 桌面外壳

- **Electron**：生态成熟、DSH 若用 Electron 可参考；包体大、需处理 node 集成与安全。
- **Tauri**：Rust 后端、包体小、安全模型好；前端走系统 webview，DSH client 的浏览器特性需验证。
- **外壳职责**：启动/连接本地 `chiyu_kernel` 后端进程（或远程）、加载 DSH client 构建产物、提供原生菜单/托盘/文件访问。
- **打包**：electron-builder / tauri bundler → exe/dmg；首版可先 dev 模式（vite + 本地后端）跑通，再补安装包。

---

## 6. 分阶段落地（建议）

- **M0 接入验证**：DSH client 构建跑起来 + 本地 `chiyu_kernel` 后端 + 最小桥（conversation + model-selection）端到端。
- **M1 插件清单 + 选插件 UI** 接 `chiyu_kernel` `LAYERS`。
- **M2 agent/subagent/workflow 调度 UI**（接 phase2/4 运行时）。
- **M3 决策/记忆/库表面板**（本平台独有）。
- **M4 桌面打包（Electron/Tauri）+ 安装器**。
- **语音**：后续 phase。

---

## 7. 风险与待决

- **R1** Electron vs Tauri 选型（影响外壳代码栈）。
- **R2** Cordis client 协议复刻成本（路线 A 须对齐 Typert 契约，否则退路线 B）。
- **R3** DSH client 的 `ui-*` 对 dsh-* host 服务耦合度（需逐模块解耦评估，见 M0 探针）。
- **R4** 本仓 `llm` provider 尚未接（Phase B），多模型切换需先接 provider。
- **R5** 进程模型：桌面壳内嵌 `chiyu_kernel` 进程 vs 远程，影响插件清单/会话持久化。

---

## 8. 下一步（待批准）

1. 锁定 **R1 Electron/Tauri** 与 **路线 A/B**（二选一）。
2. 启动 **M0 探针**：拉起 DSH client 构建 + 本地 `chiyu_kernel`，验证 `ui-conversation` 经桥接连后端的最小闭环，并输出 `ui-*` 对 host 服务耦合清单（R3）。
3. 批准后进入 writing-plans，逐 M 落地。
