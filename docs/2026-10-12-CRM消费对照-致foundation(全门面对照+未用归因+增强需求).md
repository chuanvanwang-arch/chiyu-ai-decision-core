# CRM 消费对照——致 foundation（全门面对照 + 未用归因 + 增强需求）

- 日期：2026-10-12
- 来文：《foundation 核心功能清单（全门面枚举）》（贵仓 docs/，T63 配套）
- 消费方：CRM-ai-native（Node.js 生产仓，www.chiyuai.com）
- 结论先行：
  1. CRM 与 enterprise 消费形态**根本不同**：CRM 是 Node.js 仓，无法 `import chiyu_*`——消费经**五种跨语言形态**发生：① 进程级 Python 导入（仓内 3 脚本、12 唯一符号）② 协议级（Node 主进程 ↔ Python sidecar / stdio MCP）③ 源码对拍（6 个测试守卫读贵仓源码字面量做一致性校验）④ 契约平行实现（8 件 Node 等价件，按 A9/R5 契约对齐）⑤ 部署级（wheel sha256 钉死）。
  2. 12 个唯一符号全部落在贵仓五门面 `__all__` 内（**零越面符号**，本轮逐一实取核实）；**但发现 1 处 CRM 侧 off-facade 路径导入**（`foundation_graph_write_stdio.py` 经 `chiyu_kernel.mcpserver` / `chiyu_kernel.graph.mcp` 导入 4 个符号——符号在 `chiyu_kernel.api.__all__` 内，但 import 路径非 sanctioned）——§4 诚实登记，修复待 CRM 侧批准。
  3. 未用面归因五类（架构性替代 / 脊柱形参间接 / 自建并存待裁定 / 业务阶段未到 / experimental 纪律），⛔ 无「该用没用」缺口；**portal 26 符号确认贵方 F2 观察项属实**（CRM 门户迁移排在 P3，当前非疏漏）。
  4. 另提增强需求 7 项（RFE 候选，与 enterprise E1–E6 及 2026-10-08 F-01–F-08 不重复）与扩展建议 4 项。

> **🔄 口径修订（2026-10-13，用户澄清）**：上文「CRM 是 Node.js 仓」为**当前态非终态**——CRM 仓后续亦整体迁移。「根本不同」应读作「**当前语言栈不同**」：五种跨语言形态（进程级 import / 协议级 / 源码对拍 / 契约平行实现 / wheel 钉死）均为**迁移期过渡桥**，非永久架构事实；终态收敛后五形态逐步消解（直 import 取代 ①④，协议面退役 ②⑤，对拍守卫转为同语言单测 ③）。本函未用归因五类中「架构性替代」类维持（语义层归因不受语言影响），凡依赖「语言栈不可逾越」前提的表述以本修订为准。

---

## 0. 方法与口径（机器可验，可独立复跑）

- 贵仓 `scripts/facade_usage_audit.py`（AST 扫 Python import）只适用于 Python 消费方；CRM 侧对应复跑命令：
  - 形态①：`grep -rn "^from chiyu_\|^import chiyu_" CRM-ai-native/scripts/`（实取：6 条 import / 3 文件，全量无遗漏）
  - 形态③：`grep -rln "CHIYU_FOUNDATION_ROOT" CRM-ai-native/test/`（6 守卫）
  - 形态④：`grep -rln foundation CRM-ai-native/src/mcp/ CRM-ai-native/src/decision/`（等价件族）
- 符号 sanctioned 核验：12 个符号逐一在贵仓 `chiyu_kernel/api.py` 与 `chiyu_decision/api.py` 的 `__all__` 实取核实（只引符号名 + 区段，不引行号——贵仓 `MEMORY_EXPERIMENTAL` 行号曾三天四漂，判据 #23：跨仓引述禁行号）。
- 「未用」定义沿用贵方与 enterprise 共识口径：无显式引用；经 `run_spine` 形参 / 工厂封装 / 源码对拍的间接消费**不计缺口**。
- ⚠ 口径差预告：CRM 侧「消费」含非 import 形态（协议 / 对拍 / 平行实现），与 enterprise 的「499 符号引用率」**不可直接比大小**；可比的是「直 import 面」——CRM 12 vs enterprise 99，差异全部由语言栈解释（Node 仓无 Python import 面），⛔ 不因此推断 CRM 消费深度更浅。

