# chiyu-enterprise 插件体系设计（对齐 CRM 插件范式）· 2026-09-26

> 输入：用户 2026-09-26 提问「参考 CRM 的插件功能，规划 chiyu-enterprise 应该有几个插件、应该包括哪些功能」，方案 A 已批准。
> 参照系：`D:\system\CRM-ai-native\plugin\` 三插件实测（2026-09-26 实勘）。
> 承接智能体：`enterprise-platform-builder`（契约键 `ct-chiyu-enterprise`，登记于本仓 `contract/contract-ids.json`）。
> 落点纪律：设计稿落本仓（chiyu-foundation 为唯一事实源）；插件包本体属 chiyu-enterprise 消费方产物，只在本仓登记契约，不向其他仓回写设计。

---

## §0 结论

**3 个插件，按人群切分（对齐 CRM 已验证模式），而不是按业务域切分：**

| # | 插件 | 人群 | 一句话定位 |
|---|---|---|---|
| ① | `enterprise-decision-platform` | 内部业务岗（财务/计划/质量/采购/管理层） | 企业 AI 决策专家：场景自适应对话入口 + 决策建议卡 + 两阶段写入 |
| ② | `enterprise-platform-admin` | 内部管理面 | 平台治理助手：租户接入、场景包启停、连接器、RBAC、运行洞察 |
| ③ | `enterprise-scenario-builder` | 实施伙伴（外部生态位） | 场景包构建专家：对话式产出五元组配置画像 → 草稿池 → 人工 promote |

**三条铁律**：
1. **插件 = 对话分发层**（agents + SKILL），**零新增 Action 定义、零内核改动**——业务能力全部引用平台既有 Action 治理面（`scenario/` 的 action_namespace：`gl.` / `fin.` / `wms.` / `q.`）与场景包五元组。
2. **一个专家覆盖多角色**：对齐 CRM「一个 sales 专家 + 5 角色自适应」模式，靠 RBAC + 场景包裁剪，**不按财务/供应链/质量拆插件**。
3. **红线整体继承**：禁删、两阶段写、决策第 0 闸、租户隔离、草稿不自动生效。

---

## §1 参照系：CRM 三插件解剖（实测）

| 插件 | id / 版本 | 人群 | 包内容 |
|---|---|---|---|
| 销售决策专家 | `sales-decision-platform` v1.12.0 | 内部一线 | agents/crm-native.md（5 角色自适应）+ 20 SKILL（编排入口 crm-native + query/write/risk + 15 个 method-*） |
| 平台管理专家 | `sales-decision-admin` v1.3.0 | 内部管理面 | 4 SKILL：industry-onboarding / user-rbac-admin / system-bootstrap / platform-ops-insight |
| 经销商伙伴 | `dealer-sales-partner` | 外部生态 | 报备防撞单 / 报价返利 / 提货库存 / 政策查询，跨租户 scope 隔离 |

**共性纪律（本设计全部继承）**：
- 包结构四件套：`.workbuddy-plugin/plugin.json` + `agents/` + `skills/` + `avatars/` + README；zip 为上传单元。
- manifest 字段：`id` / `name` / `description` / `version` / `configSchema` / `skills[]`。
- **权威源与分发副本分离**：源在仓库根，`plugin/` 是分发副本；打包脚本 + 校验脚本（`verify-plugin-zips.py`）做版本一致性与内容防漂移守卫。
- 版本纪律：版本描述内容，内容不变不 bump；多清单（plugin.json / openclaw.plugin.json / package.json）一致性由校验器强制。
- 名称唯一键（`name`）更名 = 平台视为另一个专家；技能 id 是独立命名空间不可轻改（防断链）。

**CRM 踩过的坑（本设计预防）**：副本 byte-equal 同步之痛（4 份副本 md5 校验）→ 企业侧包数控制在 3、副本同步进校验脚本；版本漂移（openclaw/package.json 漏 bump）→ 校验器新增 `check_version_consistency()` 同类守卫。

---

## §2 已确认决策

- 2026-09-26：用户批准**方案 A**（3 插件、按人群切分），否决方案 B（按业务域 5 插件）与方案 C（2 插件）。
- 2026-09-26：第③插件定位为「实施伙伴构建场景包」（对齐 CRM dealer 的外部生态位；对应企业级平台「场景包配置画像」的交付故事），**不是**经销商租户角色。
- 2026-09-26：builder 集成映射深化并保持（`2026-09-26-scenario-builder-integration-map.md`）；草稿池载体拍板 = enterprise 层 `host/scenario_draft.py`（ScenarioDraft 三态），不复用 SkillDraft。设计整体批准（P8），进入 writing-plans（P9）。

---

## §3 插件总表

| 项 | ① 企业决策专家 | ② 平台管理专家 | ③ 场景包构建专家 |
|---|---|---|---|
| 目录 | `plugin/enterprise-decision-platform/` | `plugin/enterprise-platform-admin/` | `plugin/enterprise-scenario-builder/` |
| manifest id | `enterprise-decision-platform` | `enterprise-platform-admin` | `enterprise-scenario-builder` |
| agents | `agents/enterprise-native.md`（多角色自适应） | `agents/enterprise-admin.md` | `agents/enterprise-builder.md` |
| SKILL 数 | 10 | 5 | 4 |
| 接入通道 | 平台 MCP / RPC（读直连、写两阶段） | 平台管理面（admin scope） | 管理面 + 场景包 loader（builder scope） |
| 权限模型 | 业务 RBAC（场景包 enabled + 角色裁剪） | admin RBAC | builder RBAC（只产草稿，无生产写） |

---

## §4 插件① 企业决策专家 `enterprise-decision-platform`

**agent 面孔**：`agents/enterprise-native.md` —— 角色自适应：按登录角色（财务分析员/计划员/质量工程师/采购/管理层）经 RBAC 裁剪可见场景包与 SKILL；同一面孔、不同能力面。

**SKILL 清单（10）**：

| SKILL | 类别 | 职责 |
|---|---|---|
| `enterprise-native` | 编排入口 | 意图路由 → 场景包分发（惰性编排），对齐 crm-native 模式 |
| `enterprise-query` | 读 | 跨场景推理查询（粒子图 + 决策链 + 检索），只读直连 |
| `enterprise-write` | 写 | 对话式写入：两阶段（phase1 表单 → confirm_token）+ 决策第 0 闸 |
| `decision-advise` | 决策 | 决策建议卡三档（A 明确处置 / B 风险提示必须审批 / C 只补信息），坐标 = 决策场景 × 业务阶段 |
| `risk-probe` | 探测 | 链断裂 / SLA 超时 / 审批堆积主动探测（事件流推送） |
| `decision-retrospective` | 复盘 | 决策复盘与效果回接（喂 evolution 判据） |
| `method-decision-rubric` | 方法论 | 结构化决策评分（九尺子式多维度确定性打分 + 一次 LLM 收紧） |
| `method-root-cause` | 方法论 | 根因链证据环：证据盘点 → 根因 → 反事实检验 |
| `method-scenario-triage` | 方法论 | 场景三级判别（单点提效 / 流程提效 / 端到端增值）→ 选对场景包类型 |
| `method-risk-gate` | 方法论 | 风险权衡与红线一票否决 |

**路由纪律（写进 enterprise-native）**：识别出业务决策诉求（记账/预测/补货/质量处置/审批等）时，**先调 `decision-advise` 取建议卡**，再走查询或两阶段写入；B 档禁止直接触发写工具。

---

## §5 插件② 平台管理专家 `enterprise-platform-admin`

**SKILL 清单（5）**：

| SKILL | 职责 |
|---|---|
| `tenant-onboarding` | 行业租户接入：生成 TenantProfile（粒子类型 / 知识谓词 / 红线事项目录**由租户注入**，内核零领域字面量铁律） |
| `scenario-registry-admin` | 场景包注册表后台启停：对齐 CRM skill_registry 模式——DB 为启停权威源、首启幂等灌种子、**禁删只改 enabled**、热生效 |
| `connector-admin` | 连接器五闸管理：接入凭据、启停、写回白名单 |
| `rbac-approval-admin` | 角色权限 + ApprovalGate/HITL 配置（阈值后台可配置，不硬编码） |
| `ops-insight` | 运行洞察：审计链、SLA、僵尸任务治理、决策监控卡 |

---

## §6 插件③ 场景包构建专家 `enterprise-scenario-builder`

**定位**：实施伙伴的交付入口——「场景包 = 配置画像，不是写代码」的平台化卖点落地处。

**SKILL 清单（4）**：

| SKILL | 职责 |
|---|---|
| `scenario-author` | 五元组对话式构建：`tenant_profile` / `action_namespace` / `agent_roles`+`agent_edges` / `connector_ids` / `assets`（prompt_templates/decision_rules/particle_schema/kb）+ `actions` 挂 guard |
| `draft-governance` | 产出物进 **SkillDraft 草稿池**：治理优先、**不自动生效**、可审计；人工 promote 才进生产注册表（对齐 evolution 承接判据 approved+good） |
| `integration-wizard` | 连接器接入向导：外部系统五闸回连配置（只产配置草稿，凭据不进对话） |
| `validation-run` | 场景包校验与试运行：判别力自证（故意投错配置必须被检出才放行） |

**安全边界**：builder 角色**无生产写权限**——只能产草稿 + 试运行（沙箱）；promote 是管理面人工动作（插件②的 scenario-registry-admin 或平台控制台执行）。

**深化篇（用户 2026-09-26 要求保持）**：builder 与当前系统的全部集成关系已固化为代码级映射，见 `2026-09-26-scenario-builder-integration-map.md`——含 4 SKILL × 17 集成点（file:line 锚点）、注册即继承机制、复用/不接清单、锚点漂移守卫与验收判据。

---

## §7 与平台机制的接线（零内核改动声明）

| 平台机制（已收口） | 插件侧用法 | 插件新增 |
|---|---|---|
| `scenario/loader.py` 注册 + 五元组 | 插件 SKILL 引用已注册场景包；builder 产新包草稿 | 零 |
| Action 治理面（`action/executor.py` + action_namespace） | 插件写动作全部引用既有 fqn | 零新 Action |
| ApprovalGate / HITL / 决策第 0 闸 | `enterprise-write` 两阶段直接复用 | 零 |
| `decision/orchestrator.run_decision` | 端到端场景经 advise → run_decision | 零 |
| `evolution/bridge.py` + SkillDraft | `draft-governance` 桥接 | 零 |
| `/rpc/{tenant}/{client_type}/action` 客户端集成 | **不经插件**（既有协议通道） | 零 |

---

## §8 共性纪律（三插件统一）

1. **包结构**：`.workbuddy-plugin/plugin.json` + `agents/` + `skills/` + `avatars/` 同级，zip 上传。
2. **权威源**：SKILL/agents 源在 chiyu-enterprise 仓库根对应目录，`plugin/` 为分发副本；副本一致性进校验脚本（md5）。
3. **版本纪律**：三清单（plugin.json / openclaw.plugin.json / package.json）版本一致由 `scripts/verify_enterprise_plugins.py` 强制；内容不变不 bump。
4. **红线继承**：无 delete/remove 工具；写动作两阶段 + 决策闸；跨租户一律 `cross_tenant_write_denied` 兜底；无凭证 `auth_required` 硬拒绝。
5. **对外名称纪律**：manifest `name` 唯一键变更 = 平台视为新专家（须重新导入）；技能 id 是独立命名空间不轻改；对外文案只留功能性语义。

---

## §9 任务分解与生命契约（T1–T5）

```contract-yaml
- task: "T1 三插件包骨架 + manifest 三清单 + verify_enterprise_plugins.py 校验器（含版本一致性守卫与副本 md5）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "python scripts/verify_enterprise_plugins.py 对 3 包输出 version/name/skills 全一致且 exit 0；故意改错一个清单版本须 exit 1（变异自证）"
```
**契约说明：** T1 由 `enterprise-platform-builder` 承接，调用 `ai-capability-audit`、读本仓与 enterprise-platform 记忆（L1，≤2 跳）；成功标准 = 校验器三包全绿且变异自证可红。

```contract-yaml
- task: "T2 插件① enterprise-decision-platform：agent 面孔 + 10 SKILL（含 decision-advise 优先路由纪律）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-context-layering, ai-native-action-design]
  memory: [enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "enterprise-native SKILL.md 含「先 advise 后写」路由表与两阶段写清单；写清单内每个动作 fqn 在平台 Action 面真实存在（零新增）；RolePlay 5 角色各可见场景包集合与 RBAC 声明一致"
```
**契约说明：** T2 同智能体承接，调用 `ai-context-layering` 与 `ai-native-action-design`；成功标准 = 路由纪律落文档、Action 零新增且 fqn 全部可解析、角色裁剪声明一致。

```contract-yaml
- task: "T3 插件② enterprise-platform-admin：5 SKILL（tenant-onboarding 注入铁律 / 场景包启停 DB 权威禁删）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-multi-agent-orchestration, ai-capability-audit]
  memory: [enterprise-platform]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "scenario-registry-admin SKILL.md 明示「DB 权威源 + 禁删只改 enabled + 热生效」三要素；tenant-onboarding 明示粒子类型/谓词/红线由租户注入且内核零领域字面量"
```
**契约说明：** T3 同智能体承接，调用 `ai-multi-agent-orchestration` 与 `ai-capability-audit`；成功标准 = 启停三要素与租户注入铁律逐字落 SKILL。

```contract-yaml
- task: "T4 插件③ enterprise-scenario-builder：4 SKILL（五元组构建 / SkillDraft 草稿池 / 判别力自证）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-particle-system-design, ai-event-driven-evolution]
  memory: [enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "新增 host/scenario_draft.py（ScenarioDraft 三态 draft→validated→promoted，2026-09-26 拍板）；validation-run 对故意投错的场景包配置（越权 action fqn / 缺 agent_role / 红线缺失）逐条检出并拒绝入草稿池；draft-governance 无任何自动 promote 路径"
```
**契约说明：** T4 同智能体承接，调用 `ai-particle-system-design` 与 `ai-event-driven-evolution`；成功标准 = 错配置必被检出（判别力自证）且草稿池零自动生效路径。

```contract-yaml
- task: "T5 打包分发 + 全链验收（3 zip + verify 全绿 + 红线扫描）"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "3 个 zip 经 verify_enterprise_plugins.py 全绿；包内全部文件过禁词扫描零命中；write/manifest 无 delete 类工具与字面量"
```
**契约说明：** T5 同智能体承接，调用 `ai-capability-audit`；成功标准 = 三包校验全绿 + 对外披露扫描零残留。

---

## §10 验收判据（不接受「应该可以」）

1. `python scripts/verify_enterprise_plugins.py` 退出码 0，且对三个包各输出 `name/version/skills` 一致性结果。
2. 变异自证：任一清单改错版本 / 删一条路由纪律 → 校验器转红；还原后复绿。
3. 插件①写清单 Action fqn 逐一在平台 Action 治理面解析成功（零新增）。
4. 插件③判别力自证：3 类故意错配置全部检出。
5. 禁词扫描（按概念扫描：权属类字样与其代号组合）三包零命中。

## §11 不做（YAGNI）

- 不按业务域拆插件（方案 B 已否决）。
- 插件内不定义新 Action / 不改内核任何模块。
- 不做插件热加载新机制（复用场景包 registry 启停）。
- 插件③不做自动 promote（草稿→生产必须人工）。
- 不做插件间互相调用（三插件各自经平台机制协作，不直连）。

## §12 闭环回写

| 任务 | 监控点 | 反馈落点 |
|---|---|---|
| T1–T5 | workbench 按 §9 契约块监控 skills/memory/success | `<本文档>.feedback.json`（task+gap_type 幂等 upsert） |
| 同一 (task, gap_type) ≥2 次 | 产出 SKILL 改进提案 | 须用户显式批准后才改 SKILL，绝不自动应用 |
