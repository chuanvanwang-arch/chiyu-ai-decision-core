# APS 答 foundation 征询——三大企业能力需求（APS 分册回执，10-13）

- 日期：2026-10-13
- 应答：foundation《征询函——三大企业能力需求收集（致 CRM/APS/enterprise）》(2026-10-13) §二 APS 分册 + ★统一问题集
- 纪律遵守：每题附源码锚点（`APS:<文件>:<行>`，可机检）；每题标 P0/P1/P2（P0=须进 foundation 1.0 稳定承诺）
- 答题身份：APS 是排产域消费仓——企业级场景 = 中冶赛迪排产（13,833 卷/85 轧程/7 组订单池）上线验收

---

## 能力① 决策有效性与闭环追溯

### Q1.1 现状（P1）

**有效性度量**（三层，前两层已基座化）：
- S2 九尺子评分：`APS:src/aps/platform/kmd.py:476`（`_stage_s2_score`，调基座 `score_rubric`）
- S3 置信度唯一来源=基座等权 ratio：`APS:src/aps/platform/kmd.py:485`（`_stage_s3_aggregate`，C-B 铁律，禁自造口径）
- 八要素填充率/本体分级：`APS:src/aps/platform/kmd.py:461`（`_stage_s1_derive`）

**闭环追溯**（APS 自建，已收敛为单管道四通道）：
- 双信号回写：`APS:src/aps/platform/decisions.py:13`（`human_signal` 即时采纳/推翻 + `outcome_signal` 滞后业务结果，`:79` 默认 `"pending"`）
- 结果回流边⑤：`APS:src/aps/platform/__init__.py:457`（`reflux_record_outcome` → `feedback_loop.record_outcome`，`APS:src/aps/platform/feedback_loop.py:157`，字段级血缘时序 + `aps.solution.result_reflowed` 事件）
- K-M-D 单回流管道四通道：`APS:src/aps/platform/reflux.py:226`（`CHANNELS=("c1","c2","c3","c3p")`，与专利 F 一一对应）；`route_retro` 按 kind 分流（`reflux.py:281-287`）；C2 反面先例 `reflux.py:245`（`record_negative_precedent`，不覆盖既有先例）
- SLA 升级 + 5-Why 结案：`APS:src/aps/platform/sla_escalation.py:1-15`（green/amber/red 两级超时升级；仅 red 可结案且须 ≥5 层 5-Why + corrective_action，append-only 留痕）

### Q1.2 企业级痛点（P0）

1. **「凭什么牺牲这张订单的交期」**：客户验收要求每个排产决策可回放（决策→当时供需→红线判定→审批记录）。S5 双轨已把 REJECTED/PENDING 落审计轨（`APS:src/aps/platform/kmd.py:525`），但**结局侧无基座契约**：tardy 实际发生后，「结局证据挂回 decision_id」的关联目前是 APS 自拼（`decisions.py:79` outcome_signal + TIMESERIES），跨仓复用必漂移。
2. **负面结局不回流 ⇒ 同类错误重复**：C2 反面先例通道已建，但输入依赖人工/SLA 升级触发，缺「结局→自动复盘候选」的管道原语。

### Q1.3 期望基座能力（**P0 = 闭环追溯管道；P1 = 有效性度量管道**）

**两者都要，分层沉淀**：
- **P0 闭环追溯管道**：① OutcomeRecord 最小契约（`decision_id` + `outcome_kind` 枚举 + `recorded_by` + `evidence_ref` + `ts`，并与审计链 hash 挂钩防篡改）；② 「结局→复盘候选」触发原语（按 case 聚合决策簇）。APS 消费面已就绪（四通道 + record_outcome 边⑤），基座出契约后一轮接线对齐。
- **P1 有效性度量管道**：评分/置信基座已有；缺「命中率/逆转率」**跨仓统一口径**（outcome ↔ 判定对账的最小统计面）。域 KPI 不收。
- ⛔ **不希望基座整体上收 K-M-D 四通道语义**：「什么 kind 走哪条通道」是域知识（同 §〇 对 CRM C1-C5 的观察——形态对齐、语义各异）。

### Q1.4 边界

| 基座原语 | 域特有（留消费方） |
|---|---|
| OutcomeRecord 契约 + decision_id 关联 + 链式校验 | 排产 KPI 如何构成 outcome 证据（tardy/makespan/切换次数） |
| 复盘触发原语（按 case 聚合） | SLA 升级策略与 5-Why 结案纪律（`sla_escalation.py`） |
| 负面先例入记忆网的统一入口 | K-M-D 通道映射语义 |

---

## 能力② 企业安全 + 可审计可追溯（含 HITL）

