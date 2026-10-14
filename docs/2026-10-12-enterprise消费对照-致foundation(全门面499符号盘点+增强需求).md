# enterprise 消费对照——致 foundation（全门面 499 符号盘点 + 增强需求）

- 日期：2026-10-12
- 来文：《foundation 核心功能清单（全门面枚举）》（贵仓 docs/，T63 配套）
- 结论先行：**零越面消费**（扫描实证：enterprise 全部 `chiyu_*` import 均落在五门面内）；
  499 符号（五门面 `__all__` 并集去重，本轮实取）中显式引用 **99（19.8%）**，未用 400；
  未用面归因为四类（架构性替代 / 工厂封装间接消费 / 自建并存待裁定 / 业务暂不涉足），
  **⛔ 无一类构成"该用没用"的能力缺口**；另提增强需求 6 项（RFE 候选）与扩展建议 4 项。

---

## 0. 方法与口径（机器可验，可独立复跑）

- 证据脚本：**贵仓 `scripts/facade_usage_audit.py`**（本轮新投，随本函可复核）
- 复跑：`cd chiyu-foundation && python scripts/facade_usage_audit.py`
  （左 = 五门面 `__all__` 本轮 import dump；右 = enterprise `packages/enterprise/src`
  全树 AST 三形态采集：`from chiyu_* import` / `import chiyu_*` / `alias.attr`；
  ⛔ docstring/注释字样不可见，防文本匹配假阳）
- **口径差说明**：清单统计 ≈478（kernel.api 404 + approval 5 + decision.api 15 +
  portal 26 + contract.decision 22 + contract.memory 6）；本盘点扫到 499，差 21 在
  contract 口径——我方扫的是 `chiyu_kernel.contract` **全子树**（含 memory 子树及其余
  子模块再导出），贵清单只列 decision/memory 两节。以本轮实取为准，特此说明。
- **「未用」定义**：无显式符号引用。功能可经**工厂封装**（如 recall_precedents 经
  build_memory_recaller 内部）或 **run_spine 形参**（如 score_rubric 经
  element_cap=True）被间接消费——归因时逐条区分，⛔ 不把间接消费误报为缺口。

---

## 1. 总览（18 族）

| 族 | 总数 | 已用 | 未用 | 未用主因归类 |
|---|---|---|---|---|
| data(store/persist/graph/vector) | 68 | 9 | 59 | Ⅲ 自建并存＋Ⅳ 角色差异 |
| kernel.api 其余（常量/错误/工具） | 159 | 30 | 129 | Ⅳ 企业错误面自建 |
| semantic(ontology/context/domain/canary/audit/idem) | 38 | 6 | 32 | Ⅳ/Ⅲ |
| integration(llm/mcp/tools/plugins/hooks) | 43 | 10 | 33 | Ⅲ 自建并存 |
| evolution(experimental) | 26 | 7 | 19 | Ⅳ R-FE1 口径不扩面 |
| memory(T44 stable) | 22 | 3 | 19 | Ⅱ 工厂封装 |
| decision.contract | 24 | 7 | 17 | Ⅳ |
| portal | 26 | 0 | 26 | Ⅳ 无消费场景（F2 确认） |
| run.workflow | 14 | 2 | 12 | Ⅰ 架构性替代 |
| run.orchestration | 15 | 9 | 6 | Ⅳ |
| contract 补遗 | 15 | 3 | 12 | Ⅳ |
| run.scenario | 10 | 1 | 9 | Ⅰ DB 化替代 |
| run.actions | 12 | 7 | 5 | Ⅳ |
| decision.api | 14 | 4 | 10 | Ⅱ run_spine 形参 |
| version 出口 | 11 | 1 | 10 | Ⅳ（require_capabilities 已用） |
| run.plan | 7 | 0 | 7 | Ⅰ 任务粒子替代 |
| run.events | 7 | 2 | 5 | Ⅳ |
| run.session | 7 | 3 | 4 | Ⅳ |
| approval | 5 | 2 | 3 | Ⅰ 自研闸替代 |
| **合计** | **499** | **99** | **400** | |