---

## 1. 总览（按来文清单十节）

| 来文节 | 族 | 直 import 符号 | 其他形态消费 | 未用主因归类 |
|---|---|---|---|---|
| §1.1 decision.api（15） | 脊柱与评分 | 1（`run_spine`） | 7 个经 `run_spine` 内部执行（源码实证，见 §3-Ⅱ） | Ⅱ |
| §1.2 contract.decision（22） | 决策契约 | 1（`RUBRIC_KEYS`，经 api 再导出） | 3 个经源码对拍（`EIGHT_ELEMENTS`/`SEVEN_DIMS`/`SEVEN_DIM_KEYS`） | Ⅳ |
| §1.3 approval（5） | 审批闸 | 1（`RedlinePriorityGate`） | — | Ⅰ/Ⅳ |
| §2 memory（22） | 决策记忆网 | 0 | — | Ⅳ（选型决策已登记） |
| §3 数据族（约 68） | store/persist/graph/vector | 4（`open_graph_write_store`/`build_graph_write_server`/`StdioTransport`/`allow_principals`，⚠ off-facade 路径） | A-1 协议链（代码就绪、kill-switch 休眠） | Ⅰ/Ⅳ |
| §4 运行族（约 65） | actions/events/workflow/orchestration/plan/scenario/session | 0 | — | Ⅰ |
| §5 集成族（约 43） | llm/mcp/mcpserver/tools/plugins/hooks | 0 | 3 件契约平行实现（canonicalArgs/confirmToken/authPolicy）+ A9 回捐验收 | Ⅰ/Ⅲ |
| §6 语义族（约 38） | ontology/context/domain/canary/audit | 1（`profile_from_dict`，api 域装配面） | — | Ⅰ |
| §7 evolution（26） | 进化（experimental） | 0 | — | Ⅴ |
| §8 版本出口（11） | kernel.api | 3（`api_version`/`capabilities`/`require_capabilities`） | R-FC4 握手 + R-C5 启动断言 | Ⅳ |
| §9 portal（26） | 页面生成 | 0 | — | Ⅳ（P3 阶段） |
| §10 contract 补遗（15） | 契约常量 | 0（`TenantProfile` 经 `profile_from_dict` 间接构造） | — | Ⅳ |
| **合计** | | **12 唯一符号** | 6 守卫 + 8 等价件 + 2 协议链 + 部署钉死 | |

---

## 2. 已用明细（五种消费形态）

### 2.1 形态①：进程级直 import（3 脚本 / 6 条 import / 12 唯一符号）

| 符号 | 门面核验（本轮实取） | CRM 文件 | 用途 |
|---|---|---|---|
| `run_spine` | `chiyu_decision.api` ✓ | `scripts/quote_approval_shadow.py` | P1 影子判定权威（报价定价单场景，生产 crm-shadow 容器在跑） |
| `set_key_format` / `profile_from_dict` | `chiyu_kernel.api` ✓ | 同上 | crm-quote 域 `TenantProfile` 进程级装配 |
| `RedlinePriorityGate` | `chiyu_kernel.api` ✓ | 同上 | 红线优先审批闸复用（不重造） |
| `RUBRIC_KEYS` | `chiyu_kernel.api` ✓ | 同上 | N2 整改后消除手抄契约复制 |
| `api_version` / `capabilities` | `chiyu_kernel.api` ✓ | `scripts/quote_approval_sidecar.py` | R-FC4 `/healthz` 握手回传（版本 + 29 能力档位） |
| `api_version` / `require_capabilities` | `chiyu_kernel.api` ✓ | `scripts/foundation_graph_write_stdio.py` | R-C5 启动期 fail-fast 断言（api_version=1.0.0 + graph/mcpserver=stable） |
| `StdioTransport` / `allow_principals` | ⚠ `chiyu_kernel.mcpserver`（**符号在 api.__all__，路径非 sanctioned**） | 同上 | A-1 stdio 行协议 transport + 主体白名单 |
| `build_graph_write_server` / `open_graph_write_store` | ⚠ `chiyu_kernel.graph.mcp`（**符号在 api.__all__，路径非 sanctioned**） | 同上 | T54 sanctioned 图写 store 工厂 + MCP server 构造 |

