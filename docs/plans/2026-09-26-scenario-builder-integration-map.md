# enterprise-scenario-builder × 当前系统集成映射 · 2026-09-26

> 定位：插件体系设计（`2026-09-26-chiyu-enterprise-plugin-design.md` §6）的**深化篇**——把插件③「场景包构建专家」与 chiyu-enterprise 当前系统的每一条集成关系固化为**代码级锚点 + 闸门 + 生命周期**，供实施与验收逐条对照。
> 实勘基线：2026-09-26，`packages/enterprise/src/enterprise/`（57 py）。所有锚点为当日实测；后续漂移以 git 为准。
> 纪律：**零内核改动**（chiyu_kernel 不动）；enterprise 层仅允许新增「草稿池」一个模块（先例：host 控制平面）；其余全部复用既有机制。

---

## §1 集成关系总图（生命周期视角）

```
[实施伙伴对话] → 插件③ SKILL 族
     │
     ├─ scenario-author ──产出──> ScenarioSpec（五元组声明式 JSON 草稿）
     │                                │ 落入
     │                          ScenarioDraft 池（enterprise 层新增，状态机 draft→validated→promoted）
     │                                │
     ├─ validation-run ──校验──> ① spec 结构完整 ② fqn 命名空间归属 ③ 连接器存在 ④ 判别力自证
     │                                │ 全绿才可 validated
     │                                │ 人工 promote（管理面按钮/插件②，绝不自动）
     │                                ▼
     │                     scenario_loader.register_scenario(name, factory)
     │                     （factory = spec → ScenarioPackage 运行时构造，不改 loader）
     │                                │ 注册即自动被消费 ↓↓（无需额外接线）
     │                     ├─ host 写闸：loader.resolve_guard(fqn) → GuardSpec 消费
     │                     ├─ action/executor.execute_action：按 fqn 路由到 handler
     │                     ├─ 控制台 GET /scenarios、/scenario/{name}：看板自动可见
     │                     └─ _scenario_type()：按 agent_roles/edges 派生三分类
     │
     ├─ integration-wizard ──产出──> 连接器接入配置草稿 → POST /integrations（host 控制面）
     │                                └─ 运行时经 connector/gateway.call_connector 五闸
     │
     └─ draft-governance ──审计桥──> evolution/bridge.SkillDraft 草稿池（决策→技能草稿）
                                      ⛔ 与场景包草稿池**分开**：前者沉淀"技能"，后者沉淀"场景包"
```

**关键洞察（注册即继承）**：场景包一旦经 `register_scenario` 注册，写闸、执行器、看板、三分类**全部自动继承**——这是 loader 注册表设计（`scenario/loader.py` 模块 docstring 明示「供 host 写闸消费」）决定的。因此插件③的集成面收敛为**一个写入点**（注册）+ **一个运行时面**（五闸执行），不需要逐模块对接。

---

## §2 集成点明细（按 SKILL 分列）

### 2.1 scenario-author（五元组构建）

| # | 集成点 | 机制 | 代码锚点 | 方向 | 闸门 |
|---|---|---|---|---|---|
| A1 | 五元组数据模型 | 对话产物 = `ScenarioPackage` 同构的声明式 spec（name/tenant_profile/action_namespace/agent_roles+agent_edges/connector_ids/assets/enabled_for/actions[]） | `scenario/package.py:44 ScenarioPackage`、`:14 ScenarioAction(fqn, capability, guard, handler)` | 写→草稿池 | spec 校验（validation-run） |
| A2 | TenantProfile 注入 | tenant_profile 领域取值（粒子类型/谓词/红线）由租户注入 spec，builder **不内置任何领域字面量** | `package.py:13`（from chiyu_kernel.contract import TenantProfile） | 读模型 | 分层铁律 |
| A3 | GuardSpec 护栏声明 | 每个 ScenarioAction 携带 guard（mutating/needs_force/rbac…），随包注册后自动进写闸 | `action/guard.py GuardSpec`、`scenario/loader.py:55 resolve_guard` | 写→草稿池 | 无（声明本身） |
| A4 | 注册写入点（唯一） | promote 后经 `register_scenario(name, factory)` 注册；factory 由 spec 构造 ScenarioPackage（运行时，零内核改动） | `scenario/loader.py:24 register_scenario`；启动注册先例 `host/control.py:146-149`（幂等确保 sales） | 写 | 人工 promote 闸 |
| A5 | handler 接线 | spec 声明 handler 绑定方式；未接 handler 的 fqn 注册后执行时**显式报接线缺口，不静默** | `action/executor.py:31-56 execute_action`（`{"ok":False,"wired":False,"error":"…未接 handler（接线缺口）"}`） | 读判据 | 接线缺口显式报错 |

