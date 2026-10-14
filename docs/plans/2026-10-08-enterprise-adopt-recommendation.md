# chiyu-enterprise 消费方采纳建议书

> 文档性质：本仓（chiyu-foundation，唯一事实源）产出的**消费方专项建议**，供评审后在 `D:\system\chiyu-enterprise` 仓执行。
> 仓边界纪律：本仓**不回写**消费方仓；本建议仅作评审依据，改动须消费方在其仓自改。
> 依据版本：本仓 `docs/plans/2026-10-08-foundation-consumability-design.md`（WS1–WS9）＋
> `docs/plans/2026-10-09-foundation-maturity-blueprint.md`（成熟度蓝图）＋ enterprise 源码实测（2026-10-08）。

---

## 一、结论先行

enterprise 决策模块**不是"脱离 foundation 的平行重写"**，而是**已守 E1 门面纪律、骑上了 foundation 基础设施、唯独没有接 `run_spine` 脊柱、且 `persist=None` 未落库**。因此改造方向是"**收敛到 `run_spine`，而非推倒重来**"。

源码级实证（均在本文档第五节给出落点）：

1. 全仓遵守"只经 `chiyu_kernel.api` 门面"（约 50 个 import 站点），决策编排器实际已骑 foundation 的
   `ApprovalGate`（`control_plane.py:19`）、`EventBus`／`chain_hash`／`verify_chain`（`orchestrator.py:30`）。
2. 唯一的分叉点：自建 `monitor → rubric(九尺子) → gate → ApprovalGate → audit` 领域编排链
   （`orchestrator.py:60`），而未调用 foundation 决策脊柱 `run_spine`。
3. `run_spine`（`chiyu-decision/src/chiyu_decision/spine.py:36`）契约是：消费方**须同时传入**
   `rubric_scores`（九尺子 9 键）＋ `elements`（八要素）＋ `profile` ＋ `redline_items` ＋ `persister` ＋ `approval_gate`；
   foundation 只做"聚合求值 ＋ 红线闸(S4) ＋ 落库"。**逐键评分与八要素提取仍归消费方**。
   ⇒ enterprise 的九尺子评分器（`rubric.py`）**保留**，不是删。

**剩余真缺口（不补则 `run_spine` 无法在生产跑通）**：
- enterprise **没有八要素提取器**（只有九尺子）——`run_spine` S2 要求的 `elements` 只能传 `{}`；
- enterprise **没有 `inject_domain`/`TenantProfile` 接线**——`run_spine` 的 profile 虽允许 None（预览态），但生产路径缺 profile 时调用点 `profile.redline` 解引用即崩，等效于强制（C3 订正：非签名层强制）；
- **`persist=None`**——决策审计链因此不落库（enterprise 自身反馈 #3 根因）。

---

## 二、建议总览（新增 / 删除 / 更新）

| 类别 | 编号 | 落点 | 一句话 |
|---|---|---|---|
| DELETE | D1 | `decision/orchestrator.py:110-145` | 删手动 audit 内存台账（审计不落库的根） |
| DELETE | D2 | `host/control_plane.py:20` | 删 `persist=None` 默认设定 |
| DELETE | D3 | `scenario/loader.py` 自管注册表状态 | delegate 到 foundation `register_scenario` |
| UPDATE | U1 | `host/control_plane.py:18-20` | 接 `inject_domain`＋`PgVectorStorePersister` |
| UPDATE | U2 | `decision/orchestrator.py:60` `run_decision` | 重写为薄适配，改调 `run_spine` |
| UPDATE | U3 | `scenario/loader.py:269` `register_scenario` | delegate foundation 版＋兼容 shim |
| UPDATE | U4 | `decision/rubric.py:28` `DEFAULT_CONFIG` | 阈值/权重从注入 `TenantProfile` 读取 |
| UPDATE | U5 | `web/*.html`＋`mock.js` | §13 零残留：清用户可见内部记号 |
| UPDATE | U6 | `decision/orchestrator.py:186` `render_board` | 从内存台账改查真实读源 |
| ADD | A1 | `decision/elements.py`（新） | 新增八要素提取器 `extract_elements` |
| ADD | A2 | `host/foundation_wiring.py`（新） | 参考集成模块（端到端接线样板） |
| ADD | A3 | `tests/test_enterprise_adopt_ws*.py`（新） | 反假绿探针（真落库/真物化/红线不落正向边） |
| ADD | A4 | `host/control_plane.py`（启动期） | `inject_domain` 接线产 `profile` |

