# foundation 侧落实 APS 回信R2–R14 · 设计方案

> 状态：**✅ 已批准（2026-10-09，用户「同意设计稿」）** → 移交 writing-plans 拆实施任务
> 日期：2026-10-09
> 来源：《APS-回信-致foundation（2026-10-09专项建议）》v2 +《foundation回信-致APS》认领项
> 方法：brainstorming（living contract，契约键注册表 = 本仓 `contract/contract-ids.json`）
> 编排：**方案 A·三批次**（已确认）
> 变更策略：**严格加法 + 弃用标注**（已确认）—— 零既存代码失效
> 范围：**仅 foundation 侧**（已确认，不跨仓写APS）

---

## 0. 背景与目标

APS 回信提出 foundation 侧请求 R1–R14。我方回信已认领 R2 / R4 / R5 / R8–R14共 11 项。
本方案把这 11 项落成可执行、可验证的设计。

**总目标**：让foundation 对三个消费方（foundation 自用 / APS / enterprise）形成
「**能力有出口、契约有守卫、违规不必靠自觉**」的可依赖底座。

**判据总纲**（守蓝图 §3 横切成熟度闸，每任务适用）：
1. **组合回归绿** —— 跑组合命令，不跑单包（本项目多次踩过"单跑绿、组合塌"）；
2. **反假绿探针 + 变异自证** —— 「字段非空 / count>0 / 无报错」恒绿**禁止**作唯一判据；
3. **零领域字面量 grep=0**。

---

## 1. 编排总览（三批次· 风险隔离）

| 批次 | 任务 | 风险 | 隔离理由 |
|---|---|---|---|
| **一** | R8 门面补齐 · R12 机械守卫 · R11 版本出口 | **零** | 纯新增，零行为变更 |
| **二** | R9 驱动解耦 · R13 双形态 DSN · R2 env 注入 | **中** | R9 动连接层，是本批唯一真实行为风险项 |
| **三** | R10 TIER 分族 · R4 experimental 显式化 · R5 docstring 清理 | **低** | 纯加法 + 文档层 |

> **为何分批而非一次全做**：批次二 R9 动连接层（`store/conn.py`）。若与批次一的
> "纯补 `__all__`" 混在一批，回归一旦变红将无法二分归因（是门面改动还是驱动解耦所致）
> —— 这正是本项目反复踩过的归因困境。**分批即归因手段**。

---

## 2. 前置事实（已实测，非推测）

设计所依赖的基线事实，逐条取证如下（**方案成立的前提**）：

| 事实 | 取证 | 对设计的影响 |
|---|---|---|
| R8 四符号均可从内部路径导入 | `store/dsn.py:79/121`、`store/conn.py:124`、`store/pg_store.py:26` | R8 是**纯新增**，零行为变更、零回归风险 |
| `api.__all__` 当前 273 项，确缺 4 符号 | 实测统计；`vec_to_pg`/`pad_to_dim` 在列而 `pg_to_vec` 不在 | "向量往返只有去程"成立 |
| `store/` 四个子模块**均有 `__all__`** | `dsn.py`/`conn.py`/`pg_store.py`/`ddl.py` 各 1 处 | R12 可真正改为**机械推导**，而非人工枚举 |
| `store` 层登记为 `EXEMPT_LAYERS["store"]`，白名单 `STORE_REQUIRED` 仅 9 项 | `tests/test_api_facade_covers_all_layers.py:31-35,49` | R8 的根因：**既未进门面、又不在豁免白名单** = 三不管 |
| `search_path` 保留 `public` 基座**已实现** | `store/conn.py:155` `SET search_path TO {schema}, public` | **R9 瘦身**：三条硬知识第3 条基座已做，APS 是重复实现 |
| `lock_timeout` / 按 `application_name` 摘连接**基座均无** | `conn.py` grep 零命中 | R9 真实缺口**只有 2 条** |
| R9 驱动耦合**仅 4 处** | `conn.py:24/150/162/178` | R9 改动面小于预估 |
| R2 真问题：报错文案硬编码 `DSN_ENV` | `store/dsn.py:88` | R2 修法＝env 键可注入 + 报错引用传入值 |
| `MEMORY_EXPERIMENTAL = True` 已存在 | `api.py:339`，已在 `__all__` | R4 主要是纳入能力清单，非新建 |
| `api.py` 无 `api_version` / capability 出口 | 实测零命中 | R11 确需新建 |
| HEAD 停在 09-27 | `git log` | ⚠️ WS6/WS2 等 10-09 落地能力**已落盘未提交** |

