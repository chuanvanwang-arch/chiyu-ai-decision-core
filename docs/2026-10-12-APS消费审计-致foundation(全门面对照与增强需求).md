# APS 消费审计 · 全门面对照与增强需求（致 foundation）

- 日期：2026-10-12
- 审计方：APS（`D:\system\APS-ai-native`，消费方）
- 审计对象：foundation《2026-10-12-foundation核心功能清单(全门面枚举).md》（十个族、五门面、≈478 符号口径）
- 性质：**源码级消费对照**（非采信转述）。每条「已用」附 APS 仓 `文件:行号` 证据；每条「未用」附检索范围与甄别记录，可当场复跑。

---

## 〇、审计方法（可复跑）

1. **消费事实源唯一化**：APS 仓对 foundation 的全部依赖只能是「import 站点」。对 `src/ tests/ scripts/ contest_a_general/ contest_b_steel/ contest_c_discrete/ aps_core/ configs/` 全域 `.py` 检索 `from chiyu_ | import chiyu_`，得 **21 处 import 站点 / 9 个文件**（全枚举，无一遗漏）：`src/aps/platform/foundation.py`（适配层，16 站）、`src/aps/platform/kmd.py`（2 站）、`src/aps/server/routes_views.py`（1 站）、`tests/test_dual_track_e2e.py`、`tests/test_foundation_adoption.py`、`tests/test_kmd_spine.py`、`tests/test_mutation_anchor_discipline.py`、`tests/test_run_spine_adoption_probe.py`、`scripts/check_base_annotations.py`。
2. **符号逐一检索**：按清单正文可枚举的 **335 个符号**，以 `\b` 词边界在 APS 全域 `.py` 逐一定位，得「有命中 88 / 零命中 247」。
3. **三重甄别**（防两类误判）：
   - **同名自研误判为消费**：APS 自有 `ActionRegistry / EventBus / Prescription / Particle / canonical / LAYERS / TASK_STATES / backfill_plan / judge_worthiness / promote / distill / issue_confirm_token / assemble / check_supply_demand / ontology_sync / verify_chain / content_hash` 等与基座同名异实，逐一查 import 来源后**剔除**（例：`APS:src/aps/platform/events.py:39` 的 `Prescription` 是 APS 自有 dataclass，非基座进化族 `Prescription`）。
   - **注释/字符串误判为使用**：如 `APS:src/aps/platform/foundation.py:144` 的 `canonical/Particle/LAYERS` 出现在「为什么不扁平再导出」的注释里；`APS:src/aps/server/routes_views.py:332-367` 的 `run_spine/SpineResult` 出现在门户展示面元知识字符串里。均已剔除。
   - **零命中 ≠ 未用（反向兜底）：生产代码对基座的所有访问只可能经上述 21 站或其再导出名，故对 404 全量门面，import 站点枚举即完备判据；335 符号检索与其结论一致。
4. **休眠再导出识别**：适配层 `foundation.py` re-export 但 APS 下游生产代码零调用的符号，单列（它们有「存在性守卫测试」，无生产消费）。

**统计结论**：335 个可枚举符号中 —— **真实消费 68**、**休眠再导出 17**（清单见 §1.7/§1.10，均经下游零调用实证）、**APS 同名自研（刻意不消费）约 25**、**零命中 247**。按清单 ≈478 总口径，APS 实际消费率约 **13–14%**。

---

## 一、逐族对照

### 1.1 决策族（chiyu_decision.api + contract.decision + approval）—— 消费最深（36 符号）

**已用（附证据）**：

