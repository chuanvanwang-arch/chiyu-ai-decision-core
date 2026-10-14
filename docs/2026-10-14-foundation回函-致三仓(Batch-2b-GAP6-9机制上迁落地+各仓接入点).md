# foundation 回函 · 致三仓（Batch-2b：GAP-6~9 机制上迁落地）

> 回函对象：CRM-ai-native / APS-ai-native / chiyu-enterprise
> 事项：APS 盘点 §5.3 第三波 **GAP-6~9 四项能力上迁**已全部落地（T88~T91 四个提交，每项过 lint 四闸 + 串行变异自证 + 组合全量回归）。
> 边界纪律不变：本仓不向你仓写任何产物；下列接入动作由你仓自完成，各跑 parity 守卫全绿即达收口。

| 提交 | 能力 | 落点 | 实测 |
|---|---|---|---|
| T88 `1cff85c` | GAP-6 feedback_loop | `contract/feedback_loop.py` + `feedback/`（template/evaluate/calibration） | 887 passed，5 变异 |
| T89 `952e07b` | GAP-7 capability_audit | `contract/capability_audit.py` + `capability_audit/`（three_check/grading/finding/four_piece） | 912 passed，4 变异 |
| T90 `ad6a12e` | GAP-8 connectors 传输层 | `contract/connector.py` + `connectors/`（base/file/registry） | 930 passed，4 变异 |
| T91 `7a1efd2` | GAP-9 promotion/reflux | `contract/promotion.py` + `promotion/`（policy/gate/candidates/channels/hindsight/reflux） | 1081 passed，8 变异 |

四项均为 **机制上迁、域值留消费方**：契约层零依赖/零 IO/零领域字面量，裁决全纯函数；你仓的域键白名单、域真值表、域事件名、DDL、bus·store 耦合一律留你仓。

---

## 一、GAP-6 feedback_loop：反馈闭环五纪律上迁

| 纪律 | 机制落点 | 留你仓的域值 |
|---|---|---|
| B1 指标模板七要素资格断言 | `feedback/template.py`（`assert_template_complete`，缺要素 fail-fast） | 指标域字段清单 |
| B5 runtime/seed 双口径 | `contract.feedback_loop.METRIC_SCOPES=("runtime","seed")` 闭集 | 双口径的域数据源 |
| B2 三档加权 + B7 undecidable 第三态 | `feedback/evaluate.py`（`safe_eval` 安全表达式子集：AST 白名单，禁 Call/Attribute/Subscript；undecidable 优先于阈值，绝不并入通过） | 权重域配置 |
| B4 拒绝出方守卫 | `feedback/calibration.py`（未达标 ⇒ blocked 且 `emit=False`——blocked 不发射事件） | 事件总线接入 |
| B3 HITL 校准闸 | `approve_transition`（仅 pending→approved） | 审批流挂接 |

- **门面撞名修正**：`DEFAULT_MIN_COVERAGE` 与 vector 层导出同名（0.80）冲突 ⇒ 反馈闭环侧更名 `CALIBRATION_MIN_SAMPLE`/`CALIBRATION_MIN_COVERAGE`（0.6）。
- **APS 接入点**：`platform/feedback_loop.py` 整模块机制改消费 `chiyu_kernel.feedback` 纯函数核心 + `chiyu_kernel.contract.feedback_loop` 词汇，删本地重造；你的 runtime-seed 域口径经 `register`/策略注入，禁保留第二事实源。

## 二、GAP-7 capability_audit：通用能力审计上迁

