# Deepseek Harness 移植 · 阶段二实施计划（skill / subagent / plan·todo）

- 日期：2026-09-25
- 状态：待执行（设计文档 `2026-09-25-deepseek-harness-python-port-design.md` §4「阶段二」已批准范围；本文件为详细实施计划）
- 形态：能力吸收式（思路 B）——忠实重写 dsh 的 skill / subagent / plan·todo 能力为 Python，复用阶段一已落地的 `AgentLoop` / `LiveAgentRegistry` / `ToolRegistry` / `SessionManager` / `build_provider`，不新建平行框架
- 契约键：`ct-chiyu-foundation`（agent `foundation-builder`），`knowledge_scope` 限 L1/L2

## 0. 锚定（dsh 真实源码形状，避免凭空发明）

- **skill** `packages/skill/skill/src/index.ts`：`SkillDefinition{name(kebab),description,whenToUse?,invocation{modelInvocable,userInvocable},source,provider,content(markdown),metadata?}`；`isSkillName` 用 kebab-case 正则 `^[a-z0-9]+(?:-[a-z0-9]+)*$`；`SkillRegistry` 负责 register（runtime 贡献）+ get（按名解析胜出）+ list（摘要）。
- **subagent** `packages/subagent/subagent/src/`：核心为 `descriptor`（name/role/instruction/tools/model）+ 委派运行一个子 agent 到完成并返回结果。dsh 的 out-of-process/ACP/continuation 部分过重，吸收为「内存内委派：构造子 agent → 经 `AgentLoop` 跑一轮 → 返回结果」。
- **todo** `packages/todo/tool-todo/src/types.ts`：`TodoItem[]`，整值替换语义（每次 `todo/write` 携带完整列表，fold 为 last-wins）。
- **plan** `packages/plan/plan-mode/src/types.ts`：`PlanProjection{active,pending}`——计划协作态，`plan/mode` 事件驱动。

## 1. 架构映射（阶段二）

| dsh 能力 | 本仓落地 | 新增/复用 | 门面登记 |
|---|---|---|---|
| `skill` | `chiyu_kernel/skills/` 子包：`SkillSpec` / `SkillRegistry` / `is_skill_name` / `load_catalog` | 新增子包 | `LAYERS` += `"skills"` |
| `subagent` | `chiyu_kernel/orchestration/subagent.py`：`SubagentDescriptor` / `SubagentPool.delegate` | 新增文件，复用 `AgentLoop` | orchestration 已覆盖，仅补 `__init__`/`api` |
| `todo` | `chiyu_kernel/plan/` 子包：`TodoItem` / `TodoList`（整值替换） | 新增子包 | `LAYERS` += `"plan"` |
| `plan` | `chiyu_kernel/plan/` 子包：`PlanStep` / `Plan` / `PlanMode`（active/pending） | 新增子包 | `LAYERS` += `"plan"` |

## 2. 任务（TDD：先写失败测试 → 跑红 → 实现 → 跑绿 → 门面守卫 → 提交）

### Task 1 — `chiyu_kernel/skills/` 技能注册表

**测试** `packages/chiyu-kernel/tests/test_skills.py`：
- `is_skill_name`：`"foo-bar"` 真、`"Foo_Bar"`/`"a b"` 假。
- `SkillRegistry.register` 后 `get` 返回同名 `SkillSpec`；`list()` 返回全部摘要。
- `load_catalog({"summarizer": {"description":..., "content":...}})` 批量注册；`get` 可解析。
- 重复名 register：低 rank 胜出（faithful to dsh rank 胜出），或显式抛 `SkillConflict`？→ 采用 dsh 语义：**后注册同名 skill 若 rank 更低则胜出**，否则保留前者；测试覆盖「同名同 rank 抛 `SkillConflict`」。

