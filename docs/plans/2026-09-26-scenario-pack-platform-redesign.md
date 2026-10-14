# 场景包 · 开发/运行双阶段平台化设计（重设计）

> 状态：**待批准**（P5 闸门）
> 日期：2026-09-26
> 上承：`2026-09-26-scenario-pack-design.md`（首版，已废）、`2026-09-26-client-enterprise-integration-design.md`（M0'，已批，复用其 RPC/治理词汇表）
> 契约键：`ct-chiyu-enterprise`（agent=`enterprise-platform-builder`）

---

## 0. 用户原意（首版理解错误，本版纠正）

用户 2026-09-26 明确纠正首版方向：**场景包不是 web 端本地生成/显示**，而是三件事：

| # | 需求原话 | 首版做了（错） | 本版设计（对） |
|---|---------|---------------|---------------|
| ① | 开发阶段，经**本地 MCP 服务**写入**平台侧**的场景包 | 包写进本仓 `web/backend/scenario_packs/` 私有目录 | 本地 **stdio MCP server** → 写入**平台 8000**（`chiyu-host`） |
| ② | 运行阶段，选不同场景包（**类 WorkBuddy 专家**）**与平台连接**，形成数据交互 | 选包仅驱动本仓 chat 链路 | **web 门户工作台(5173)** 读平台 `GET /control/scenarios` 选包 → 经 `POST /rpc/{tenant}/{client_type}/action` 与平台数据交互 |
| ③ | 开发/运行阶段用**用户名+角色**区分 | 无身份概念 | 复用平台 `/control/rbac`（admin/finance/sales_manager）：开发=写权限、运行=读+action 权限 |

---

## 1. 已确认决策（用户 2026-09-26 逐条批准）

| # | 决策点 | 结论 |
|---|--------|------|
| D1 | 平台侧 8123 真相 | **8123 只是静态壳**（`python -m http.server`，`/api/*` 全 404）；**真相 = 8000 `chiyu-host` 平台**（FastAPI，接口已就绪可访问） |
| D2 | 开发阶段 MCP 形态 | **本地 stdio MCP server**（本仓提供可执行入口） |
| D3 | 运行阶段客户端 | **web 门户工作台（localhost:5173）**，从 8000 选场景包、以 tenant+client_type 身份经 RPC 交互 |
| D4 | 用户/角色区分 | 复用平台 `/control/rbac`；开发=读+写、运行=读+action |
| D5 | 平台写接口来源 | **给本仓 chiyu-host 补 `POST /control/scenarios`**（RBAC 鉴权 + G0 决策锚），部署替换为 8000 生效 |
| D6 | 架构方案 | **方案 A**：平台管存储/鉴权、MCP 管开发写入协议、kernel 管数据结构校验，三层不重叠 |
| D7 | 契约对齐 | **双模型映射层**：MCP 收 kernel `ScenarioPack` → 适配器转平台模型 `{pkg/namespace/tenant/actions/assets/integrations/status}` 写入 |
| D8 | 承接智能体 | `enterprise-platform-builder`（键 `ct-chiyu-enterprise`） |

---

## 2. 现状实勘（trust but verify，2026-09-26 实测）

### 2.1 平台 8000（chiyu-host）能力地图

```
POST    /api/{method}                                     DSH RPC 面（dsh_rpc，与场景解耦）
GET     /control/scenarios        ✅ 场景包读（返回 {items:[{pkg,namespace,tenant,actions,assets,integrations,status}]}）
GET     /control/scenario/{name}  ✅ 单包读
GET     /control/rbac             ✅ 用户名/角色（admin/finance/sales_manager）
GET     /control/agents/{role}    ✅ 按角色 agent
POST    /control/integrations     ✅ 连接器注册（写）
POST    /control/providers/register|switch  ✅ provider（写）
POST    /control/secret           ✅ 密钥（写）
POST    /rpc/{tenant_id}/{client_type}/action|decision  ✅ 运行通道（读/写类 Action，含 confirm+写闸 G0-G3）
GET     /rpc/{tenant_id}/{client_type}/events           ✅ SSE 事件流
```
**缺口**：`POST /control/scenarios` **不存在**——开发阶段 MCP 写入缺落点（D5 补）。

### 2.2 关键事实（决定设计落点）

