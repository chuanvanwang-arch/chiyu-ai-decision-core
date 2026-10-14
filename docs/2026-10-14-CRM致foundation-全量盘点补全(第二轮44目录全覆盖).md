# CRM 致 foundation · 全量盘点补全（第二轮 44 目录全覆盖）

> **来源**：CRM 仓 `docs/2026-10-13-crm-底座能力盘点与迁移账.md` §七（2026-10-14 第二轮）。
> **性质**：纯文档交接，零代码改动。本函补全第一轮交接总览（`fad57d9`）的盘点盲区，**取代其 56+12 统计口径**。

## 〇、为什么有第二轮

第一轮盘点（56 上收 + 12 留）仅覆盖 decision/approval/calibration/monitor 等老目录。经真实目录结构核对，CRM `src/` 实有 **44 个目录**，其中 **connectors/context/llm/mcp/signal/sync/skill(s)/ontology/knowledge/alerts/calc/contract/federation/web/account/aiAttributes/assets/feedback 等约 20 个目录从未分类**——其中包括大量零脱域成本的通用框架。按「通用功能必须全部收敛到 foundation」的唯一要求，第二轮以三步实证完成全覆盖：

1. `ls` 全目录文件清单（44 目录逐一点名）；
2. 逐目录域字面量污染检测（`grep -rE "sales|BANT|商机|报价|ICP|CRM_"` 计数：命中文件数/总文件数）；
3. 命中文件行明细 + 零命中文件头部语义确认。

## 一、新增上收（H-57 ~ H-70，14 项）——请纳入 harvest 计划

| H-ID | 能力 | 主锚点 | 脱域要点 |
|---|---|---|---|
| H-57 | 外部系统同步引擎（游标/幂等/写回闸/trust/挂载） | `sync/engine.js`/`factory.js`/`provider.js`/`mapping.js`/`cursor.js`/`gate.js`/`exportGate.js`/`writeback.js`/`pendingWrite.js`/`trust.js`/`mount.js`/`resolver.js` | 12/14 文件零域字面量；`sync/presets/`（salesforce 等）移注册表/种子 |
| H-58 | MCP 协议基础设施（server/鉴权/OAuth/两阶段令牌/规范参数） | `mcp/server.js`/`auth.js`/`authPolicy.js`/`httpAuth.js`/`oauth*.js`/`issueToken.js`/`tokenFormat.js`/`canonicalArgs.js`/`confirmToken.js`/`confirmSecret.js`/`config.js`（14 协议件） | 轻度污染：env 名 `CRM_API_TOKEN`/`CRM_CONFIRM_SECRET` 参数化、`minPrivilegeFallback:'sales'` 注入化；域装配留（tools/gateway/intent） |
| H-59 | **Agent 契约静态校验**（声明 skills/memory/knowledge_scope ⊆ 注册表） | `contract/contractParser.js`/`contractService.js`/`contractStore.js`/`probe.js` | **4/4 全零污染**；纯逻辑、IO 可注入。⚠ 目录名易误读为「业务合同」，实为 Agent 契约校验 |
| H-60 | **公式引擎 + 重排调度** | `calc/formulaEngine.js`/`reflowDispatcher.js` | **2/2 全零污染**，纯函数 |
| H-61 | 告警框架（注册表/存储/规则求值/钩子/端点） | `alerts/alertRegistry.js`/`alertStore.js`/`ruleEvaluator.js`/`alertHook.js`/`alertSignalHook.js`/`alertEndpoints.js`/`feedbackMetrics.js` | 注册表内容注入；`financeAlertHook.js` 域钩子留 |
| H-62 | **情境装配框架**（ai-context-layering L1-L4：分层/路由/范围/注入/快照） | `context/assembler.js`/`routing.js`/`routingExperiment.js`/`scope.js`/`injector.js`/`snapshotStore.js`/`supplySpec.js`/`timelineSource.js` | `assembler.js:26`(ICP_MATCH)/`:292`(CRM_KNOWLEDGE SQL) 脱域；particleTypes/roleProfiles=域配置注入；`assembleContextV2.js`（脊柱 S5 域装配）留 |
| H-63 | LLM 出口统一（config 驱动客户端/密钥解密/预检计量/降级回退） | `llm/client.js`/`llmConfigStore.js`/`secret.js`/`embeddingBootstrap.js`/`tokenAccountingShim.js` | 6/7 零污染；`llm/aiAttributes.js` 域留 |
| H-64 | 技能注册表 + 技能范围 | `skills/skillRegistry.js`/`registry.js`/`skill/skillScope.js` | `methodologySync`/`methodOutreachHook`/`seed` 域留 |
| H-65 | 事件总线补遗（失败追踪 + 事件契约） | `events/busFailures.js`/`eventContract.js` | 零污染 |
| H-66 | 信号通用件补遗（摘要/日历/路由） | `signal/digest.js`/`ics.js`/`route.js`/`router.js`/`workbenchView.js` | 零污染；信号域件 6 个留 |
| H-67 | 多租户联邦读框架（tenantIds 集合读 + 越权拒绝语义） | `federation/read.js`/`scope.js`/`conflict.js`/`config.js` | `territory.js`/`reportProject.js`（撞单/报备）域留 |
| H-68 | AI 属性评估协议（2D 模型/payload.ai.* 落轴/置信度 needsReview/LLM 注入+degraded 兜底） | `aiAttributes/evaluator.js` | 框架=评估协议通用；`AI_ATTR_DEFS`（CRM_DEAL 属性定义）+sales 依赖→域注入 |
| H-69 | 文件存储抽象 | `assets/storage.js` | 零污染；upload 阈值已走 config_store 注入（合规） |
| H-70 | 前端共享基座（R1-R7 UI 组件/布局/util/api/tokens） | `web/util.js`/`components.js`/`layout.js`/`api.js`/`*.css` | 可选上收（portal 前端基座）；~110 域页面 html 留 |

