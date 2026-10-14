# foundation 对 enterprise 反馈的正式回信与整改设计

> 本仓：`chiyu-foundation`（唯一事实源）　发送方/接收方：foundation → enterprise（消费方）
> 对应反馈：`D:\system\chiyu-enterprise\docs\2026-10-08-enterprise-to-foundation-blocking-feedback.md`
> 性质：**逐一落实的整改设计**（用户裁定：全部 8 项落地，不争论、不辩解，逐条给出技术方案）
> 日期：2026-10-08　设计方法：brainstorming　状态：评审中

---

## 〇、总体立场

enterprise 反馈的 **3 条阻塞（B1/B2/B3）与 7 条底座要求（N1–N7）全部成立**，本设计**逐项认领并给出落地技术方案**。
反馈所附 4 处表述订正（C1–C4）亦全部认领——其中 **C1（`run_spine` 未过门面）与 C2（9 键已返回）** 是本仓此前表述的两处实质错误，已在 §三 显式修正。

不做辩解。只回答「每一项怎么落实」。

---

## 一、正式回信：8 项待裁定逐一答复

| # | 待裁定项 | foundation 裁定 | 落实情况 |
|---|---|---|---|
| **B1** | 是否补 `run_spine` 到门面？ | **认领**。`run_spine` 在 `chiyu_decision.api` 已导出（`api.py:14,17`），但未收进 `chiyu_kernel.api`。**根因 = E1 sanctioned 面未成文**，与 N2 同构。方案见 §四.B1/N2 | 设计 |
| **B2** | `chiyu-decision` 是否属交付面？分发方式？ | **认领交付面**。`chiyu-decision` 是 foundation 的 L2 核心授权层，须有稳定分发。方案见 §四.B2 | 设计 |
| **B3** | 脊柱是否引入 PENDING 态？ | **认领（硬前置，方案 Z 三态枚举）**。`DecisionApprovalVerdict` 由两态升三态，`spine.py` 增 pending 分支。方案见 §四.B3 | 设计 |
| **N1** | `__version__` + CHANGELOG + 破坏性声明 + 分发？ | **认领（P0）**。`api.py` 透出 `__version__`；新增 CHANGELOG + deprecation 政策 + 版本钉分发。方案见 §四.N1 | 设计 |
| **N2** | sanctioned import 面成文 + CI 门禁？ | **认领（P1）**。成文定义 sanctioned surface（含决策包门面），CI 加 import 门禁，**E1 双向适用**。方案见 §四.B1/N2 | 设计 |
| **N3** | `execute` 返回契约？ | **认领（P1）**。明确 `execute`=只写不可 fetch、`execute_fetch`=可读，类型去 `Any`。方案见 §四.N3 | 设计 |
| **N4** | 决策读回契约？ | **认领（P2）**。定义 `decision_backlinks`/`timeline_view` + `verify_chain` 复核为权威读面。方案见 §四.N4 | 设计 |
| **N5** | `contract` 常量过门面？ | **认领（P2）**。`EIGHT_ELEMENTS`/`RUBRIC_KEYS`/`SPINE_ORDER` 进 sanctioned 面。方案见 §四.B1/N2 附 | 设计 |
| **N6** | `AgentRegistry` baseline？ | **认领（P2）**。提供登记样例 + 消费方登记处说明。方案见 §四.N6 | 设计 |
| **N7** | canary 探针件？ | **认领（P2）**。内核 ship `canary_probe`（WS9 落地形态）。方案见 §四.N7 | 设计 |

> 备注：enterprise 反馈 §七「本轮已决定做的事」T1–T6 与其转观察项 U2/A2/D1/U3/D3 的切割，与本设计**不冲突**——本设计是 foundation 侧整改，enterprise T1–T6 是其仓内自闭环，双向并行。D1 推迟逻辑（删 audit 链须待 run_spine 落地）正确，本设计 B3/B1 落地后 D1 即可解除挂起。

---

## 二、反馈 4 处订正认领