> ⛔ **实施前置**：动手前须先跑一次组合回归取基线。当前 HEAD 与落盘状态不一致
> （大量能力已写入未提交），**不取基线就动手 ⇒ 无法判断回归是否由本次改造引入**。

---

## 3. 批次一 · 门面纯新增（R8 + R12 + R11）

### 3.1 任务 1.1 ── R8 门面补齐 4 个已实现未导出符号

```contract-yaml
- task: "R8 门面补齐 4 个已实现未导出符号"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-capability-audit, ai-context-layering]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "api.__all__ 含 assert_no_hard_delete/validate_dsn/assert_safe_identifier/pg_to_vec，且消费方仅 import chiyu_kernel.api 即可拿到全部 4 个"
```

**契约说明**：本任务由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），必须调用 `ai-capability-audit`、`ai-context-layering` SKILL、读取 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为 4 个符号进入门面 `__all__`，消费方无需触碰内部路径。

**背景**：APS `foundation.py:67-70` 因门面缺口，被迫 import `chiyu_kernel.store.{conn,dsn,ddl,pg_store}` 四个**内部路径** —— 而这违反基座自定的「消费方只许 import `api` 与 `contract`」纪律。**消费方的违规是被门面缺口逼出来的。**

**改动**
1. `api.py` 补 `from chiyu_kernel.store.dsn import validate_dsn, assert_safe_identifier` 与
   `from chiyu_kernel.store.pg_store import assert_no_hard_delete`、
   `from chiyu_kernel.store.conn import pg_to_vec`（补齐往返回程）；
2. `api.__all__` 增 4 项；
3. `STORE_REQUIRED` 同步增 4 项。

**判据（反假绿 + 变异自证）**
- 正向：`test_api_facade_covers_all_layers.py` 绿；消费方仅 `from chiyu_kernel import api` 即可取全4 符号；
- **变异自证**：从 `api.__all__` 删除 `pg_to_vec` ⇒ `test_api_facade_covers_all_layers` 必须转红；
  还原后复绿。**未做变异自证不得判验收**（防恒绿探针）。

**风险**：**零**。纯新增，既有测试不应受影响；若有变化须查明原因，不得顺手改测试。

---

### 3.2 任务 1.2 ── R12 `STORE_REQUIRED` 由人工枚举改为机械推导

```contract-yaml
- task: "R12 门面导出完整性守卫：STORE_REQUIRED 由人工枚举改为机械推导"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "store 层公共符号漏登记即测试转红（非人工枚举），守卫对子模块直连层生效"
```

**契约说明**：本任务由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），必须调用 `ai-capability-audit` SKILL、读取 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为 `store` 层符号漏登记时提交即红，守卫不再依赖人工白名单。

**背景（我方与 APS 对该缺陷的共识）**：APS 判断"无结构性拦截"；**我方实测修正**——已有`test_no_undeclared_layer`（扫磁盘子包，二选一否则红），
但它对「子模块直连 + 人工白名单」的 `store` 层失效。**R12 的正确形态不是新建守卫，
而是把 `STORE_REQUIRED` 从人工枚举改为从 `store/*.py` 的 `__all__` 机械推导。**

**改动**
- `tests/test_api_facade_covers_all_layers.py`：新增推导函数，遍历 `store` 子包全部公共符号
  （非 `_` 开头、已入 `__all__`），与门面导出集比对；差异即红；
- 保留 `STORE_REQUIRED` 作为**显式豁免白名单**（给确不应导出的符号留口子，须写明理由）。

