# enterprise 回执 · 致 foundation（Batch-3 五项切换 E1–E5 全部收口）

> 回函对象：chiyu-foundation（Batch-3 跨仓包级去重启动函 T95 + 施工图 T94 §四）
> 事项：enterprise 侧 **E1–E5 五项全部完成**，每项 parity 守卫全绿 + 全量回归差集实证零新增失败；随函答复启动函「请三仓回复」两项确认，并报备一项底座增补建议。
> 边界纪律：所有切换在本仓完成；删而不切/切而不删均未发生（每项先建守卫后删，禁第二事实源）。

---

## 一、五项完成标注（闸门③）

| # | 动作 | 实测收口 | parity 守卫 |
|---|---|---|---|
| E1 | 删 `tenant/store.py` 双键层（`_REGISTRY`/`_PROFILES`）+ `host/credential_backend.py`/`host/scenario_events.py` 两处 `PgVectorStore` 直构回避，改消费 `api.open_store(profile, schema=...)` | 守卫 12/0；隔离三判据（异 schema 异实例/同键单实例/异 profile 同 schema 隔离）经域入口 `store_for` 重放全绿；相关回归 12 passed | `scripts/verify_batch3_e1_store_isolation.py`（G1-G5 静态 AST + M1 pre-T86 键控变异/M2 永不缓存变异均转红） |
| E2 | 删 `decision/rubric.py` 本地九尺子词汇表（RUBRICS/`_SCALE_MAX`）与等权聚合段；词汇/满档取 `contract.decision` 四常量；**等权基准单一取值路径 = `chiyu_decision.api.score_rubric`**；权重/焦点/白名单（config_store 域配置语义）保留 | 守卫 10/0；3 组输入对拍 ratio/missing 逐值相等；域覆盖路径与域加权公式回归锁；rubric 测试 12 passed | `scripts/verify_batch3_e2_rubric_aggregation.py`（P1-P4 + M1 错分母变异/M2 恒 1.0 假面变异均转红） |
| E3 | `approval/state_machine.py` 核态拼写从 `APPROVAL_CORE_STATES` 派生（禁第二词汇表）；投影 `_CORE_OF` 加载期双断言（定义域=域态集/值域=契约四核态）+ 扩展边/基座闭集重叠断言；`next_state` 经 `assert_approval_transition(core_from, core_to, extra=...)` **契约终审**；扩展边显式声明：pending 自环（submit/任务级操作）+ 三终态只读自环 | 守卫 7/0；5 态 × 12 操作全笛卡尔积对拍——合法迁移返回值与域矩阵语义逐值相等、投影 ∈ 闭集∪extra、非法操作恒「状态机拒绝」；状态机测试 9 passed | `scripts/verify_batch3_e3_approval_states.py`（P1-P3 + M1 契约闸桩恒拒证明闸在链上/M2 投影缺核态转红） |
| E4 | **删本地 `llm/openai_compat.py`**（回赠收口）；`llm/__init__` 改 foundation 别名 + 域装配面导出；`platform_provider.py` 工厂改构造 `chiyu_kernel.api.OpenAICompatProvider`（租户凭据解析/ProviderSwitch 留本仓）；3 个测试文件 import 切 `chiyu_kernel.api`，全仓 grep 零残留 | 现有 llm 单测 **19 passed（含 test_providers_e2e）**——同断言在 foundation T93 类上全绿（fail-closed `match="api_key"` 兼容；sender 替身零真网） | 既有 `test_openai_compat_provider.py` 即 parity 守卫（docstring 已标注） |
| E5 | 核查（不阻塞）：① IAM 首 admin/专家授权种子 **env 驱动确认**（`CHIYU_BOOTSTRAP_ADMIN` 缺失即跳过，幂等 upsert，`iam_backend.py:105-122`）；② `mcp_bridge.py:539/634` 确认为**注释级**历史命名对照（零行为）；③ `action/platform_catalog.py` 实测 **62 个平台 Action 命名零域关键词**（grep `crm/sales/fin./ful./商机/客户` 零命中）——施工图「建议随租户资产外置」按实测**无需外置**（保守建议更正）；④ `host/control.py:4301-4320` CRM 行业画像**演示种子**仍在，但为三级降级链兜底（仅 PG 未配置首装态，显式标注）——建议后续随租户资产外置，不在本批 | 核查结论如上 | grep + 源码锚点 |

## 二、启动函两项确认（§四「请 enterprise 回复」）

1. **E1 切换窗口**：已确认并随本批完成——本地 foundation 工作树 HEAD=T95（含 T86 schema 双键与 T93 provider），`open_store(profile, schema)` 五项能力实测可用（含 `contract.security.APPROVAL_CORE_STATES`、`chiyu_decision.api.score_rubric`）。
2. **E2 对拍基准**：确认以 **APS `kmd.py` 现成消费形态为范本**——逐尺域启发式本地产出 → `score_rubric(raw)` 取等权 ratio/missing；「等权时两口径恒等」归 parity 测试锁死（本仓 `test_decision_rubric.py::test_default_path_ratio_equals_foundation_score_rubric` + 守卫 P1/M1），运行期单一取值路径，不做双口径分支。

## 三、底座增补建议（不阻塞，建议 Batch-1b 吸收）

`open_store` 的 `_stores` 注册表**无公开快照/重置面**。enterprise 的 `registered_schemas()`（control.py 展示兜底，生产恒空）现以**观测索引**实现（记录 store_for 放行过的 (domain, schema)，显式非实例源、禁用于隔离裁决）；`clear_registry()`（仅测试消费）以 `close_all()` + 清观测索引过渡（实例对象由底座键控持有，同键重取仍单实例）。建议 foundation 增补公开 `registered_store_schemas()` / `reset_store_registry()`，enterprise 侧随即收掉观测索引。当前实现**非第二事实源**（实例恒由 open_store 出，守卫 G4 AST 锁死）。

## 四、全量回归差集实证（闸门②）

- 本轮改动树：`210 failed / 1186 passed / 15 skipped / 62 errors`（7m05s）；
- **stash 基线树**（本轮 19 文件暂存还原后）：`210 failed / 1185 passed / 15 skipped / 62 errors`（7m00s）；
- 失败集合逐项 comm 差集：**271 项共同失败，双向各 1 项孤立差异**（`test_alert_engine::test_default_rules_four` 与 `test_config_center_api::test_profile_templates_and_assign_roundtrip`）——隔离复跑两向翻转，证实为**顺序依赖偶发**（两树各随机翻一个），非确定性回归；
- **确定性差值 = +1 passed**（E2 新增对拍测试）⇒ **E1–E5 零新增失败**。
- 存量红归属（非本轮、非本任务线，移交）：`test_platform_handlers_wiring.py` 62 errors（需 host 运行态）、`test_profile_store.py`（`pg_config_store.py`/`config_store.py` 既存未提交改动与夹具冲突）、sales 包移除遗留（action_executor 5F 等）、RBAC/console 真数据面 6F。

## 五、提交状态（R8：AI 不 commit，命令已交用户）

本批 12 文件 + 3 守卫脚本（LF 落盘，CR=0 复核），拟按特性线分 5 笔提交（E1/E2/E3/E4/回函文档）；`tenant/config_store.py`/`grant.py`/`pg_config_store.py` 等既存改动属其他任务线，提交命令显式排除。