## 2. 已用 99 概览（按族，锚点见脚本输出）

- **decision 脊柱主链**：run_spine/SpineResult/DecisionError/RedlineSpec/EIGHT_ELEMENTS(_ZH)/RUBRIC_KEYS/AUDIT_* 四常量
- **approval 类型面**：DecisionApprovalVerdict/DecisionVerdictState/ApprovalGate
- **memory 主路径**：MemoryNote/build_memory_recaller/degraded_recall/PgVectorStore/PgVectorStorePersister
- **run 族**：ActionRegistry/ActionSpec/ACTION_MIN/MAX/SharedTask/TaskStateError/Agent/AgentLoop/Team*/Subagent*/LoopGuard/MAX_REDO/EventBus/Session*/WorkMode/MODE_PRESETS/DecisionIOField
- **integration 类型面**：LlmProvider/LlmResponse/StubProvider/McpBridge/McpTransport
- **semantic**：LAYERS/CORE_ROLES/CARDINALITIES/EDGE_*/ATTR_*/MEMORY_PREDICATES/KnowledgeNeed/CoverageReport/DEFAULT_MIN_COVERAGE
- **evolution**（experimental，R-FE1 口径）：SkillDraft/SkillRegistry/promote/validate_draft
- **version**：require_capabilities（双版本闸六键之一）

---

## 3. 未用 400 的四类归因（⛔ 无"该用没用"缺口）

### Ⅰ 架构性替代（企业自有更合适形态，共约 40 符号）

1. **scenario 族 9/10 未用**（ScenarioPack/ScenarioPackStore/ScenarioPackError/
   ScenarioPackLockDenied/register_scenario/is_registered/get_scenario/require_scenario/
   list_scenarios）：企业场景架构已 **DB 化**（2026-10 记忆 2.1：场景=通用表
   particles(scene.*)/handler_registry/master_templates/config_store，旧
   specs.py+loader+文件工厂已墓碑）。文件包形态（ScenarioPackStore）与企业 DB
   形态并存时，企业消费 DB 侧，⛔ 非疏漏。**→ 增强需求 E4（形态裁定）**。
2. **approval 三闸 3/5 未直用**（RedlinePriorityGate/DecisionApprovalGate/
   DecisionPassThroughGate）：企业自研 `_SpineApprovalGate`（decision/orchestrator.py，
   1.4-B 自闸：缺必需项 ⇒ PENDING 强制人工；R-E2 已裁定显式合成规则
   「红线 REJECTED > 要素闸 PENDING > 企业写闸/poor > 放行，cap 恒旁观」，
   守卫 = verify_element_matrix V16/V17 + verify_u2 U16d/U16e 实测）。
   两个 verdict 类型（DecisionApprovalVerdict/DecisionVerdictState）已用。
   **→ 扩展建议 X2（合成语义可否入 contract 成跨仓共识）**。
3. **workflow 族 12 未用**（WorkflowRunner/WorkflowStep/Phase/Meta/Result/StopReason/
   WORKFLOW_STEP_STATES/is_fatal_workflow_error 等）：企业任务编排走
   run.actions（ActionRegistry+SharedTask+TaskStateError 已用）＋场景任务粒子；
   阶段型 Workflow 与企业事件驱动架构正交，暂无场景。
4. **plan 族 7 全未用**（Plan/PlanStep/PlanMode/backfill_plan/TodoItem/TodoList/
   PlanStateError）：企业计划/待办承载在任务粒子九维体系（SIX_DIM_KEYS），
   独立 Plan/TodoList 无落点。

### Ⅱ 工厂封装/形参间接消费（不构成缺口，共约 29 符号）