1. **8000 不是本仓 `packages/chiyu-host` 源码**：本仓 host 目录只有 `app.py/boot.py/bridge.py/jobs.py/methods.py/web.py`，**无 control 模块**（grep 零命中 scenarios/rbac/rpc）；8000 是独立部署的另一实例（源码仓外/已分叉）。
2. **落点结论**：补 `POST /control/scenarios` 的**正确落点是本仓 `packages/chiyu-host`**（仓边界纪律：本仓唯一事实源），由部署侧重启/替换为 8000 生效；该实例的身份不阻塞设计与本仓实现。
3. **运行通道现成**：`/rpc/{tenant}/{client_type}/action` 已具备读/写类 Action 分流 + 两阶段 confirm + 写闸 G0–G3 + 反 CRUD 爆炸（`registry.detect_crud_explosion`）——运行阶段 web 客户端直接复用，**无需新增**。
4. **用户/角色设施现成**：`/control/rbac` 已返回用户名+角色；开发=写权限、运行=读+action 可据此分流。

---

## 3. 架构总览（方案 A + 双模型映射）

```
                        ┌──────────── 开发阶段（写）────────────┐   ┌────────── 运行阶段（读 + 交互）──────────┐
                        │                                      │   │                                        │
  开发工具(CLI/WorkBuddy) │   stdio MCP    ┌──────────────┐    │   │   web 门户工作台(5173)                  │
  用户名=dev.*            │  ───────────→  │ 本仓 mcp server│    │   │   用户名=运行角色                    │
                        │  scenario-     │ (新, stdio)   │    │   │   │                                   │
  经 MCP 工具面           │  pack-write/   │ 内部调 8000    │    │   │   │  GET /control/scenarios 选包       │
  (scenario 3 tools)     │  list/lock     │ POST 写接口    │    │   │   ▼                                   │
                        │                └──────┬───────┘    │   │  ┌──────────────────────────┐          │
                        │               适配器层 │            │   │  │ chiyu-host 平台 8000       │          │
                        │  (kernel 模型→平台模型)│            │   │  │ /control/scenarios(GET)   │          │
                        │                       ▼            │   │  │ /control/rbac(用户名/角色) │          │
                        │  chiyu-host 平台 8000              │   │  │ /rpc/{t}/{c}/action        │←───────┘
                        │  POST /control/scenarios (D5 补)   │   │  │ /rpc/{t}/{c}/events (SSE)  │
                        │  复用 kernel scenario_from_dict 校验│   │  └──────────────────────────┘
                        └────────────────────────────────────┘

 身份区分：开发= dev.* 用户名 + 写权限；运行= 业务角色(admin/finance/sales_manager) + 读/action 权限
          读/写分流复用车问 /control/rbac + /rpc 的 confirm+写闸
```

**要点**：
- **开发阶段**：本地 stdio MCP server 收 kernel `ScenarioPack` → 适配器层转平台模型（D7）→ `POST /control/scenarios`（D5 补）写入平台。平台侧该端点内部**复用 kernel `scenario_from_dict` 校验闸**（单一校验逻辑，不重复）。
- **运行阶段**：web 门户(5173) **只读平台**——`GET /control/scenarios` 列包、选中装载、以 `tenant+client_type` 身份 `POST /rpc/.../action` 做数据交互（完全复用平台现成通道）。
- **身份区分**：开发/运行经**用户名断言**区分（开发用户走 MCP 写路径持写 token；运行用户走 RPC 持读/action token），`/control/rbac` 提供权威角色。

---

## 4. 双阶段设计

### 4.1 开发阶段：本地 stdio MCP server（本仓新增 `tools/mcp_scenario_server.py`）

- **transport**：stdio（标准 MCP 协议），复用 `chiyu_kernel.mcp` 的 `InMemoryMcpServer` 反向——本仓作为 **server 端**。
- **MCP 工具面**（3 个动作，防 CRUD 爆炸）：

| 工具 | 语义 | 落点 |
|------|------|------|
| `scenario-pack-write` | 收 kernel `ScenarioPack` dict → 适配器转平台模型 → `POST 8000/control/scenarios` | 平台写接口（D5） |
| `scenario-pack-list` | 读 `GET 8000/control/scenarios` | 平台读 |
| `scenario-pack-lock` | 平台侧锁定（D5 补 `lock` 语义，需 `confirm:true`，HITL） | 平台写接口 |

