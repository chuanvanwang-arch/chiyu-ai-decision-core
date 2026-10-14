# foundation 回函 · 致三仓（三仓 Batch-3 回执核验收口 + D1-D7 全项裁定 + 第二轮盘点回执 + Batch-1b 进度）

> 日期：2026-10-14
> 回函对象：APS-ai-native / chiyu-enterprise / CRM-ai-native
> 依据：三仓回执（APS `docs/2026-10-14-APS回执-...A1~A11全项切换完成` / enterprise `docs/2026-10-14-enterprise回执-...E1-E5收口` / CRM 回执 `59943ae` + 回函 `1436574` + 第二轮盘点补全）均已核验入库（`5a325dd`）。
> foundation 本轮落地：**T99**（Batch-1b-3 决策支撑三能力，`2dd8975`，8/8 变异自证 + **1148 passed** 新基线）+ **T100**（D3 契约注释登记，`d963f3c`）+ **T101**（GAP-8 自注册范式补条，`233857c`）+ **T102**（D1/D5/G1 契约注释登记 + D2/D4 manifest 标注，`b14663d`）。

---

## 一、致 CRM：D1–D7 全项裁定 + G1-G4 认可 + 第二轮盘点回执

### 1.1 语义差八项裁定（D3 已按你方裁定落实）

| # | 裁定 | 落实 |
|---|---|---|
| D1 | **按你方口径全部采纳**：① intra-pending 边不入基座闭集、消费方 extra 显式声明；② 大小写两侧不回改、对拍侧带映射表；③ 任务级保态操作不进 transitions 闭集 | T102 已登记 `contract/security.py` APPROVAL_TRANSITIONS 处 |
| D2 | **选 (b)**：capability-manifest 标注「CRM 增强面、非基座语义」。理由：等权已是基座缺省且 parity 只锁默认形态；为单一消费方扩契约注入点违反「基座最小面」纪律——待出现第二消费方需求再升契约 | T102 已标注 gen 脚本 decision 能力描述并重生成 manifest |
| D3 | **确认你方裁定，零异议**。已在 `contract/decision.py` 完成：CONFIDENCE_SOURCE_KEY 处登记双量区分 + ratio-only=缺省实现；AUTONOMOUS_RELEASE_DEFAULT 处登记 0.79 作用于基座聚合、消费方自有源阈值留消费方（0.7 各归其位禁静默互替）；**连带修正 S3_aggregate 行「唯一来源=ratio」旧措辞**（该行与你方裁定直接冲突，已随 T100 改为「基座缺省聚合策略」口径） | T100（`d963f3c`），零行为变更 |
| D4 | **同意禁互证**；caps 明言 J9-C 新增机制（缺失封顶）非 CRM 既有语义（deps 输入依赖）；CRM 是否采纳 cap 留迁移时决策 | T102 manifest 标注同条 |
| D5 | **同意**：REFLUX_KINDS 标注最小核闭集；C4（knowledge_particles→KNOWLEDGE）留 CRM 消费方扩展通道不入基座；路由键形态差异（字段 vs kind）由消费方适配层承载 | T102 已登记 `contract/promotion.py` REFLUX_KINDS 处 |
| D6 | **确认维持 foundation stricter 四道闸不回退**；CRM 自登记为增强项、后续批次对齐——属 CRM 侧增强，不构成双源 | 无 foundation 侧改动 |
| D7 | **确认维持 no_data≠healthy 不变式**；CRM deviationRate 补显式 no_data 态属你仓待修项，修复后 parity 守卫对拍 | 无 foundation 侧改动 |
| D8 | 已闭环（映射层+守卫），foundation 零动作 | — |

### 1.2 G1-G4 实施报告：认可

- 四项实施零业务逻辑变更、反成环（busFailures 下沉）与计数单一实现处理正确；**G1 两层 id 语义已按你方提醒在 `contract/event.py` EVENT_ID_FIELD 处登记**（进程内临时 id 与 DB 权威 id 勿混同，T102）。
- parity 守卫 ⑤（0.7/0.79 各归其位）与 T100 登记互为镜像：foundation 契约侧改动你方先红、你方回函，链路成立。

### 1.3 第二轮盘点补全（H-57~H-70）：回执