（`api_version` 两脚本各 import 一次 ⇒ 唯一符号 12、import 语句 6。⚠ 项详见 §4）

### 2.2 形态②：协议级消费（Node 主进程 ↔ Python 子进程）

- **链 A（生产在跑）**：`src/sales/quoteShadowBridge.js`（spawn stdio 影子桥）→ `quote_approval_shadow.py`（`run_spine` 判定，stdout JSON 回传）；`src/sales/quotePricingSidecar.js`（HTTP 客户端 + R-FC4 握手校验，版本/能力不符即降级告警不静默）→ `quote_approval_sidecar.py`（crm-shadow 容器 4319，仅绑 127.0.0.1）。kill-switch 默认 `node` 休眠（权威裁定仍在 Node 侧）。
- **链 B（代码就绪、未接线）**：`src/decision/foundationTransport.js`（JSON-RPC 行协议 + 两阶段确认 + 批量写 + 连接自愈 + fail-open）→ `foundation_graph_write_stdio.py`（glue，含 `_FlushWriter` 逐行 flush）→ 贵仓 `McpServer.handle_request` / `write_controlled_edges`。kill-switch `A3A_EDGE_MIRROR` 默认休眠；真实接线三待：① 部署侧 env 注入（`A1_MIRROR_*` + `CHIYU_DB_*`）② HITL 翻开关 ③ P1 硬前置。判据 #16：暴露≠可调用，零跨仓写不谎称已消费。

### 2.3 形态③：源码对拍（6 守卫，零 import）

| 守卫（CRM `test/scripts/`） | 贵仓源码 | 对拍内容 |
|---|---|---|
| `rfc3-seven-dims-consistency.test.js` | `contract/decision.py` | `SEVEN_DIMS` ↔ CRM `DIMENSIONS` 同键同序（R-FC3） |
| `r9-eight-elements-consistency.test.js` | `contract/decision.py` | `EIGHT_ELEMENTS` ↔ 本地八要素（N1：`implications↔impact` 唯一差异钉死） |
| `r9-edge-consistency.test.js` | `contract/particle.py` | `MEMORY_PREDICATES` ↔ CRM `WRITABLE_EDGES` 七边 |
| `r9-edgewrite-field-whitelist.test.js` | `graph/mcp.py` | `edge_attribute` 字段白名单（props 静默丢弃整改） |
| `r9-vertex-substrate-consistency.test.js` | `contract/particle.py` | E5 异常 substrate（entity `kind=exception`） |
| `a1-stdio-glue-consistency.test.js` | mcpserver 协议形态 | glue 与协议一致性（含 `_FlushWriter` 块缓冲缺陷变异自证） |

另：`test/fixtures/a1_foundation_stdio_stub.py` + `a9_foundation_mcpserver_stub.py` 两个协议桩（**零 foundation import**）+ `test/decision/foundationTransport-stdio-e2e.test.js`（真 spawn 子进程走真实管道 E2E，变异自证 `A1_STUB_NO_FLUSH=1` 实测超时报红）。

### 2.4 形态④：契约平行实现（8 件 Node 等价件，按 A9/R5 契约）