> 说明：enterprise **没有"整文件可删"的冗余**。`rubric`／`monitor`／`kanban`／`sla`／`propagation`／`scheduler`
> 都是有价值的领域零件，**全部保留**。删除集中在"内存 audit 台账 ＋ `persist=None` ＋ 自管注册表"三处。

---

## 三、详细处方

### 三.1 DELETE（删除）

**D1 — 删 `run_decision` 内手动 audit 链（`decision/orchestrator.py:110-145`）**
- 删：`chain_hash` 追加 → 内存 `_records` 台账 → `persist=None` 落库。
- 由：`run_spine`＋`PgVectorStorePersister`＋foundation `audit/chain` 取代。
- 理由：内存 `_records` 正是"审计不落库"的根，删掉它才有真实审计读源。

**D2 — 删 `persist=None` 默认设定（`host/control_plane.py:20`）**
- 由：注入真实 `PgVectorStorePersister` 取代。
- 理由：这是决策审计链不落库（enterprise 自身反馈 #3）的直接根因。

**D3 — `scenario/loader.py` 自管 `_REGISTRY`／`_UNPERSISTED` 状态**
- 由：delegate 到 foundation `register_scenario`（单一事实源，WS5）后不再需要。
- ⚠️ 保留 `register_scenario(name, factory)` 函数名作兼容 shim（见 U3），否则 6+ 调用点全改。

### 三.2 UPDATE（更新）

**U1 — `host/control_plane.py:18-20` 接 `inject_domain`＋persister**
- 改为：
  ```python
  persister = PgVectorStorePersister(store=open_store(profile), profile=profile, event_bus=_bus)
  control_plane = DecisionOrchestrator(..., persist=persister)
  ```
- 前置：**生产路径必须先注入 `profile`**——spine 本身允许 None（`spine.py:63-64` pass），但调用点 `profile.redline` 解引用会崩（C3 订正 2026-10-09：失效点在调用点而非签名层）；当前 control_plane 无 profile，必须先注（见 A4）。

**U2 — `run_decision`（`decision/orchestrator.py:60`）重写为薄适配**
- ① `rubric.rubric_scores(ctx)` 产 9 键 `rubric_scores`；
- ② `elements.extract_elements(ctx)` 产 `elements`（见 A1）；
- ③ 调 `run_spine(..., profile=profile, rubric_scores=, elements=, redline_items=profile.redline,
  persister=persister, approval_gate=_approve)`；
- ④ `publish_decision(event)`。
- 保留 `decision-0` 锚断言（foundation 也要求 `decision_id`）。

**U3 — `register_scenario`（`scenario/loader.py:269`）delegate foundation 版＋shim**
- 改 delegate `chiyu_kernel.scenario.registry.register_scenario`，做 `factory → (key, title, rubric, redline)` 适配，
  重复键 overwrite（`if is_registered: clear_registry(); register_scenario(...)`）。
- ⚠️ foundation 版签名 `(key, *, title, rubric, redline)`、重复即抛（`registry.py:74,91`）；
  enterprise 版 `(name, factory)`＋覆盖。不写 shim 会断裂
  `control.py:543/5327`、`platform_handlers.py:1311/1823`、`scenario/platform_handlers.py:885/1338`、`lifecycle.py:35`。

**U4 — `rubric.py:28` `DEFAULT_CONFIG` 改从注入 `TenantProfile` 读取**
- 阈值/权重/焦点不再硬编码，守蓝图"配置经 `TenantProfile` 注入，内核零领域字面量"。
- 新增 `rubric_scores(ctx, opts) -> Mapping[str, float]`（9 键规范化 0–1）供 `run_spine`。
  **【C2 订正 2026-10-09】**：enterprise 实测 `score_decision` 的 return 块（`rubric.py:258`）
  **本就返回 `"scores"`（9 键完整映射）**，且键名与 `contract/decision.py:39 RUBRIC_KEYS` 完全一致、
  `_SCALE_MAX=4` ≡ `RUBRIC_SCALE_MAX=4` —— 数据侧只需 **reshape 对齐**，非重建；原文"只返 ratio/level、缺口大"表述错误。

