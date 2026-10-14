# P2b `chiyu-portal` 免代码门户 · 详细设计 + 实施计划

> 依据：概念设计 §5（免代码扩展）+ §10 块 3（`chiyu-portal` 三段式契约）+ `ai-portal-page-generation` 方法论（v0.1 MVP 六文件）。
> 本仓约定：Python 包 `packages/chiyu-portal/`（src-layout，模块 `chiyu_portal`），与 `chiyu-decision` 同构、同解释器纪律。
> 触发：用户 2026-09-22「按照这个概要设计，进行详细设计，并开始开发」——已显式授权详细设计 + 开发，跳过独立评审闸，Inline 执行。

## §0 纪律（不可推翻）

- **C-P1 三段式不可短路**：NL → 受控 Schema → 运行时渲染器。渲染器是**唯一**渲染出口、Schema 是**唯一**输入；NL 层（`nl_parser`）**绝不产出 HTML**（守卫 + 测试双重锁死）。
- **C-P2 受控渲染**：`render_page` 渲染前**再校验** Schema（非法即拒、返回字段级错误，绝不尽力渲染）；所有动态值 `html.escape`；交互仅 `data-action` 声明式（无 `onclick`/内联 JS）；输出强制不含 `<script>` / `on*=`。
- **C-P3 粒子/动作受控**：`particleType` 必须 ∈ 注入的 `ParticleTypeSet`（消费方 L4 注入，框架零硬编码）；`action` 必须 ∈ 白名单；**状态字段仅 `eq` 不聚合、快照字段仅 `latest`**（注入式校验，旧粒子直接拒绝，非静默映射）。
- **零领域字面量**：协议常量只声明**形态**（页面/组件类型、算子、聚合函数），不写业务对象名；粒子类型/动作经注入。
- **披露纪律 §13.2**：包源码与渲染产物不得含 `专利|[A-H] ?件|实施例|权 ?[0-9]|7[×xX*]7` 等禁用字样（test_disclosure 扫描锁死）。
- **解释器纪律**：测试严格用 hermes venv；pytest 经 pyproject `pythonpath=["../../chiyu-kernel/src","src"]` 双路径覆盖（禁用 `-o pythonpath`）。
- **提交纪律**：分层提交、单行 `-m`、显式 `git add <paths>`（禁用 `git add -A`）。

## §1 任务拆分（与 P2a 同构，T1–T5）

### T1 包骨架 + Schema 协议常量 + 校验器
- `pyproject.toml`（hatchling，packages=src/chiyu_portal，pytest pythonpath 双路径）
- `src/chiyu_portal/__init__.py`（重导出门面）
- `src/chiyu_portal/schema.py`：
  - 协议常量：`PAGE_TYPES`(6: dashboard/table/form/detail/workspace/approval)、`COMPONENT_KINDS`(10)、`THEMES`(light/dark)、`FILTER_OPS`(7)、`AGG_FUNCS`(6: count/sum/avg/min/max/latest)、`DEFAULT_ALLOWED_ACTIONS`(框架级 4 个：`data-particle-read`/`data-particle-write`/`page-reload`/`aiattr-generate`)、`SCHEMA_VERSION="0.2"`
  - `ValidationError(path, message)`（字段级定位）
  - `validate_page_schema(schema, *, particle_types: ParticleTypeSet, allowed_actions=None, status_fields=(), snapshot_fields=()) -> tuple[ValidationError,...]`
    - 校验 `version`/`type`/`layout.theme`/`components[].kind`/`actions[].action`(白名单)
    - 递归 `_validate_binding`：`source` 仅 `particle`；`particleType` ∈ `particle_types.names`；`filters[].op` ∈ `FILTER_OPS` 且状态字段仅 `eq`；`metrics[].agg` ∈ `AGG_FUNCS` 且状态字段不可聚合、快照字段仅 `latest`
- `tests/test_schema.py`（TDD 先红后绿，**≥9 passed**）：合法通过；未知粒子/页面类型/组件类型/动作/算子/聚合→各拒；状态字段非 eq、状态聚合、快照非 latest→各拒。
- 提交 `T1: ...`

### T2 输入层护栏
- `src/chiyu_portal/guardrails.py`：`GuardResult(ok, reason)`、`guard_nl_input(text)`——拦截 `<script`/`javascript:`/`<iframe`/`on\w+=`/`eval(`/`<object`/`<embed`（正则，IGNORECASE）。纵深防御第一层。
- `tests/test_guardrails.py`（**≥5 passed**）：干净→ok；各注入模式→拒。
- 提交 `T2: ...`

