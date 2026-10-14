# foundation sanctioned import 面（消费方合法 import 边界）

> 状态：**已生效**（2026-10-09，B1 + N2 落地；由 `tools/check_import_surface.py` 机械守卫，接 `make lint`）
> 来源：enterprise 反馈 B1（`run_spine` 未进可见面）/ N2（sanctioned 面未成文）/ N5（contract 常量过门面）
> 适用对象：所有消费方（CRM-ai-native / APS-ai-native / chiyu-enterprise）**与 foundation 自身**（E1 双向）

---

## 1. 为什么要有这份文档

此前"消费方只许 import `chiyu_kernel.api` 与 `chiyu_kernel.contract`"是一条**写在 docstring 里的纪律**，
但存在三个结构性空洞：

1. `chiyu_decision.api`（决策脊柱面，含 `run_spine`）**不在**被允许清单里 ⇒
   消费方"想合规就用不到脊柱"（enterprise B1 实测：`from chiyu_kernel.api import run_spine` 零命中）；
2. `chiyu_kernel.approval`（决策审批闸）、`chiyu_portal.api`（门户面）同样是正式能力却无成文出口；
3. 纪律**无门禁** ⇒ 违规不报错，只能靠自觉（APS 因此被迫 import `chiyu_kernel.store.{conn,dsn,ddl,pg_store}` 四个内部路径）。

⇒ 本文把"允许清单"从 docstring 提升为**成文契约 + 可执行门禁**。

---

## 2. sanctioned 面（唯一事实源）

| 面 | 模块 | 承载 |
|---|---|---|
| 基础内核面 | `chiyu_kernel.api` | store / vector / ontology / context / domain / persist / graph / mcpserver / orchestration … 全部门面导出 |
| L0 契约面 | `chiyu_kernel.contract`（含其子模块，如 `chiyu_kernel.contract.decision`） | `TenantProfile` / `EIGHT_ELEMENTS` / **`EIGHT_ELEMENTS_ZH`**（八要素中文名，R25 display_name 用）/ `RUBRIC_KEYS` / `SPINE_ORDER` / `AUTONOMOUS_RELEASE_DEFAULT` / `MEMORY_PREDICATES` / `CORE_ROLES` |
| 决策审批闸面 | `chiyu_kernel.approval` | `DecisionApprovalVerdict`（三态）/ `RedlinePriorityGate` / `DecisionPassThroughGate` |
| 决策脊柱面 | `chiyu_decision.api` | **`run_spine`** / `SpineResult` / `SPINE_ORDER` / `score_rubric` / `evaluate_redline` / `aggregate_confidence` / `autonomous_release` |
| 门户面 | `chiyu_portal.api`（若授权） | 门户渲染与页面存储 |

**规则**

- 允许：`chiyu_kernel.contract.decision` 这类**子模块**导入（父面 sanctioned 即其子树合法）。
- 禁止：`chiyu_kernel.store.pg_store`、`chiyu_kernel.vector.infer`、`chiyu_kernel.llm.client` 等
  **不在上表**的内部路径。
- ⛔ **`from chiyu_kernel.api import run_spine` 不可用，这是刻意设计**：`chiyu-decision` 是独立
  分发包（L2 授权层），kernel（L0/L1）**不得反向依赖** decision。决策能力请走
  `from chiyu_decision.api import run_spine`（与 `chiyu_kernel.contract` 直连纪律同构）。

---

## 3. 门禁脚本与判定口径

```bash
python tools/check_import_surface.py            # 全仓扫描，违规即 exit 1
python tools/check_import_surface.py --verbose  # 打印已扫描文件数与豁免项
```

判定口径（**机械，无人工白名单**）：

1. **扫描范围** = `packages/{chiyu-kernel,chiyu-decision,chiyu-portal}/src` + `examples/`；
2. **同分发内导入允许**：`chiyu_kernel.*` 内部模块互相 import 属实现细节，不受本门禁约束
   （门禁只管**跨分发**的消费关系）；
3. **跨分发导入**必须命中 §2 表格中的 sanctioned 前缀（相等或为其子树）；
4. **`tests/` 目录豁免**：白盒测试需直连被测内部实现，豁免**且理由记入脚本**（不得静默）；
5. **`packages/chiyu-host` 豁免**：该包已于 2026-09-26 标记弃用并并入 `chiyu-enterprise`，
   其遗留内部 import 随弃用下线；⛔ **不得新增**依赖该包的跨面导入。

