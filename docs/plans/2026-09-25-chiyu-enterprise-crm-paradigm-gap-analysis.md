# chiyu-enterprise E3–E6 借鉴 CRM-ai-native 真实范式｜差距分析与深化方向

> 状态：**调研完成，待评审**。本文档回答用户批评："E3\E4\E5\E6 开发太快、没看详细设计文档、效果惨不忍睹"——现以 `D:\system\CRM-ai-native`（成熟多租户 CRM SaaS 消费方）的真实实现为范本，逐模块做差距分析，给出深化方向。**不重写 foundation**，只深化 chiyu-enterprise 消费方实例的领域深度。

---

## §0 结论（结论先行）

CRM-ai-native 是 **JavaScript/Node 多租户 SaaS**，**不直接 import `chiyu_kernel`**（`grep chiyu_kernel` 零命中）——所以它不是"foundation 的 Python 门面消费方纪律"示范，而是**多租户企业级平台的领域深度范式**。它恰好是 chiyu-enterprise 要成为的东西的成熟版。

我此前 E3–E6 只写了**接口骨架 + 占位**（SourceConnector 干run / EventBus 订阅 / action_fqns 命名空间 / FastAPI 401 路由），**缺了真实多租户平台应有的：闸门流水线、防雪崩、可观测化、配置化铁律、终态治理**。CRM 范式全部命中这些缺口。

**差距性质判定**：
- E5（Action 治理）缺口**最严重**——CRM 的 action/executor.js 有完整 5 道写闸，我的只有命名空间展开。
- E3（记忆）次之——CRM 的三重防雪崩 + 蒸馏调度是真实生产刚需。
- E4（决策监控）——CRM 的九尺子"8+1 确定性评分"是核心范式，我的 EventBus 订阅只有 3 个测试。
- E6（接入）——CRM 的两阶段 confirm + 权益闸是零信任刚需，我的只有 401。

---

## §1 证据基线（已实读，非记忆）

| 模块 | CRM 真实文件 | 行数 | 核心范式 |
|---|---|---|---|
| 决策评分 | `src/decision/rubricScorer.js` | 296 | 九尺子 8 确定性+1 LLM，degraded 不假填充，逐尺子落库，阈值走 config_store |
| 记忆沉淀 | `src/memory/precipitate.js` | 166 | 三重防雪崩（价值/字段/去重窗）+ 配置化出厂缺省 + fail-open |
| 记忆蒸馏 | `src/memory/distillScheduler.js` | 59 | 注册即预热 + int32 钳制防 1ms 风暴 + append-only 不删 |
| Action 执行 | `src/action/executor.js` | 431 | 写通道第 0/1/1.5/1.7/2 闸流水线 |
| Action 注册 | `src/action/registry.js` | 96 | 反 CRUD 爆炸护栏（detectCrudExplosion） |
| 审批态机 | `src/approval/stateMachine.js` | 41 | 状态×操作矩阵，审批禁删红线，终态只读 |
| 监控聚合 | `src/monitor/monitorStore.js` | 366 | getGateMetrics 自主/升级/处置分布 + failsByKind 可观测化 + T13 租户隔离回退 |
| MCP 接入 | `src/mcp/gateway.js` | 355 | 两阶段 confirm（hashParams 冲突检测 + 只增补禁覆盖）+ 权益闸 + 降级弹窗 |

---

## §2 E5 Action 治理面｜缺口最严重

**我当前的实现**：`scenario/package.py` 只有 `action_fqns()` 把多智能体角色 + 连接器实例归一为 `sales.agent.*` / `sales.integration.*` 命名空间树。**只有"命名空间展开"，没有"执行闸门"。**

**CRM 真实范式**（`action/executor.js`）——写通道 5 道闸流水线，每道闸都是 `gate` 判定 + `emit trace` + fail-open/fail-closed 决策：

| 闸 | 判定依据 | fail 语义 |
|---|---|---|
| **第 0 闸 决策强制** | 写 Action 必须携带 `decision_id`（`kind==='write' && !decisionId && !bootstrap && !autoDecision`） | fail-closed：无决策不写，附 `advice` 建议卡 |
| **第 1 闸 数据范围** | `isParticleScoped` → `enforceScope`（角色 profile） | 越界不写 |
| **第 1.5 闸 角色 RBAC** | `def.rbac_roles` 白名单，未声明则默认放行 | 未识别/越权拒绝 |
| **第 1.7 闸 套餐权益** | `def.requiresEntitlement` → `resolveEntitlements` | 缺 tenantId fail-closed；解析异常 fail-open |
| **第 2 闸 高危 force** | `params.force` 双闸 | needs_force 拒绝 |