### 2.2 draft-governance（草稿池治理）

| # | 集成点 | 机制 | 代码锚点 | 方向 | 闸门 |
|---|---|---|---|---|---|
| B1 | 场景包草稿池（**enterprise 层新增**，本设计唯一新模块） | ScenarioDraft 状态机 `draft → validated → promoted`（JSON 文档落盘 + 审计轨迹）；promoted 才调 A4 注册 | 新模块（建议 `host/scenario_draft.py`，先例 `host/control_plane.py`） | 写 | validated 前禁 promote |
| B2 | 技能草稿池（决策→SKILL） | **不复用、不混写**：evolution 桥承接 approved+good 决策事件 → `SkillDraft` → foundation `promote`（仍不入生产注册表）；场景包草稿与技能草稿是**两条独立泳道**，看板分开展示 | `evolution/bridge.py:34 _should_evolve`（verdict=approved/skipped + score=good + gate=allowed）、`:69 evolve_from_event`、`:86 EvolutionBridge.start`（订阅 "decision" 主题） | 读+审计 | promote 不入生产注册表 |
| B3 | 草稿不自动生效 | 两池共享同一纪律：进池产物 status=draft，promote 是人工动作；自动生效路径 = 零（验收判据） | `bridge.py:1-12`（模块 docstring 明示「草稿绝不自动生效」） | 判据 | 人工闸 |

### 2.3 integration-wizard（连接器接入）

| # | 集成点 | 机制 | 代码锚点 | 方向 | 闸门 |
|---|---|---|---|---|---|
| C1 | 连接器注册（控制面） | 向导产出连接器配置草稿 → `POST /integrations`（host 控制面既有端点）；凭据**不进对话**（向导只回传凭据引用 id） | `host/control.py:689 POST /integrations`、`:628 GET /integrations`、`:664 /integrations/{cid}/probe`（连通性探测） | 写→控制面 | 管理面 RBAC |
| C2 | 五闸运行时 | 配置生效后所有调用经 `call_connector`：G-A 跨租户 / G-B 只读优先 / G-C 决策锚 / G-D HITL(confirm_token) / G-E 传输缺失不假成功 | `connector/gateway.py:29-41 闸序列`、`connector/adapters.py`、`connector/registry.py SCOPE_READ_WRITE` | 读判据 | 五闸（不可绕过） |
| C3 | 写动作判定 | 未显式标记时按写动词后缀**保守推断为写**（宁可多走 HITL） | `gateway.py:44-54 infer_is_write`、`WRITE_SUFFIXES` | 读判据 | G-D |
| C4 | 连接器作用域 | spec 的 connector_ids 只能引用**已注册且本租户**的连接器实例（租户资产） | `package.py` connector_ids 字段 + `gateway.py` G-A | 读判据 | G-A 跨租户 |

### 2.4 validation-run（校验与试运行）

