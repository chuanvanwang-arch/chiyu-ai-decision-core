# chiyu-foundation 定位说明

> 成文：2026-10-09 ｜ 性质：本仓（AI 原生底座）的官方定位口径，唯一事实源

---

## 一、官方定位（一句话口径）

> **为其它项目提供公共能力，提供其它项目支撑与运行的底座。一次做成，多次复用。通过我们专业的封装和专业能力，为其它项目提供高效、快速、专业支持。**

这一句是本仓的最高定位锚点，以下各节是它的落地映射。

---

## 二、定位 → 工程落地的映射

| 定位表述 | 本仓对应实现 |
|---|---|
| 为其它项目提供**公共能力** | `CAPABILITIES`（28 项：contract/vector/ontology/context/actions/domain/persist/approval/graph/mcpserver/canary/orchestration/evolution/events/audit/llm/plugins/session/tools/skills/plan/mcp/hooks/interaction/workflow/scenario/store/decision/memory）+ 机制函数（评分/红线/审批闸/脊柱） |
| 提供**支撑与运行的底座** | 分层铁律 kernel→decision→portal；sanctioned 面（`chiyu_kernel.api` / `chiyu_kernel.contract` / `chiyu_decision.api`）是唯一合法消费入口；唯一事实源，消费方只读取快照、严禁回写 |
| **一次做成，多次复用** | 严格加法（新增不破既有调用，旧符号保留别名/过渡，零既存代码失效）；deprecation 政策（先 warn 一版再移除，`TIER_*`→`VTIER_*` 别名在册）；变异自证（每个闸门删判据→转红→还原，防假绿）——保证消费方升级不破 |
| **专业的封装** | 分层边界（内核只声明形态，取值与执行归消费方）；零领域字面量（域装配 S1 / 域红线 S4 归消费方）；门面守卫（R12 机械推导 `STORE_REQUIRED` 由 `store.__all__` 推导，漏登记即红） |
| **高效、快速、专业支持** | 守卫工具链（`check_import_surface.py` 导入方向 / `check_facade_coverage.py` 门面覆盖）；升级安全闸（版本/能力档位/符号缺失在 import 期 fail-fast）；兼容承诺 + 实证窗口收编（APS 生产接入缺陷台账回传本仓） |

---

## 三、分层与合法消费面

- **三层**：`kernel`（形态 / 存储 / 上下文 / 记忆 / 动作 / 域…）→ `decision`（评分 / 红线 / 审批闸 / 脊柱运行时）→ `portal`（门户 / 页生成）
- **sanctioned 面**（消费方唯一可 import）：
  - `chiyu_kernel.api`
  - `chiyu_kernel.contract`（含子树）
  - `chiyu_decision.api`（含 `score_rubric` 等评分符号；`vector` 五符号加 `vector_` 前缀）
- **铁律**：内核只声明形态，取值与执行归消费方；域逻辑不进入基座。

## 四、对外提供物（契约面）

1. **版本 / 能力出口**：`API_VERSION` / `CONTRACT_VERSION`、`api_version()` / `capabilities()` / `capability_status()` / `deprecations()`
2. **机制函数**：评分 `score_rubric` / `check_elements` / `aggregate_confidence`、红线 `evaluate_redline`、审批闸 `autonomous_release`、脊柱 `run_spine`
3. **契约 ID**：`contract/`（决策场景 I/O 契约、`required_gates` 闭集、注册期 fail-fast）
4. **守卫工具**：`check_import_surface.py`（导入方向）、`check_facade_coverage.py`（门面覆盖）、R12 机械推导

## 五、底座纪律（差异化内核）

- **严格加法**：零既存代码失效；旧符号保留别名 / 过渡
- **变异自证**：每个闸门必须判别力自证（删判据分支 → 转红 → 还原），退出码判据禁止经管道
- **零领域字面量**：域装配（S1）/ 域红线（S4）归消费方
- **红线优先**：命中即屏蔽自主放行，强制改判 REJECTED
- **升级安全闸**：版本 / 能力档位 / 符号缺失在 import 期 fail-fast
- **仓边界**：只落本仓 `docs/`，不回写消费方（APS / CRM / enterprise）

## 六、对消费方的承诺

- **兼容承诺**：`capabilities` 档位（stable / experimental）+ deprecation 政策（先 warn 一版再移除）
- **实证收编**：消费方生产实证接入的缺陷台账 / 升级演练回传本仓收编（见 `docs/2026-10-09-foundation收编-APS实证窗口台账.md`）
- **专业支持闭环**：建议 / 回信 / 回执 / 收编全部落本仓 `docs/`，消费方按 sanctioned 面消费，升级不破

---

## 七、与"公司 / 产品"层的区别

- **ChiYu AI（公司）**：北京青羽智行科技，对外品牌，B2B（制造 / 医疗 / 化工 / 涂料）
- **产品层**：CRM-AI-Native / PDM-ai-native / Agent2B
- **foundation（本仓）**：上述产品与 APS 等消费方的**技术底座**——不卖产品、不持领域，只做"形态 + 契约 + 机制 + 守卫 + 版本纪律"，把领域执行让给消费方。

> 本定位与"一次做成、多次复用"互为因果：底座每多固化一项公共能力、每多一道防假绿守卫，消费方就少重复造一次轮子、少踩一次升级坑。