| 符号 | APS 证据 | 用途 |
|---|---|---|
| `score_rubric` | `APS:src/aps/platform/foundation.py:162` → `APS:src/aps/platform/kmd.py:77`（`is` 断言） | S2 九尺子评分 |
| `aggregate_confidence` | `APS:src/aps/platform/foundation.py:166` → `APS:src/aps/platform/kmd.py:80-82` | S3 置信度唯一来源（C-B 铁律） |
| `check_elements` | `APS:src/aps/platform/foundation.py:163` → `APS:src/aps/platform/kmd.py:78` | S2 八要素齐备 |
| `evaluate_redline` | `APS:src/aps/platform/foundation.py:165` → `APS:src/aps/platform/kmd.py:246-273` | S4 红线判定（判据由 APS 域回调注入） |
| `autonomous_release` | `APS:src/aps/platform/foundation.py:164` | S5 链末硬闸 |
| `validate_spine_order` | `APS:src/aps/platform/foundation.py:265-269` | 构造期脊柱顺序硬校验 |
| `RedlinePriorityGate` | `APS:src/aps/platform/kmd.py:88-92` | M2 双轨审批闸注入（2026-10-12 四模式落地） |
| `DecisionVerdictState` | `APS:src/aps/platform/kmd.py:90,566-569` | 三态判读（APPROVED/REJECTED/PENDING） |
| `run_spine` / `resume_spine` | 仅 `APS:tests/test_run_spine_adoption_probe.py:33-38` | **仅测试探针**（验证基座可注入性）；生产编排不用，见 §3-A |
| `SPINE_ORDER` 等 14 个契约常量 | `APS:src/aps/platform/kmd.py:38-53`；`APS:contest_a_general/portal/kmd_portal.py:42+` | 脊柱结构/九尺子/八要素/阈值/门表达式/七维的单一事实源 |
| `AUDIT_RECORD_KIND` / `AUDIT_EVENT_APPROVAL_PENDING` / `AUDIT_EVENT_APPROVAL_REJECTED` | `APS:src/aps/platform/kmd.py:94-96` | M2 双轨：REJECTED/PENDING 走审计轨 |

**未用 + 原因**：

| 符号 | 原因分类 | 说明 |
|---|---|---|
| `cap_rubric_by_elements` / `ELEMENT_RUBRIC_CAPS` / `ELEMENT_MISSING_CAP` | C 能力缺口 | 尺子封顶机制未接。APS S2 有自己的要素供给率（`supply_rate`，`APS:src/aps/platform/kmd.py:445-455`），与基座静态封顶表的复合语义缺文档（见 E3） |
| `AUDIT_APPROVAL_EVENTS` / `AUDIT_EVENT_APPROVAL_RESUMED` | C 能力缺口 | APS 双轨当前无 resume 路径（`resume_spine` 未接生产）；三个具体事件常量已直接用，集合常量反成冗余（见 E2/E4） |
| `DecisionError` / `DECISION_ERROR_CODES` / `DecisionPassThroughGate` / `DecisionApprovalVerdict` | D 口径 | APS 用 `DecisionVerdictState` 判读三态；错误码走 APS 自有异常体系 |
| `SpineResult` / `RubricReport` / `RedlineVerdict` | B 同名自研 | APS 自有同名类携带域字段（`source/thresholds` 等，`APS:src/aps/platform/kmd.py:204,246`），与基座纯计分结构语义不同；适配层 `APS:src/aps/platform/foundation.py:150-156` 明文记录不扁平导出的理由 |
| `DecisionApprovalGate` | D 口径 | 仅 import + 就绪断言（`APS:src/aps/platform/kmd.py:89,99`）；协议对象不实例化 |

### 1.2 决策记忆网（memory 函数族）—— 全族未用（B 类：APS 自有记忆层）

`write_decision_memory_net / PgNoteStore / InMemoryNoteStore / NoteStore / build_memory_recaller / recall_precedents / RecalledItem / degraded_recall / rrf_fuse / RRF_K_DEFAULT / PgMemoryLogStore / MemoryLogEntry / MemoryLogStore / MemoryNote / note_hash` **全部零命中**。

原因：APS 自有完整记忆实现（`APS:src/aps/platform/memory.py`：`judge_worthiness`（:276）、`promote`（:729）跨租户升格；`APS:src/aps/platform/embedding.py:189` 自有 `content_hash`；`APS:src/aps/platform/store.py:1585` 自有 `backfill_plan`，注释明载「采纳基座 `coverage.backfill_plan` 的同名纪律」——**同名再造，非消费**）。APS 记忆表 DDL 在 `db/schema.sql`（DDL 唯一事实源铁律），不接基座建表面。**这不是拒绝，是替换成本问题**：见扩展建议 X1（记忆存储协议面 + 逐面迁移适配器）。

### 1.3 数据族 —— 纯函数消费 16 符号，存储/图/向量整装门面基本未用

**已用**：