| # | 原表述 | 订正依据（本仓源码） | 处理 |
|---|---|---|---|
| **C1** | §5 表"`run_spine` 已导出" | `chiyu_kernel/api.py` 对 `run_spine` 零命中；`chiyu_decision/api.py:17` 才导出 ⇒ 顶层门面未收 | **已认错**：顶层门面确实未导出。§四.B1 修复 |
| **C2** | "`score_decision` 只返 `ratio/level`" | enterprise `rubric.py:258-267` 已返 `"scores"`（9 键）；键名 ≡ `contract/decision.py:39 RUBRIC_KEYS`，`_SCALE_MAX` ≡ `RUBRIC_SCALE_MAX` | **已认错**：数据侧仅需 reshape，非重建 |
| **C3** | "生产路径强制 `profile`" | `spine.py:63-64` 为 `if profile is None: pass`（明确允许）；真失效点为调用点 `profile.redline` 解引用 | **已认错**：改表述，见 §四 风险说明 |
| **C4** | "`web/*.html` 内部记号规模性违规" | `⛔` 绝大多数在 JS 注释内；用户可见仅 `agents.html:200` 类错误文案 | **已认错**：降级为卫生清理（enterprise T6 已覆盖） |

---

## 三、设计总原则（约束每一处改动）

1. **分层铁律不动**：`chiyu-kernel`（L0/L1）**不反向依赖** `chiyu-decision`（L2）。B1 用「sanctioned 面扩入决策包门面」而非「kernel 收 decision」，避免包反向依赖。
2. **E1 双向适用**：sanctioned 面**成文**，foundation 自身也遵守；CI 加 import 门禁，不只约束消费方。
3. **红线铁律不松**：B3 引入 PENDING 态时，**红线命中仍硬 `rejected`**，不因 pending 豁免（embody A 红线优先 / 金律26）。
4. **注入式透传保留**：`approval_gate=None` 默认透传既有行为；新增 pending 态不影响既有 approved/rejected 消费方（Backward Compatible）。
5. **反假绿自证**：每项改动须配**变异自证**（删判据分支→测试转红→还原），不接受"单跑绿"为验收。

---

## 四、整改设计：逐项技术方案

### B1 + N2 — sanctioned import 面成文 ＋ E1 双向 ＋ `run_spine` 可见化（合并设计）

**问题**：`run_spine` 只经 `chiyu_decision.api`（`api.py:17`），但消费方被允许的门面是 `chiyu_kernel.api`（`api.py:3` 明写"只许 import 本模块与 contract"）。两条门面未对齐 ⇒ 消费方"想合规就用不到脊柱"。

**方案（取向：扩 sanctioned 面，不做 kernel→decision 反向依赖）**：

1. **成文 sanctioned surface**：新文档 `docs/sanctioned-import-surface.md`，明确定义消费方合法 import 面 =
   - `chiyu_kernel.api`（基础内核面）
   - `chiyu_kernel.contract`（L0 契约面）
   - `chiyu_kernel.approval`（决策审批闸面，B3 后含 PENDING 语义）
   - `chiyu_decision.api`（决策脊柱面，`run_spine`/`SpineResult`/`SPINE_ORDER` 等）
   - `chiyu_portal.api`（门户面，若授权）
2. **E1 双向门禁**：`make lint` 新增 import 门禁脚本，校验**任何源码文件**（含 foundation 自身）不得 import sanctioned 面之外的内部路径。`spine.py:14-17` 直接 `from chiyu_kernel.approval/contract.decision` —— 因 approval/contract 已进入 sanctioned 面，此 import **转为合规**，无需改写。
3. **`run_spine` 可见化**：在 `chiyu_kernel.api` 顶部加**转发注释**（不 import，避免 kernel→decision 反向依赖），并更新 `api.py:3` 的"只许 import"注释，把 `chiyu_decision.api` 列为 sanctioned 面之一。`from chiyu_kernel.api import run_spine` 仍不可用（正确，因决策在独立包）；消费方用 `from chiyu_decision.api import run_spine`（同 `chiyu_kernel.contract` 直接 import 纪律）。