| # | 集成点 | 机制 | 代码锚点 | 方向 | 闸门 |
|---|---|---|---|---|---|
| D1 | spec 结构校验 | 五元组字段完整、agent_edges 三元组(from,to,action)合法、action_namespace 与 fqn 前缀一致 | `package.py:44-` 模型字段 | 读 | 不绿不入池 |
| D2 | fqn 归属校验 | 每个 action fqn 必须落在包命名空间树内（`<ns>.agent.*` / `<ns>.integration.*` / 显式 actions） | `package.py:action_fqns()` | 读 | 不绿不入池 |
| D3 | 判别力自证 | 投 3 类故意错配置（越权 fqn / 缺 agent_role / guard 缺失）必须逐条检出，才允许 validation-run 上线 | 本设计 §10 验收判据 4 | 判据 | 自证闸 |
| D4 | 试运行沙箱 | 试运行走 execute_action 但 handler 指向沙箱桩（不触真实连接器）；真实调用必须经 C2 五闸 | `executor.py`（handler 注入点） | 读 | 沙箱隔离 |

---

## §3 对接既有控制面路由（复用清单）

| 路由（host/control.py） | 插件③用途 |
|---|---|
| `GET /scenarios`（:426）、`GET /scenario/{name}`（:509） | 草稿 promote 后自动出现在看板（验收：无需插件侧额外上报） |
| `POST /integrations`（:689）、`GET /integrations/{cid}/probe`（:664） | integration-wizard 的写入与连通性验证 |
| `GET /events`（:728） | 草稿池/注册/写闸拒绝事件流（向实施伙伴展示实时反馈） |
| `GET /agents`（:598）、`GET /agents/{role}`（:611） | agent_roles/edges 配置后的装配视图 |
| `GET /connectors`（:569）、`GET /rbac`（:559）、`GET /governance`（:564） | 向导的只读上下文（已有连接器、角色、治理态） |

## §4 明确不接（防越界）

| 不接项 | 理由 |
|---|---|
| `provider.switch` 平台级动作 | 独立于业务 Action 面（`executor.py:27` 明示不经场景包）；builder 无权触达 |
| memory/writeback 回写通道 | 属决策运行链（run_decision 产物回写），builder 只产配置不产数据 |
| decision/orchestrator 决策执行 | 端到端场景由插件①经 advise→run_decision 消费，builder 不触达 |
| 审批状态机（approval/state_machine.py） | 审批属插件②管理面与 host 写闸管线；builder 草稿走自己的三态机 |
| 生产技能注册表 | SkillDraft promote 明示不入生产注册表（`bridge.py:8-10`）；插件③同样无权写 |

---

## §5 保持与验收（「梳理清楚并保持下来」的落地）

1. **本文档即权威记录**：落本仓 `docs/plans/`（chiyu-foundation 为唯一事实源）；chiyu-enterprise 侧实施时以本文档为契约输入，**不回写**对方仓。
2. **锚点漂移守卫**：T4 实施时对 §2 全部 file:line 锚点做存在性断言（测试读源码 grep 锚点符号，符号消失即红）——集成关系不是一次性文档，而是**可执行契约**。
3. **验收判据**（并入插件设计 §10）：① promote 后 `GET /scenarios` 自动可见（零额外上报）；② 未接 handler 的 fqn 执行返回接线缺口错误（不静默）；③ 写闸对注册包的 fqn 按 GuardSpec 真实拦截；④ 草稿池自动生效路径为零（变异自证：删人工闸判定 → 测试转红）；⑤ C1 凭据零进对话。
4. **记忆沉淀**：本映射摘要已写入工作记忆 `2026-09-26.md`，跨会话可检索。

## §6 草稿池载体（已拍板 · 2026-09-26 用户批准）

**决策**：enterprise 层新增 `host/scenario_draft.py`（ScenarioDraft，JSON 草稿 + 三态状态机 `draft → validated → promoted`，先例 `host/control_plane.py`）；**不复用** foundation SkillDraft 承载五元组（语义混装：技能 vs 场景包，字段勉强）。已并入插件设计 T4 任务范围。