| 符号 | APS 证据 |
|---|---|
| `parse_dsn / validate_dsn / mask_dsn / DBConfigError` | `APS:src/aps/platform/foundation.py:73,80-83,125-127`（DSN 双形态校验，含 keyvalue→URI 适配 :276-320） |
| `assert_safe_identifier / assert_no_free_jsonb / assert_no_hard_delete` | `APS:src/aps/platform/foundation.py:84,88-89,124,132-133` |
| `pad_to_dim / vec_to_pg / pg_to_vec` | `APS:src/aps/platform/embedding.py:258-259`（`_F.pad_to_dim` 真调用）；`APS:src/aps/platform/foundation.py:85-87,129-131` |
| `FORBIDDEN_HOSTS / FORBIDDEN_ROLES` | `APS:src/aps/platform/foundation.py:348-350`（隔离连接收尾只摘本进程） |
| `drop_ephemeral_schemas / drop_test_schema / probe_schema_isolation / ddl_statements` | `APS:src/aps/platform/foundation.py:416-485`（pytest 隔离层） |

**未用 + 原因**：

| 符号族 | 原因分类 | 说明 |
|---|---|---|
| `PgVectorStore` / `PgVectorStorePersister` | **A 架构裁决不采纳** | `APS:src/aps/platform/foundation.py:32-36` 书面记录三坑：`upsert_particle` 硬编码 `dim=1024`、`connect(dsn=)` 绕过 `validate_dsn`、env 键名不可注入。APS 自有 `pg.py/store.py` |
| `open_store / make_cursor / ensure_schema / ensure_tsvector / terminate_* / in_testing_context / driver_available` | A/B | APS 自有 `pg.py`；schema 唯一事实源是 `db/schema.sql`（18 表 DDL），`ddl_statements` 建表会构成双事实源且撞基座 `_IDENT` 大写限制 |
| 审计链族 `chain_hash / build_chain / verify_chain / VerifyResult / hash_signature` | B 同名自研 | APS 自有 `APS:src/aps/platform/audit.py`（`payload_hash` + `verify_chain`，genesis 取自 `.schema`；import 仅 `hashlib/json/.schema`，:14-20）。`content_hash` 亦 APS 自有（`embedding.py:189`） |
| 受控图写族 `open_graph_write_store / write_controlled_edges / EdgeWrite / GraphStore / PgCteGraphStore / decision_backlinks / relation_view / timeline_view / fold_history` 等 | B/C | APS 自有边写入（`store.scoped_identity()/pid_for()` + 幂等，`DECIDED_ON` 边引擎溯源在 `kmd.py`）。两阶段 confirm 的图写 MCP 工具未排期 |
| 向量检索族 `vector_available / vector_backend / vector_resolve / vector_info / vector_index_ddl / ensure_embedding / cosine / hash_vector / OnnxRunner` 及 `TIER_FTS_VECTOR` 档位族 | B/C | APS 自有 `embedding.py`：离线哈希签名 dense 通道 + **诚实降级自述**（「非 pgvector 真 embedding」，`APS:tests/test_context_query_degradation.py:58-64` 实证）。ONNX 真向量未排期 |

### 1.4 运行族（actions/events/workflow/orchestration/plan/scenario/session）—— 全族未用（B 类：APS 全域自研）

零命中符号：`ActionSpec / ACTION_MAX / ALLOWED_TRANSITIONS / assert_transition / TaskStateError / TERMINAL_STATES / TASK_KINDS / SharedTask / WorkerRun / PublishReport / SessionEvent / Subscriber / counting_subscriber / log_subscriber / EVENT_TYPE_DECISION / EVENT_TYPE_MEMORY_LOG / Workflow 全族 / AgentLoop / AgentSpec / AgentRegistry / TeamMember / TeamRegistry / TeamSpec / SubagentDescriptor / SubagentPool / LoopGuard / FAILURE_LIMIT / MAX_REDO / GuardViolation / GuardDenied / PlanStep / PlanMode / PlanStateError / TodoItem / TodoList / ScenarioPackStore / ScenarioStep / scenario_from_dict / scenario_build_in_memory_server / DecisionScenarioProfile / DecisionIOField / IO_KINDS / GATE_KINDS / register_scenario / is_registered / get_scenario / require_scenario / list_scenarios / MAX_REQUIRED_FIELDS / SessionManager / SessionLog / TerminalSession / WorkMode / resolve_work_mode / MODE_PRESETS / resolve_storyline_policy`。

