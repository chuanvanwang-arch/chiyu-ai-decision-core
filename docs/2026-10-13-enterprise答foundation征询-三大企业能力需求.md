# enterprise 答 foundation 征询 —— 三大企业能力需求回执

> **发出方**：chiyu-enterprise（消费仓）
> **日期**：2026-10-13
> **复函对象**：`2026-10-13-foundation征询函-三大企业能力需求(致CRM-APS-enterprise).md` §三 enterprise 分册 + 统一问题集
> **纪律声明**：全部锚点为本仓实测（grep 行号级），非转抄征询函；征询函一处文件名笔误已订正（见 Q1.1）。
> **优先级口径**：P0 = 必须进 foundation 1.0 稳定承诺；P1 = 强烈需要；P2 = 可选。

---

## ① 决策有效性与闭环追溯

### Q1.1 现状（P0 陈述面）

**有效性度量**：
- 九尺子评分经 E5 接线（T58 audit-first）进审计 canonical：`decision/orchestrator.py:435`（`rubric_scores` 入 canonical）、`:479`（`_audit_persister`，轨身份按 `AUDIT_RECORD_KIND` 硬断言 fail-loud）、`:586`（run_spine 接线）。判据 `scripts/verify_u2_spine_route.py` U18 五断言 + 变异⑧，真值态 101/0；运行态 E2E `scripts/verify_u2_e2e_spine_audit.py` 对真 host 实证 REJECTED/PENDING 两路径 canonical 均含九尺子+elements。
- 八要素必需闸 + 严格度水位：`decision/strictness.py:45`（`ELEMENT_PRIORITY`，⛔ 明示为业务判断不等于 foundation 定义顺序，`:12`）、M1 固化（`:86-87`）；四评分矩阵 M1-M4 配置链（`:56` 起，租户默认→场景覆盖→复盘 apply，判据 39/0）。

**闭环追溯**：
- 审计落库：`host/decision_audit_store.py:93`（`persist_decision_audit`，chain_hash SHA-256 链）。
- 复盘调度：`host/retro_backend.py:65`（`MemRetroStore`/`append_report`，PG 双轨）。
- 记忆网：`host/decision_memory_store.py:84/:108`（`persist_decision_memory`/resume 变体）＋ `host/decision_memory_recall.py:116`（`decision_recall`）。**订正**：征询函写的 `recall.py` 实为 `decision_memory_recall.py`。
- 复盘建议→审批→一键执行：`evolution/retro_toggle.py:44/:109`（`build_toggle_proposals`/`submit_toggle_proposals`，复用 `gate-approval-decide` 回派，⛔ 无手动启停开关）。

**缺口（诚实申报）**：决策→执行→**结局**（成交/失败/付款类 outcome）的自动采集管道企业侧未闭环——复盘证据面靠 `evolution/retro_strictness.py:64`（`collect_strictness_evidence` 反查审批记录），结局信号源缺失。这是本函最想从基座获得的能力（见 Q1.3）。

### Q1.2 企业级痛点（P0）

客户/合规最常质疑「**错了怎么追责到当时的依据**」。实证：审计 canonical 此前只有拒因没有**复算双 inputs**（当时九尺子评分 + 当时要素声明），审计复算断档——本轮 E5 补齐即为此痛点（`orchestrator.py:382-385` docstring 明示）。第二痛点是「复盘建议谁批的、批完改了什么」须与决策审计同链可追。

### Q1.3 期望基座能力（P0/P1）

**两者都要，分两批**：
- **P0 闭环追溯管道**：结局事件采集原语（决策 id → 结局类型/时间/证据引用）＋ 复盘触发原语（结局→复盘报告→负面先例回流记忆网）。理由：三仓各自造结局采集必然口径漂移，且企业侧现状即缺口。
- **P1 有效性度量记录原语**：评分/置信/水位快照的 canonical schema（`record_kind`+`rubric_scores`+`elements` 三键形态已实证可用，建议直接毕业为 schema 契约）。

### Q1.4 边界

- **基座原语**：审计 canonical schema、结局事件原语、复盘报告存储接口、记忆网读写接口（本仓已按接口消费，双轨 PG/Mem）。
- **域特有必须保留**：九尺子业务语义与评分尺子实现、八要素/优先级（`strictness.py:12` 业务判断定界）、复盘建议的业务判定逻辑、场景包 `evolution_candidates` 声明校验（`scenario/package.py:169/:400`）。

---

## ② 企业安全 + 可审计可追溯（含 HITL）

### Q2.1 现状（P0 陈述面）

- 三段审计链：`host/governance.py:35-37`（`_AUDIT_PHASES = ("requested","executed","failed")`，T5 接线）。
- 写闸 + 两阶段 confirm：`governance.py:12`（`check_write_gates` GateEnv/GuardSpec）＋ `:23`（`ConfirmSessionStore`/`merge_phase2_params`）；guard 三级权威源解析 `:90-103`（场景包→平台动作目录→零约束）。
- IAM：`host/iam_backend.py:104-158`（bootstrap：五档角色 sysadmin/tenant_admin…＋PBKDF2 `set_password`，幂等 env 驱动）；双层 effective_roles：`tenant/rbac.py:37`（全局＋租户归并）。
- HITL：`host/approval_backend.py:84`（Mem/PG 双轨 store）＋ `approval/state_machine.py:13-56`（`INSTANCE_STATES`/`OPERATIONS_BY_STATE`/`assert_transition`/`next_state`）。
- 动作级最小权限：`action/platform_catalog.py` 全目录 `rbac_roles` 声明（47-160 条），G1.5 强制 dispatch 校验。