| Node 件（CRM `src/`） | 对应贵仓契约/符号 | 对齐证据 |
|---|---|---|
| `mcp/confirmToken.js` | `issue_confirm_token` / `verify_confirm_token` | HMAC + `timingSafeEqual` 等价 |
| `mcp/canonicalArgs.js` | `canonical_args` | 跨语言逐字节对拍（A9 回捐验收②） |
| `mcp/authPolicy.js` | `McpServer` `auth(ctx)` 钩子 | A9 契约 §1/§2/§5.1 |
| `decision/foundationTransport.js` | R5 transport 契约 + `graph/mcp.py` 两阶段 | 四方法 + 错误语义 + token 重试 |
| `decision/foundationHttpServer.js` | ③号线 HTTP 适配器 | 已交付；服务端切换属 HITL 排期 |
| `decision/eightElementsToFoundation.js` | N1 键名映射层 | `implications→impact` 纯函数 + 守卫 |
| `decision/graphVertexMirror.js` | A-3a 顶点粒子化 | `prepareDecisionMirrorBatch` |
| `decision/edgeMirrorToFoundation.js` | A-1 镜像批处理 | `mirrorBatchToFoundation` |

A9 回捐验收五条（无 auth⇒AuthDenied / canonical 逐字节 / 绑定三元组变异三例 / 错误语义 / 白名单外 AuthDenied）CRM 侧全过（43 单测 + 11 E2E + 协议桩 + 变异自证）。

### 2.5 形态⑤：部署级消费

`scripts/tencent-lighthouse-deploy/deploy.sh::verify_foundation_wheels()` —— 发布前校验 `foundation-wheels/` 与 `foundation-pins.txt` 的 sha256 一致（判据 #14），不一致 exit 1；crm-shadow 容器镜像内含 foundation wheel。

---

## 3. 未用归因（五类，⛔ 无「该用没用」缺口）

### Ⅰ 架构性替代（CRM 自有更合适形态）

1. **memory 族 22 全未用**：CRM 记忆/向量/闭环为 Node 自建（`src/memory` + `src/ontology` + `src/knowledge`）。T44 毕业转 stable 后，「是否切换消费底座记忆」已登记为 CRM 侧选型决策（CRM 迁移计划 §3.2，须单独立项评估迁移成本 / AGE 图与 `OntologyGraph` 语义对齐 / 现有向量口径），非底座欠账。
2. **运行族约 65 全未用**：CRM 自有对应物——`src/action`（Action Registry + `autonomyEngine` 分级放行）、`src/agents`（skillCalls⊆capabilities 装配）、事件驱动 Node 化；阶段型 Workflow / Plan / TodoList 与 CRM 事件驱动架构正交，暂无场景。
3. **集成族 LLM/MCP 双层/confirm/sandbox 未直 import**：CRM MCP 暴露面是生产核心（113 工具 + OAuth + 零信任 + 两阶段 confirm），走官方 SDK + 自建网关；对应能力以契约平行实现存在（§2.4），非缺失。
4. **语义族 ontology/context/canary/audit 未直 import**：CRM 自有 `src/ontology` + `src/context` + `src/knowledge` + 假绿判据库；金丝雀职责由 `shadow-review.mjs` 与跨仓守卫承担。

### Ⅱ 脊柱形参间接消费（不构成缺口，本轮源码实证）

`decision.api` 15 符号中 14 个未直 import，其中 `score_rubric` / `aggregate_confidence` / `cap_rubric_by_elements` / `check_elements` / `evaluate_redline` / `autonomous_release` / `validate_spine_order` **七个由 `run_spine` 内部依次执行**——本轮在贵仓 `chiyu_decision/spine.py` 源码实证（`score_rubric`/`check_elements`/`cap_rubric_by_elements`/`aggregate_confidence`/`evaluate_redline`/`autonomous_release` 调用点齐备，`validate_spine_order` 构造期断言）。CRM 消费的是脊柱编排结果（`SpineResult` 字段子集：decision_id/state/confidence/redline_hit/redline_reasons/autonomous），非零件。
`resume_spine` 未用：报价场景单次裁定，人工审批在 CRM 侧闭环，无「审批后续跑脊柱」场景。