**同名自研实证**（均非基座对象）：`APS:src/aps/platform/actions.py`（自有 `ActionRegistry` + 39 条 `ActionDef` 目录 + M1 静态差集守卫）；`APS:src/aps/platform/events.py:12-39`（自有 `EventBus`/`Prescription`，import 仅 `.audit/.event_payload/.schema`）；`APS:src/aps/platform/schema.py:741`（自有 `TASK_STATES`）；`APS:src/aps/scenario_packs/`（自有场景包）；`APS:src/aps/platform/store.py:1585`（自有 `backfill_plan`）。

原因：APS 是**排产域平台**，运行族（任务态/工作流/多智能体团队/会话模式）在其域内已有完整实现且与 DDL/铁律耦合深；基座运行族是通用形态，逐面替换无排期。**注意 `GATE_KINDS` 未用的代价**：APS 审批闸形态（红线 spec/required_gates）目前是自有约定，与基座 `GATE_KINDS` 闭集无对齐（见 E4/X2）。

### 1.5 集成族（llm/mcp/mcpserver/tools/plugins/hooks）—— 全族未用

- **LLM 族**（`LlmProvider / LlmResponse / ToolCall / build_provider / DeepSeekProvider / StubProvider`）：零真实接线。APS 仅消费契约常量 `RUBRIC_LLM_ELIGIBLE`（`APS:src/aps/platform/kmd.py:45,241`，作为 rubric 元数据 `llm_eligible` 列出），`source="llm"` 只是 `kmd.py:204` 的枚举值，无调用路径；`OfflineStub` 仅存在于 docstring（`APS:src/aps/platform/__init__.py:660`）。**原因**：排产决策走确定性求解（CP-SAT/构造解），clarity 尺子 LLM 精评是可选增强，未排期（见 X3）。
- **MCP 双层**（`McpBridge / McpTransport / StdioTransport / McpServer / InMemoryMcpServer / McpToolDef / ToolRegistry / ToolSpec / ExposedTool / register_*_tools / run_command`）：零命中。APS 的 `mcp` 仅是自有 `ActionDef` 的 surface 标签（`APS:src/aps/platform/actions.py:88` `surfaces=("tool","cli","mcp")`），**不是**基座 MCP 协议栈。11-06 Streamable HTTP 窗口正需此项（见 X5）。
- **两阶段确认**（`issue_confirm_token / verify_confirm_token / ConfirmRequired / ConfirmTokenInvalid / CommandRejected`）：APS 自有同名实现（`APS:src/aps/platform/actions.py:669` `issue_confirm_token` 方法），未消费基座版。
- **沙箱族**（`SandboxedFs / PathEscapeError / ScopeDenied / READONLY_PATH_PREFIXES`）：零命中，APS 无文件沙箱需求面。
- **插件/钩子族**（`PluginRegistry / PluginSpec / BUILTIN_PLUGINS / active_plugins / disabled_plugins / HookBus / HookResult`）：零命中，未排期。

### 1.6 语义族（ontology/context/domain/canary/audit 规范/幂等）—— 少量已用，金丝雀全族缺口

**已用**：`meta_redline_hits`（`APS:src/aps/platform/evolution_feed.py:477,490` 真调用，元红线检出）。

**未用 + 原因**：

| 符号族 | 原因分类 | 说明 |
|---|---|---|
| `canary_probe / CanaryReport / g2_suspend_on_redline / BLOCK_KINDS / assert_block_kind / assert_anchor / assert_result_ref / assert_writable / apply_atomic` | **C 能力缺口（重点）** | APS 全域 `grep -i canary` **零命中**——APS 没有金丝雀防线。基座 `canary` 能力已 stable（`foundation:packages/chiyu-kernel/src/chiyu_kernel/version.py:67` CAPABILITIES 29 项之一），三判据（event+particle 成对 / engine 边恰好相等 / 红线挡落库，`foundation:packages/chiyu-kernel/src/chiyu_kernel/canary/__init__.py:57`）正是 APS G2/G3 需要的。未接原因是缺「自有 store 消费方」的协议面文档（见 E5/X4） |
| `CONTEXT_LAYERS / CONTEXT_DIMENSIONS / LAYER_NAMES / LAYER_LABELS_ZH / missing_context_dimensions / KNOWLEDGE_LAYERS / DomainBundle / inject_domain / assemble / AssemblyResult / DomainInjectionError` | B 同名自研 | `assemble/check_supply_demand` 命中均为 APS 自有 `ContextAssembler` 方法（`APS:src/aps/platform/context.py:122`，`kmd.py:450-451` 调用点）；`LAYERS` 是 APS 自有 `("L1","L2","L3","L4")`（`APS:src/aps/platform/context.py:32`），适配层 `foundation.py:143-147` 明文记录不扁平导出理由 |
| `OntologyGraph / ontology_sync / PRESCRIBABLE_PREDICATES / is_prescribable` | B 同名自研 | `store.py:229 _ontology_sync` 是 APS 自有方法 |
| `canonical / canonical_args / stable_stringify / is_forbidden_change / classify_change / BASELINE_FIELD / assert_not_baseline_skill` | B/D | `canonical` 命中为 APS 测试局部变量（`APS:tests/test_spec_single_source.py:129`）；审计规范 APS 自有 spec 模块 |
| `derive_idem_key / nightly_idem_key / IDEM_PREFIX / read_dispatch_cfg / dispatch_cfg_report` | B | APS 自有幂等键（schema/边幂等） |