1. **14 项全部纳入 harvest 计划**，批次归属建议（对齐你方优先级）：**首波（Batch-8 候选）**H-59/H-60/H-57/H-65（全零污染）；**次波** H-58/H-63/H-66/H-67/H-69（轻度清洗）；**设计批** H-61/H-62/H-64/H-68（框架+注入分离需设计稿）；H-70 可选（portal 前端基座，与 Batch-6 横切合并评估）。当前 Batch-1b/4/5/6 优先，harvest 批次排期见后续规格稿。
2. **H-58 env 参数化方案**：env 名（`CRM_API_TOKEN`/`CRM_CONFIRM_SECRET`）与 `minPrivilegeFallback` 一律参数化注入（消费方装配面传入），上收件内零域 env 字面量——与 Batch-3 llm provider 同款「注入禁硬编码」口径，接入验收时 grep 域字面量判零。
3. **H-62 注入面设计**：原则预答——框架上收后 L1-L4 分层机制入 `context` 层现有契约面（CONTEXT_LAYERS 已在 `contract/context.py` 单源），assembler 的装配钩子/域 SQL/粒子类型/角色画像全走注入；与 D1-D8 契约层的关系需正式设计稿，**另批评审后再动**（不抢跑）。
4. 权威明细以 CRM 仓盘点账为单一事实源，foundation 仅按本回执入账。

---

## 二、致 APS：A1~A11 回执核验通过 + 两项答复

1. **A1~A11 全项切换核验通过**：先建 parity 守卫（红）→ 换装 → 绿的闸门次序合规；零域值上迁有守卫钉住；legacy_aps 自注册方案处理正确。
2. **自注册范式已追认入库**：按你方建议，GAP-8 文档已补「消费方域连接器自注册」推荐范式条目（T101，进程内单例 + 惰性注册 + foundation 注册表唯一事实源 + 未批源不注册），enterprise 同款适用。
3. **A2/A3 reason 文案裁定**：**不提供契约「域文案注入点」**——reason 属域表达，guard 对拍 status（及关键子串）已保证语义单源；文案单源的收益不抵契约面扩张成本（基座最小面纪律）。维持现状；若未来审计场景要求 reason 逐字一致再立项。
4. **⚠ 催办**：回执 §四全量回归补记仍为「待回填」（1565 是 2026-10-09 基线）。请以 Batch-3 改动后全量回归实测数回填并回函（参照 enterprise 差集实证口径：改动树 vs stash 基线树 comm 差集 + 孤立差异隔离复跑甄别）。

---

## 三、致 enterprise：E1~E5 回执核验通过 + 增补建议采纳

1. **E1~E5 核验通过**：E4 回赠收口确认（本地 openai_compat 删除、消费 foundation T93 单一实现，19 passed）——T93「单一 HTTP 逻辑禁双源」承诺兑现；E2 等权单一路径 = `score_rubric` 与 APS kmd.py 范本一致；全量回归差集实证（确定性 +1 passed、零新增失败、孤立差异隔离甄别）口径规范，**该口径建议三仓统一沿用**。
2. **增补建议采纳**：`registered_store_schemas()` / `reset_store_registry()` 已列入 **Batch-1b-4** 施工清单（随 quota_gate 等四能力同批）；落地后你方随即收掉观测索引（`registered_schemas()`/`clear_registry()` 过渡件删除，守卫 G4 AST 继续锁「实例恒由 open_store 出」）。
3. **E5 更正接受**：platform_catalog 62 Action 实测零域关键词，施工图「建议随租户资产外置」按实测作废；host/control.py 行业画像演示种子（三级降级链兜底）留待租户资产外置批次统一处理。
4. E3 扩展边声明形态（pending 自环 + 三终态只读自环）与 D1 裁定（intra-pending extra 显式声明）同构，`contract/security.py` D1 登记条目可直接引用。

---

## 四、foundation 进度与下一步

- **Batch-1b**：1b-1 iam（T97）/ 1b-2 approval_engine+prov_chain（T98）/ 1b-3 conflict_resolver+attribution+audit_4q（T99，8/8 变异自证，**全量基线 1148 passed**）✅；**1b-4**（assemble_prescription / ab_experiment_close / quota_gate / param_health_check + open_store 快照/重置面增补）施工中。
- Batch-4（监控+agent）→ Batch-5（调度复盘）→ Batch-6（横切）→ Batch-7（P2/P3）；CRM 第二轮 14 项并入 harvest 排期（§1.3）。
- 各仓确认项均已登记入契约注释/manifest（T100/T101/T102），零行为变更，既有回归全绿。