### Q2.1 现状

- **RBAC + 三档模式**：`APS:src/aps/platform/security.py:59`（`SECURITY_MODES=("off","advisory","enforced")`，默认 off）+ `:75`（`PERMISSION_MATRIX`）+ `:190`（`Principal`）+ `:365`（`check()`：off 恒放行但 reason 显式「未启用」、advisory 真判恒放行 + `would_deny`、enforced 真拦 `:246 PermissionDenied`）；`:380` 断言 `advisory.would_deny == not enforced.allowed` **防两档漂移**。
- **案例作用域身份**：`APS:src/aps/platform/store.py:410`（`scoped_identity()`；`security.py:14` 明写语义复用不另造）。
- **审计链**：`APS:src/aps/platform/audit.py:23`（`sha256_hex`）+ append-only `audit_chain`（previous_checksum 全链串联，`:108` `last_checksum`/GENESIS 起点可检测篡改与硬删除断链）。⚠ 与基座 `chain_hash` 目前**同名异实**（10-12 消费审计已甄别）——收敛时应合一（见 Q2.3）。
- **HITL 双层**：① 决策层 = M2 双轨审批闸（`APS:src/aps/platform/kmd.py:88` 消费基座 `RedlinePriorityGate`；PENDING → 审计轨人工确认）；② 动作层 = 四闸（`APS:src/aps/platform/actions.py:687` `dispatch`：force 编程闸 / `:669` `issue_confirm_token` 对话一次性令牌 TTL 600s / needsApproval 审批流 / `:744` `require()` 安全校 enforce 闸）。
- **违例物化唯一出口**：`APS:src/aps/platform/violation_store.py:1`；能力审计 `capability_audit.py`。

### Q2.2 企业级痛点（P0/P1）

1. **P0 审计追责到个人（resume 侧缺口）**：重排/覆盖红线类动作，「谁、何时、基于什么、批了什么」四问 APS 审计链可答；但**人工审批后放行 PENDING 决策（resume）的证据结构无基座契约**——`AUDIT_EVENT_APPROVAL_RESUMED` 事件存在，resume 的 principal/依据 payload 无契约锚。
2. **P1 租户级隔离**：`scoped_identity` 覆盖案例作用域；跨案例的租户隔离语义基座无原语，APS 靠 store 层约定。
3. **P1 渐进收紧是企业刚需**：企业上线不可能一步 `enforced`——APS 三档实测路径：默认 off（存量零破坏）→ advisory（生产流量观测 `would_deny` 命中率）→ enforced（收口）。

### Q2.3 期望基座能力（**愿意贡献，两项 P0**）

- **P0-A：三档模式（off/advisory/enforced）应成基座安全层默认范式**。理由：① 渐进收紧 + advisory 生产观测比「一次性 IAM 大全套」更可落地；② advisory/enforced 判定一致性须结构保证（APS `security.py:380` 的防漂移断言应升格为基座不变量）；③ 对存量系统零破坏是 enterprise 级迁移的硬约束。
- **P0-B：HITL 审批原语补 resume 侧证据契约**（resume_principal/resumed_at/basis，挂 `approval_resumed` 事件族）。
- P1-C：IAM/RBAC **判定接口**进基座（`Principal`/`SecurityDecision` 形态，`security.py` 可贡献），权限矩阵本体留消费方。
- P1-D：**审计链合一**——基座 `chain_hash` 与 APS `audit.py` 自有 SHA-256 链收敛为单一事实源，消费方只余接线（消除同名异实）。

### Q2.4 边界（域特有，不可上收）

| 项 | 理由 |
|---|---|
| 红线规则业务语义（mutex_top/sensitive 判定内容） | 闸**机制**在基座，规则**内容**是排产域知识 |
| `PERMISSION_MATRIX` 具体 角色-动作映射 | 域动作名空间（`actions.py:75` 矩阵键即 ActionDef 名） |
| principal ↔ MES/ERP 身份源映射 | 企业 IdP 对接属部署侧 |

---

## 能力③ 自我进化

### Q3.1 现状（人工可控 = 双闸位）