**N5（contract 常量）一并解决**：`EIGHT_ELEMENTS`/`RUBRIC_KEYS`/`SPINE_ORDER` 经 `chiyu_decision.api` 与 `chiyu_kernel.contract` 均已可达，随 sanctioned 面成文即合法，无需改 import 路径。

> **验收判据**：① sanctioned 面文档发布；② import 门禁脚本存在且 `make lint` 绿（含 foundation 自检通过）；③ `from chiyu_decision.api import run_spine` 可用、`from chiyu_kernel.api import run_spine` 明确不可用且文档说明原因。**变异自证**：故意把 `spine.py` 改 import 一个 sanctioned 之外路径 → lint 转红。

### B2 — 决策包交付面（稳定分发）

**问题**：`deploy/Dockerfile` 只 COPY kernel，`chiyu-decision` 未进生产镜像。

**方案**：
1. **明确交付面**：`chiyu-decision` 属 foundation L2 核心授权层，纳入正式交付。
2. **稳定分发**：阶段 P3 前，采用**版本钉的 src 路径**（同现有 kernel 口径）：`prep_build_context.sh` 同时 stage `packages/chiyu-kernel/src` 与 `packages/chiyu-decision/src`，`Dockerfile` `COPY decision /app/src/decision`，`PYTHONPATH` 增 `/app/src/decision`。
3. **构建期 import 闸扩展**：现有 build 期 import 闸（`:54-58`）从仅校验 kernel 扩展到校验 `run_spine`/`SpineResult` 可 import，防"符号改名静默进生产"（N1 同源）。
4. 阶段 P3 后切换 `make dist-release` 编译 `.pyd` wheel（kernel + decision 同 wheel 族）。

> **验收判据**：`prep_build_context.sh` stage 两包；Dockerfile COPY decision；构建期 import 闸断言 `run_spine` 可 import。**变异自证**：删 decision stage → 构建失败。

### B3 — 决策脊柱 PENDING 态（方案 Z：三态枚举）

**问题**：`DecisionApprovalVerdict`（`approval/__init__.py:15-21`）只有 `approved:bool` + `requires_human:bool`；`spine.py:93-105` 只判 `if not approved:` 走 `approval_rejected`。`requires_human` 时"等人批"被记为 `approval_rejected`（错值），且不落正向边。

**方案 Z（用户裁定）**：

1. **`DecisionApprovalVerdict` 改三态**（`approval/__init__.py`）：
   ```python
   class DecisionVerdictState(Enum):
       APPROVED = "approved"
       REJECTED = "rejected"
       PENDING  = "pending"

   @dataclass(frozen=True)
   class DecisionApprovalVerdict:
       state: DecisionVerdictState
       reason: str
       requires_human: bool = False
       # 兼容字段：approved 派生属性（approved = state is APPROVED），旧消费方不破
   ```
   保留 `approved`/`reason`/`requires_human` 兼容（旧消费方读 `.approved` 仍工作）。
2. **`spine.py` 三态分支**：
   - `state == APPROVED` → 走 persister 落库（既有行为）。
   - `state == REJECTED` → `approval_rejected = reason` + audit `approval_rejected` + 不落库（既有，红线硬拒）。
   - `state == PENDING` → **新增**：不落正向决策边、`persisted=False`、audit 留 `approval_pending` 痕（记 reason + requires_human）、`SpineResult` 增 `pending=True` 状态位。决策进入"待人工审批"，由消费方编排异步审批→批准后回派底层 action。
3. **默认闸行为不变**：`DecisionPassThroughGate` 仍返回 `APPROVED`（`run_spine` 默认透传，未注入闸的既有消费方零影响）；`RedlinePriorityGate` 红线段仍返 `REJECTED`（红线不因 pending 豁免，守 A）。
4. **WS3 变异测试扩展**：新增 pending 分支测试：
   - pending 时不落正向边、审计为 `approval_pending`；
   - 红线命中时即使消费方 gate 返 pending 意向，红线仍 `REJECTED`（红线优先不可覆盖）；
   - 兼容：旧两态消费方（读 `.approved`）不破。