### Ⅲ 自建并存面（请求权威裁定）

1. **两阶段 confirm**：CRM `confirmToken.js`（HMAC 令牌）与贵仓 `issue_confirm_token`/`verify_confirm_token` 并存——CRM 侧已按 A9 契约逐字节对齐并回捐验收（五条全过）。请贵仓裁定：A9 契约是否为 1.0 主路径、Node 等价件是否计入「已消费」。（enterprise E2 同题；CRM 补充跨语言对齐证据）
2. **LLM provider**：CRM 自有 `src/llm` 多 provider 运行时切换；`build_provider`/`DeepSeekProvider` 未用。（enterprise E3 同题）
3. **PG 基建层**：CRM 自有 `src/db`（PG16 pgvector 直连）；`connect`/`ensure_schema`/`ddl_statements` 等未用。

### Ⅳ 业务阶段未到（CRM 迁移计划已排期）

1. **portal 26 全未用**：确认贵方 F2 属实——CRM 门户为 Node SSR（`src/portal` 5,760 行 / 93 HTML + Shadow DOM 组件），门户迁移排在 P3 阶段；届时 NL→页面生成方有消费场景。
2. **graph 读回视图**（`relation_view`/`timeline_view`/`fold_history`/`decision_backlinks`/`PgCteGraphStore`）：A-1 C1 第二步（真库 E2E 验证一致后切权威）才读回——读路径须先澄清，见增强需求 C6。
3. **scenario 注册面**（`register_scenario`/`require_scenario`/`list_scenarios`）：CRM 决策场景 DB 化（`config_store` 播种，26/27 键口径对账项已登记），P2 场景迁移才接；P1-0 未播种键补种已设计（否则 spine 首调 `UNKNOWN_SCENARIO`）。
4. **`audit_persister` 双轨（T58）**：CRM sidecar 当前 `audit_sink=None`；双轨审计持久化在 P2 迁移时接——见 C5。
5. **版本出口其余 8 符号**（`__version__`/`API_VERSION`/`CONTRACT_VERSION`/`PACKAGE_VERSION`/`capability_status`/`deprecations`）：`api_version()` 门面兼容版本口径已在 R-FC4/R-C5 两处用；分发包版本与契约版本的分寸 CRM 暂无消费场景。

### Ⅴ experimental 纪律

evolution 26 全未用——CRM 迁移计划铁律「协议态能力不得作为生产依赖」；enterprise R-FE1 同口径，两消费方一致。

---

## 4. 自查缺陷：1 处 off-facade 导入（诚实登记）

**事实**：`scripts/foundation_graph_write_stdio.py` 的 `_import_foundation_syms()` 经 `chiyu_kernel.mcpserver` / `chiyu_kernel.graph.mcp` 导入 `StdioTransport` / `allow_principals` / `build_graph_write_server` / `open_graph_write_store` 四符号。经本轮核实：四符号均在 `chiyu_kernel.api.__all__`（再导出区段实取），但 **import 路径不在贵仓 sanctioned 五面**（`docs/sanctioned-import-surface.md` 明示适用对象含 CRM-ai-native）。

**为何发生**：该 glue 按贵仓 `graph/mcp.py` 注释区引用的子模块路径直写（「transport 由消费方自实现」语境），未走门面再导出。

**影响面**：该脚本为 A-1 参考骨架、kill-switch 休眠未接线（判据 #16），当前零生产触达；一旦接线即构成 sanctioned 面违规。

**修复方案**（待 CRM 侧批准后实施，本函不自主改码）：四符号改 `from chiyu_kernel.api import ...` 单行导入，语义零变化（api 为再导出而非 wrapper）。

**根因启示**：贵仓 `tools/check_import_surface.py` 的 SCAN_ROOTS 只覆盖贵仓自身（`packages/{kernel,decision,portal}/src` + `examples/`），**消费方代码无门禁覆盖**——CRM 此次为人工审计才发现。⇒ 增强需求 C1。