**判据（变异自证）**
- 故意从 `store/dsn.py` 的 `__all__` 删一个公共符号 ⇒ 测试转红；
- 或故意把某符号加入 `STORE_REQUIRED` 但不导出门面 ⇒ 豁免须带理由，否则红。

**⚠️ 已知副作用（诚实标注）**：这是**测试收紧**，可能暴露既有漏项。
若转红项属"真实漏导出"⇒ **修门面，不改测试**；若属"确应豁免"⇒ 登记豁免 + 写明理由。
**禁止为了让测试变绿而放宽判据。**

---

### 3.3 任务 1.3 ── R11 门面暴露版本与能力出口

```contract-yaml
- task: "R11 门面暴露 api_version与 capability manifest"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "api.api_version() 返回版本号且 api.capabilities() 返回能力清单，消费方可用版本断言替代 hasattr 嗅探"
```

**契约说明**：本任务由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），必须调用 `ai-capability-audit` SKILL、读取 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为门面提供版本与能力清单出口，消费方无需符号嗅探。

**背景**：`chiyu_kernel.__version__` 与 `chiyu_decision.__version__` 恒为 `0.1.0`，
且门面无版本出口⇒ APS 只能用 `hasattr` 探针（`kmd.py:679` 的 `aggregate_confidence_exported`）。
符号嗅探无法表达"最低要求版本"，也无法表达"某符号是刻意移除而非从未提供"。

**改动**
- 新建 `chiyu_kernel/version.py`：`API_VERSION` / `CONTRACT_VERSION` / `CAPABILITIES`（元组，含
  `memory.experimental` 等状态位）；
- 门面 re-export `api_version()` / `capabilities()`；
- 与任务 3.2（R4）**合流**：experimental 边界登记进 `CAPABILITIES`。

**判据（变异自证）**：新增能力而未登记 `CAPABILITIES` ⇒ 守卫转红。

---

## 4. 批次二 · store 加法（R9 + R13 + R2）

>⚠️ 本批含**唯一有真实行为风险**的任务（4.1）。严格加法约束下，
> 新参数一律**默认走旧路径**，保证既有调用零影响。

### 4.1 任务 2.1 ── R9 驱动解耦+ 吸收两条硬知识

```contract-yaml
- task: "R9 store 隔离机制驱动解耦（connect_factory 注入）+ 吸收 lock_timeout 与 application_name 精准摘连接"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-ontology-vector-build, ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "注入 connect_factory 后 psycopg3 环境可跑通隔离机制；DROP SCHEMA 前 lock_timeout 兜底生效；摘连接按 application_name+pid 精准命中本进程"
```

**契约说明**：本任务由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），必须调用 `ai-ontology-vector-build`（存储/本体落库纪律）与 `ai-capability-audit` SKILL、读取 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为 psycopg3 可注入驱动、两条硬知识生效。

**背景**：基座 `store/conn.py` 在 `:24/:150/:162/:178` 硬绑 `psycopg2`；APS 裁决书 R1 定psycopg3
⇒ APS 只能自建约 200 行（`foundation.py:337-538`）。三条硬知识本属基座职责，
其中**第 3 条（`search_path` 保留 `public`）基座已实现**（`conn.py:155`），不重复做。

**改动**
1. `connect()` 增 `connect_factory: Optional[Callable[[], Connection]] = None`，
   默认 `None` ⇒ 走既有 psycopg2 路径（**既有调用零影响**）；
2. `drop_test_schema()` 前置 `SET lock_timeout`（参照 APS `foundation.py:428`，取 3s）；
3. 新增按 `application_name`（含 pid 后缀）精准摘除**本进程**连接的函数。

**判据（反假绿，重点）**
- **快速失败判据**：持锁连接下`DROP SCHEMA` 必须在有限时间内抛错，**不得卡死**
  （APS 实测曾卡死 >7 分钟 ⇒ 这是真实踩过的坑，不是假想）；
- **不误伤判据**：并行会话（不同 pid）的连接**不得**被摘除 —— 只按名字扫库会误伤，
  须按 `application_name` + pid 精准命中；
