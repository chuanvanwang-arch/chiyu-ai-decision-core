# 实施计划：M0-T3 DSH client 真渲染闭环（重建 clientModules + 同源托管）

> 阶段：writing-plans（路线已定：重建 clientModules + 真渲染）
> 关联：M0 总计划 `2026-09-25-dsh-client-chiyu-backend-plan.md`、R3 耦合矩阵 `2026-09-25-dsh-client-r3-coupling.md`、T2 桥接 `chiyu-host`（已收口 `a8b18b3`）
> 决策：用户选「重建 clientModules + 真渲染」（最高保真）。

---

## 0. 关键事实（实测，约束本次实现）

- **DSH client API base = `window.location.origin`**（`connection/src/client/rpc.ts:52`）。要让 client 打 chiyu-host，页面必须由 chiyu-host **同源**提供 ⇒ chiyu-host 同时托管静态 client + `/api/*` RPC + `WebSocket /api/events.mux`。
- **`__DSH_BOOT__` 是 DSH host 运行时合成**（`packages/client/modules/src/index.ts` `ClientModuleRegistry.compose()`），非静态产物。`apps/web` 的 vite `dist/` 只有 shell，boot 图由 host 在 serve 时注入 `<head>`。
- **boot 图可离线复刻**：`compose()` 仅扫描「声明 `dsh.client.platform==='web'` 的包」，每条 `{id:包名, url:'/plugins/<id>/client.js?rev=<sha1-12>', rev, inject?, immediately?}`。`rev` = 包体 sha1 前 12 位。chiyu-host 扫描 DSH `packages/client/*`（+`packages/web-*`）的 `package.json` 即可复刻，**无需跑 DSH host**。
- DSH client 是**薄校验调用层**：RPC 走 `POST /api/<method>`+`ClientRequest` 信封，响应用 `serverResponseSchema` 校验；mux 走 `WebSocket /api/events.mux` 下行 `ServerRequest`/`MuxFrame`。chiyu-host(T2) 已对齐这些 schema。

## 1. 目标

chiyu-host 同源托管 DSH client（注入 boot 图 + serve `/plugins/<id>/client.js` + vite assets），浏览器打开即渲染 `ui-conversation` + `ui-model-selection` + `ui-settings-plugins`，数据全部来自 chiyu_kernel（经 T2 桥接）。记录降级阻断点回填 R3。

---

## 0.5 实施事件（2026-09-25）：DSH install 被沙箱黑名单阻断 → 回退路线 A

- `pnpm install`（后台 31min）失败，根因两层：
  1. **沙箱程序黑名单拦 `wmic.exe`**（`PROGRAM BLOCKED BY SECURITY POLICY`，无法从当前命令批准/绕过，需用户在「安全中心→命令安全→程序黑名单」移除）；
  2. **沙箱写拦截** pnpm-cache/store 临时文件 + 由此引发的 `minimumReleaseAge` 核实超时（44 个 lockfile 条目「无法核实」被拒，非真策略违规）。
- 网络正常（npmjs 1.7s / npmmirror 2.4s 均可达），lockfile 合法（`minimumReleaseAgeExclude` 已列 pi-ai 等）。
- **按 T3-1 门**：不假绿硬凑全量构建 → 回退 headless 契约验证（路线 A）。已落地且验证的 T3-2/T3-3（boot 图重建 + 同源托管）与路线 A 不冲突，保留。
- 已提交 `7ef3450`（T3-2/T3-3 代码 + 本计划）。
- **何时可重启路线 B**：用户在安全中心移除 `wmic` 后重跑 install（`pnpm clean --lockfile && pnpm install`）；或换免 wmic 环境（如 CI/Linux）。

## 2. 任务分解

### T3-1 构建 DSH client 产物（在 reference，不改源码）
- `pnpm install`（后台探针，task `9XSrEc`）。
- `pnpm build:lib:client` → 各 client 包 `client.js` 懒加载包（确认输出路径，预期 `packages/client/<x>/dist/client.js`）。
- `pnpm --filter @deepseek-ai/dsh-web-frontend run build` → `apps/web/dist/` shell。
- ⚠️ 门：安装/构建失败（网络/版本）→ 立即上报，建议回退 headless 契约验证（路线 A），不假绿。

### T3-2 chiyu-host 重建 clientModules（新模块 `web.py`）
- **BootGraph 合成器**：读 `DSH_CLIENT_DIR`（默认 `D:/system/reference/deepseek-harness-master`）下 `packages/client/*/package.json`，筛 `dsh.client.platform==='web'`，解析 `exports["./client"]`→abs 包体路径，算 `rev=sha1(content)[:12]`，构 `WebBootGraph`。
- **静态路由**（Starlette `Route`/`StaticFiles`）：
  - `GET /` → `apps/web/dist/index.html`，注入 `<script>window.__DSH_BOOT__ = <graph></script>`（`<` 转义，同 DSH `injectBootManifest`）。
  - `GET /assets/*` → vite assets（`StaticFiles`）。
  - `GET /plugins/<id>/client.js` → 对应包体（忽略 `?rev=` 查询），`content-type: text/javascript`。
- 复用 T2 的 `POST /api/<method>` RPC 路由器 + `WebSocket /api/events.mux`（不重造）。

### T3-3 同源接线 + 启动
- chiyu-host `app.py` 组装：RPC 路由 + mux WS + web 静态路由，单 origin 启动（uvicorn `:port`）。
- `GET /api/boot` 返回 boot 图 JSON（便于核验/调试，非必需）。

### T3-4 浏览器真渲染验证 + 阻断点回填
- 启动 chiyu-host，浏览器开 `http://localhost:<port>/`。
- 断言：① ui-conversation 显示来自 chiyu_kernel 的会话（session.list/create）；② ui-model-selection 列出 llm.providers/models + agentPreset.list；③ ui-settings-plugins 列出 skill.list/subagent.list/host.describe。
- 记录降级：哪些 ui-* 因未实现域静默降级（如 ui-subagent 缺 subagent.prompt 等）→ 回填 R3 §5。

## 3. 文件布局

- 新增：`packages/chiyu-host/src/chiyu_host/web.py`（clientModules 重建 + 静态托管）。
- 新增：`packages/chiyu-host/tests/test_web_boot.py`（boot 图合成单测：扫描 DSH 包→条目数/字段对齐 `WebBootEntry`；注入 HTML 含 `__DSH_BOOT__`）。
- 复用：T2 `app.py`/`bridge.py`/`methods.py`。
- DSH 构建产物经 `DSH_CLIENT_DIR` 引用，**不复制、不提交**（vendor 引用；构建步骤写入 README）。

## 4. 风险与门

- R-build：DSH monorepo 安装/构建失败 → 上报 + 回退路线 A。
- R-boot：boot 图格式错（rev/url 不符）→ 浏览器白屏；以 `test_web_boot.py` 单测锁形。
- R-cors：同源托管天然规避 location.origin 绑定；若误跨域会 CORS 失败，单 origin 规避。
- 提交纪律：chiyu-host web 模块独立 commit；DSH 产物不入库。

## 5. 完成判据

- chiyu-host 同源托管 DSH client，boot 图正确注入；浏览器渲染 3 个 UI 模块且数据来自 chiyu_kernel；`test_web_boot.py` 绿；降级清单回填 R3。