### 1.7 进化族（experimental）—— 契约常量消费 15 符号，函数族全未用

**已用**（经 `APS:src/aps/platform/evolution_feed.py:49-64`）：`RISK_TIERS / TIER_AUTO / TIER_GUARDED / TIER_FORBIDDEN / DIRECTIONS / DIR_WIDEN / DIR_TIGHTEN / DIR_FLAT / PRESCRIPTION_STATES / META_REDLINES / VERDICTS / VERDICT_PASS / VERDICT_REJECT / FAIL_SAFE_VERDICT` + `meta_redline_hits`。

**休眠再导出**（适配层 re-export + 守卫测试断言存在性，生产零调用）：`EVOLUTION_OBJECTS / PRESCRIPTION_TERMINAL / PRESCRIPTION_TRANSITIONS / BASELINE_SKILL_PREFIX / PRESCRIPTION_AUDIT_FIELDS`（`APS:tests/test_evolution_base_adoption.py:222-227` 只证「在」，不证「用」）。

**函数族全未用**（`SkillDraft / promote / validate_draft / SkillRegistry / SkillSpec / SkillDraftError / SkillConflict / readiness_report / ReadinessReport / KnobSpec / KnobTable / begin_replay / shadow_replay / ReplayVerdict / distill / DistillReport / judge_worthiness / check_supply_demand / SupplyDemandGap / build_knowledge_needs / KnowledgeNeed / compute_coverage / CoverageReport / BackfillChannel / TraversalResult`）：APS 自有 evolution_feed/memory 实现（`judge_worthiness` 在 `APS:src/aps/platform/memory.py:276`；`promote` 在 `memory.py:729`；`distill`/`compute_coverage` 命中均为 APS 自有方法或测试局部变量），且 evolution 包 experimental 不在 1.0 承诺，按口径不外接。

### 1.8 版本出口 —— 5 符号已用

`require_capabilities`（`APS:src/aps/platform/foundation.py:231`，启动能力闸 `{"decision":"stable","persist":"stable","memory":"stable"}`）、`api_version`（:227，断言 ==1.0.0）、`PACKAGE_VERSION / CONTRACT_VERSION / capabilities`（`APS:src/aps/server/routes_views.py:604-606` 展示面）。未用：`API_VERSION / capability_status / deprecations`（见 E8）。

### 1.9 portal（chiyu_portal.api 26 符号）—— 全族未用（与 foundation 观察项 F2 一致）

`parse_nl_to_schema / guard_nl_input / validate_page_schema / render_conversation / render_onboarding / direction_cards / level_cards / mode_cards / workflow_cards / onboarding_steps / PageDraft / PageStore / COMPONENT_KINDS / AGG_FUNCS / FILTER_OPS / THEMES / DEFAULT_ALLOWED_ACTIONS` 等零命中。`render_page / PAGE_TYPES / SCHEMA_VERSION` 的命中均为 **APS 自有门户渲染器**（`APS:contest_a_general/portal/portal_renderer.py`，`kmd_portal.py:42` 起自建 PageSpec 体系）。原因：APS 门户已按「NL→受控 Schema→渲染器」铁律自建且与赛题展示面深度耦合；基座 portal 的 NL→schema 解析与 APS 受控 PageSpec 是两套契约，替换无排期。

### 1.10 契约补遗 —— 已用 7，休眠 8，零命中 5