- 信号聚合→处方：`APS:src/aps/platform/evolution_feed.py:237`（`aggregate_run_signals`）+ `:283`（`propose_run_evolution`）+ `:293`（`_to_prescription`——**红线模式缺 mode_exit 即抛错** `:296-300`：处方必须声明退出条件，防「无处可退」）。
- 权重调参**恒为建议**：`APS:src/aps/platform/outer_loop.py:129`（`propose_weight_shift`）→ 走 **C3′ 记忆影响/建议通道，绝不直接改配置**（`APS:src/aps/platform/reflux.py:122` 注释明写）；`APS:src/aps/platform/weight_tuner.py:22`（`suggest_weights` 纯函数，dataclass 不可变天然可回滚）。
- 晋升闸：`APS:src/aps/platform/promotion.py:135`（`promote_gate` 纯函数三态 promoted/blocked/rejected；裁决顺序 白名单→证据数→一致性）+ `:313`（`promotion_overwrite_guard` 防覆盖）+ `:332`（`audit_drift`）。
- C3 处方**恒 PENDING**：`APS:src/aps/platform/reflux.py:16`（白名单内键恒 PENDING 须第 0 闸 + HITL，绝不自动 apply）。
- 词汇守卫：`APS:src/aps/platform/evolution_feed.py:424`（`_assert_evo_status` 防假守卫）。

### Q3.2 企业级痛点（P0）

1. **P0「排产结果悄悄变了」= 验收事故**：权重/阈值自动调整直接改变客户每日排产输出。APS 对策是**进化产物永不直接生效**（建议走 C3′、配置走 C3 恒 PENDING、晋升过 promote_gate）——但该不变量目前是 **APS 自律，无基座结构背书**，第三方接线可绕过。
2. **P1 过拟合**：负面先例累积后系统过度保守，需「先例衰减/复核」原语（APS 未建，期望基座统一形态）。

### Q3.3 期望基座能力（**P0**）

- **P0：「草稿→回测→HITL→生效」沉淀为基座毕业原语，且 HITL 闸须基座结构保证**——生效入口只认带 HITL 证据链的 payload，而非「消费方记得调用闸门」的约定。APS 的 `promote_gate`/`promotion_overwrite_guard`/`audit_drift` 判据形态可贡献为参考。
- P1：基座 evolution（guard/knob/prescription/replay/readiness/skill_draft）毕业并三仓统一；APS 愿把 C3 恒 PENDING 语义对齐基座 prescription 面。

### Q3.4 边界

- **HITL 闸必须基座保证**（结构性：生效 API 强制校验 HITL 证据链）。理由：Q3.2 的企业风险本质是「约定可绕过」，约定级闸对企业验收无说服力。
- 回测判据域特有：排产回测=重放排产求解对比 KPI（tardy/makespan/切换）；基座提供回测框架位（replay 已有雏形），判据函数留消费方。

---

## Q4 跨能力耦合（P0 观点）

**三者互为前提，非独立能力**——APS 用 M2 双轨实证了这一定性：

- **②是①的追溯轨**：REJECTED/PENDING 决策走审计轨（`APS:src/aps/platform/kmd.py:525`）本身就是「安全审批+闭环追溯」同一机制（record_kind=audit 同时服务追责与复盘素材）；
- **①喂③**：C3 处方通道消费复盘输出、产出进化输入（`APS:src/aps/platform/reflux.py:16`）。

**收敛顺序建议：② 审计轨/审批原语 → ① 结局采集/复盘管道 → ③ 进化毕业**。倒序会使进化消费一个尚不存在的复盘出口。1.0 稳定承诺优先序据此排。

---

## 汇总：APS 需求清单（供 foundation 排收敛批次）

| # | 项 | 档 | 归属能力 |
|---|---|---|---|
| 1 | OutcomeRecord 契约（decision_id 关联 + 链式校验）+「结局→复盘候选」触发原语 | **P0** | ① |
| 2 | 三档模式（off/advisory/enforced）为基座安全层默认范式 + advisory/enforced 防漂移不变量 | **P0** | ② |
| 3 | HITL resume 侧证据契约（resume_principal/resumed_at/basis） | **P0** | ② |
| 4 | 进化原语「草稿→回测→HITL→生效」，HITL 闸结构性不可绕过 | **P0** | ③ |
| 5 | 有效性统计跨仓统一口径（outcome↔判定对账最小面） | P1 | ① |
| 6 | IAM/RBAC 判定接口（Principal/SecurityDecision）进基座；审计链合一（chain_hash ↔ audit.py） | P1 | ② |
| 7 | 租户级隔离原语（跨案例） | P1 | ② |
| 8 | 先例衰减/复核原语 | P1 | ③ |
| 9 | K-M-D 回流管道语义 | ⛔ 不上收（域知识） | ① |

**APS 可贡献的现成形态**：三档安全模式全实现（`security.py`，457 行）、C3 恒 PENDING + 第 0 闸语义（`reflux.py`）、promote_gate 三态判据（`promotion.py`）、SLA 升级+5-Why 结案纪律（`sla_escalation.py`）。

*APS 回执 · 2026-10-13 · 锚点均可机检（`grep -n` 复现）*
