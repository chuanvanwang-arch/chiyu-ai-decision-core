# CHANGELOG

> 本文件记录 **对外可感知** 的变更（门面导出面 / 契约取值 / 行为语义）。
> 纯内部重构不在此列。破坏性变更以 `[BREAKING]` 显式标注，且必须先经一版 deprecation 警告
> （政策见 `docs/versioning-and-deprecation.md`）。
> 版本口径见 §「版本三元组」：分发包版本（`__version__`）· 门面版本（`API_VERSION`）· 契约版本（`CONTRACT_VERSION`）。

## [Unreleased]

（空——生产实证窗口期（≥4 周）的变更在此累积，1.0 发布时整体转入 `[1.0.0]` 并附 compatibility 声明。）

## [0.1.0] — 首个稳定发行版（2026-10-09 打 tag，含内核抽取至 T31 全部内容）

> 版本口径：分发包 `__version__` = 0.1.0；门面 `API_VERSION` / 契约 `CONTRACT_VERSION` = 1.0.0（已先行）。
> tag `v0.1.0` 为 1.0 升级演练的真实起点。

### 内核抽取基线（T1–T5）

- contract / vector / ontology / context / store 五层 + 门面纪律。
- 决策脊柱 `chiyu-decision`（S1→S5）、自进化引擎、门户 `chiyu-portal`。

### Added（严格加法，零破坏）

- **门面版本与能力出口**（R11 / R4）：`chiyu_kernel.api` 新增 `__version__`（动态取分发包版本）、
  `PACKAGE_VERSION`、`API_VERSION` / `CONTRACT_VERSION`、`api_version()` / `capabilities()` /
  `capability_status()` / `deprecations()`。`memory` 标记 `experimental`（T5′ 未验收）可机检。
- **门面补齐已实现未导出符号**（R8 同族，两批）：
  - `assert_no_hard_delete` / `validate_dsn` / `assert_safe_identifier` / `pg_to_vec`（向量往返回程）；
  - `SharedTask` / `SubagentDescriptor` / `SubagentPool` / `TeamMember` / `TeamRegistry` / `TeamSpec`
    与 LLM 客户端 6 符号（`ToolCall` / `LlmResponse` / `LlmProvider` / `StubProvider` /
    `DeepSeekProvider` / `build_provider`）。
  - 新增守卫 `tests/test_facade_import_vs_all.py`：门面 import 了却没进 `__all__` 即红（机械推导）。
- **sanctioned import 面成文**（B1 / N2 / N5）：新增 `docs/sanctioned-import-surface.md`
  与门禁 `tools/check_import_surface.py`（接 `make lint`，对 foundation 自身同样生效）。
  决策脊柱面 `chiyu_decision.api`（含 `run_spine`）正式列为 sanctioned 面。
- **命名分族**（R10）：向量降级族以 `VTIER_*` 为主名，`TIER_*` 保留为**弃用别名**（零破坏），
  与自进化风险族 `TIER_AUTO/GUARDED/FORBIDDEN` 不再同名歧义。
- **能力子包**：`domain`（领域注入 SDK）、`persist`（标准 persister + 记忆网 writer）、
  `approval`（决策审批闸）、`graph`（图存储只读派生）、`mcpserver`（MCP 服务端骨架）进门面。
- **参考消费层** `examples/reference_consumer`（WS9）：端到端闭环 + 5 条反假绿探针 + canary。
- **B 双轨记忆运行时**（T20）：`memory_tracks`（LOG append-only 轨 + notes upsert 轨 +
  蒸馏四闸闭合）；审计凭证边写入即定，`PRESCRIBABLE_PREDICATES` 严格真子集 import 期校验。
- **真库 E2E**（T30）：`@pytest.mark.pg` 便携 PG 四判据（三表落库读回+幂等 / 零硬删除实拦 /
  递归 CTE 图派生 / 决策回链审计四问）；无库自动跳过。

### Fixed

- `examples/reference_consumer` 三处跨面 import 回归 sanctioned 面（此前摸了
  `chiyu_decision.spine` / `chiyu_decision.scoring` / `chiyu_kernel.vector.infer` 内部路径）。
- `canary.py` 对八要素的 `try/except` 兜底移除：吞掉导入失败会让八要素为空集而探针仍"绿"。
- `PgCte._cte_sql` 递归成员漏谓词过滤（第二跳起幻影边漏入关系视图）——对拍 InMemory
  参考语义实锤后修复（T30）。

### Changed

- `STORE_REQUIRED` 由人工枚举改为**机械推导**（R12），store 层符号"三不管"状态提交即红。

### 兼容性声明（compatibility）

- **stable 能力层（27 项）进入 1.0 兼容承诺**：此后 BREAKING 必须先走完整 deprecation
  周期（先 warn 一版再移除，见 `docs/versioning-and-deprecation.md`）。
- **experimental（memory / evolution）排除出 1.0 兼容承诺**；对外表述必须同时声明其实验态。
- `TIER_*` 向量降级族别名在册弃用（`deprecations()` 可查），一版后移除。

### 版本口径说明

- ⚠️ 历史上"0.1.0"长期未随实现演进 ⇒ 消费方只能靠 `hasattr` 嗅探（即 R11 的由来）；
  本版起分发包版本随发布物对齐演进。