**反爆炸护栏**（`registry.js:detectCrudExplosion`）：系统性检测两类 CRUD 爆炸——① substrate 层 per-type CRUD（`data-deal-create` → 折叠为 `data-particle-create({type})`）；② 业务命名空间同 type ≥2 CRUD 动词（`crm-quote-create+update+delete` → 折叠为 `crm-quote-submit` 领域动词）。**单个意图 Action 合法，全家桶爆炸。**

**深化方向（chiyu-enterprise E5）**：
1. `scenario/package.py` 的 Action 定义补充**护栏元数据 schema**：`{kind, rbac_roles, requires_entitlement, needs_force, confirmation_token, redline_guard, decision_scenario}`。
2. 新增 `action/executor.py`：实现写通道 5 闸流水线（纯函数可测，复用 foundation `contract.redline_hit` / `ApprovalGate`）。
3. 新增 `action/registry.py`：反 CRUD 爆炸护栏 `detect_crud_explosion()`（守 E1 守卫，只 import `chiyu_kernel.api`/`contract`）。
4. **新增测试**：五闸逐闸 fail 语义 + 反爆炸检出。

---

## §3 E3 记忆与知识引擎｜缺口次之

**我当前的实现**：`memory/ingress.py` 只有 `SourceConnector` 数据类 + `ingest` 拉取式接口，dry-run 可测。**缺记忆沉淀、防雪崩、蒸馏调度。**

**CRM 真实范式**（`memory/precipitate.js`）——粒子写入自动沉淀记忆（C3），**三重防雪崩**：
- **① 价值闸**：`judgeWorthiness`（凭证/瞬态噪声/价值视界）过滤垃圾。
- **② 字段闸**：只沉淀规则显式 watch 的字段，**值真的变了才产出**（同值提交 0 条，`diffFields` 纯函数可单测）。
- **③ 去重窗**：同 `(锚点, topic, 字段, 新值)` 在 `dedupeHours` 内已写过 → 跳过（`recentlyPrecipitated`）。
- **配置化铁律**：规则走 `config_store['memory-precipitate-rules']`，代码内只是**出厂缺省**，禁硬编码业务字段。
- **fail-open**：沉淀失败只 emit trace + `recordFailure`，**绝不阻断业务写**。

**蒸馏调度**（`distillScheduler.js`）：注册即预热（铁律）+ **int32 钳制**（30 天=2_592_000_000 > int32 上限 → Node 钳为 1ms → 蒸馏风暴打满连接池 → 监控台假死；须钳到 2_147_483_647）+ append-only 不删（禁 DELETE 铁律）。

**深化方向（chiyu-enterprise E3）**：
1. `memory/ingest.py` 保留 `SourceConnector`，但输出改为**可沉淀的变更事件**（`{anchor, topic, kind, changes, ttlDays}`，`diff_fields`/`should_precipitate` 纯函数）。
2. 新增三重防雪崩纯函数（价值闸判据、字段 diff、去重窗判定），守"护栏判据放被调用方"。
3. 新增 `memory/distill.py`：`register_distillation` 调度（预钳间隔，注册即预热），append-only。
4. **新增测试**：字段闸同值 0 产出、去重窗命中跳过、fail-open 不阻断。

---

## §4 E4 决策统一监控与调度｜缺口明显

**我当前的实现**：`decision/monitor.py` 用 EventBus subscribe/publish（已修正为真实 `chiyu_kernel.api` API），先持久化后分发。**缺决策质量评分、聚合监控、可观测化、租户隔离回退。**

**CRM 真实范式**：
- **九尺子确定性评分**（`rubricScorer.js`）：clarity/accuracy/precision/relevance/depth/breadth/logic/importance/fairness，**8 项确定性代码判定 + 1 项 LLM（默认关）**。核心纪律：**degraded 不假填充**（无证据计 0，不 LLM 填），保证"同一决策重跑得分一致"，趋势才有意义。命名铁律：顺序固定 1清晰…9公平，**禁「关联性」**（同名异物陷阱）。逐尺子落库（`persistRubric`），阈值走 `config_store`（`loadRubricConfig`，禁硬编码）。
- **监控聚合**（`monitorStore.js`）：`getGateMetrics` 按 scenario 聚合**自主/升级/处置**分布；`failsByKind` 内存失败计数（**可观测化：静默吞错改观测**）；七根因码**单一事实源复用** `rootCauseClassifier.ROOT_CAUSES`（新增第八类自动同步，禁硬编码漂移）；**T13 租户隔离回退范式**：`tenantId='*'`=全量，显式租户按 `(tenant_id=$N OR tenant_id='system')` 回退。

**深化方向（chiyu-enterprise E4）**：
1. `decision/` 增加**确定性评分器**：`score_decision()` 纯函数（8 尺子确定 + 1 LLM 可选），`degraded` 不假填充，评分可复跑一致。
2. `decision/monitor.py` 增加 `get_gate_metrics()`：按 scenario 聚合自主/升级/处置 + `fails_by_kind` 可观测化 + T13 租户隔离回退。
3. **新增测试**：确定性重跑一致、degraded 语义、租户隔离回退。

