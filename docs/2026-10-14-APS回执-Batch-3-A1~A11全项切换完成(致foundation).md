# APS 回执 —— Batch-3 A1~A11 全项切换完成（致 foundation）

> 日期：2026-10-14
> 依据：foundation `docs/2026-10-14-Batch-3-跨仓包级去重规格(盘点+就绪核验+三仓接入施工图).md` §三
> 回执：foundation `docs/2026-10-14-foundation回函-致三仓(Batch-3-跨仓包级去重启动+llm-provider已补齐).md`
> 状态：**A1~A11 十一项全部完成**，先建 parity 守卫（红）→ 换装 → 全绿；全量回归见 §四。

## 一、逐项完成情况

| # | 本地件处置 | 换装后消费 | parity 守卫（APS 仓 tests/） | 结果 |
|---|---|---|---|---|
| A1 | `platform/connectors/` 删 `base.py`/`file.py`/`registry.py`（传输层三件） | `chiyu_kernel.api`：SourceConnector/ConnectorResult/FileConnector/ConnectorRegistry/default_registry/ConnectorNotRegisteredError；`legacy_aps` 经 `ConnectorRegistry.register` **自注册** | `test_connectors_parity.py`（is 锚 + get_registry 单例 + 域连接器留位） | ✅ 22 passed+6 subtests |
| A2 | `platform/promotion.py` 删裁决段（promote_gate/extract_numeric_candidates/drift_detected/audit_drift/promotion_overwrite_guard/build_promotion_payload） | `chiyu_kernel.promotion` 七模块纯函数 + `contract/promotion.py` 词汇（经 api 门面） | `test_promotion_parity.py`（核心六键逐键 parity + 装配面留 APS + 域值不泄漏） | ✅ 19 passed；既有 `test_promotion_gate.py` **零改动**全绿 |
| A3 | `platform/reflux.py` 删裁决段（prescribe 四道闸/route_retro 分流/deviation_rate/hindsight_check AND 条件） | `reflux_prescribe_guard`/`kind_to_channel`/`proposal_channel`/`deviation_rate`/`window_status`/`should_prescribe`/`deviation` | `test_reflux_parity.py`（is 锚 + 三闸状态 parity + 别名归一 + 域值留 APS） | ✅ 14 passed；reflux 八件功能套件 **零改动** 78 passed |
| A4 | `platform/feedback_loop.py` 删机制段（B1 模板断言/B2 三档+B7 undecidable/B4 拒绝出方/B3 HITL 闸） | `chiyu_kernel.feedback`（template/evaluate/calibration）+ `contract/feedback_loop.py` | `test_feedback_parity.py`（is 锚 + evaluate/prescribe_guard/approve_transition parity + DDL/事件面留 APS） | ✅ 20 passed；`test_feedback_loop.py` **零改动** |
| A5 | `platform/capability_audit.py` 删机制段（三查法/分级/计数/四件套/探针） | `chiyu_kernel.capability_audit`（three_check/grading/finding/four_piece） | `test_capability_audit_parity.py`（is 锚 + 判定次序 parity + C7 operator 不代填 + 域映射留 APS） | ✅ 14 passed；audit 四件套 **零改动** 61 passed |
| A6 | `platform/event_payload.py` 删机制（注册表/强校验/coerce）；`events.py` 加契约词汇 | `chiyu_kernel.events.payload` + `contract/event.py`（GAP-1 契约面首次经 sanctioned 面可达） | `test_vocab_parity_batch3.py::TestA6`（is 锚 + 域契约自登记 + PUBLISH_INVARIANTS 在 PG 总线成立） | ✅ 域契约（unit.published/run.*）**经 register_schema 自登记** |
| A7 | `platform/context.py` LAYERS 改契约单源 | `contract/context.py` CONTEXT_LAYERS（同一对象） | `TestA7`（is 锚） | ✅ |
| A8 | embedding 后端闭集对拍（mock provider 确认为 **APS 域扩展，未回填契约**） | `contract/vector.py` EMBEDDING_BACKENDS + shim 纯函数直用（vec_to_pg/pad_to_dim/assert_safe_identifier 已在 foundation.py） | `TestA8`（闭集对拍 + mock 禁回填锚 + shim is 锚） | ✅ |
| A9 | llm 档位词汇对拍 | `contract/llm.py` LLM_TIERS | `TestA9`（契约档位 + simple/full 域路由留 APS + OfflineStub 零网） | ✅ |
| A10 | orchestrator 状态词汇对拍 | `contract/orchestration.py` TASK_STATES/TERMINAL_STATES/BLOCK_KINDS | `TestA10`（TaskState ⊆ 契约闭集 + 终态/block_kind 逐值） | ✅ |
| A11 | memory/store/pg 词汇经 shim 直用（既有 `_contract()` 接线确认） | `contract/memory.py` MEMORY_KINDS/PROVENANCE_SOURCES | `TestA11`（kind↔表映射 + provenance 四分类落契约闭集） | ✅ |

## 二、A1 legacy_aps 自注册方案（回函征询意见的答复）

采用「**进程内单例 + 首次访问惰性注册**」（`aps/platform/connectors/__init__.py:54-65`）：