已用：`MEMORY_KINDS / MEMORY_ADDRESS_KEYS / PROVENANCE_SOURCES`（`APS:src/aps/platform/memory.py:72` 惰性 `_contract()`）、`MEMORY_PREDICATES / EDGE_LAYERS / SEVEN_DIM_KEYS`（`APS:src/aps/platform/schema.py:24-26`）。
休眠再导出（生产零调用）：`MEMORY_DEFAULTS / BUSINESS_CLOCK_FIELD / RECORD_CLOCK_FIELD / PredicateSpec / PredicateSet / ParticleTypeSet / HASH_DIM / VECTOR_DIM / AUDIT_HASH_ALGO / AUDIT_GENESIS_HASH / AUDIT_REQUIRED_FIELDS / PROBE_ASSERTIONS`（共 12，仅守卫测试证存在）。
零命中：`TenantProfile / RISKS / LEVEL_IDS / TIERS / Particle`（`Particle` 命中为 APS 自有 `store.py:3` 类）。

---

## 二、未使用原因的四分类深析

| 类 | 定义 | 代表 | 对 foundation 的含义 |
|---|---|---|---|
| **A 架构裁决不采纳** | 有书面裁决记录，接=破坏 APS 铁律 | `PgVectorStore`（三坑，`APS:src/aps/platform/foundation.py:32-36`）、`ddl_statements`（与 `db/schema.sql` 双事实源）、`run_spine` 生产编排（10-09 三硬判据，其中两条已被基座演进部分证伪，见 §四） | 这些是**契约冲突**，不是推广问题；需基座侧选项化（E1） |
| **B APS 域自研（同名异实）** | APS 有自有实现且与 DDL/铁律耦合深，刻意不消费 | ActionRegistry/EventBus/Prescription/audit 链/记忆层/上下文装配/两阶段确认/门户渲染 | 替换是**迁移工程**，需协议面+适配器（X1/X5），不是「宣传不足」 |
| **C 能力缺口/未排期** | APS 想要但未接（真缺口） | LLM 族、canary 族、MCP 双层、尺子封顶、插件钩子、沙箱 | **增强需求的主战场**（§三 E1-E8、§四 X1-X6） |
| **D 口径/休眠** | 再导出未用或枚举值未选路 | 18 个休眠契约符号、`AUDIT_APPROVAL_EVENTS` 冗余、`DecisionApprovalGate` 未实例化 | 需「按需 re-export」纪律与推荐用法文档（E4/E6） |

---

## 三、增强需求（对 foundation 现有功能，消费者视角）

> 优先级：P0=阻塞某项已承诺窗口；P1=显著降本；P2=体验/文档。

### E1【P0】`run_spine` S5 语义选项化——「REJECTED 也落库」开关
- **现状**：基座 `run_spine` 的 APPROVED 走 `persister`，REJECTED/PENDING 只走 `audit_persister`（`foundation:packages/chiyu-decision/src/chiyu_decision/spine.py:76-86`）。APS 的域语义是**无条件落库 + DECIDED_ON 边**（被驳回的决策也是事实，`APS:src/aps/platform/kmd.py:525-600` M2 双轨即在 APS 侧重建该语义）。
- **诉求**：增加 `persist_rejected: bool = False`（或 `persist_policy` 枚举 `approved_only / all`），让消费方显式选择 S5 语义；选 `all` 时 REJECTED 也走 `persister` 且 payload 带 `record_kind`。
- **价值**：这是 10-09「维持现状」硬判据③的唯一解。解了它，APS 自有 `KmdSpine` 与基座 `run_spine` 的语义差归零，接管评估可重开。

### E2【P0】`resume_spine` 补齐 `audit_persister` 形参
- **现状**：`resume_spine(result, *, persister, audit_sink, approval_ref)`（`foundation:.../spine.py:265-268`）无 `audit_persister`。
- **诉求**：与 `run_spine` 签名同构补上；PENDING→批准落库时若走审计轨口径，两条路径必须一致。
- **价值**：APS M2 双轨已跑通 REJECTED/PENDING/APPROVED 三路径（`APS:tests/test_dual_track_e2e.py`，11 断言全绿），但**无 resume 入口**——人工在环批准后目前只能整链重跑。补上后 APS 的 PENDING 收口可直接复用。