---

## 5. 增强需求（RFE 候选，7 项；与 enterprise E1–E6 / 贵仓旧 F-01–F-08 不重复）

| # | 需求 | 动机（锚点） | 优先级 |
|---|---|---|---|
| C1 | **消费方侧 sanctioned import 门禁**：`check_import_surface.py` 增加 `--consumer-root` 模式（或发布 CI 片段），让 CRM/enterprise/APS 在各自仓自检跨面导入 | §4 实证：CRM off-facade 导入无人报案；门禁对消费方零覆盖 | **P1** |
| C2 | **契约的机器可读导出**：将 contract 面（`EIGHT_ELEMENTS`/`RUBRIC_KEYS`/`SEVEN_DIMS`/`MEMORY_PREDICATES`/`SPINE_ORDER`…）导出为版本化 JSON/manifest（贵仓 `tools/gen_capability_manifest.py` 已有磁盘枚举机械守卫，可扩展），供消费方守卫吃稳定导出物 | CRM 6 个跨仓守卫全部 `readFileSync` 解析贵仓 Python 源码字面量（含嵌套元组括号配平）；贵仓 `MEMORY_EXPERIMENTAL` 行号曾三天四漂（判据 #23），源码对拍形态脆弱 | **P1** |
| C3 | **键名别名 / deprecation 机制**：`EIGHT_ELEMENTS` 第 5 键 `impact` 与 CRM 存量 `implications` 的跨仓键名分裂（N1 已实证：P2 迁移直喂必炸）——建议契约面提供 deprecated alias 表，并对历史键名变更发 `deprecations()` 警告 | `eightElementsToFoundation.js` 映射层是消费方补丁；alias 机制可让多消费方免各自造映射 | **P1** |
| C4 | **跨语言 sidecar 参考骨架**：`examples/reference_consumer` 是 Python 内消费样板；CRM 消费形态是 Node 主进程 + Python sidecar 子进程。建议补「polyglot consumer」最小样例：spawn → `/healthz` 握手（版本/能力）→ `/judge` → 降级路径 | CRM 本轮自造 R-FC4 握手语义 + `_FlushWriter` 块缓冲坑（贵仓 `serve()` 只 write 不 flush，pipe 场景 Python 块缓冲致 CRM 侧 8000ms 超时）——跨消费方共性坑，应沉淀为骨架 | P2 |
| C5 | **双轨审计的跨语言消费样例**：T58 `audit_persister`（REJECTED/PENDING fail-closed）CRM 未接（sidecar `audit_sink=None`）；enterprise E6 亦请求同款样例。CRM 补充：需要 Node 侧审计持久化如何经 sidecar 透传双轨的样例 | 防消费方把双轨审计做成单轨假完备（CRM 假绿判据库同族） | P2 |
| C6 | **graph 读回视图的 sanctioned 路径澄清**：`relation_view`/`timeline_view`/`fold_history`/`decision_backlinks`/`PgCteGraphStore` 的合法消费路径——经 mcpserver 工具暴露，还是消费方可直连 PG 只读？A-1 C1 第二步（读回切权威）开工前必须明确 | CRM 迁移计划 §3.1.2 C1 第二步前置；路径不定则读回无法设计 | P2 |
| C7 | **「恒人工审批」一等契约表达**：报价场景必须恒 PENDING（除非红线），当前靠 elements 强制空 + `RedlinePriorityGate` 隐式行为实现（该 gate 不读 `autonomous_allowed`、`autonomous_threshold∈[0,1]` 约束无法逼恒 False——CRM `shadow_once` 注释区详细记载此 hack 的脆弱性）。建议审批闸提供显式 `force_pending` / 三态表达 | 副作用编程式契约消费，基座演进即静默破义；多消费方同需（enterprise `_SpineApprovalGate` 亦自造同构逻辑） | P2 |

## 6. 扩展功能建议（4 项）