> **验收判据**：① 三态枚举落地；② pending 走 `approval_pending` 审计 + `pending=True` + 不落正边；③ 红线仍 `REJECTED`；④ 既有 approved/rejected 测试全绿。**变异自证（三处）**：禁 pending 分支→pending 探针转红；禁红线优先分支→红线转 pending 的探针转红；删 pending 审计→审计断言转红。

### N1 — 版本钉 + CHANGELOG + deprecation 政策 + 分发（P0）

**方案**：
1. `chiyu_kernel/api.py` 导出 `__version__`（从 `pyproject.toml` version 注入：`importlib.metadata.version("chiyu-kernel")`，或读常量）。消费方构建期 `assert version(kernel) >= 基线` 可行。
2. 新增 `CHANGELOG.md`：逐版本列变更；破坏性变更显式标 `[BREAKING]`。
3. `docs/versioning-and-deprecation.md`：API 稳定性策略（stable 子集 semver）、deprecation 政策（**先 warn 一版、再移除一版**）、版本钉分发（wheel / src 路径 + 版本号）。
4. 分发方式：B2 的 src 路径 stage + 版本号；P3 后 wheel。

> **验收判据**：`from chiyu_kernel.api import __version__` 可用且 = pyproject 值；CHANGELOG 存在；deprecation 政策文档存在。**变异自证**：改 version → `__version__` 同步变化（断言相等）。

### N3 — `execute` 返回契约（P1）

**方案**：
1. `store/pg_store.py:56` `execute` 返回类型从 `Any` 改为 `None`（语义：只写、cursor 随 context 关闭、不可 fetch、不返回可读句柄），docstring 明示"**写路径，仅供执行无返回的 DML；需要读结果用 `execute_fetch`**"。
2. `execute_fetch`（`:67`）返回类型改为 `list[dict]`（`fetch_all=True`）/ `dict | None`（首行），去 `Any`。
3. 全仓清理对 `execute(...)` 返回值做 fetch 的调用点（若存在），统一走 `execute_fetch`。

> **验收判据**：`execute` 标注 `-> None`；`execute_fetch` 标注明确；docstring 说明写/读分工；`make lint` 绿。**变异自证**：把某 DML 调用点改成读 `execute` 返回值 → 类型 checker 红（如启用 pyright）或 lint 断言。

### N4 — 决策读回契约（P2）

**方案**：以 WS8 已有只读派生面（`graph/`）为**权威读回面**，成文定义：
- `decision_backlinks(decision_id)` → 决策回链审计四问（被谁引用/覆盖谁/谁覆盖我/源自哪条例外）；
- `timeline_view(...)` → 时间线叙事（四源只读聚合）；
- `relation_view(...)` → 关系图谱（受控边多跳）；
- `verify_chain` 复核审计链（audit 层）。
写 `docs/decision-readback-contract.md`：表名（event/particle/graph_edge 的 schema）、复核 API、证伪方法（"真落库 + 链自洽"统一判定式，取代各消费方自造读面）。

> **验收判据**：读回契约文档发布，给出统一判定式；消费方 A3/enterprise T5 探针可复用该判定式。

### N6 — `AgentRegistry` baseline 登记（P2）

**方案**：
1. 内核 `tests/` 或 `examples/` 提供一份 baseline 登记样例：展示 `AgentSpec`（`contract_task_id` 必填）的构造、登记、重复即抛。
2. `docs/agent-contract-registry.md`：说明消费方应在何处登记自己的 agent 契约键（本仓 `contract/contract-ids.json` 是唯一事实源），并给出跨仓闭合路径（workbench 校验 `contract_task_id` 归属在消费方侧如何 `registryChecked=true`）。

> **验收判据**：baseline 样例可运行登记；文档说明登记处；设计文档校验 `registryChecked=true`（跨仓闭合）。

### N7 — canary 探针件（P2）