- **变异自证**：把 `lock_timeout` 去掉 ⇒ 判据应在有限时间内转为"卡死/超时失败"（红）。

**⚠️ 已知既有违规**：`tools/check_cython_friendly.py` 长期报 1 条历史既有违规
（`llm/client.py:60` C2-kwargs-dispatch）⇒ **非本批引入**，不计入本批验收失败。

---

### 4.2 任务 2.2 ── R13 `validate_dsn` 接受 keyword/value 双形态

```contract-yaml
- task: "R13 validate_dsn 接受 keyword/value 双形态（免消费方构造含口令中间串）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "validate_dsn 接受 URI 与 keyword/value 两种形态且红线判定一致，消费方无须自行构造转换串"
```

**契约说明**：本任务由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），必须调用 `ai-capability-audit` SKILL、读取 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为双形态入口就绪、红线口径与原函数一致。

**背景**：基座 `validate_dsn`（`store/dsn.py:79`）走 `urlparse`，**只认 URI**；
APS 的 DSN 契约是 keyword/value ⇒ APS 被迫自写 `dsn_to_uri()`（`foundation.py:256-293`），
且该函数**返回串含口令**，docstring 须挂"不得回灌连接、不得写日志"的安全约束。
**一个为绕过形态限制而生的、带安全约束的中间态。**

**改动**：`validate_dsn(..., form: str = "auto")` —— `auto`（默认，保持既有行为）/
`uri` / `kv`；内部走 `psycopg.conninfo.conninfo_to_dict` 解析 kv形态，
**但不构造含口令的 URI 串**（在基座内部直接判定，消除中间态外泄）。

**判据**：同一 DSN 以两形态传入，**红线判定结论必须一致**（对拍断言）；
`FORBIDDEN_HOSTS` 命中行为两形态同样拒绝。

---

### 4.3 任务 2.3 ── R2 env 键名改为可注入

```contract-yaml
- task: "R2 PgVectorStore 第③坑：env 键名改为可注入参数"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-ontology-vector-build]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "env 键名可由调用方传入，报错信息随之变化而非硬编码 CHIYU_DB_DSN"
```

**契约说明**：本任务由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），必须调用 `ai-ontology-vector-build` SKILL、读取 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为 env 键名可注入且报错信息随之变化。

**背景**：D1 三坑的第 ③ 条（`store/dsn.py:19-24` 的 `DSN_ENV`/`SCHEMA_ENV` 等仍是模块级常量）。
实测真问题不只是"取不到值"，而是**报错文案硬编码 `DSN_ENV`**（`dsn.py:88`）
⇒ 消费方传了自定义键名后，报错仍提示 `CHIYU_DB_DSN`，**误导排障**。

**改动**：`get_dsn` / `get_schema` 增可选 `env` 形参；`dsn.py:88` 报错文案引用**传入值**。
**严格加法**：默认值 = 现有常量，既有行为不变。

**判据**：传入自定义 env 键名 ⇒ 报错文案含该键名（不是 `CHIYU_DB_DSN`）。

---

## 5. 批次三 · 命名与披露（R10 + R4 + R5）

### 5.1 任务 3.1 ── R10 `TIER_` 两族加法分族

```contract-yaml
- task: "R10 TIER_ 两族加法分族：新增 VTIER_* 并保留 TIER_* 弃用别名"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "向量降级族以 VTIER_* 为主名且 TIER_* 仍可用（弃用标注），两族不再同名歧义"
```

**契约说明**：本任务由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），必须调用 `ai-capability-audit` SKILL、读取 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为向量族以 `VTIER_*` 为主名、旧名保留可用，歧义消除。

**背景**：两族共用 `TIER_` 前缀、同处 `api` 命名空间、语义毫不相干：
- 向量降级族（`context/retrieval.py:28-33`）：`TIER_FTS_VECTOR`/`TIER_VECTOR`/`TIER_FTS`/`TIER_NONE`/`TIER_ORDER`；
- 自进化风险族（`contract/evolution.py:34`）：`TIER_AUTO`/`TIER_GUARDED`/`TIER_FORBIDDEN`。