- **X-C1 契约变更的消费方影响面通知**：贵仓 `contract/` 子树变更时产出「键集/常量 diff 摘要」（哪些符号键集变了），或随 capability manifest 发修订号，让消费方守卫对拍「契约修订号」而非文件内容——CRM 6 守卫目前 fail-closed 依赖本地文件可达性，主动通知能更早暴露漂移。
- **X-C2 合成顺序命名常量**：红线 REJECTED > 人工强制 PENDING > 自主放行的合成顺序（C7 的契约化形态）若贵仓认可为跨仓共识，可入 contract 作命名常量——与 enterprise X2 同向，CRM 附跨语言证据（两消费方各自自造同构闸即漂移实锤）。
- **X-C3 ⛔ 明确不建议入 foundation**：CRM 领域尺子/阈值（如 `autonomous_threshold=0.79`）/场景键/审批语义——业务判断层留 CRM 侧（本函即划界声明，与 enterprise X3 一致）。
- **X-C4 reference_consumer 致谢与复用计划**：F-07 已交付（`examples/reference_consumer` 含 probes/canary 常驻探针 + agents.py N6 登记样例），CRM 将在 P2 场景迁移对拍中复用其探针范式；建议贵仓把 probes 范式同步进 memory 毕业文档（T44）作消费方标配。

---

## 7. 结论

1. **消费健康度**：CRM 对 foundation 的消费集中在决策脊柱主链（`run_spine` + `RedlinePriorityGate` + `TenantProfile` 装配）、版本能力闸（R-FC4/R-C5）、图写受控通道（代码就绪待接线）——即来文清单 §一§三§八核心稳定面；evolution 按纪律零消费。
2. **零越面符号**：12 唯一符号全在五门面 `__all__`（本轮实取）；1 处 off-facade 路径已诚实登记并给修复方案（§4）。
3. **无能力缺口**：未用面全部有归因（§3 五类），⛔ 无「该用没用」；portal 确认贵方 F2 观察项属实。
4. **C1/C2/C3 状态更新（10-13 第四轮反馈）**：foundation 第四轮反馈确认 C1/C2/C3 接受为 P1 候选——C1 与第三轮回执 §2.2 选项②（贵仓另起 `tools/` 正式件）正面对齐、已随用户 10-13 拍板立项（F-A/F-B/F-C 整族转入 P2）；C2/C3 维持 P1 候选待贵仓排期。C4/C5/C6/C7 按 CRM P1→P2 排期触发；X-C1/X-C2 若采纳可按月度回捐节奏。
5. **CRM 侧待办**（本函登记，不自主改码）：§4 off-facade 导入修复（4 符号改走 `chiyu_kernel.api`）——随选项②立项转入 P2 开工首项（F-C），待 P2 开工指令触发。

---

## 8. 第四轮反馈联动（10-13）

foundation 第四轮反馈（会话）要点与 CRM 处置：

- ① 确认本函四条结论（12 符号零越面 / 未用归因五类无缺口 / §4 off-facade 诚实登记 / C1–C3 接受候选）——C1/C2/C3 状态由「待裁」更新为「P1 候选已接受」（见 §7.4）；
- ② 选项②确认不撤销：用户 10-13 拍板「foundation 另起 tools/ 正式件兼 C1」+ 下一轮「继续迁移」默示确认；贵仓无记录系 CRM 有意延迟投递（存档于 CRM 仓 `docs/2026-10-13-decision-facade-audit-c1-p2.md`，commit `8824a91`），非决策未立；
- ③ 10-13 核收件已同批投递贵仓 `docs/`（文件名同 CRM 仓）存档闭环；
- ④ 62 存量失败 foundation 不背书，CRM 早已单列排查（任务 #69，触发=用户明确指令）、从未声称获背书——详见 CRM 10-13 回应函 `docs/2026-10-13-crm-response-foundation第四轮反馈.md`。

— 追加于 2026-10-13

— CRM 消费方（CRM-ai-native 仓），2026-10-12（§8 追加 2026-10-13）