**方案**：内核 ship `chiyu_kernel/canary/` 包（WS9 参考消费层的落地形态）：`canary_probe(dsn, profile)` 一键跑 3 判据：
1. 决策真落库（`event`/`particle`/`graph_edge` 有行）；
2. 7 谓词真物化（`graph_edge` 7 条 `edge_source='engine'`）；
3. 红线命中即 `REJECTED`/`pending` 不落正向边。
消费方只填连接参数即跑，判据口径由 foundation 统一维护（替代各消费方自造探针）。

> **验收判据**：`canary_probe` 存在；填 DSN 可跑出三判据判定；探针判据与 N4 读回契约的判定式一致。

---

## 五、风险与前置依赖

| # | 风险 | 处置 |
|---|---|---|
| 1 | **B3 三态枚举是否破坏既有 approved/rejected 消费方** | 保留 `approved` 派生属性（`state is APPROVED`）+ `reason`/`requires_human` 不删；WS3 既有测试全绿为准 |
| 2 | **`run_spine` 仍在独立包，kernel 不反向依赖** | 用 sanctioned 面文档 + import 门禁解决可见性，不做 kernel→decision import |
| 3 | **B2 引入 `chiyu-decision` 进生产 = 新增跨仓依赖** | 构建期 import 闸扩展校验 `run_spine`；`PYTHONPATH` 钉版本；P3 后 wheel |
| 4 | **B3 红线优先不可被 pending 覆盖** | `RedlinePriorityGate` 红线段恒返 `REJECTED` + 变异测试守 |
| 5 | **N3 改 `execute` 返回类型可能波及其他消费方** | 先全仓排查 `execute(...)` 被读的调用点；deprecation 政策（先 warn 一版） |

---

## 六、执行次序

```
R1  B1+N2  sanctioned 面成文 + import 门禁 + run_spine 可见化     [低风险，先解锁 enterprise 合规路径]
R2  N1  __version__ + CHANGELOG + deprecation 政策                [P0，低风险]
R3  B3  PENDING 三态枚举（方案 Z）+ WS3 变异测试扩展              [核心，高风险，须独立验收]
R4  B2  chiyu-decision 交付面 + 构建脚本 + import 闸扩展          [B3 后，因 run_spine 需稳定可用]
R5  N3  execute 返回契约                                          [P1]
R6  N4 读回契约文档 + N6 baseline + N7 canary 探针件              [P2 配套]
R7  N5  contract 常量随 sanctioned 面成文自动闭合                  [随 R1]
```

每阶段：全量回归绿 + 变异自证通过 + §13 零残留复核，再进入下一阶段。

---

## 七、交付物清单

| 交付物 | 落点（本仓） |
|---|---|
| sanctioned 面文档 | `docs/sanctioned-import-surface.md` |
| import 门禁脚本 | `tools/check_import_surface.py` + 接 `make lint` |
| `__version__` 导出 + CHANGELOG + deprecation | `api.py` / `CHANGELOG.md` / `docs/versioning-and-deprecation.md` |
| PENDING 三态 + spine 分支 + 变异测试 | `chiyu_kernel/approval/` / `chiyu-decision/spine.py` / tests |
| 决策交付面构建 | `prep_build_context.sh` / `Dockerfile`（enterprise 仓） |
| `execute` 返回契约 | `store/pg_store.py` |
| 读回契约文档 | `docs/decision-readback-contract.md` |
| AgentRegistry baseline + 文档 | `examples/` / `docs/agent-contract-registry.md` |
| `canary_probe` | `chiyu_kernel/canary/` |

> ⚠️ 交付物中「决策交付面构建」（B2 的 Dockerfile/prep 脚本）落 **enterprise 仓**（消费方自改）；本仓产设计 + kernel/decision 侧代码，不向 enterprise 写入。B2 的 build import 闸扩展若在 foundation 仓则落 foundation。

---

## 八、待批复事项（本设计文档的批准门）

1. **B3 方案 Z 已获裁定**（用户选型），本文档固化之；
2. **B1/N2 合并取向**：走「扩 sanctioned 面」而非「kernel 收 decision」——确认是否认可（涉及 E1 纪律的定义变更）；
3. **执行顺序 R1→R7** 是否按此推进、是否先做 R1（低风险解锁合规路径）。

