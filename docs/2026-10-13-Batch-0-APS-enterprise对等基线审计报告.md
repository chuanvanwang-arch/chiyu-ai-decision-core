# Batch-0 — APS / enterprise 三大支柱对等基线审计（只读零代码）

> 触发：用户战略指令「APS/enterprise 在三大支柱须达 CRM 同等层级」+ CRM 审定补充要求「先建对等基线审计（只读零代码），否则验收无基线不可测、且防重复建设」。
> 方法：Explore 子代理只读测绘 APS / enterprise 三支柱实现（带 file:line 锚点），上游 trust-but-verify 抽查 3 处关键锚点全部命中；对照 CRM 已建回捐件（24 项）+ foundation 现状。
> 纪律：本仓严禁向三仓写产物；本审计只读，零代码变更。

## 一、审计范围与三仓技术栈（实测校正）

| 仓 | 路径 | 栈 | 消费 foundation 方式 |
|---|---|---|---|
| CRM-ai-native | `/d/system/CRM-ai-native` | **Node** (.mjs) | executor/auditability/calibration 自造，部分已回捐 |
| APS-ai-native | `/d/system/APS-ai-native` | **Python** (pyproject, `src/aps/`) | `src/aps/platform/foundation.py` 门面取 `run_spine`/评分/审计 canonical |
| chiyu-enterprise | `/d/system/chiyu-enterprise` | **Python** (pyproject, `packages/enterprise/src`) | `orchestrator.py` `from chiyu_kernel.api import chain_hash, verify_chain, EventBus` |

⚠️ **栈校正**：先前按 memory 推断「APS 同 CRM 为 Node」**错误**——APS 实为 Python 栈（与 enterprise 同栈，与 CRM 异栈）。三仓栈不同，上收机制必须**栈无关（L0 契约 + 机制纯函数）**，否则无法跨仓复用。

## 二、关键结论（对原战略假设的修正）

1. **验收标准已基本满足**：原假设「CRM 首个落地、foundation 收敛不全面、APS/enterprise 差距大」——实测 APS（18 项）、enterprise（14+ 项）与 CRM 回捐件**高度同构**，三仓三支柱能力已大体对等。
2. **真正风险不是"收敛不全面"，是"分叉成第二事实源"**：三仓各自造了同构域无关机制（决策脊柱、审计链、八闸、两阶段令牌、RBAC、处方状态机…），未统一收口 foundation → 印证 CRM 审定「防收敛变分叉」。
3. **harvest 方向反转**：不是「从 CRM 单向 harvest 到 foundation」，而是**双向**——① 三仓同构机制统一收口 foundation（去重）；② 三仓**共有缺口**由 foundation 建统一机制供给三仓。
4. **第0闸选型已定（a）**：轻量决策凭证契约（消费方签发、内核只验），与 D1/D3 同源，保持「不产决策、零领域字面量」。

## 三、三支柱 × 三仓对照矩阵

图例：✅ 已建(域无关) / ⚠️ 部分或方法分歧 / ❌ 缺失 / 域特定(留消费方)

### 支柱① 决策闭环追溯
| 能力(回捐件/P级) | CRM | APS | enterprise | 同构判定 |
|---|---|---|---|---|
| decision_gate 无决策不写(P0) | ✅ | ✅ actions.py:79/708 | ✅ guard.py:146 | 三仓都有→foundation 收口 |
| prov_chain PROV-O(P0) | ✅ | ✅ audit.py:50 | ✅ 复用 foundation chain_hash | foundation D6 已有，去重 |
| audit_4q 四问评分(P1) | ✅ 四问 | ⚠️ 九尺子(方法分歧) | ⚠️ 九尺子 | **口径分歧→foundation 评分契约统一** |
| closure_loop 闭环(P1) | ✅ | ✅ feedback_loop | ✅ orchestrator | 三仓都有 |
| confidence_scorer(P3) | ✅ | ✅ 取 spine | ⚠️ 透传 | foundation score_rubric 已统一 |
| param_health_check(P1) | ✅ | ⚠️ 漂移检测 | ❌ | **三仓共有缺口** |
| shadow_replay 影子重放(P1) | ✅ | ❌ 仅标志 | ❌ | **三仓共有缺口** |
| quota_gate 配额闸(P2) | ✅ | ❌ | ❌ 仅计费 | **三仓共有缺口(决策≠计费)** |
| write_guard 写白名单(P2) | ✅ | ✅ actions.py:805 | ✅ guard.py:269 | 三仓都有 |