- `three_check`（三查法文件遍历）是 sanctioned IO 边界；判定链全纯函数：**零命中最优先 missing（P0，硬编码分支不得遮蔽）→ 符号在但生产零调用 ⇒ partial（零外部入口假绿形态）→ landed**；定义行不算调用点。
- 四件套（`four_piece.py`）：operator 身份 **AI 不代填**（缺省 None + `DRAFT_PENDING_USER_CONFIRM）；无历史基线时显式 missing+reason；追溯图缺跳显式标注；`probe_piece_discrimination` 缺件无 reason ⇒ FAIL；`assemble_four_piece` 报告**恒 DRAFT** 至用户确认。
- **顺带修 APS 同款两处 Windows 崩点**：relpath 相对扫描根（原对 cwd，跨盘符 ValueError）+ 归一 `/` 后判 exclude（原 `tests/` 匹配不到 `tests\`）。
- **APS 接入点**：`platform/capability_audit.py` 改消费本包；enterprise 做能力审计时同样消费 `assemble_four_piece`，勿各写一份四件套装配。

## 三、GAP-8 connectors：传输层上迁，域连接器留消费方

- `ConnectorResult`（rows/external_refs/meta 三字段）+ `SourceConnector` ABC（name + fetch）——**无状态工厂**：每次 `get` 新实例，防跨请求状态串味。
- `FileConnector`：csv（utf-8-sig BOM 兼容）/ json（双形态：list 或 `{"rows": [...]}`）/ xlsx（pandas→openpyxl 回退），**外部字段名原样保留**（no_conversion_in_connector）；不支持扩展名/缺 path ⇒ fail-closed。
- `ConnectorRegistry`：**登记即承诺**；未注册 `get` ⇒ `ConnectorNotRegisteredError`（KeyError 子类，保 APS `except KeyError` 契约）；`default_registry()` 只预注册域无关 file。
- **APS 接入点**：`platform/connectors/base.py|file.py|registry.py` 传输层删本地重造；`legacy_aps` 域连接器**留 APS**，经 `ConnectorRegistry.register(name, factory)` 自注册后同样走 `default_registry()` 取用。
- **消费方域连接器自注册·推荐范式**（APS A1 实证后追认，2026-10-14）：进程内单例 + **首次访问惰性注册**——消费方 `get_registry()` 首调时取 `default_registry()`（foundation 预注册域无关 `file`），随后 `reg.register(LegacyApsConnector)` 自注册域连接器；**foundation 注册表是唯一事实源**，消费方不持第二份注册表实现；`ConnectorNotRegisteredError`（KeyError 子类）保既有 `except KeyError` 零改动；**未批源不注册**（注册即承诺可拉取，如 db/message 属 W-5.2 未批源保持不注册）。enterprise 及后续消费方域连接器同款适用。

## 四、GAP-9 promotion/reflux：知识升格与回流管道机制上迁

- **升格三态**（`promote_gate`，裁决顺序即不变式）：白名单 → 证据数 → 一致性；集合外**直接拒绝**（不降级待人工）、孤证/矛盾 ⇒ blocked（**不发射事件**）、达标 promoted 产物**恒 PENDING**（第 3 闸 HITL 在外层）。零副作用（bus.emit 留消费方）。
- **候选反假绿**（`extract_numeric_candidates`）：只认显式声明 `<key>[:=]<数值>`，不从散文猜数字——抽不到交闸门 blocked，不硬凑。
- **漂移三值**（`drift_detected`）：True 冲突 / False 一致 / **None 不可比（必须冒泡为告警，不静默吞）**；`audit_drift` 的 `checked==0` 语义是"没有可审计项"≠"零漂移"。
- **覆盖守卫**（`promotion_overwrite_guard`）：`calibrated` 禁覆盖——AI 归纳值冒充标定值 = 知识污染不可逆；**载荷红线**（`build_promotion_payload`）：恒带 `params_source="PROMOTED"`，绝不写 CALIBRATED。
- **回流四通道**（`kind_to_channel`）：fact→c1 / falsified→c2 / config_patch→c3 / hindsight→c3p；**未知 kind 抛 `RefluxChannelError`**（禁静默丢弃：事实没落任何通道却报"已处理"= 假绿）；处方未登记 kind 默认 **c3p 建议通道**（永远不会被自动 apply）。
- **处方四道闸**（`reflux_prescribe_guard`）：白名单外直接拒绝 → 解析失败拒绝（防据不存在的键改配置）→ 空 rationale 拒绝 → 否则 pending（**从不改配置**）。
- **后见之明**（`hindsight.py`）：出方条件 **AND 不是 OR**（单条超阈 **且** 窗口告警）；每次校验都留痕（否则窗口偏差率被系统性高估——隐蔽统计假绿）；`no_data ≠ healthy`；空转（有偏差零批准）停方。
- **跨契约一致性**：`PRESCRIPTION_PENDING` 与 `contract.evolution.PRESCRIPTION_STATES` 的 "pending" 同值，守卫测试对拍；**处方状态机机制在 `evolution.prescription`（既有），promotion 包严禁重造**。
- **门面撞名修正**：feedback 侧已占 `prescribe_guard` ⇒ 回流侧更名 `reflux_prescribe_guard`。
- **实现期加固（相对 APS 版的差异，特此报备）**：`drift_detected` 对注入真值含非数值项时 APS 版会 TypeError，foundation 版过滤非数值真值、全非数值 ⇒ None（不可比，同一冒泡语义）——`audit_drift` 的 `incomparable` 计数器因此由死字段变活，有守卫测试覆盖。
- **APS 接入点**：`platform/promotion.py` + `platform/reflux.py` 的裁决段改消费本包纯函数；`PRESCRIBABLE` 域键（reschedule.*）、`TRUTH_FIELD_BY_KEY` 域真值表、`configs/*.json` 域配置、`aps.*` 事件名、store·bus 耦合**留 APS**；策略外部化消费 `load_json_policy`（未知键不进结果/逐键回落/缺文件全量默认）。

## 五、顺带修正的基础设施漂移（你仓曾依赖的生成面）

1. **manifest 生成器双向漂移**：Batch-1a 的 gate 只手改 JSON 未同步生成器；evolution 语义/verify 停留在 T78 毕业前。已修生成器（补 gate + 本次四项映射 + evolution 毕业口径 + compatibility_notes 订正），`capability-manifest.json` 全量重生成（**34 capabilities**）。
2. **门面撞名两处**（见上）：`CALIBRATION_MIN_*` / `reflux_prescribe_guard`。
3. `three_check` Windows 两崩点（见上）。
4. 新增能力登记三项同步（version.py CAPABILITIES / test LAYERS / Makefile lint `--layers`）全部随各提交落地，新能力均登记 **stable**。

## 六、状态与下一步

- Batch-0 ✅ → Batch-1a ✅(T84) → Batch-2a ✅(T86) → **Batch-2b ✅(T88~T91，GAP-6~9 全就绪)** → **Batch-3（跨仓包级去重，前置依赖"Batch-2 全量就绪"已满足，可启动）** → Batch-4/5（监控+agent / 调度复盘）→ Batch-6 横切 → Batch-7 P2/P3。
- 你仓启动 Batch-3 去重时，按本函各接入点删本地重造、改消费 foundation 纯函数核心；每删一处跑一处 parity 守卫，**禁保留第二事实源**。
- 你仓若对契约闭集有异议（如回流 kind 增补、门槛默认值调整），以回函或工单指明，foundation 按单一事实源修订并同步 manifest。
