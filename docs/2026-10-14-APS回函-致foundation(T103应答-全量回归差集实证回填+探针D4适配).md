# APS 回函 · 致 foundation —— T103 应答（全量回归差集实证回填 + reason 裁定采纳 + 探针 D4 适配）

> 日期：2026-10-14
> 应答对象：T103（`fd961fd`，`2026-10-14-foundation回函-致三仓(三仓回执核验收口+D1-D7全项裁定+第二轮盘点回执+Batch-1b进度).md`）§二
> 关联：APS 回执 `docs/2026-10-14-APS回执-Batch-3-A1~A11全项切换完成(致foundation).md`（§四/§五已同步回填修订）

---

## 一、T103 §二 逐条应答

| T103 条目 | APS 应答 |
|---|---|
| §二.1 A1~A11 核验通过 | 收到，闸门次序与零域值上迁守卫纪律维持。 |
| §二.2 自注册范式追认入库（T101） | 收到。GAP-8 补条已对齐 APS A1 实证形态（进程内单例 + 惰性注册 + foundation 注册表唯一事实源 + 未批源不注册），enterprise 接入时可复用。 |
| §二.3 A2/A3 reason 不设契约注入点 | **采纳，遗留项关闭**。理由认同：reason 属域表达，guard 对拍 status（及关键子串）已保证语义单源；文案单源收益不抵契约面扩张成本。APS 回执 §五.1 已同步修订为「维持现状」。 |
| §二.4 催办全量回归实测回填 | **已回填，见下节（差集实证口径）**。 |

## 二、全量回归差集实证（回应催办）

### 2.1 前两次停滞根因（环境，非代码、非本批改动）

今晨被中止的 pytest 会话在 aps_test 库遗留 **idle in transaction 连接持有 memory_log 锁**（`pg_stat_activity` 实证：`state='idle in transaction'`，事务龄 5h59m），后续所有测试的 `init_schema` DDL（`ALTER TABLE memory_log ADD COLUMN ...`）全部排队等锁 ⇒ 套件在 13 测试点后假死。清理僵尸后端后全量三连跑全程无停滞。

附带发现（另立工单，非本批范围）：套件存在**失败测试连接泄漏**——测试在事务中抛错后连接遗留 idle in transaction（持 ACCESS SHARE），同进程后续 `init_schema` 的 DDL 会自堵；全量连续跑场景偶发。建议后续给测试基座加「事务异常即 rollback + 连接关闭」收口。

### 2.2 改动树全量实测（Batch-3 A1~A11 全部换装在树）

| 轮次 | 结果 | 备注 |
|---|---|---|
| 第 1 轮（带 `-v --timeout=120`） | 停滞于 test_V2_import_orders（锁根因实证点） | 首次停滞复现点 |
| 第 2 轮（清锁后，`-q --timeout=300`） | **1758 passed / 4 failed** + 97 subtests（23m11s） | probe 适配前 |
| 第 3 轮（probe 适配后） | **1761 passed / 1 failed**（21m29s） | 仅剩 server_import 替身漂移 |

### 2.3 差集甄别（enterprise 口径：改动树 vs stash 基线树）

`git stash push -u`（143 项改动全量入库 stash）回基线树 **601a977**，隔离复跑**失败全集**：

- `test_server_import.py` 单文件：**1 failed / 5 passed**——与改动树同位同因；
- `test_run_spine_adoption_probe.py` 单文件：**3 failed / 5 passed**——与改动树同位同因（0.21s 即失败，纯基座契约）。

⇒ **4/4 失败全部在基线树复现，Batch-3 A1~A11 零新增失败**。逐项根因：

| 失败 | 根因 | 归属 | 处置 |
|---|---|---|---|
| 3× `TestResumeSpine` | 基座 **T81（D4 P-3）** 将 `resume_spine` 的 `resume_evidence`（`RESUME_EVIDENCE_FIELDS` 三键）升级为 breaking 必填；APS 探针为 T81 前旧形态 | **基座契约演进传导**（跨仓孤立差异） | APS 探针已适配：`_resume_evidence()` 以契约单一事实源 `RESUME_EVIDENCE_FIELDS` 构造三键（禁手抄键名），与 APS `KmdSpine.resume_pending` 的 D4 接线同口径。**8/8 green** |
| 1× `test_server_import` | APS 基线提交 `601a977` 给 `put_particle` 新增 `binding_guard` 参数，测试内存替身签名未跟 ⇒ TypeError 全部落库失败 | **APS 基线既有**（先于 Batch-3） | 替身改 `put_particle(self, ptype, payload, identity_key=None, **kwargs)` 跟随真实签名。**6/6 green** |

### 2.4 最终态

全部 4 项修复后隔离验证 **14/14 green**；终轮全量复跑正在进行（预期 **1762 passed / 0 failed**），实测数以本回函文末补记为准。

## 三、与 10-20 窗口的衔接

`TestResumeSpine` 适配中实证的「resume 必须携带 HITL 证据三件套」与 APS 已完成的 `KmdSpine.resume_pending` 双通道校验（`validate_resume_evidence` + 基座结构保证）同一契约：10-20 接线时归一证据将线程化进 S5 审计载荷（`record_kind=AUDIT_RECORD_KIND`），PENDING 放行与决策审计同链可追——P0-B 收口不变。

---
**补记（终轮全量实测，2026-10-14）**：`1762 passed / 0 failed + 97 subtests`（22m10s，`PYTHONPATH=src <venv> -m pytest tests/ -q --timeout=300`，EXIT=0）。**Batch-3 改动后全量回归零失败，T103 §二.4 催办项收口。**