### E3【P1】尺子封顶与消费方自有供给率的复合语义文档 + 可注入封顶
- **现状**：`cap_rubric_by_elements` / `ELEMENT_RUBRIC_CAPS` / `ELEMENT_MISSING_CAP` 是静态表；APS S2 有域供给率（`supply_rate`，由 `ContextAssembler` 产出，`APS:src/aps/platform/kmd.py:445-455`）。
- **诉求**：① 文档明确「消费方自有供给率时如何与基座封顶复合」（先封顶还是先供给率降权）；② 或提供 `cap_fn: Callable[[str, Mapping], float]` 注入位。
- **价值**：APS 未接封顶的直接原因是复合语义无定义，怕双口径叠加出不可解释的 confidence。

### E4【P1】`GATE_KINDS` / 审批闸形态与消费方对齐指南
- **现状**：APS 审批闸形态（红线 spec `mutex_top/sensitive` + required_gates）是自有约定；基座 `GATE_KINDS` 闭集零消费。
- **诉求**：出「域审批闸 → `GATE_KINDS` 映射」指南（如 `mutex_top→hard_block / sensitive→human_in_loop`），并文档化 `DecisionScenarioProfile` 的 `required_fields` 与 APS 八要素的对应。
- **价值**：三仓审批形态目前各说各话；对齐后审计面可跨仓比对。

### E5【P1】`canary_probe` 的「自有 store 消费方」协议面文档
- **现状**：三判据很强（`foundation:packages/chiyu-kernel/src/chiyu_kernel/canary/__init__.py:57`），但 APS 这类「自有 store/自有 events」的消费方不知道要实现哪个最小方法集才配被 probe。
- **诉求**：文档化 canary 依赖的 store 鸭子类型（最小方法集 + 返回结构契约），最好附一个「InMemory store 消费方」示例。
- **价值**：APS 零金丝雀是真缺口；文档到位后 APS G2/G3 防线可直接落地（判据可扩展，见 X4）。

### E6【P2】「re-export 使用即消费」守卫（或按需 re-export 纪律入文档）
- **现状**：APS 适配层一次性 re-export 了 17 个契约符号，下游生产零调用，仅守卫测试证存在（`APS:tests/test_evolution_base_adoption.py:222-227`）。三仓都有类似死重量风险。
- **诉求**：foundation 文档明确「按需 re-export，禁一次性全量搬；re-export 未见消费即删」；或提供 `tools/` 下「re-export 死符号」扫描器。
- **价值**：减少跨仓静默漂移面（改口径时要同步的死名字更少）。

### E7【P2】`meta_redline_hits` 字段级契约文档
- **现状**：APS `evolution_feed.py:477,490` 在用，但输入动作结构哪些字段参与命中判定，靠读源码。
- **诉求**：文档化输入结构字段级契约（哪些字段必填、哪些参与匹配、命中返回结构）。
- **价值**：元红线是自进化安全阀，字段契约不清则消费方不敢扩用。

### E8【P2】`require_capabilities` 失败信息附 `deprecations()` / `capability_status()`
- **现状**：APS 只在 `foundation.py:231` 见到 RuntimeError 列表，看不到「哪个能力什么状态、何时废弃」。
- **诉求**：fail-fast 时报文直接附 `deprecations()` 与相关能力 `capability_status()` 输出。
- **价值**：升级排障从「猜」变「读」。

---

## 四、扩展建议（foundation 应新增的能力）

### X1【P1】记忆存储协议面（Protocol）+ 逐面迁移适配器
APS 与基座是**两套记忆实现**（APS：`memory.py`/`embedding.py`/`store.py`；基座：`write_decision_memory_net`/`PgNoteStore`/`recall_precedents`/`rrf_fuse`）。建议基座提炼「记忆存储协议面」（note 写入口 / recall 质量阈 / RRF 融合 / 日志轨四个 Protocol），让 APS 这类自有记忆的消费方**逐面替换**（如先只换 `rrf_fuse` 融合算法），而非全有全无。毕业路径可参照 memory T44 先例。

### X2【P1】制造排产域 Decision profile 模板
基座 `TenantProfile / DecisionScenarioProfile / DecisionIOField` 是通用决策 I/O。建议出「制造排产」域模板：订单池 / 轧程（卷）/ 设备态 / 七源供给率作为标准 context 维度与 IO kind 映射。APS 每次装配 `KnowledgeNeeds`（`context.py:115-119`）都在重复这套域形状；模板化可降三仓域消费方装配成本，也让 `GATE_KINDS` 对齐（E4）有载体。