- **鉴权**：开发工具调用时由 MCP server 注入 dev token（用户名=dev.*，role=admin 或独立 dev role），写入须经 G0 决策锚。
- **适配器层**（D7）：`kernel ScenarioPack {id/level/mode/workflow DAG/knowledge_needs}` ↔ 平台模型 `{pkg/namespace/tenant/actions/assets/integrations/status}` 双向映射；映射规则固化（见 §5）。

### 4.2 运行阶段：web 门户工作台(5173) 读平台 + RPC

- **改向**：把上一轮 web `scenario` 端点从「本仓私有 store」**重定向到平台 8000**：
  - `GET /api/scenario/list` → 代理 `GET 8000/control/scenarios`
  - `POST /api/scenario/select` → 装载（会话态，写）
  - `POST /api/scenario/run` → `POST 8000/rpc/{tenant}/{client_type}/action`（读类 Action 真执行）
  - 锁定 → `POST 8000/...`（confirm HITL）
- **身份**：web 会话登录用户（经 `/control/rbac`），以 `client_type=web`（或沿用 desktop/M0' 口径）调 RPC。
- **数据交互**：运行包内 `actions` 声明经 `/rpc/.../action` 执行，事件经 `events` SSE 回流渲染进对话。

### 4.3 用户名 + 角色区分（开发/运行）

| 阶段 | 用户名断言 | 角色/权限 | 通道 |
|------|-----------|----------|------|
| 开发 | `dev.*` | 读场景包 + **POST 写** + lock（G0 锚） | stdio MCP → `POST /control/scenarios` |
| 运行 | 业务用户（admin/finance/sales_manager） | 读场景包 + `/rpc/.../action`（读/写类，confirm+写闸） | web 5173 → `/rpc/{tenant}/{c}/action` |

- 平台侧 `POST /control/scenarios` 校验：仅 `dev.*` 用户名 + 写 token 放行（`/control/rbac` 兜底）。
- 运行侧不开放写场景包（无 POST 权限）——**开发/运行权限隔离**是核心。

---

## 5. 双模型映射层（D7 固化）

| 平台模型字段 | 来源（kernel ScenarioPack） | 映射规则 |
|-------------|---------------------------|---------|
| `pkg`      | `id`（kebab-case）               | 直映射；平台唯一键 |
| `namespace` | `direction`（消费方注入的域命名空间） | 直映射 |
| `tenant`   | 调用上下文 tenant（MCP 注）        | 由 MCP server 注入 |
| `actions`  | `workflow.steps` 的 FQN 列表       | steps[name] → action 声明 |
| `assets`   | `knowledge_needs`（L1–L4 检索需求） | 转平台资产声明 |
| `integrations` | `plugins`（注册表插件）         | 插件 → 连接器声明 |
| `status`   | write 时的初始状态（`draft`/`active`） | 默认 `draft`，lock 后 `active` |

- **反向**（读回）：平台 `{pkg/namespace/tenant/actions/assets/integrations/status}` → kernel `ScenarioPack`（供开发侧预览/运行前校验）。
- ⛔ 单一校验闸：**kernel `scenario_from_dict` 是唯一写前校验**，平台 `POST /control/scenarios` 内部复用，适配器只做字段映射不做重复校验。

---

## 6. 任务分解与生命契约

> 本文档覆盖 **1 个登记 agent（`enterprise-platform-builder`）**，注册表逆覆盖不触发全 roster 断言（守反向覆盖铁律：若后续覆盖 ≥2 agent 须全部覆盖）。

### T1 平台写接口 `POST /control/scenarios`（本仓 chiyu-host 补）

```contract-yaml
- task: "T1 本仓 chiyu-host 补 POST /control/scenarios（写场景包 + lock 语义，RBAC 鉴权 + G0 决策锚；内部复用 kernel scenario_from_dict 校验闸）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-native-action-design, ai-multi-agent-orchestration]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "packages/chiyu-host/src/chiyu_host 新增 control 路由；POST /control/scenarios 以 dev.* 用户名 + 写 token 可写入平台模型包；非 dev.* 用户名或无写 token 返回 403；非法 ScenarioPack 经 scenario_from_dict 返回 4xx；lock 缺 confirm:true 返回 400"
```

### T2 本地 stdio MCP server（本仓新增入口）

```contract-yaml
- task: "T2 本仓新增本地 stdio MCP server（tools/mcp_scenario_server.py）：scenario-pack-write/list/lock 三工具，内部经适配器调 8000 平台，复用 kernel 校验与 InMemoryMcpServer"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-native-action-design]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "可用标准 MCP stdio 客户端连接并读到 3 个 mcp__scenario_pack__* 工具；经 write 工具写入的包在 8000 GET /control/scenarios 可见；list 读到平台包；lock 无 confirm:true 被拒"
```