### Q2.2 企业级痛点（P0）

四条按苛刻度排序：① **追责到个人**（token 验签→user_id→审计链三段全落，匿名即超管已封死 `control.py:3992-4029` 只留显式开关）；② **最小权限**（动作级白名单而非角色级粗粒度）；③ **多租户隔离**（tenant_scope＋effective_roles 双层）；④ **HITL 留痕**（审批 decision_id 与决策审计同链）。

### Q2.3 期望基座能力（P0/P1，分批上收）

愿意贡献形态，但按改造成本分批：
- **P0（可直接毕业）**：三段审计链原语（`_AUDIT_PHASES` 形态＋SHA-256 链，本仓已实证）；HITL 审批状态机原语（`state_machine.py` 形态，CRM/APS 可直接复用）。
- **P1（需三仓同步窗口）**：IAM/RBAC 完整层上收（五档角色＋effective_roles＋token 验签过期吊销——形态成熟，但 CRM/APS 无 IAM 层，收敛=两仓新建，建议 foundation 出接口契约、enterprise 贡献参考实现）；两阶段 confirm 会话原语（`ConfirmSessionStore`）。

### Q2.4 边界（不可上收）

动作目录（`platform_catalog.py` 业务动作＋rbac_roles 声明属域知识）、场景包 guard 解析（`governance.py:90-103` 三级权威源是场景模型的一部分）、租户粒子/DB 权威源、web 会话面。基座管**协议与格式**（审计链、验签、审批状态机、confirm 会话），消费方管**动作语义与存储**。

---

## ③ 自我进化

### Q3.1 现状（P1 陈述面）

- 基座消费：`evolution/bridge.py:20`（SkillDraft/validate_draft/promote，experimental 口径块已按 R-FE1 落 docstring，判据面零依赖）。
- 域实现（人工可控闭环）：`evolution/retro_toggle.py:44/:109`（建议→审批→一键执行，⛔ 无手动开关）；`evolution/retro_strictness.py:64/:138/:206`（证据采集→建议→提交，水位只进不退）；场景包声明候选 `scenario/package.py:169/:400`（`evolution_candidates`＋`validate_evolution_candidates`，声明 vs 埋点实证对照防「有值≠生效」）。

### Q3.2 企业级风险（P0 认知面）

① **失控**——系统自己改自己（⛔ 企业红线：任何阈值/规则/技能变更必须经人工审批，本仓连「维度启停」都强制走复盘建议→审批，禁页面手点）；② **过拟合**——单租户复盘样本泛化污染全局（⇒ 建议/apply 必须带 tenant 作用域，本仓 `retro_strictness.py:125` `_norm_tenant` 归一即此）。

### Q3.3 期望基座能力（P1）

**支持 evolution 毕业**。「HITL 草稿→回测→生效」正是期望通用形态——本仓 retro_toggle/retro_strictness 就是该形态的域实现（建议→审批→apply），语义与 `icpSelfEvolution`（CRM）同构。毕业前提：稳定承诺＋RFE 流程（R-FE1 口径维持，⛔ 禁伪稳定包装）。

### Q3.4 边界（P0）

**HITL 闸必须基座保证，不可消费方自担**。理由（本仓实证教训）：审批闸散落各 handler 曾致「专家派发卡死」「匿名即超管」类漂移；人工可控是底线，基座应定义**接口＋状态机＋不可绕过断言**，存储实现可下放消费方（本仓 Mem/PG 双轨即例）。

---

## Q4 三能力耦合（P0 设计建议）

**互为前提，不是三个独立能力**，本仓链路实证：
1. 安全审计是决策闭环的**追溯轨**——决策事件→审计 canonical（`_audit_persister`）与三段写审计（`_AUDIT_PHASES`）同属一条 SHA-256 链；
2. 进化消费决策闭环的**复盘输出**——`retro_toggle`/`retro_strictness` 建议源=决策/审批/埋点证据，apply 回写矩阵/启停（闭环喂回）；
3. HITL 是三者的**公共闸**——决策放行（need_approval）、写操作（confirm/审批）、进化生效（建议→审批）同一状态机语义。

⇒ 建议 foundation 按「**决策→审计→复盘→进化**」事件链统一设计原语族（事件总线＋record_kind 分轨＋审批状态机贯穿），而非三个独立模块；否则三仓必然各自再拼一遍接缝。

---

## 附：优先级汇总（供 foundation 排收敛批次）

| 项 | 内容 | 级 |
|---|---|---|
| 1 | 结局事件采集＋复盘触发原语（闭环缺口） | **P0** |
| 2 | 三段审计链原语（requested/executed/failed＋SHA-256） | **P0** |
| 3 | HITL 审批状态机原语＋不可绕过断言（含进化闸） | **P0** |
| 4 | 审计 canonical schema（record_kind/rubric_scores/elements）毕业 | P1 |
| 5 | IAM/RBAC 接口契约＋enterprise 参考实现上收 | P1 |
| 6 | 两阶段 confirm 会话原语 | P1 |
| 7 | evolution 毕业按 RFE 流程 | P1 |
| 8 | 评分尺子/八要素/动作目录/场景 guard | 域特有，不上收 |

*enterprise 回执 · 2026-10-13 · 锚点均实测于本仓 `packages/enterprise/src/enterprise/` 与 `scripts/`；副本留本仓 `docs/`。*