### X3【P1】clarity-only LLM 精评的标准接法
`RUBRIC_LLM_ELIGIBLE` 已限定只有 clarity 可 LLM 精评，但基座没有「LLM 精评 + 失败回落确定性结构评分」的标准实现。建议提供 `build_provider × score_rubric` 组合适配器（含 StubProvider 回落路径与「精评失败不得静默改分」判据）。APS 的 clarity 精评可直接落地，排产确定性主链路不受影响。

### X4【P2】canary 判据组的消费方注册机制
当前三判据是决策域固定判据。排产域需要额外判据：「保底解零硬违规」「求解器分层目标字典序未被破坏」（`W_TARDY_ORDER=1e8 > W_TARDY=1000 > W_MAKESPAN=1`）、「重排只冻结已完工工序」。建议 `canary_probe` 支持注册自定义判据组（返回统一 `CanaryReport`），APS 的 G2/G3 金丝雀即可域化落地。

### X5【P2】ActionDef → MCP ToolDef 标准桥
APS 有 39 条 `ActionDef` 目录 + handler 注册 + M1 静态差集守卫（`APS:scripts/check_action_registration.py` 绿）；基座有 `McpServer / ToolRegistry / ToolSpec / ExposedTool`。建议出标准桥：`ActionDef(surfaces 含 "mcp") → ExposedTool`，两阶段 confirm 走基座 `issue_confirm_token`。这正好服务 APS 11-06 Streamable HTTP 窗口（R-FA4），也是 enterprise 侧工具暴露的同一诉求。

### X6【P2】跨仓协作的 `仓名:路径:行` 锚点规范
三仓协作中「裸 `foundation.py:229`」类工单因仓名歧义对端 0 命中（APS 侧实锤：该文件在 APS 仓是适配层、foundation 仓无同名文件，误判「锚点漂移」）。建议 foundation 文档体系带头采用 `<仓名>:<路径>:<行>` 限定格式并写入三仓协作规范——本次报告已全程自循该格式。

---

## 五、增强闭环实证（回路有效，予以记录）

1. **`audit_persister`（T58）**：`run_spine` 签名 docstring 明载「2026-10-12 裁定接纳，**APS 诉求**」（`foundation:.../spine.py:80-85`）——APS 的审计轨诉求已变成基座能力，APS M2 双轨（`kmd.py:525-600`）与基座契约常量对齐落地。
2. **四个注入点**：APS 探针脚本 `scripts/check_base_annotations.py:41-45` 实时对拍显示，「基座无装配器注入形参 / 无记忆召回钩子 / 无域红线回调 / 无结构化红线」四条旧声明**已被基座演进证伪**（现行 `run_spine` 均含 `context_factory / memory_recaller / redline_callback / redline_spec`，`foundation:.../spine.py:56-68`），脚本以 `[WATCH]` 观察态跟踪。**这直接软化了 10-09 硬判据①②**——建议 foundation 与 APS 约窗口重开接管评估（判据③ S5 语义待 E1 解决）。
3. **能力登记同步**：基座 2026-10-10 将 memory 升 stable，APS 门槛同步至 `{"decision","persist","memory"}: stable`（`APS:src/aps/platform/foundation.py:229-231`），`CAPABILITIES` 29 项中仅 `evolution` 为 experimental——版本出口链路工作正常。

---

## 六、复核窗口与复跑方式

- **复跑本审计**：APS 侧检索脚本逻辑见 §〇（`\b` 词边界 + 21 站 import 全枚举双通道互证）；foundation 侧可对拍 `python -c "from chiyu_kernel.api import __all__"`（404 符号）与 `version.py:67` CAPABILITIES（29 项）。
- **建议复核窗口**：① E1/E2 落地后 1 周内——APS 重开 run_spine 接管评估；② X5（MCP 桥）落地后——对齐 11-06 Streamable HTTP；③ X1（记忆协议面）立题后——APS 启动逐面迁移的第一面（建议 `rrf_fuse`）。
- **本报告未提交 git**（按 APS 铁律：AI 不提交，精确命令由各仓负责人本地 commit）。

---

## 附：本报告引用的跨仓锚点格式说明

全文采用 `<仓名>:<路径>:<行>` 限定格式（`APS:` = `D:\system\APS-ai-native`；`foundation:` = `D:\system\chiyu-foundation`），避免裸文件名跨仓解析 0 命中（见 X6）。