### 支柱② 企业安全 + 可审计
| 能力(回捐件/P级) | CRM | APS | enterprise | 同构判定 |
|---|---|---|---|---|
| gate_chain 可配置闸链(P0) | ✅ executor 9级 | ⚠️ 硬编码闸 | ✅ guard.py:8-15 八闸 | foundation 应建统一可配置 N 级四分类链 |
| two_phase_token(P0) | ✅ | ⚠️ 对话闸雏形 | ✅ confirm.py:59 | 三仓都有雏形/完整→收口 |
| rbac_core(P1) | ✅ | ✅ security.py:80 | ✅ roles.py | 三仓都有，foundation D7 之上 |
| standing_credential(P1) | ✅ | ❌ | ✅ grant.py:39 | APS 缺口，foundation 建统一 |
| approval_engine(P1) | ✅ | ⚠️ 单闸 | ✅ state_machine.py:29 | 三仓都有→收口 |
| conflict_resolver(P2) | ✅ | ⚠️ 域特定 | ❌ | **enterprise 缺口** |
| decision_retro_agent(P2) | ✅ | ✅ reflux.py | ⚠️ 域特定 | 三仓都有 |
| attribution_rules(P2) | ✅ | ✅ | ❌ | **enterprise 缺口** |
| ab_experiment_close(P2) | ✅ | ❌ | ❌ | **三仓共有缺口** |

### 支柱③ 自我进化
| 能力(回捐件/P级) | CRM | APS | enterprise | 同构判定 |
|---|---|---|---|---|
| patch_state_machine(P0) | ✅ | ✅ never auto-apply | ✅ writeback.py:122 | 三仓都有→收口 |
| nightly_self_evo_agent(P1) | ✅ | ❌ 无定时 | ✅ scheduler.py:44 | **APS 缺口定时调度** |
| auto_patch_subscribe(P3) | ✅ | ✅ events.py | ⚠️ 草稿 | 三仓都有 |
| calibration 回测 | ✅ | ✅ | ⚠️ 预测域 | 三仓都有 |
| memory_promote | ✅ | ✅ | ✅ | 三仓都有 |
| icpSelfEvolution | ✅ | ✅ | ✅ foundation | 已毕业 stable |

### 遗漏 5 项（CRM 审定补）
| 项 | CRM | APS | enterprise |
|---|---|---|---|
| 事件订阅/出方 | ✅ | ✅ events.py:62 | ✅ control.py:91 |
| 信号双路 metrics | ✅ | ✅ feedback_loop:176 | ⚠️ 弱 |
| 维度覆盖率 | ✅ | ⚠️ | ⚠️ |
| 配置中心 id36 禁改 | ✅ | ⚠️ 外置 | ⚠️ 近似(roles.py:48) |
| 升格引擎 vs 评分拆分 | ✅ | ✅ promotion.py:135 | ✅ |

## 四、去重清单（三仓已造、foundation 应统一收口的域无关机制）

按「消费方重复造、foundation 建一次供给三仓」优先级：

1. **decision_gate**（P0）— 三仓都有第0闸，foundation 建 `chiyu_kernel.gate.decision_required`（契约+纯函数 fail-closed），三仓接入去重。
2. **prov_chain**（P0）— foundation D6 canonical + `chain_hash/verify_chain` 已存在，APS/enterprise 直接复用，CRM 切换消费（消除第二事实源）。
3. **gate_chain**（P0）— 建「可配置 N 级四分类闸链」框架（事前校验/权限边界/红线拦截/事后可溯），域闸名留消费方注入；收敛 CRM executor/APS actions/enterprise guard。
4. **two_phase_token**（P0）— 建域无关双阶段令牌机制（issue/consume/一次性/TTL），统一 CRM/enterprise 实现，APS 升格。
5. **rbac_core**（P1）— foundation D7 `SecurityDecision`/`Principal`/`RoleGate` 之上建 RBAC 引擎，三仓接入。
6. **standing_credential**（P1）— foundation 建常驻凭证/授权策略库（APS 缺口、enterprise 已有可参考）。
7. **approval_engine**（P1）— foundation 建审批流状态机（enterprise state_machine 可参考），APS 单闸升格。
8. **patch_state_machine**（P0）— foundation 建处方状态机（绝不自动 apply），三仓接入。