### T3 NL 解析层（绝不直出 HTML）
- `src/chiyu_portal/nl_parser.py`：`ParseResult(schema, confidence, needs_clarification, notes)`、`parse_nl_to_schema(text, *, entity_map=None, title=None)`
  - 确定性映射：意图词→`type`（看板/dashboard→dashboard，表→table，表单→form，详情→detail，工作台→workspace，审批→approval，缺省 dashboard）
  - 实体→粒子经注入 `entity_map`；未命中→`confidence=0.3` + `needs_clarification=True` + 无 `particleType`
  - 阈值高亮：`低于|小于|少于 X%`→`op=lt,value=X/100,color=red`；`高于|超过|大于|多于 X%`→`op=gt`
  - 产出结构化 Schema（**绝不 HTML**）
- `tests/test_nl_parser.py`（**≥5 passed**）：type 映射；未知实体→needsClarification+低置信+无 particleType；已知实体→particleType 落位；阈值高亮；**断言产物不含 `<html`/`<script`/`onclick` 等任何 HTML 标记**（锁死 C-P1）。
- 提交 `T3: ...`

### T4 渲染层（唯一出口）
- `src/chiyu_portal/renderer.py`：`RenderResult(ok, html, errors)`、`render_page(schema, *, particle_types, allowed_actions=None, status_fields=(), snapshot_fields=())`
  - 先 `validate_page_schema` → 非法即 `RenderResult(False, errors=...)`（返回字段级错误）
  - 合法→拼 HTML：`<title>`/`component-title`/`metric`/`action-btn` 全部 `html.escape`；交互仅 `<button data-action="...">`（无 onclick/内联 JS）
  - 渲染后硬闸门：正则拒 `<script`/`on\w+=`，命中即 `RenderResult(False)`
- `tests/test_renderer.py`（**≥6 passed**）：合法→ok 且 HTML 含转义标题、含 `data-action`、无 `<script`、无 `on*=`<；非法 Schema（未知粒子）→拒+字段级错误；`<` 注入标题被 escape；action 仅声明式。
- 提交 `T4: ...`

### T5 生命周期 + 门面 + 全量回归 + §10 块3 自证
- `src/chiyu_portal/page_store.py`：`PageDraft`/`CreateResult`/`PageStore`（内存存储，无 PG 全绿）
  - `create_page_from_nl(text, *, particle_types, entity_map=None, ...)` → `guard_nl_input`→`parse_nl_to_schema`→`validate_page_schema`→存 draft
  - `publish_page(draft_id)`、`render(draft_id, **kw)`
- `src/chiyu_portal/api.py`：唯一公开门面，重导出全部公共符号
- `tests/test_page_store.py`（**≥5 passed**）：合法创建→draft+置信；注入→guard 拒；未知实体→校验错无 draft；发布；渲染 ok
- `tests/test_disclosure.py`（**≥2 passed**）：扫描 `chiyu_portal/**/*.py` 对 §13.2 禁词零命中；且断言 `nl_parser`/`guardrails`/`schema` 三模块**无 HTML 标记产出**（无绕过 Schema 的直出路径）
- 全量：`pytest packages/chiyu-portal/src/chiyu_portal/tests` 全绿
- 内核回归：`pytest packages/chiyu-kernel/tests tools/tests` 266 passed 不受影响
- §10 块3 自证 4 条：① 非法 Schema 被渲染器拒+字段级错误 ✅（test_renderer）；② 仓内无 LLM 直出 HTML 路径 ✅（test_disclosure）；③ 数据源=particle（非静态假数据）✅（schema 校验 `source` 仅 particle）；④ §13 零残留 ✅（test_disclosure）
- 提交 `T5: ...`
- 收口：回写概念设计 §5/§8 的「chiyu-portal 未建」→「已抽取」

## §2 Self-Review（执行前自检）
- [x] 三段式铁律未被破坏（NL 绝不直出 HTML，Schema 唯一输入，renderer 唯一出口）
- [x] 粒子类型/动作受控（注入式，框架零硬编码）
- [x] 三层护栏齐备（输入 guard / 结构 validate / 渲染 render 再校验）
- [x] 4 粒子护栏（particleType 值域 / 状态仅 eq / 快照仅 latest / 动作白名单）
- [x] 零领域字面量（协议常量只声明形态）
- [x] §13.2 披露零残留（扫描锁死）
- [x] 无 PG 依赖（内存 store，全绿）
- [x] 解释器/提交纪律与 P2a 一致

## §3 执行后动作
- 回写 `docs/2026-09-21-决策智能平台概念设计.md` §5/§8：`chiyu-portal 未建` → `✅ 已于 2026-09-22 抽为 packages/chiyu-portal/`，附实测计数与 §10 块3 自证结论。
- 更新 `.workbuddy/memory/2026-09-22.md` 实施记录。