### T3 适配器层（kernel ↔ 平台模型）

```contract-yaml
- task: "T3 场景包双模型映射适配器（kernel ScenarioPack ↔ 平台 {pkg/namespace/tenant/actions/assets/integrations/status}），双向映射 + 单一校验闸复用"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-particle-system-design]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "适配器正向（kernel→平台）与反向（平台→kernel）往返一致；映射规则 §5 逐字段可测；两端模型在门面 __all__ 均可见"
```

### T4 单测 + 变异自证

```contract-yaml
- task: "T4 场景包平台化全链路单测 + 变异自证（写接口鉴权/MCP write/list/lock/双模型往返/运行 RPC 代理）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "新增测试 ≥12 例全绿；故意删除某处鉴权/映射判据分支后 ≥1 例转红（变异自证），还原复绿；全量 make test 无回归"
```

### T5 web 客户端重定向到平台（5173）

```contract-yaml
- task: "T5 web 门户场景包端点重定向到平台 8000（list→GET /control/scenarios、run→/rpc/.../action、select/lock 写平台），会话用户身份经 /control/rbac"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-native-action-design, ai-multi-agent-orchestration]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "curl 实测：list 返回平台包；run 经 /rpc/.../action 返回 Action 结果；开发角色用户不可写场景包（403）；运营角色可读+action"
```

---

## 7. 验收判据（curl/pytest 实测，不接受「应该可以」）

1. `pytest packages/chiyu-kernel/tests packages/chiyu-host/tests -q` 全绿（含新增 ≥12 例）。
2. 变异自证：删写接口鉴权/双模型映射判据 → ≥1 例红 → 还原绿。
3. **开发阶段**：stdio MCP 客户端连本仓 server → write 包 → `GET 8000/control/scenarios` 可见；非 dev 用户 write 403。
4. **运行阶段**：web `GET /api/scenario/list` 返回平台包；select 后 `run` 经 `/rpc/{tenant}/{c}/action` 返回真实 Action 结果；事件流 SSE 回流。
5. **身份区分**：开发（dev.*）与运行（admin/finance/sales_manager）权限隔离——开发能写、运行不能写，运行能 action、开发 read-able。
6. `npm run typecheck && npm run build` 全绿。

---

## 8. 红线（偏离即推翻）

- 内核 scenario 模块**零领域字面量**（已有，保持）；平台模型字段 `pkg/namespace/tenant/actions/...` 仅存于适配器层与平台，不进 kernel 机制层。
- **单一校验闸**：`scenario_from_dict` 是唯一写前校验；适配器只映射不重复校验。
- 开发/运行**权限隔离**：平台写接口仅 `dev.*` + 写 token；运行侧无写场景包权限。
- 写类操作（平台写/锁/运行写类 Action）须 confirm + 写闸 G0–G3（复用平台治理），HITL 闸保留。
- 不新增粒子类型、不改 `contract/*.py`（不触发 manifest 重生成）。
- 8000 非本仓源码：本仓只落**设计 + chiyu-host 源码补丁 + MCP/适配器代码**；「部署替换 8000」属部署侧，标注为后续步骤，不阻塞本仓实现。

---

## 9. 闭环回写

| task | gap_type | observed | expected | severity | ts |
|---|---|---|---|---|---|
| （待 workbench 监控回填） | | | | | |

---

## 10. 不做（YAGNI）

- 场景包版本管理 / 多版本共存。
- pack 内嵌红线目录（红线仍由 TenantProfile 注入）。
- stdio MCP 之外的 HTTP/SSE transport（P2 视需要）。
- 平台写接口的审计看板 / 审批 UI（后续）。
- 修改 8000 实例本身（源码仓外，属部署替换，非本仓代码改动）。

---

## 11. 批准记录

> 本设计经用户逐条批准 D1–D8（2026-09-26 AskUserQuestion）后定稿。批准后进入 writing-plans 并落执行：
> 1. T1 本仓 chiyu-host 补 `POST /control/scenarios`（RBAC + G0 锚 + 复用 kernel 校验）；部署替换 8000。
> 2. T2 本地 stdio MCP server（write/list/lock）。
> 3. T3 双模型适配器。
> 4. T4 单测 + 变异自证。
> 5. T5 web 客户端重定向到平台。
