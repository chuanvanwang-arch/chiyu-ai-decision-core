# 设计：session.prompt 接入 L1–L4 上下文装配（复用 AgentLoop）

> 阶段：brainstorming（P0–P5 已过；P8 用户评审 **已批准 2026-09-26**）✅
> 关联：M1 全量域（提交 `ffff599`/`22b0f24`/`7c292c9`）、`native-context-assemble` 工具已注册可调、`META_REDLINES` 元红线硬闸门已接线。
> 状态：设计已批准 → 已产出实施计划 `docs/plans/2026-09-26-chiyu-host-session-prompt-context-plan.md`，待执行。
>
> ⚠️ **实现修正（批准范围内）**：§2.2 伪代码同时为 `session.prompt` 与 `AgentLoop.run_turn` 写 `user/message`，会造成**重复 append**。
> 实际实现以 `run_turn` 内部 append 为准，`session_prompt` 自身不再 append user 事件（外部行为不变：会话落 exactly 一条 user/message + assistant/message + turn/end，返回 `{accepted:true}`）。
> 目标：`session.prompt` 由「仅 append 事件不调 LLM」升级为「复用 AgentLoop 真跑一轮 LLM，且把 L1–L4 上下文装配结果注入模型上下文」。

---

## 0. 已拍板决策（brainstorming P2/P3）

| 决策点 | 选择 |
|---|---|
| 装配结果落地形态 | **进入模型上下文**（facts 作为 pre-step 注入的上下文消息） |
| LLM 调用链 | **复用 AgentLoop**（session 与 subagent 同链，共享 `redline_guard`） |
| 委派时序 | **A 同步委派**（内部同步跑完一轮再返回 `{accepted:true}`；PhaseB 接真实 LLM 再升级异步） |

契约依据（实测 DSH `sessions.schema.ts`）：
- `sessionPromptRequestSchema`: `{sessionId, mode∈(queue|steer), content, clientTimeZone?}`
- `sessionPromptValueSchema`: `{accepted: literal(true), command?: {kind:'success', text?}}`

## 1. 现状（实测 `methods.py` session_prompt，L185–196）

```python
def session_prompt(payload):
    sid = payload["sessionId"]; log = _session_or_raise(sid)
    text = "".join(p.get("text","") for p in content if ...)
    ev = log.append("user/message", {"content": text})
    wire = to_wire_session_event(ev)
    _bus.publish({... "event": wire}, persist=_noop_persist)
    return {"accepted": True}
```
- **不调 LLM**：只 append user 事件 + 发布 + 返回 accepted。
- DSH 语义是 queue（立即返回），但当前无真实推理链路。

## 2. 设计结构（复用 AgentLoop）

### 2.1 session 主 agent（惰性注册）
- 在 `_subagent_pool._live`（`LiveAgentRegistry`）**按 sid 惰性注册** `Agent(key=sid, tools_scope="", pre_step=_ctx_inject)`。
- `pre_step(messages) -> messages`：**装配钩子**。调用 `context.assemble(L1–L4 needs, provided)`，把 `facts` 作为一条上下文消息插入消息序列首部，返回改写后的 messages。
- 不注册重复：`live.get(sid) is None` 时才 register。

### 2.2 `AgentLoop.run_turn(sid, text)` 路径
```
session.prompt:
  append user/message
  loop = AgentLoop(llm=StubProvider, tools=_tools, sessions=_session_manager,
                   live_agents=_subagent_pool._live, redline_guard=_guard)   # 复用同链
  result = loop.run_turn(sid, text)          # pre_step 注入 L1–L4 装配 facts → 真调 LLM
  _bus.publish(assistant 事件)               # assistant 落 session log
  return {"accepted": True}                  # 对齐 sessionPromptValueSchema
```
⚠ 每次新建 `AgentLoop`（与 `SubagentPool.delegate` 同构），不缓存实例（保持委派隔离）；`_tools`/`_guard`/`_live` 共享同一实例。

### 2.3 缺口处置（fail-safe 不阻塞）
- `assemble` 返回 `AssemblyResult(facts, supply_report)`。
- `missing/degraded_layers` **结构化写入**装配消息的元数据（供追踪），**不抛错**。
- 维持 `session.prompt` 返回 `{accepted:true}`（DSH 契约不变）。

