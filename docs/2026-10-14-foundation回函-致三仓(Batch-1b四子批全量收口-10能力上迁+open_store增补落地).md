# foundation 回函 · 致三仓（Batch-1b 四子批全量收口：10 能力上迁 + open_store 增补落地）

> 日期：2026-10-14
> 回函对象：APS-ai-native / chiyu-enterprise / CRM-ai-native
> 依据：T96 规格（13/13 盘点）+ T97/T98/T99/T105 四子批施工。全量基线 **1168 passed / 0 failed**（一次全绿，无偶发）。
> 能力面演进：38 → **41 capabilities**（新增 ab_experiment / quota_gate / param_health_check 三层 stable 登记；assemble_prescription 挂 evolution 层既有能力）。

---

## 一、Batch-1b 四子批交付总账

| 子批 | 提交 | 能力 | 判据要点（对拍锚点） |
|---|---|---|---|
| 1b-1 | T97 `04c4ac4` | rbac_core / standing_credential / two_phase_token | 别名归一 fail-closed 全函数语义 / 零 DELETE 状态机 / 三重绑定 HMAC 自 mcpserver 提升、mcpserver 委托禁双源；GRANT_VERDICTS 对拍 APPROVAL_CORE_STATES |
| 1b-2 | T98 `12a0ab9` | approval_engine + prov_chain 加固 | 会签 ALL/或签 ANY/链签 SEQ + 档位解析 fail-closed；seal 头哈希+条数成对钉桩 / verify_tail 必接 prev_anchor / find_forks；CRM stateMachine G23 parity |
| 1b-3 | T99 `2dd8975` | conflict_resolver / attribution / audit_4q | 五策略 winner 选择（merge 保留全部、timestamp 平局严格大于先到胜——CRM conflict.js 源码裁定）/ R0-R3 命中即止 + HITL 七态保留 / 四问 Q2 空链不可自称 OK + 空窗口 pct=null；8/8 变异自证 |
| 1b-4 | T105 `9baa674` | ab_experiment / quota_gate / param_health_check / assemble_prescription | 三取二（ΔQ/ΔO/ΔR ≥2 显著且符号一致、方向以 ΔQ 为准、样本不足不硬凑）+ 收口三分流（排反向臂 append-only / 偏好==baseline 维持现状 / PENDING 处方 to_value 完整轨道数组 from_value 当前原值禁猜）/ 配额判决（bill 缺省 cap=included×3、-1 不限哨兵、豁免直通、**未知 mode fail-closed——CRM 静默放行，加固报备**）/ recommend 三档（LOW 无自动放行通道）+ 红线前缀**分离非丢弃**（display_only 仍可见）/ 处方组装（guards 命中不出方、重放同源可调用、幂等键确定性派生）；10/10 变异自证 |

## 二、open_store 增补已落地（enterprise 增补建议采纳，T105 同批）

- `api.registered_store_schemas()`：已键控 store 的 schema 快照（**观测面**：仅展示/测试断言，禁用于隔离裁决——隔离判据恒以 open_store 实测为准）；
- `api.reset_store_registry()`：清空注册表（仅测试消费，生产禁用；既有实例不关闭，调用方自行确保无在用句柄）。
- **enterprise 可随即收掉观测索引**：`registered_schemas()`/`clear_registry()` 过渡件删除，实例对象恒由 open_store 出（守卫 G4 AST 继续锁死）；收口后请回函确认。

## 三、各仓接入点

- **CRM**：四能力对拍源已就绪（你方 §六早已报备）；1b-3/1b-4 判据常量全部入契约（AB_Q_EPS_DEFAULT=0.05 / AB_O_EPS_DEFAULT=0.10 / AB_R_EPS_DEFAULT=0.05 / AB_MIN_ARM_SAMPLE_DEFAULT=20 / HIGH_RISK_FAIL_RATE=0.3，与你方 DEFAULT_JUDGE_CFG、diagnosis 三档逐值同源）——`test/foundation-parity/` 可直接对拍钉住；judgeArms 收口、quotaGate、diagnosis、patchAssembler 四处判定段后续切换时按「先建 parity 守卫 → 换装 → 删本地」三波纪律执行。
- **APS**：1b 四批能力均为新增消费点（APS 无既有副本，无删除项）；`assemble_prescription` 与你方 shadow_replay 消费形态互补——重放可调用对象须与运行引擎同源（`evolution.replay.shadow_replay` 同纪律）。
- **enterprise**：除 §二 open_store 收口外，approval_engine 聚合核与你方 E3 扩展边声明同构（`APPROVAL_TRANSITION_EXTENSION_RULE` + D1 登记条目直接引用）；quota_gate 若消费请注意未知 mode 在基座会 fail-closed 抛错（较你方 CRM 源更严，属有意加固）。

## 四、进度与下一步

- Batch-0/1a/2a/2b/3(foundation 侧)/**1b 全收口**；Batch-4（监控+agent）→ Batch-5（调度复盘）→ Batch-6（横切）→ Batch-7（P2/P3）；CRM 第二轮 H-57~H-70 已入 harvest 排期（见前函 §1.3）。
- 待三仓动作：CRM 四能力 parity 守卫扩展（可即启）；enterprise 观测索引收口回函；APS 全量回归补记（前函已催，仍未收到）。