---

## §5 E6 接入层（chiyu-host）｜缺口明显

**我当前的实现**：`host/app.py` 只有 FastAPI `tenant+client-type` 维度路由 + 401 鉴权闸。**缺零信任 confirm、权益闸、降级弹窗。**

**CRM 真实范式**（`mcp/gateway.js`）：
- **两阶段 confirm**：`confirm_token` → `confirmSessions` Map（`{action, kind, params, actor, role, expiresAt}`，TTL 10min）。
- **hashParams 冲突检测**：phase2 只增补、禁覆盖已展示字段（`mergePhase2Params`）——否则"用户确认 A、实际执行 B"confirm 形同虚设。
- **协议位隔离**：`PROTOCOL_KEYS`（confirm_token/api_token/choice/switched_role/utterance/decision_id）不参与业务参数合并；**force 不在此列**（否则 R6 高危写 force 双闸永远拒绝）。
- **套餐权益闸**：`assertMcpAccess`（MCP 通道整体，缺 tenantId fail-closed，system 豁免，解析异常 fail-open）。
- **降级弹窗**：凭证不全自动降级 sales 只读，AI 绝不接收/显示密钥明文。
- **审批态机**（`stateMachine.js`）：状态×操作矩阵，**审批态禁删=禁删红线，终态只读=审计留痕**。

**深化方向（chiyu-enterprise E6）**：
1. `host/` 增加**两阶段 confirm 通道**：phase1 冻结参数+发 token，phase2 只增补禁覆盖（hashParams 冲突检测）。
2. `host/` 增加**权益闸**（tenant 档位 → `requires_entitlement`）。
3. 审批实例状态机（守禁删红线/终态只读）。
4. **新增测试**：confirm 冲突拒绝、权益闸 fail-closed/fail-open。

---

## §6 纪律复核（CRM 范式是否守 foundation 分层铁律）

| CRM 范式 | 是否引入领域字面量进 foundation | 判定 |
|---|---|---|
| 九尺子评分（clarity/accuracy...） | 通用决策质量维度，**非销售专属** | ✅ 可进 foundation 或 enterprise 通用层 |
| 三重防雪崩沉淀 | 通用记忆机制，watch 字段是**租户配置** | ✅ 机制进 foundation，规则进 enterprise 配置 |
| 写通道 5 闸 | 通用治理闸，RBAC/权益/force 均通用 | ✅ 机制进 foundation，`sales.*` 命名空间进 enterprise |
| monitor 聚合 | 通用监控，scenario 是租户配置 | ✅ |
| confirm 两阶段 | 通用零信任 | ✅ |

**结论**：CRM 范式中"机制层"（评分器、防雪崩、写闸、confirm、态机）全部是**与业务无关的通用治理能力**，可安全纳入 foundation 通用机制或 enterprise 通用层；"实例层"（`sales.*` action 命名空间、watch 字段、红线事项目录）经 `TenantProfile`/`config_store` 注入，不进 foundation 代码。**不违背分层铁律。**

---

## §7 落地优先级（P0→P2）

| 优先级 | 模块 | 落地内容 | 参照 CRM 文件 |
|---|---|---|---|
| **P0** | E5 Action 治理 | 写通道 5 闸 + 反 CRUD 爆炸护栏 | executor.js / registry.js |
| **P0** | E3 记忆沉淀 | 三重防雪崩 + 配置化规则 + fail-open | precipitate.js |
| **P1** | E4 决策监控 | 确定性评分器 + gate 聚合 + 可观测化 | rubricScorer.js / monitorStore.js |
| **P1** | E3 蒸馏调度 | 注册即预热 + int32 钳制 + append-only | distillScheduler.js |
| **P2** | E6 接入 | 两阶段 confirm + 权益闸 + 审批态机 | gateway.js / stateMachine.js |

---

## §8 待你确认

1. **深化深度**：是否按 P0→P1/P2 分批深化（先 E5+E3，再 E4+E6）？还是本次全量深化？
2. **机制归属**：评分器/写闸/confirm 等通用机制，是放 **foundation 通用层**（需谨慎——守零领域铁律）还是 **enterprise 通用层**（`enterprise/core/`）？我倾向 enterprise 通用层，foundation 保持纯底座。
3. **语言差异**：CRM 是 Node，chiyu-enterprise 是 Python——只借鉴范式/语义（闸门、防雪崩、可观测化），不搬代码。

确认后我据此重写 E3–E6 对应代码（守 E1 守卫：只 import `chiyu_kernel.api`/`contract`），并逐模块跑测试 + 变异自证。