**U5 — `web/*.html`＋`mock.js` §13 零残留**
- 移除用户可见的内部记号：`⛔`／`九尺子`／`ApprovalGate`／`run_decision 全链`／`decision-0`／`G0`／`E1` 等。
- **【C4 订正 2026-10-09】**：enterprise 实测这些记号**绝大多数在 JS 注释内**（`// ⛔ …`），
  用户可见面仅 `agents.html:200` 一类错误文案 —— 属**卫生问题**，非规模性违规；按用户可见面优先清理即可。

**U6 — `render_board`（`decision/orchestrator.py:186`）从内存改查真实读源**
- 从内存 `_records` 改为查 store（落库的 `event` 表，或 foundation `GraphStore` WS8 只读派生）。
- 配 D1 删除内存台账后，看板必须有真实读源。

### 三.3 ADD（新增）

**A1 — `decision/elements.py`（新文件）：八要素提取器**
- `extract_elements(ctx) -> Mapping[str, object]`，产 foundation `run_spine` 所需的**八要素**。
- 不补 ⇒ `run_spine` 的 `elements` 只能传 `{}` ⇒ `elements_missing` 全缺，损失八要素闸（只靠九尺子＋红线）。

**A2 — `host/foundation_wiring.py`（新文件）：参考集成模块**
- `inject_domain` 注入 `TenantProfile`（含 rubric 权重＋redline 目录）→ `register_scenario`（foundation 注册表）
  → `run_spine`（注入 persister＋ApprovalGate＋redline_items）→ `PgVectorStorePersister` 落库＋7 谓词物化。
- 价值：端到端样例，让后续 host 不必重蹈平行重写。对应 enterprise 自身反馈 #5。

**A3 — `tests/test_enterprise_adopt_ws*.py`（新文件）：反假绿探针**
- ① 决策真落库（查 `event`／`particle`／`graph_edge` 有行）；
- ② 7 谓词真物化（查 `graph_edge` 7 条 `edge_source='engine'`）；
- ③ 红线命中即 `approval_rejected` 且**不落正向边**。
- 价值：证"真接通"非"表有行即绿"，对应 WS9 参考消费层 canary。

**A4 — `host/control_plane.py`（启动期）`inject_domain` 接线**
- 把 enterprise 的 rubric 权重／红线目录／粒子类型／谓词边整理为 `profile_from_dict` 输入。
- 前置：生产路径须先注入 `profile`（C3 订正：spine 允许 None，失效点在调用点 `profile.redline` 解引用）；当前 control_plane 无任何 profile 注入。

---

## 四、风险与前置依赖（verify 再动，否则回归）

| # | 风险 | 处置 |
|---|---|---|
| 1 | `PgVectorStore.execute()` 返回不可 fetch 的 cursor（enterprise 已知坑：`config_backend.py:13`、`pg_approval_store.py:4`） | `PgVectorStorePersister` 内部若走 `execute` 写可能**只写不读** ⇒ U6 看板读不能裸依赖，须走 enterprise 自有 store 或 WS8 `GraphStore`；删 D1 前必确认读路径可用 |
| 2 | `run_spine` 要求 `profile` | **A4 必须先于 U1/U2 落地**，否则生产 `profile=None` ⇒ 红线/分级失效 |
| 3 | 注册表语义不兼容（foundation 重复即抛，enterprise 覆盖重置） | U3 必须用 shim 保语义，否则测试大规模红 |
| 4 | 八要素缺失 | A1 不补，损失八要素闸，决策质量降级 |
| 5 | 跨仓纪律 | 改动都在 `D:\system\chiyu-enterprise`（独立消费方仓），**本仓 `chiyu-foundation` 不回写**；需授权与范围 |

---

## 五、源码落点速查（全部经 2026-10-08 实测）