⇒ APS 被迫在 `foundation.py:184-187` 写长注释警告"不得简写为 `TIER_*`" ——
**消费方在替基座的命名缺陷打补丁**。

**改动（严格加法，零破坏）**：`context/retrieval.py` 新增 `VTIER_*` 为主名 +
`TIER_*` 保留为别名并标弃用 docstring；`api.__all__` 同增两族。
覆盖面仅 5 个符号，成本可控。

**判据**：两族在 `api` 命名空间内不再同名；旧名仍可导入（不破坏）。

---

### 5.2 任务 3.2 ── R4 memory experimental 边界显式化

```contract-yaml
- task: "R4 显式化 memory 子系统 experimental 边界"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-memory-lifecycle, ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "memory experimental 状态进入 capabilities 清单，消费方可机检而非读注释推断"
```

**契约说明**：本任务由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），必须调用 `ai-memory-lifecycle`、`ai-capability-audit` SKILL、读取 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为 experimental 边界进入能力清单、可机检。

**背景**：`MEMORY_EXPERIMENTAL = True`（`api.py:339`）**已存在且已导出**，
但消费方多靠"读注释/读文档"推断 ⇒ **边界不可机检**。

**改动**：把 experimental 边界登记进任务 1.3 建的 `CAPABILITIES` 清单；
并在对外表述纪律中明确：**凡提及"决策记忆网 / 双轨记忆闭环"必须同时声明
"memory 层 experimental、T5′未验收"**。

**判据**：`capabilities()` 中可查到 `memory` 的 experimental 状态位。

---

### 5.3 任务 3.3 ── R5 门面 docstring 移除内部标记（守 §13 披露纪律）

```contract-yaml
- task: "R5 公开门面 docstring 移除内部标记与违约字样（守 §13 披露纪律）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "chiyu_decision/api.py docstring 无内部标记与违约字样，compileall 后零残留"
```

**契约说明**：本任务由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），必须调用 `ai-capability-audit` SKILL、读取 `chiyu-foundation` 记忆（L1，≤2 跳）；成功标准为门面 docstring 清理干净且重编译后零残留。

**背景**：`chiyu_decision/api.py:4` 等处含内部路径违约字样（"import … 内部路径即违约"）。
公开门面 docstring 会外泄到对外材料 ⇒ 守 §13 类纪律。

**改动**：`chiyu_decision/api.py` docstring 中性化内部标记。

**判据（⚠️ 按项目铁律执行）**
- **必须 `compileall -f` 强制重编译**（docstring 会编入 `.pyc`）；
- 再 `grep -rq` 复核**含 `.pyc`** 零残留。
⚠️ 禁以「`git status` 未列出该文件」为准（大目录只显示 `?? dir/`，易误判）。

---

## 6. 跨批次守卫 · 三消费方影响面断言

```contract-yaml
- task: "跨批次回归：APS 消费方导入面不受破坏"
  contract_task_id: ct-aps-consume
  agent: consumer-integrator
  skills: [ai-capability-audit]
  memory: [APS-ai-native]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "严格加法下 APS 既有导入面零失效，改造后其 import 路径仍可用"
```

**契约说明**：本任务由 `consumer-integrator` 承接（契约键 `ct-aps-consume`），必须调用 `ai-capability-audit` SKILL、读取 `APS-ai-native` 记忆（L1，≤2 跳）；成功标准为严格加法保证 APS 既有导入面零失效。

```contract-yaml
- task: "跨批次回归：enterprise 消费方导入面不受破坏"
  contract_task_id: ct-chiyu-enterprise
  agent: enterprise-platform-builder
  skills: [ai-capability-audit]
  memory: [chiyu-foundation, enterprise-platform]
  knowledge_scope: { layers: [L1], max_hops: 2 }
  success: "enterprise 消费方既有导入面在改造后仍可用，无版本失效"
```