## 五、parity 待补项（三仓共有缺口 → foundation 真正 harvest 优先级）

交集（CRM 有而 APS/enterprise 均缺或弱）→ 这是"达 CRM 同等层级"的**真实补齐清单**：

| # | 回捐件 | 级 | 现状 | foundation 动作 |
|---|---|---|---|---|
| 1 | shadow_replay 影子重放 | P1 | 三仓均缺/仅标志 | foundation 建重放引擎，喂 TIER_GUARDED 处方 |
| 2 | ab_experiment_close AB实验闭环 | P2 | 三仓均缺 | foundation 建 AB 实验闭环 |
| 3 | quota_gate 决策配额闸 | P2 | 三仓均缺(计费≠决策) | foundation 建决策配额闸（非计费语义） |
| 4 | param_health_check 参数健康检 | P1 | 三仓均弱/缺 | foundation 建周期健康检查 loop |
| 5 | conflict_resolver 冲突消解 | P2 | enterprise 缺/APS 域特定 | foundation 建通用冲突消解（域约束留消费方） |
| 6 | attribution_rules 归因 | P2 | enterprise 缺 | foundation 建决策可解释归因 |
| 7 | audit_4q 评分口径统一 | P1 | CRM 四问 / APS·ENT 九尺子分歧 | foundation 评分契约统一口径（四问 or 九尺子归一） |

## 六、第0闸轻量决策凭证契约（选型 a，设计落点）

- **契约** `chiyu_kernel/contract/gate.py`：`DECISION_CREDENTIAL_FIELDS = (decision_id, issuer, issued_at, ttl, checksum)`；`verify_decision_credential(payload: Mapping) -> None`（fail-closed：缺/过期/校验和不符即 `DecisionCredentialError`）。
- **机制**：消费方在写动作 dispatch 入口签发凭证（决策脊柱 run 后回写 decision_id+issuer+有效期+checksum）；内核只验不产，与 D1 结局 `decision_id` 强关联同源。
- **去重**：三仓现有第0闸（CRM executor / APS actions:79 / enterprise guard.py:146）改为消费此契约，消除三套实现。
- **纪律**：零领域字面量、零 IO（不落库，仅内存校验）。

## 七、验收硬闸（沿用 CRM 审定 G-域无关 / G-零IO / G-对等可测）

- **G-域无关**：每个 harvest 件 `test_contract_no_domain_literals` 零违反（grep 禁 CRM/APS/enterprise 字面量）。
- **G-零IO**：内核机制禁 DB 写回；持久化留消费方。
- **G-对等可测**：每批 harvest 建 `*parity.test`（含变异自证），三仓接入后跑 parity 守卫全绿即达 parity。
- **parity 基线**：本节 §三 矩阵即为 6+6+6 验收清单的事实版（实测三仓已大体对等，真正待补为 §五 的 7 项交集）。

## 八、下一步（Batch-1 重新定义）

原 Batch-1（单向从 CRM harvest）**作废**，改为双向：

- **Batch-1a 去重收口**（消除第二事实源）：decision_gate / prov_chain / gate_chain / two_phase_token / rbac_core / standing_credential / approval_engine / patch_state_machine —— 每批带 `*parity.test` + 变异自证 + 组合回归。
- **Batch-1b 共有缺口补齐**（达 CRM 同等）：shadow_replay / ab_experiment_close / quota_gate / param_health_check / conflict_resolver / attribution_rules + audit_4q 口径统一。
- **下游验收**：三仓接入 foundation 后跑 parity 守卫（§三矩阵全绿）即满足用户验收标准。

> 待用户拍板：是否按 Batch-1a（去重收口）→ Batch-1b（共有缺口）顺序推进；首批建议从 `decision_gate` + `gate_chain`（八闸框架，用户点名项）开工。