**优先级建议**：H-59/H-60/H-57/H-65（全零污染，收割成本最低）→ H-58/H-63/H-66/H-67/H-69（轻度清洗）→ H-61/H-62/H-64/H-68（框架+注入分离，需设计）→ H-70（可选）。

## 二、新增留 CRM（M-A ~ M-K，11 项）——不上收，仅备案

M-A 客户洞察（`account/insightService.js`）· M-B 脊柱 S5 域装配（`context/assembleContextV2.js`）· M-C 信号域件 6 个（跟进/线索/活动）· M-D 本体域钩子+域词表（`ontology/hooks.js:71-83`/`vocabulary.js`）· M-E 方法论知识注入（`knowledge/methodologyInjection.js`，域表耦合）· M-F 技能域同步/钩子/种子 · M-G 财务告警钩子 · M-H MCP 域装配（`tools.js`/`gateway.js`/`intent.js`）· M-I 经销商域联邦件（`territory.js`/`reportProject.js`）· M-J 门户域页面 ~110 html · M-K `llm/aiAttributes.js`。

## 三、全量口径与验收

- **全量统计**：上收 **70 项**（H-01~H-70）+ 留 **23 项**，CRM `src/` 44 目录零盲区。权威明细始终以 CRM 仓盘点账为单一事实源。
- **脱域三铁律不变**（G-域无关 / G-零IO / G-对等可测），逐项适用于本函新增 14 项。
- **分类修正提示**：`contract/`=Agent 契约校验（非业务合同）；`federation/`=混合态拆分（读框架上收、撞单/报备留）；`context/`=框架与 S5 域装配分离。
- **请 foundation 确认**：① 本函 14 项是否全部纳入 harvest 计划及批次归属；② H-58 MCP 协议件 env 名参数化方案；③ H-62 情境框架的注入面设计（与现有 D1-D8 契约层的关系）。

—— CRM-ai-native（AI 原生企业销售决策平台）2026-10-14