**契约说明**：本任务由 `enterprise-platform-builder` 承接（契约键 `ct-chiyu-enterprise`），必须调用 `ai-capability-audit` SKILL、读取 `chiyu-foundation` 与 `enterprise-platform` 记忆（L1，≤2 跳）；成功标准为企业侧导入面零失效。

> ⚠️ **跨仓只读**：本仓**不得**向 `APS-ai-native` / `chiyu-enterprise` 任何路径写入产物。
> 上述断言**只验证foundation 侧导出面**，不修改消费方代码；验证方式为
> "以 foundation 改造后的门面模拟消费方 import 语句可成功"。

---

## 7. 验收与提交纪律

**每批次三件套（缺一不可）**
1. 组合回归绿（`pytest packages/chiyu-kernel/tests tools/tests packages/chiyu-decision/... -q`，
   **不跑单包**）；
2. 反假绿探针绿 + **变异自证**（故意删判据分支 ⇒ 必须转红 ⇒ 还原）；
3. 零领域字面量 `grep` = 0。

**⛔ 边界纪律**
- 本轮**不改 `contract/*.py`** ⇒ 不触发 `contract/manifest.json` 重生成；
- 只用显式路径 `git add`，禁 `git add -A`；
- 分层提交，单行 `-m`，前缀 `T<n>:`，尾部附实测计数；
- 零 remote。

**⚠️ 本机约束**
- **无 `make`** ⇒ 验证 Makefile 目标须直接实跑其命令行；
- 解释器：`C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe`。

---

## 8. 风险登记

| 风险 | 批次 | 缓解 |
|---|---|---|
| **HEAD 落后于落盘**（10-09 能力已写未提交） | 全部 | ⛔ 动手前先取组合回归基线，否则无法归因回归来源 |
| R12 机械推导暴露既有漏项 ⇒ 测试转红 | 一 | 属"暴露真实缺陷"，**修门面不放宽判据** |
| R9 连接层回归（卡死/误伤并行会话） | 二 | 独立成批 + 快速失败判据 + 不误伤判据 |
| R13 kv 解析口径与 APS 自写转换不一致 | 二 | 双形态**对拍断言**同一 DSN 判定一致 |
| `connect_factory` 注入路径未被真实验证 | 二 | 须实跑 psycopg3 环境，**不得只加参数不验证** |
| R5 清理后 `.pyc` 残留 | 三 | `compileall -f` + `grep -rq` 含 `.pyc` |

---

## 9. 契约自检（P7 执行记录）

- 校验命令：
  `node C:/Users/wangchuan08/.workbuddy/skills/brainstorming/scripts/validate-contract.mjs <doc.md> --registry contract/contract-ids.json`
- ⛔ **必须用 `C:/` 绝对路径**：`~` 在 Git Bash 下展开为 `/c/Users/...`，
  node 按当前盘符解析成 `D:\c\Users\...` ⇒ `MODULE_NOT_FOUND`；
  `/tmp/*.md` 同理报 `doc not found`（文档与注册表两侧都要绝对路径）。
- ⛔ **契约块 YAML 只支持行内值**：`knowledge_scope` 必须写 `{ layers: [L1], max_hops: 2 }` 一行；
  写成多行会被解析成 `{}` 并**静默通过结构检查**（membership 失效）。
- ⛔ **反向覆盖铁律**：本文覆盖 3 个已登记 agent（`foundation-builder` /
  `consumer-integrator` / `enterprise-platform-builder`）⇒ **必须全部覆盖**，缺一方即自检失败。
- ⛔ **判别力自证**：交付前投一个故意写错的块（错契约键 / 越界 memory / 越界 layer），
  校验器须**逐条检出并退出 1** —— 否则可能空跑。

---

## 10. 闭环回写

| task | agent | gap_type | observed | expected | ts | severity |
|---|---|---|---|---|---|---|
| （待运行后填） | | | | | | |

> workbench 监控 → 写`<doc>.feedback.json` → 下一轮 P0 吸收。
> 同`(task, gap_type)` 复现 ≥2 次 ⇒ 提出 SKILL 改进建议（**仅建议，需用户批准**）。