- `get_registry()` 首调时取 `default_registry()`（foundation 预注册域无关 `file`），
  随后 `reg.register(LegacyApsConnector)` 自注册域连接器 —— **foundation 注册表是唯一事实源**，
  APS 不持第二份注册表实现；
- `get_connector(source)` 委托 `registry.get()`；`ConnectorNotRegisteredError` 继承 `KeyError`，
  既有 `except KeyError` 消费方零改动；
- db/message 属 W-5.2 未批源，**保持不注册**（注册即承诺可拉取）。

意见：该形态对 enterprise 同样适用（其域连接器亦可用同款「自注册 + 惰性单例」），
建议 foundation 在 GAP-8 文档补一条「消费方域连接器自注册」推荐范式。

## 三、机制采纳边界执行情况（防域值泄漏）

逐项核对「留 APS」清单，**零域值上迁**：

- `TRUTH_FIELD_BY_KEY` / `PRESCRIBABLE` / `configs/*.json` / `aps.*` 事件名 / DDL 行形 /
  `_CAP_TO_SKILL`·`_CAP_EVIDENCE`·`_PRODUCTION_USAGE` / coerce 域键清单 /
  mock provider（D-P3/D-P4）/ simple-full 路由策略 —— 全部留本仓，且有守卫断言
  （如 `TestDomainValuesStayLocal` 族）钉住「不随机制上迁」。
- reason 文案属域表达：A2/A3 的拒绝 reason（指向本仓 `PRESCRIBABLE` 符号 /
  `configs/` 解析 / why 层硬门槛）由适配器按 guard **同闸序**还原 —— 状态与闸序
  单源 foundation，文案域表达（parity 守卫逐例对拍 status）。

## 四、验证情况

**受影响面（全部针对性套件）**：全绿，合计 **300+ passed**——

| 范围 | 套件 | 结果 |
|---|---|---|
| A1 | connectors parity + 功能 | 22 passed + 6 subtests |
| A2 | promotion parity + 闸门 + 接线静态 | 68 passed + 21 subtests（功能套件零改动） |
| A3 | reflux parity + 八件功能套件 + evolution/outer_loop | 78 passed + 14（功能套件零改动） |
| A4 | feedback parity + 功能 + outer_loop + capability_audit | 41 passed + 5 subtests |
| A5 | audit parity + 四件套 + 零绿 + kmd 探针 + contract_ids | 61 passed + 14 subtests |
| A6~A11 | 词汇对拍守卫 + events/payload/context/agents/orchestrator/memory-contract | 88 passed + 3 subtests |

**全量回归（已按 T103 §二.4 催办回填，差集实证口径）**：见文末补记（三树实测 + 基线隔离甄别）。

## 五、遗留与移交

1. ~~**A2/A3 适配器 reason 域文案**与 foundation 文案存在措辞差异……~~ **已按 T103 §二.3 裁定收口（2026-10-14）**：foundation 不提供契约「域文案注入点」，reason 属域表达、guard 对拍 status 已保证语义单源——APS 采纳，维持现状，此项遗留关闭。
2. A5 `CapabilityFinding`/`three_check` 直接再导出（同对象）；`build_traceability_graph` 等 report 入参包装器委托 foundation 核心（私有别名锚定）。
3. 本仓改动未提交，commit 命令由用户本地执行（纪律）。

---
**补记（2026-10-14 全量回归实测，响应 T103 §二.4 催办）**：

1. **前两次停滞根因（环境，非代码）**：今晨被中止的 pytest 会话遗留 **idle in transaction 连接持 memory_log 锁**（pg_stat_activity 实证，xact 5h59m），后续所有测试的 `init_schema` DDL 全部排队等锁 ⇒ 13 测试点后假死。清理僵尸后端后全程无停滞。附带发现套件次要缺陷：失败测试事务中抛错会泄漏连接，同进程后续 DDL 自堵（已记录，另立工单）。
2. **改动树全量实测（Batch-3 全部换装在树，两轮一致）**：`1758 passed / 4 failed + 97 subtests`（23m11s）与 `1761 passed / 1 failed`（21m29s，probe 适配后）。
3. **差集甄别（enterprise 口径）**：`git stash` 回基线树 `601a977`，隔离复跑**失败全集 4/4 在基线同样失败** ⇒ **Batch-3 零新增失败**。逐项根因：
   - 3× `test_run_spine_adoption_probe::TestResumeSpine`：基座 T81（D4 P-3）`resume_spine` 的 `resume_evidence` 升级为 breaking 必填，APS 探针未跟上 ⇒ **已适配**（`_resume_evidence()` 以契约 `RESUME_EVIDENCE_FIELDS` 构造三键，8/8 green）。
   - 1× `test_server_import`：基线提交 `601a977` 给 `put_particle` 新增 `binding_guard` 参数，测试内存替身签名未跟 ⇒ **已修复**（替身 `**kwargs` 跟随真实签名，6/6 green）。
4. **最终态**：全部 4 项修复后隔离验证 14/14 green；**终轮全量复跑实测 `1762 passed / 0 failed + 97 subtests`（22m10s，EXIT=0）**——Batch-3 改动后全量零失败，T103 §二.4 催办收口（详见 APS T103 回函）。