**实现** `packages/chiyu-kernel/src/chiyu_kernel/skills/__init__.py`：
```python
@dataclass(frozen=True)
class SkillSpec:
    name: str
    description: str
    content: str = ""
    when_to_use: str = ""
    model_invocable: bool = True
    user_invocable: bool = True
    source: str = "runtime"
    provider: str = "runtime"
    rank: int = 250
    metadata: Mapping[str, Any] = field(default_factory=dict)

class SkillConflict(ValueError): ...

def is_skill_name(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name))

class SkillRegistry:
    def __init__(self): self._by_name: dict[str, SkillSpec] = {}
    def register(self, spec: SkillSpec) -> None:   # rank 更低胜出；同名同 rank → SkillConflict
        if spec.name in self._by_name and self._by_name[spec.name].rank <= spec.rank:
            if self._by_name[spec.name].rank == spec.rank:
                raise SkillConflict(spec.name)
            return  # 现有胜出
        self._by_name[spec.name] = spec
    def get(self, name: str) -> SkillSpec: ...   # 缺失 → KeyError
    def list(self) -> list[SkillSpec]: ...
    def summaries(self) -> list[dict]: ...

def load_catalog(catalog: Mapping[str, Mapping[str, Any]]) -> SkillRegistry:
    reg = SkillRegistry()
    for name, body in catalog.items():
        reg.register(SkillSpec(name=name, **{k: body[k] for k in (...)}))
    return reg
__all__ = ["SkillSpec","SkillRegistry","SkillConflict","is_skill_name","load_catalog"]
```

**门面**：`api.py` 加 `from chiyu_kernel.skills import (...)` + `__all__` 增 5 项；`LAYERS += "skills"`。

### Task 2 — `chiyu_kernel/orchestration/subagent.py` 子智能体委派

**测试** `packages/chiyu-kernel/tests/test_subagent.py`：
- `SubagentPool.delegate("调研子任务", subagent_key="researcher")` 经 `AgentLoop` 跑一轮，返回 `{"ok": True, "messages": [...], "content": "..."}`。
- 子 agent 的 `tools_scope` 生效：委派内调用的工具受作用域约束。
- 未知 `subagent_key` → `KeyError`。

**实现** `packages/chiyu-kernel/src/chiyu_kernel/orchestration/subagent.py`：
```python
@dataclass
class SubagentDescriptor:
    key: str
    role: str
    instruction: str
    tools_scope: str = ""
    tier: str = "default"
    pre_step: Optional[Callable] = None

class SubagentPool:
    def __init__(self, *, llm, tools, sessions, redline_guard=None):
        self._llm=llm; self._tools=tools; self._sessions=sessions; self._rg=redline_guard
        self._descs: dict[str, SubagentDescriptor] = {}
        self._live = LiveAgentRegistry()
    def register(self, desc: SubagentDescriptor) -> None:
        self._descs[desc.key] = desc
        self._live.register(Agent(key="sub:"+desc.key, system_prompt=desc.instruction,
                                  tools_scope=desc.tools_scope, pre_step=desc.pre_step))
    def delegate(self, task: str, *, subagent_key: str, session_key: str | None = None) -> Mapping[str, Any]:
        if subagent_key not in self._descs: raise KeyError(subagent_key)
        loop = AgentLoop(llm=self._llm, tools=self._tools, sessions=self._sessions,
                         live_agents=self._live, redline_guard=self._rg)
        return loop.run_turn("sub:"+subagent_key, task)
__all__ = ["SubagentDescriptor","SubagentPool"]
```
**门面**：`orchestration/__init__.py` 增 `from .subagent import SubagentDescriptor, SubagentPool` + `__all__`；`api.py` orchestration runtime 块增 import + `__all__` 增 2 项。

### Task 3 — `chiyu_kernel/plan/`（todo + plan 数据模型）