### 2.4 纪律约束
- **不 import `chiyu_kernel.api` 门面**（触发 pg）；直接消费 `context` / `orchestration` 子模块（与 M0/M1 同策略）。
- **零领域字面量**：needs/provided 由中性策略提供（消费方应注入 TenantProfile；桥接层默认中性）。
- **被调用方硬闸门**：AgentLoop 内的 `tools.execute` 已挂 redline_guard（元红线），session 链路同样受益。

## 3. need/provided 中性装配策略（bridge 层默认）
- needs：声明 **L1–L2**（foundation-builder 契约授权层）各层一个 `KnowledgeNeed`，dims 用 `KNOWLEDGE_NEEDS_DEFAULT_DIMS`（semantics/precedent/operation/governance）。
  ⛔ 不声明 L3/L4 need——机制虽支持全层，但契约 scope 收敛授权层，避免越界（校验器会拦 L3/L4）。
- provided：默认 `{}`（无领域供给）→ `supply_report.missing` 会列出全部层（degraded），facts 为空。
- 语义：**机制接通、缺口可见**。消费方接真实 `TenantProfile`/检索后再注入真实 provided。
- 判别项：即使 provided 为空，也须返回 `{accepted:true}` 且 session log 出现 `assistant/message` + 装配元数据（missing 结构化）。

## 4. 测试（防假绿）
- `session_prompt` 改造后：session 会话出现 `user/message → (装配辅助) → assistant/message → turn/end`，`accepted` 仍为 true。
- need 声明但 provided 空 → `missing` 非空（supply_report 结构化暴露，非吞）。
- 变异自证：删掉 pre_step 装配钩子 → 测试转红（会话缺装配元数据）。
- 回归：`pytest packages/chiyu-host/tests` 全绿，`chiyu-kernel` 相关子集不回归。

## 5. 风险与门
- R1：`Agent` 按 sid 惰性注册是否污染 subagent 注册表 → 用 sid 作 key 与 `sub:*` 不冲突（前缀不同），且 `live.get(sid)` 判重。
- R2：同步委派阻塞返回时长 → 当前 StubProvider 一轮瞬时（ms 级），可接受；PhaseB 真实 LLM 升级异步。
- R3：装配 facts 是否真进 LLM 上下文 → pre_step 返回的 messages 含装配消息，断言 `assistant` 生成前上下文含 facts 元数据。
- 门：全绿 + 变异自证 + 不假绿（不真调 LLM 则 assistant/message 缺失转红）。

## 6. 完成判据
- `session.prompt` 返回 `{accepted:true}` 且 session 会话出现 `assistant/message`（真调 LLM）。
- L1–L4 装配 facts 以上下文消息注入 pre_step；provided=空时 missing 结构化暴露。
- chiyu-host 测试全绿 + 变异自证通过；M 阻断点回填文档。

---

## 7. 生命契约（§A 双轨）

```contract-yaml
- task: "session.prompt 接入 L1–L4 上下文装配（复用 AgentLoop 同步委派）"
  contract_task_id: ct-chiyu-foundation
  agent: foundation-builder
  skills: [ai-context-layering]
  memory: [chiyu-foundation]
  knowledge_scope: { layers: [L1, L2], max_hops: 2 }
  success: "session.prompt 返回 accepted:true 且该 session 会话出现 assistant/message 事件；provided 为空时装配缺失信息结构化暴露（missing 非空）"
```

> 注：`context.assemble` 机制本身支持 L1–L4 全层（§2.3），但本任务契约 scope 收敛到 foundation-builder 被注册表授权的 L1–L2（不越界；L3–L4 留给后续领域注入）。

**契约说明：** 本任务由 `foundation-builder` 承接（契约键 `ct-chiyu-foundation`），须调用 `ai-context-layering` SKILL、读取 `chiyu-foundation` 记忆（L1–L2，≤2 跳）；成功标准为 `session.prompt` 返回 accepted 且 session 会话真现 assistant 事件（证明真调 LLM），provided 为空时缺失信息结构化暴露（防吞）。

## 8. 闭环回写

| task | gap_type | observed | expected | ts | severity |
|---|---|---|---|---|---|
| session.prompt L1–L2 装配 | success | session 真现 assistant/message + context/assemble 事件（missing 含 L1/L2） | session 真现 assistant + missing 结构化 | 2026-09-26 | — |

---

*校验：`node C:/Users/wangchuan08/.workbuddy/skills/brainstorming/scripts/validate-contract.mjs docs/2026-09-26-chiyu-host-session-context-layering-design.md --registry contract/contract-ids.json`*