---

# §A 生命契约（双向覆盖）

## 契约块 1 — foundation 侧整改执行

```contract-yaml
- task: "foundation 对 enterprise 反馈的 8 项整改落地（B1/B2/B3 + N1–N7）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-particle-system-design, ai-capability-audit, ai-native-action-design]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "sanctioned 面文档+import 门禁绿；__version__ 导出；B3 三态枚举+变异自证转红后还原；CHANGELOG+deprecation 政策；execute 返回契约；读回契约文档；AgentRegistry baseline；canary_probe 可用"
```

**契约说明：** 本任务由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），须调用 8 项整改相关方法论 SKILL、读取 `chiyu-foundation` 记忆（L1/L2，≤2 跳）；成功标准为 §四 各项验收判据全部通过（含 B3 变异自证）。

## 契约块 2 — enterprise 侧采纳契约

```contract-yaml
- task: "enterprise 按 feedback 已决定事项 T1–T6 + 本设计落地的 foundation 面进行采纳"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-capability-audit, ai-native-action-design]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "T1 audit 链持久化 / T2 render_board 真读源 / T3 八要素 / T4 rubric 9 键 / T5 反假绿探针(含 pending≠rejected) / T6 §13 卫生清理全落地；且不依赖 run_spine 的本地闭环测试绿"
```

**契约说明：** 本任务由 `enterprise-platform-builder` 承接（契约键 `ct-chiyu-enterprise`），其 T1–T6 本地闭环（不依赖 foundation B3/B1 落地即可推进）须全部完成；待 foundation 侧 B1/N2/B3 落地后切换 `run_spine`。

## 契约块 3 — APS 侧不变（覆盖纪律：≥2 agent 须全覆盖，故补记 APS 非本次范围）

```contract-yaml
- task: "APS 侧不受本 enterprise 整改设计影响（本设计范围=enterprise 反馈，不波及 APS）"
  contract_task_id: ct-aps-consume
  agent: consumer-integrator
  skills: [ai-capability-audit]
  memory: [APS-ai-native]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "本设计落地后 foundation 的 sanctioned 面/版本钉/execute 契约/读回面等改动不引入 APS 已采纳能力的回归（APS 侧测试保持绿）"
```

**契约说明：** 本任务由 `consumer-integrator` 承接（契约键 `ct-aps-consume`）。APS 不在本设计的整改范围内，本契约仅为满足"文档覆盖 ≥2 登记 agent 须全覆盖"的覆盖纪律而补记，声明 foundation 本次改动（sanctioned 面/版本/execute/读回面）不得引入 APS 已采纳能力的回归。

---

## 闭环回写

本设计交付后由 agent workbench 监控（P10）；若执行 agent 未调用 `skills`、未读 `memory`、或 `success` 未达成，回写 `*.feedback.json`（按 `task+gap_type` 幂等 upsert），下轮 P0 吸收，提出 SKILL/设计改进提案（须用户批准后应用）。

---

## 实施状态（2026-10-09 收口；计数口径见下方注记）