**测试** `packages/chiyu-kernel/tests/test_plan_todo.py`：
- `TodoList.write([TodoItem(content="x"), ...])` 整值替换；`items` 返回完整列表；状态默认 `pending`；`mark(content, status)` 改状态；`render()` 返回投影。
- `PlanStep(content)` 状态机 `pending→in_progress→done/failed`；非法转移抛 `PlanStateError`。
- `Plan(steps=[...])` + `PlanMode`：`enter()` 置 `active=True`；`exit()` 置 `active=False`；`projection()` 返回 `{active, pending}`（faithful to dsh `PlanProjection`）。

**实现** `packages/chiyu-kernel/src/chiyu_kernel/plan/__init__.py`：
```python
TODO_STATES = ("pending","in_progress","completed","cancelled")
@dataclass
class TodoItem:
    content: str
    status: str = "pending"
    active_form: str = ""
    def __post_init__(self): assert self.status in TODO_STATES

class TodoList:
    def __init__(self): self._items: list[TodoItem] = []
    def write(self, items: list[TodoItem]) -> None:   # 整值替换（last-wins）
        self._items = [TodoItem(c.content, c.status, c.active_form) for c in items]
    def mark(self, content: str, status: str) -> None: ...
    @property
    def items(self) -> list[TodoItem]: ...
    def render(self) -> list[dict]: ...

PLAN_STEP_STATES = ("pending","in_progress","done","failed")
ALLOWED_STEP = {("pending","in_progress"),("in_progress","done"),("in_progress","failed"),("done","pending")}
class PlanStateError(ValueError): ...
@dataclass
class PlanStep:
    content: str; status: str = "pending"
    def transition(self, to: str) -> None:  # 越权 → PlanStateError
        if (self.status,to) not in ALLOWED_STEP: raise PlanStateError(...)
        self.status = to
class Plan:
    def __init__(self, steps=None): self.steps=[PlanStep(s.content,s.status) for s in (steps or [])]
    def projection(self) -> dict: return {"active": self._mode_active, "pending": self._mode_pending, "steps":[...]}
class PlanMode:   # {active,pending} 协作态（faithful）
    def __init__(self): self.active=False; self.pending=False
    def enter(self): self.active=True
    def exit(self): self.active=False; self.pending=False
__all__ = ["TodoItem","TodoList","PlanStep","Plan","PlanMode","PlanStateError","TODO_STATES","PLAN_STEP_STATES"]
```
**门面**：`api.py` 加 `from chiyu_kernel.plan import (...)` + `__all__` 增 8 项；`LAYERS += "plan"`。

### Task 4 — 阶段二 E2E 冒烟

**测试** `packages/chiyu-kernel/tests/test_harness_phase2_e2e.py`（复用阶段一 conftest 跨包插入）：
- 构造 `SkillRegistry` + `SubagentPool` + `TodoList`/`Plan`；
- 父 agent 委派子 agent 完成「调研」任务（子 agent 通过 `native-context-assemble` 工具调本仓能力），子 agent 用 `TodoList.write` 记录进度，`PlanMode.enter` 置态；
- 经 `render_conversation` 渲染，断言 HTML 含对话内容 + goal-bar。

**门面守卫**：每步均带 `test_api_facade_covers_all_layers.py` 运行；`manifest.json` 未动（contract/ 未改）。

## 3. 提交纪律（AI 不 commit；按 Task 显式 add 单文件）

```bash
# T1
git add packages/chiyu-kernel/src/chiyu_kernel/skills/__init__.py packages/chiyu-kernel/tests/test_skills.py packages/chiyu-kernel/src/chiyu_kernel/api.py packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py
git commit -m "feat(harness): skill 技能注册表（dsh skill 能力吸收）"
# T2
git add packages/chiyu-kernel/src/chiyu_kernel/orchestration/subagent.py packages/chiyu-kernel/src/chiyu_kernel/orchestration/__init__.py packages/chiyu-kernel/src/chiyu_kernel/api.py packages/chiyu-kernel/tests/test_subagent.py
git commit -m "feat(harness): subagent 子智能体委派（复用 AgentLoop）"
# T3
git add packages/chiyu-kernel/src/chiyu_kernel/plan/__init__.py packages/chiyu-kernel/src/chiyu_kernel/api.py packages/chiyu-kernel/tests/test_plan_todo.py packages/chiyu-kernel/tests/test_api_facade_covers_all_layers.py
git commit -m "feat(harness): plan/todo 数据模型（dsh plan/todo 能力吸收）"
# T4
git add packages/chiyu-kernel/tests/test_harness_phase2_e2e.py
git commit -m "test(harness): 阶段二 E2E 冒烟（skill→subagent→plan/todo→渲染）"
```