| 落点 | 路径 | 关键行 |
|---|---|---|
| 决策编排器 | `D:\system\chiyu-enterprise\packages\enterprise\src\enterprise\decision\orchestrator.py` | `:30` import；`:60` `run_decision`；`:110-145` audit 链；`:186` `render_board` |
| 控制面 | `...\enterprise\host\control_plane.py` | `:12` ApprovalGate/EventBus/ToolRegistry；`:15` 导入；`:18-20` persist=None |
| 九尺子评分 | `...\enterprise\decision\rubric.py` | `:28` DEFAULT_CONFIG；`:258` score_decision |
| 场景注册表 | `...\enterprise\scenario\loader.py` | `:269` register_scenario |
| 反馈文档 | `D:\system\chiyu-enterprise\docs\feedback-to-foundation-2026-10-08.md` | #1/#2/#3/#5 |
| foundation 脊柱 | `D:\system\chiyu-foundation\packages\chiyu-decision\src\chiyu_decision\spine.py` | `:36` run_spine 签名；**【C3 订正 2026-10-09】**`:63-64` 为 `if profile is None: pass`（**允许 None**，预览/测试友好）——真实失效点是调用点 `profile.redline` 解引用抛 `AttributeError`，非"强制要求" |
| foundation 注册表 | `...\chiyu-kernel\src\chiyu_kernel\scenario\registry.py` | `:74,91` 重复即抛 |
| 门面 | `...\chiyu-kernel\src\chiyu_kernel\api.py` | `register_scenario`/`PgVectorStorePersister`/`inject_domain`/`ApprovalGate` 已导出。**【C1 订正 2026-10-09】**：`run_spine` **不在** `chiyu_kernel.api` —— 它在 `chiyu_decision.api:17`（决策包 sanctioned 门面）；依 B1/N2 裁定，sanctioned 面已扩为五面成文（`docs/sanctioned-import-surface.md`），`from chiyu_decision.api import run_spine` 为合法入口 |

---

## 六、执行次序建议

```
P0  §13 预检（U5 扫 web/*.html 内部记号）→ 零残留报告      [零风险、纯观察]
P1  A1 八要素提取器 + A4 inject_domain 接线（U4 读 TenantProfile）  [填真缺口]
P2  U1+U2 接 run_spine + PgVectorStorePersister（D1/D2）      [核心收敛]
P3  U3 注册表 delegate shim（D3）                            [单一事实源]
P4  A2 参考集成 + A3 反假绿探针（接 CI canary）               [证真接通]
```

每阶段完成后：`make test` 全绿 ＋ 反假绿探针（A3）＋ §13 零残留复检，再进入下一阶段。

---

## 七、验收标准

1. **收敛**：`run_decision` 体内不再有 self-contained 的评分/闸/落库逻辑，全部走 `run_spine`；
   源码树对 `run_spine`／`PgVectorStorePersister`／`inject_domain` 有实际调用（非零引用）。
2. **落库**：生产路径 `persist` 非 None；决策事件在 `event`／`particle`／`graph_edge` 三表可查。
3. **物化**：7 条决策↔记忆↔知识谓词在 `graph_edge` 有 `edge_source='engine'` 实例。
4. **红线**：命中红线即 `approval_rejected`，且不落正向决策边。
5. **§13**：`web/*.html` 与后端 docstring 无内部记号残留（按**概念**而非单词扫描）。
6. **回归**：全量测试绿，A3 反假绿探针通过（删判据分支须转红，防假绿）。

---

## 八、待裁定事项

在动手前需明确以下三项（brainstorming HARD-GATE 对该类跨仓/对外改动仍有效）：

1. **授权范围**：是否就核心层（`chiyu-decision`／`chiyu-portal`）对外授权给出确认；
2. **跨仓改动授权**：本建议的执行主体是 `D:\system\chiyu-enterprise` 仓，需你明确可改动范围；
3. **优先级**：先做 P0（零风险纯观察），还是直接进 P1 填真缺口。

---

*本文档由本仓产出，作评审依据；执行与改动的最终决定权与落地动作归属 `chiyu-enterprise` 消费方仓。*