| 项 | 状态 | 落点与证据 |
|---|---|---|
| R1 sanctioned 面（B1/N2/N5） | ✅ | `docs/sanctioned-import-surface.md` + `tools/check_import_surface.py`（106 文件/108 跨面 import 全合规，接 `make lint`）；守卫 `packages/chiyu-kernel/tests/test_sanctioned_import_surface.py`（13 passed，含 3 条变异自证）；cli `_plugins.py` 门面漂移修复（13 passed） |
| R2 版本钉（N1） | ✅ | `api.py` 导出 `__version__`(0.1.0)/`PACKAGE_VERSION`/`API_VERSION`(1.0.0)/`CONTRACT_VERSION` + `api_version()`/`capabilities()`(28 键)/`deprecations()`(5 条 TIER→VTIER)；`CHANGELOG.md` + `docs/versioning-and-deprecation.md`；守卫 `test_facade_import_vs_all.py` |
| R3 PENDING 态（B3，方案 Z） | ✅ | `DecisionVerdictState` 三态枚举（approval/__init__.py:24）+ `.approved`/`.pending` 兼容派生属性；spine.py:115 PENDING 分支（不落正向边、审计留 `approval_pending`、persisted=False）；红线命中恒 REJECTED 不可降级（spine.py:92 强制改判守卫）；WS3 全量 30 passed |
| R4 graph 读回（N4） | ✅ | `chiyu_kernel/graph`（WS8 只读派生，纯 PG CTE 参考实现）进门面 api.py:389-390 |
| R5 execute 契约（N3） | ✅ | `store/pg_store.py` 重写（07:14 落定）；`test_store_execute_contract.py` 4 passed（含 hard-delete 拦截） |
| R6 AgentRegistry 样例（N6） | ✅ | `examples/reference_consumer/agents.py`（baseline 登记 + 三闸说明 + 幂等）+ 守卫 `tests/test_agents_registry.py`（6 passed，三闸各配破坏性构造） |
| **B2 交付面裁定**（blocking-feedback §三） | ✅ | `chiyu-decision` **属交付面**（D3 授权分级、可单独授权），分发方式 = **独立 wheel**（`packages/chiyu-decision/pyproject.toml` version=0.1.0）+ 版本钉；`Makefile dist` 已扩展为 kernel+decision 双 wheel（替代 enterprise "拷 src 快照"现状）；消费方按授权择一安装 |
| **#6 决策点 I/O 契约 schema**（feedback #6 后半截，原判"部分完成"） | ✅ | `DecisionScenarioProfile` 增 3 个可选契约字段：`inputs`/`outputs`（`DecisionIOField(name,kind,required,description)`，kind ∈ 中性闭集 `IO_KINDS`={particle,asset,context,event,graph-edge}）+ `required_gates`（⊆ `GATE_KINDS`={redline,approval}，对齐 spine 实际闸位）；`register_scenario` 注册期 fail-fast 校验（6 道闸）；向后兼容（不声明=旧式登记）；门面导出 `DecisionIOField`/`IO_KINDS`/`GATE_KINDS`；守卫 `test_scenario_io_contract.py` 11 passed（每道校验闸各配破坏性构造）+ 既有 7 passed + 组合 **692 passed** |
| **C1–C4 文档订正**（blocking-feedback §六 / 待裁定 #8） | ✅ | 建议书 `2026-10-08-enterprise-adopt-recommendation.md` 已按 enterprise 实测订正 7 处（全部带【C# 订正 2026-10-09】标记）：C1 run_spine 位置、C2 score_decision 本返 9 键、C3 profile 失效点在调用点、C4 降级为卫生问题 |
| R7 canary 探针件（N7） | ✅ **kernel 已 ship（G6 同步，2026-10-09）** | `chiyu_kernel.canary.canary_probe` + `CanaryReport` **已过门面**（api.py:409-410, 563-564，`capabilities()` 报 `canary: stable`）——决策落库三判据统一判定式收归基座（event+particle 成对 / engine 边恰好相等 / 红线挡落库），判据口径单一事实源、消费方只注接线；`examples/reference_consumer/canary.py` 为参考接线样例（已进 `make test` 闸门）。⚠ 本行原表述"不在 kernel 另 ship"已被实施推进推翻，据 enterprise G6 实测订正 |

**验收口径（H2 统一，2026-10-09）**：`make test` 等价组合命令 = kernel+tools+decision+portal+examples+cli **一个口径**；历史数字（675→680→692）是同一口径随 commit 演进的快照，**以最新实跑为准**：2026-10-09 09:1x 实跑 **723 passed / 0 failed**（含本轮 G2–G5 新守卫 14 项；与 enterprise 复测锚 bdb6d98 的 692 相比，增量 = 本轮新守卫 + 并发演进）。本文档其他处出现的 passed 数字一律指该组合口径。
**剩余工作**：enterprise 侧 adopt（其仓内执行——run_decision 接 run_spine、persist 注入、§13 清内部记号），见 `docs/plans/2026-10-08-enterprise-adopt-recommendation.md`。