## 4. 风险与判别力

- **R2 重复框架**：已规避——`SubagentPool` 复用阶段一 `AgentLoop`，不新建 driver。
- **门面静默未接线（同阶段一陷阱）**：每个新子包（`skills`/`plan`）必加 `LAYERS`，否则 `test_no_undeclared_layer` 红；`subagent` 补 orchestration `__init__` + api。
- **变异自证（同阶段一纪律）**：Task 2 的 `delegate` 未知 key 测试 + 作用域约束测试自带鉴别力；Task 1 同名同 rank 抛 `SkillConflict` 可做变异（注释 register 判据→转红）。
- **回归**：阶段二完成后 `make test`（kernel+tools）+ portal 套件全绿；新增 18 例。

## 5. 实施修正记录（inline 执行实测偏差，均在设计文档阶段二范围内，无需再批设计）

- **`api.py` import 块静默未插入（同阶段一陷阱再现）**：Task 3 给 `api.py` 加 `plan` 的
  `__all__` 成功、但 `from chiyu_kernel.plan import (...)` 块未真正写入（锚点静默不匹配）。
  表现为 `test_facade_covers_every_layer_export` 报 `TodoItem` 等未在门面。已重读该区域、
  锚定 `skills` 块末尾显式补入 import 块后转绿。→ 教训：每次改 `api.py` 后必须**单独跑**
  `test_api_facade_covers_all_layers.py` 而非仅看本 Task 测试。
- **子包 `__all__` 含实现常量致守卫红**：`skills`/`plan` 子包原 `__all__` 含 `RUNTIME_PROVIDER`/
  `RUNTIME_RANK`/`TODO_STATES`/`PLAN_STEP_STATES` 等实现常量，`test_facade_covers_every_layer_export`
  要求层 `__all__` 全集进门面。已将这些常量移出子包 `__all__`（保留定义、仅作内部默认），
  门面只暴露公共 API。
- **`SubagentPool.delegate` 的 `session_key` 参数误导**：初版误把 `session_key` 当 `run_turn`
  第二参（实际 `run_turn(agent_key, user_input)`，session 按 agent_key 派生）。已移除
  `session_key` 参数，session 自然按子 agent `live_key` 隔离（与阶段一 `AgentLoop` 一致）。
- **E2E 三个实测偏差**：① `register_native_tools(tools)` 需 `profile=` 关键字参（合法
  `TenantProfile` 须含 5 个 `CORE_ROLES`），已补；② `render_conversation` 返回 `RenderResult`
  对象（取 `.html`），非字符串；③ 事件须为 dict（`{"role","content"}`）而非 `SessionEvent`
  对象（阶段一 E2E 用 `derive_messages()` 产出 dict）。
- **变异自证（Task 1）**：`test_same_rank_dup_raises_conflict` 做变异——将
  `existing.rank == spec.rank` 改为 `False` ⇒ 测试转红（DID NOT RAISE `SkillConflict`），
  还原 ⇒ 转绿，证明 `SkillConflict` 非假绿。
- **回归计数**：`make test`（kernel+tools）**321 passed / 0 failed**（基线 303/0 + 阶段二 18 例：
  skills 6 / subagent 3 / plan·todo 9 / phase2-e2e 1）；portal 套件 **55 passed**。
  `manifest.json` 未动（contract/ 未改）。
