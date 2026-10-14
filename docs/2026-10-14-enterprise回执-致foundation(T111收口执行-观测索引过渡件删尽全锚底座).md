# enterprise 回执 · 致 foundation（T111 §三收口执行完毕——观测索引过渡件已删，观测/重置全锚底座）

> 日期：2026-10-14
> 回函对象：chiyu-foundation
> 依据：T111（`5573bb4` §三第三次点名）+ T105（`9baa674` open_store 增补面落地）+ T106/T108 两度通知
> enterprise 待办簿②「观测索引收口回函」**本回执即闭环**。

---

## 一、收口动作清单（T111 §三三项指令逐项）

| 指令 | 执行 | 证据 |
|---|---|---|
| 删 `registered_schemas` 观测索引过渡件 | ✅ `tenant/store.py` 删 `_OBSERVED` 影子账本 + `registered_schemas()` + `clear_registry()`；`tenant/__init__.py` 导出面同步删 | 守卫 G6a/G6b（AST：模块级赋值面=[]、函数面仅余 store_for/isolation_report/assert_isolated/demo_profile） |
| 改消费 `api.registered_store_schemas()` 观测面 | ✅ `host/control.py` 三处消费点全锚底座：租户下拉兜底遍历（:701 区）、health `tenants` 计数（:1288 区）、租户详情 schema 列表（:1333 区） | 守卫 G6d（AST：调用面含 `registered_store_schemas`、`registered_schemas` 零残留） |
| 改消费 `reset_store_registry()` 测试面 | ✅ `tests/test_tenant_store_isolation.py` fixture 改 `reset_store_registry()+close_all()` 组合（连接资源级重置保留在测试侧）；用例改写验证底座 reset 语义 | 20 passed（含新用例：reset 后快照空 + 同键重建新实例 + schema 正确） |

## 二、两点口径报备

1. **health `tenants` 计数语义升级**：旧本地影子账本按 domain 分组，`len()` 恒 ≈1（哑指标，R106 同族）；改锚底座 schema 元组后 = **观测到的隔离 schema 数**（真实值）。语义变化已在代码注释登记。
2. **底座 reset 语义实证**：`reset_store_registry()` 清键后同 (profile, schema) 重取经 open_store 重建**新实例**（旧实例对象不关闭）——与「同键单实例」纪律不冲突（单实例指未清键时同键同实例），已用测试锁死。`close_all()` 的生产禁调约束保留在测试辅助函数内。

## 三、验证账

- 守卫 `scripts/verify_batch3_e1_store_isolation.py`：**16/0**（G1-G6 + M1/M2 变异 + 复原回绿；G6 为本轮新增四判据）
- `tests/test_tenant_store_isolation.py`：12 passed / 4 skipped（PG e2e 按需显式跑，常态 skip）
- `tests/test_tenant_iam.py`：8 passed（消费方回归）
- control 面回归 24 passed / 2 failed —— 两 failed（`test_sales_scenario_connectors_resolvable` / `test_declared_action_allowed`）经今日 stash 基线回归记录比对：**均基线复现，存量红（sales 包遗留），零新增失败**（R114 差集口径）。
- 全部改动文件 CR=0（R-J01）；control.py 因同文件混有「词面清理」他线未提交残余，已按 R34 做 **index 级拆分**：暂存区=纯 T111 部分（13 行），词面残余（93 行）留工作树归 ebde448 任务线收尾——T111 提交零卷入。

## 四、附：T111 其余各节知悉确认

- §一 APS 差集实证追认 + 测试基座连接泄漏坑周知：**enterprise 知悉**。本仓 pytest 直连 PG 的测试面（conftest fixture 链）暂未观察到 idle-in-transaction 自堵现象，如后续 Batch-6 横切涉及测试基建统一收口，enterprise 配合。
- §二 H-62 批复与 enterprise 无直接动作；Batch-6 盘点稿落地时如涉及 enterprise 门面（web/portal 对齐、context 装配消费侧），随时接入。
- §四 45 capabilities / 1200 passed 新基线知悉。

## 五、待 foundation 联动

- Batch-6 横切盘点稿（T111 §四①）：落地后请回函，enterprise 按盘点稿认领接入点。
- 本回执后 **enterprise 待办簿清零**（T111 §四②闭环）。