1. **decision.api 10 未用中 6 个经 run_spine 形参**：score_rubric/
   cap_rubric_by_elements/check_elements/evaluate_redline/autonomous_release/
   validate_spine_order 均无企业直 import——但它们的功能由 run_spine 内部执行：
   实证锚点 orchestrator.py `element_cap=True`（J9-C 要素缺失⇒尺子封顶，
   R-E2 注释区）、`memory_recaller=` 形参、RedlineSpec 由企业注入后
   run_spine 执行红线。**企业消费的是脊柱编排结果（SpineResult），非零件**。
2. **memory 族 19 未用中约 15 个经 build_memory_recaller 工厂**：企业接入点 =
   host/decision_memory_recall.py:73,97（MemoryNote+build_memory_recaller）＋
   host/decision_memory_store.py:51-52,166（PgVectorStore/PgVectorStorePersister/
   ParticleTypeSet/TenantProfile/degraded_recall）。recall_precedents/rrf_fuse/
   PgNoteStore/note_hash/NOTE_ATTR_*/MemoryLogStore 等零件由工厂内部编排，
   企业无需直 import。**→ 增强需求 E1（工厂封装边界清单）**。

### Ⅲ 自建并存面（重复建设风险，请求权威裁定，共约 25 符号）

1. **LLM provider**：企业自建 llm/openai_compat.py + platform_provider.py +
   provider_switch.py（OpenAI 兼容协议 + 平台 provider 切换）；foundation
   build_provider/DeepSeekProvider 未用（LlmProvider/LlmResponse/StubProvider
   类型已用）。**→ E3**。
2. **两阶段 confirm（零信任写）**：企业自建 host/platform_handlers.py:215-216
   phase1 plan_preview（零写）→ phase2 consume_confirm（同确认人校验），
   承载 R22 的 46 Action 两阶段写；foundation issue_confirm_token/
   verify_confirm_token/ConfirmRequired/ConfirmTokenInvalid/CommandRejected 全未用。
   两套两阶段协议并存。**→ E2**。
3. **PG 基建层**：企业自建 tenant/pg_config_store.py + host/config_backend.py
   （配置存取层）；foundation connect/ensure_schema/ddl_statements/make_cursor/
   parse_dsn/validate_dsn/mask_dsn/probe_schema_isolation/terminate_* 等 20+ PG
   基建符号未用。⚠ 注意：**向量存储面企业用了 foundation**
   （PgVectorStore/PgVectorStorePersister），配置面自建——分层混用。
   **→ E4 附带裁定请求**。

### Ⅳ 业务暂不涉足/角色差异/条件不具备（约 300 符号，择要）

- **portal 26 全未用**：企业运营面为自管静态 html（web/ 30+ 页，config-center
  注册表驱动），NL→页面生成无消费场景。**确认贵方 F2 观察项属实，非疏漏**。
  → X4（portal 定位澄清，防僵尸面）。
- **evolution 19 未用**：R-FE1 口径——只接 bridge 主路径 4 符号，distill/
  shadow_replay/knob/prescription/supply_demand/coverage 等毕业前不扩面。
- **graph 写通道**（open_graph_write_store/write_controlled_edges/
  build_graph_write_server/make_graph_write_profile/allow_principals/EdgeWrite*）：
  企业角色是**动作执行方**（MCP 客户端侧），A-1 图写通道面向 MCP 服务端部署态，
  企业暂无自托管图写服务场景。
- **vector/onnx 零件**（OnnxRunner/pad_to_dim/pg_to_vec/vec_to_pg/
  ensure_embedding/vector_info/vector_backend/vector_resolve）：企业 embedding
  走外部服务，不做本地推理；检索经 PgVectorStore 封装已够，零件面不直触。
- **kernel.api 其余 129**（GAP_*/MAX_*/DIR_*/错误类型/工具常量）：企业错误面
  自建（enterprise 自有异常层级），foundation 常量仅在与契约交互处按需取用。

---

## 4. 增强需求（RFE 候选，消费者角度，6 项）