> ⛔ 第 4/5 条是**显式豁免**，脚本输出会打印豁免项与命中数 —— 静默豁免即假绿，故豁免必须在输出中可见。

---

## 4. `run_spine` 可见化（B1 的落点）

`chiyu_kernel.api` 顶部已加转发注释（只注释、**不 import**，守分层铁律），
`chiyu_decision.api` 列为 sanctioned 面之一。消费方路径：

```python
from chiyu_kernel.api import TenantProfile, PgVectorStore        # 基础面
from chiyu_kernel.contract.decision import EIGHT_ELEMENTS, RUBRIC_KEYS   # 契约面
from chiyu_kernel.approval import RedlinePriorityGate            # 闸面
from chiyu_decision.api import run_spine, SpineResult            # 脊柱面（⛔ 不是 chiyu_kernel.api）
```

守卫测试：`packages/chiyu-kernel/tests/test_sanctioned_import_surface.py`
（断言上表 5 个面可 import、`run_spine` 从 `chiyu_decision.api` 可达、`chiyu_kernel.api` 确无 `run_spine`）。

---

## 5. 与既有纪律的关系

- 本面是 `tests/test_app_imports_contract_only.py`（门面纪律）的**成文 superset**：那份测试守"消费方
  不摸内部路径"，本文守"哪些面算正式出口"。
- `tools/check_facade_coverage.py` 守**门面覆盖度**（能力是否漏出）；
  `tools/check_import_surface.py` 守**导入方向**（是否摸了非 sanctioned 路径）。两者互补，不可互相替代。

---

## 6. 易冲突名清单（N1，2026-10-09）

> 来源：enterprise / APS 在落地 L0/L1 时实测到——`Particle` / `normalize` / `canonical` / `LAYERS` / `ATTR_TYPES`
> 等符号与消费方**自有对象同名异义**，被迫放弃扁平导入（Python 静默覆盖、不报错）。
> 此为**成文清单 + 机械提示**：门禁对 `from <sanctioned> import <易冲突名>` 的扁平导入给出**警告级提示**
> （**不阻断**，sanctioned 违规才是阻断），并建议改命名空间引用。单一事实源在门禁 `CONFLICTING_NAMES`，
> 本文为其可读镜像。

**使用判据**：若你 import 后这些名被自有对象覆盖（`hasattr` 结果非预期）、或 IDE 无声遮蔽，
请改 **命名空间引用**（`import chiyu_kernel.api as api; api.<name>`）或**显式改名**
（`from ... import X as own_X`），不要依赖"恰好没撞名"。

| 易冲突名 | 撞名风险 | 建议用法 |
|---|---|---|
| `Particle` | 与消费方领域 `Particle` 实体同名异义 | `import chiyu_kernel.api as api` 后经 `api.Particle` 引用 |
| `normalize` | 泛用名，消费方 own normalize 常见 | `api.normalize` 或 `from chiyu_kernel.contract import normalize as kernel_normalize` |
| `canonical` | 泛用名，遮蔽消费方 own canonical 逻辑 | 经 `api.canonical` 引用 |
| `LAYERS` | 与消费方「分层」配置同名 | 显式改名或经命名空间引用 |
| `ATTR_TYPES` | 与消费方 own 属性类型定义撞名 | 显式改名 |
| `vector_available` | 向量可用性标志（前缀已降低撞名率，仍提示） | 经 `api.vector_available` 引用 |
| `get_schema` / `get_dsn` / `mask_dsn` | 易与消费方 own 配置读取/掩码工具撞名 | 显式改名（如 `from ... import get_dsn as kernel_get_dsn`） |
| `register_scenario` | ⛔ **跨仓同名异义（H1，enterprise 2026-10-09）**：enterprise `scenario/loader.py` 有同名函数 `(name, factory)`（登记场景包构造器），本门面为 `(key, *, title, ...)`（登记决策场景 profile），签名互不兼容；已致消费方排查误判一次 | `import chiyu_kernel.api as api` 后经 `api.register_scenario(...)`，或 `from chiyu_kernel.scenario.registry import register_scenario` 全限定引用 |

> ⛔ 本清单非空是门禁判别力前提（`test_conflicting_names_table_is_nonempty` 判红）；新增易冲突名须同时登记
> 门禁 `CONFLICTING_NAMES` 与本文，缺一即两处不同源。