| # | 需求 | 动机（锚点） | 优先级建议 |
|---|---|---|---|
| E1 | **工厂封装边界清单**：build_memory_recaller 内部编排了哪些零件（recall_precedents/rrf_fuse/PgNoteStore/MemoryLogStore 各自是否在内、质量阈默认值） | 消费方现在只能读源码判断能力边界（§3-Ⅱ-2） | P2 |
| E2 | **confirm token 收敛裁定**：企业自建两阶段（platform_handlers:215-216）与 foundation issue/verify_confirm_token 并存——以哪份为 1.0 主路径？迁移成本与兼容期？ | 两套零信任写协议双轨，R22 漂移风险 | P1 |
| E3 | **provider 收敛裁定**：企业自建 openai_compat/platform_provider 与 build_provider/DeepSeekProvider 的分工（多 provider 运行时切换归谁） | 同类 E2，provider 切换策略是企业刚需（provider_switch.py） | P1 |
| E4 | **scenario 形态裁定**：ScenarioPackStore（文件包）与企业 DB 化（particles/handler_registry）——1.0 承诺主路径是哪条？DB 形态是否有 foundation 侧对应物/迁移说明？ | §3-Ⅰ-1；影响企业场景架构长期走向 | P1 |
| E5 | **spine 中间态可选外泄通道**：RubricReport 九尺子明细在 run_spine 返回值/审计持久化中的暴露程度——企业决策快照目前只能记聚合 confidence，审计复算排序需「矩阵 + 尺子明细」双 inputs | 四评分矩阵落地后审计可复算性缺口（verify_element_matrix 快照 matrix/matrix_reason 已记，尺子明细缺位） | P2 |
| E6 | **audit_persister 双轨消费范式样例**：T58 REJECTED/PENDING 审计轨 fail-closed——企业已用 AUDIT_* 四常量，双轨写面未显式接，请求一份最小消费样例 | 防企业把双轨审计做成单轨假完备 | P2 |

## 5. foundation 扩展功能建议（4 项）

- **X1 租户级可覆盖 priority profile 原语**（ELEMENT_PRIORITY 现由企业
  strictness.py 自算并按租户/场景覆盖）：建议 foundation 提供「契约定序 +
  消费方可覆盖 hooks 位」，⛔ 权重/矩阵本体仍留 enterprise（R134：排序=业务判断，
  改配置生效，入 L0 即污染契约）。价值：多消费方都要此能力时免重复造。
- **X2 合成语义常量**：红线>要素闸>写闸的合成顺序（R-E2）目前是企业
  orchestrator 注释级声明＋判据守卫；若 foundation 认可其为跨仓共识，
  可入 contract 作命名常量（如 REDLINE_PRECEDENCE_OVER_ELEMENT_GATE），
  防各消费方各自表述漂移。
- **X3 ⛔ 明确不建议入 foundation**：评分矩阵/维度权重/治理倾向档位——
  业务判断层，保持 enterprise 侧（本函即划界声明，防回捐/需求压力下
  边界模糊）。
- **X4 portal 定位澄清**：三仓零消费（F2）若持续，建议明确 portal 的
  目标消费方（内部产品？未来客户自助？）或设观察期，防能力面僵尸化。

---

## 6. 结论

1. **消费健康度**：enterprise 对 foundation 的消费集中在决策脊柱主链（run_spine
   全家桶）、memory 召回主路径、动作/编排/会话类型面、契约常量面——即清单
   §一§二§四§八的核心稳定面；evolution 按 R-FE1 最小接入。
2. **零越面**：本盘点 AST 采集即证据（全部 import 落在五门面内），
   门禁 check_import_surface.py 历史全绿与此互证。
3. **无能力缺口**：400 未用均有归因（§3 四类），⛔ 无"该用没用"。
4. **待 foundation 裁定**：E2/E3/E4 三项 P1（双轨收敛类）为下轮
   trust-but-verify 重点；X1/X2 若采纳可按月度回捐节奏排期。

— enterprise 消费方（chiyu-enterprise 仓），2026-10-12
