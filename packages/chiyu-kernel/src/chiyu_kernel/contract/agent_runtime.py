"""agent_runtime 契约（L0：零依赖 / 零 IO / 零领域字面量）。

Batch-4b agent 运行时判据词汇。上收自 CRM agent 内核纯函数判据核
（eventTrigger.js / glassBox.js / contractMonitor.js / agents.js），
agent 名 / skill 名 / 矩阵行域值由消费方注入，本契约只收结构与机制口径。

不变量（AGENT_RUNTIME_INVARIANTS）：
  A1 触发匹配只读白名单 fail-closed：非白名单 skill 即刻拒绝并留痕
     （reason=not-readonly），禁「默认放行」（eventTrigger.js:98-101）。
  A2 去重查询失败保守放行 + 必须留痕（recordFailure），禁静默吞
     （eventTrigger.js:143-145）；DB 去重为主、内存冷却为辅。
  A3 glassBox 脏信号必须过滤：trace 项数 = 有效信号数；无信号不抛错走
     「无信号」叙述分支（glassBox.js 铁律 ②③）。
  A4 契约合规 success 无人工标记恒 'pending'，禁猜 'pass'/'fail'
     （contractMonitor.js:60）。
  A5 KG 收敛：effective = declared ∩ served（served 由调用方注入，foundation
     不硬编码降级态名）；dropped 非空 → triggered（装配失败）；
     resolve_runtime 只返回 effective 防契约层静默误判（agents.js:40-64）。
  A6 冷却窗口内 skip 必须留痕（reason=cooldown），非静默丢弃（eventTrigger.js:127）。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError
from typing import Tuple

# ── 事件触发（eventTrigger.js）───────────────────────────────────────────────
#: 触发源三源闭集；矩阵行 source 缺省视为 'event'（向后兼容，:89 注释）
TRIGGER_SOURCES: Tuple[str, ...] = ("event", "timer", "external")
TRIGGER_SOURCE_DEFAULT = "event"

#: 矩阵行必带字段（结构契约；值域归消费方）
TRIGGER_ROW_FIELDS: Tuple[str, ...] = (
    "source", "domain", "type", "entity_type",
    "intent", "agent", "skill_slug", "dedup_field",
)

#: 去重键空值哨兵（dedup_field=null 或取值空 → 每次都算新，:114-117）
DEDUP_EMPTY_SENTINEL = "new"
#: 缺省冷却窗口 ms（match 级 cooldown_ms 可覆盖，:15-17）
DEFAULT_COOLDOWN_MS = 300_000
#: 冷却判决输出闭集
COOLDOWN_VERDICTS: Tuple[str, ...] = ("dispatch", "skip_cooldown")
#: 派发 skip 留痕 reason 闭集（A2/A6：skip 必带 reason）
TRIGGER_SKIP_REASONS: Tuple[str, ...] = ("cooldown", "db-dedup", "not-readonly")

# ── glassBox 可解释推理链（glassBox.js）──────────────────────────────────────
#: 输出三字段
GLASSBOX_FIELDS: Tuple[str, ...] = ("judge", "trace", "why_narrative")
#: trace 项字段
GLASSBOX_TRACE_FIELDS: Tuple[str, ...] = ("signal", "rule_ref", "j_score")
#: judge 轴缺省
GLASSBOX_AXIS_DEFAULT = "capability"
#: 无信号叙述哨兵词（why_narrative 中信号名空缺时的占位，域文案由消费方覆盖）
GLASSBOX_NO_SIGNAL_SENTINEL = "无信号"

# ── 契约合规矩阵（contractMonitor.js）────────────────────────────────────────
#: 三维度判定列
COMPLIANCE_DIMENSIONS: Tuple[str, ...] = ("skill_ok", "memory_ok", "success")
#: success 无人工标记恒 pending（A4）
COMPLIANCE_PENDING = "pending"
#: 人工 success 标记闭集（observed 值域；'pending' 仅缺省）
COMPLIANCE_SUCCESS_MARKERS: Tuple[str, ...] = ("pass", "fail")
#: join 键候选来源：稳定键优先、回退标题（:21-28）
COMPLIANCE_JOIN_PRIORITY: Tuple[str, ...] = ("contract_task_id", "task")
#: skill_ok 判定参与的 episode phase（:45）
COMPLIANCE_SKILL_PHASES: Tuple[str, ...] = ("loop-started", "loop-done")
#: memory_ok 判定参与的 episode phase（:48）
COMPLIANCE_MEMORY_PHASE: str = "context-injected"

# ── KG 收敛闸门（agents.js）──────────────────────────────────────────────────
#: KG 层级全序（天花板与收敛判定基线）
KG_LAYER_ORDER: Tuple[str, ...] = ("L1", "L2", "L3", "L4")
#: 收敛闸门输出键
KG_GATE_FIELDS: Tuple[str, ...] = (
    "ok", "declared", "target", "effective", "dropped", "triggered", "detail",
)
#: 无 kg_target → 开放到最高层（agents.js:26-27）
KG_TARGET_UNBOUNDED = None

# ── 装配守卫名闭集（agents.js 断言族；机制核只收两条纯函数守卫）────────────────
ASSEMBLY_GUARD_NAMES: Tuple[str, ...] = (
    "l3_stated_but_kg_degraded",   # 声明 L3 而 KG 降级 → 装配失败（:14-18）
    "kg_convergence",              # 运行时层级收敛到 served ∩ target（:40-58）
)

# ── 判据自检 ─────────────────────────────────────────────────────────────────
AGENT_RUNTIME_INVARIANTS: Tuple[str, ...] = (
    "A1_readonly_failclosed",        # 非白名单 skill 拒绝留痕，禁默认放行
    "A2_dedup_fail_open_traced",     # 去重查失败保守放行+留痕，禁静默
    "A3_dirty_signals_filtered",     # 脏信号过滤；无信号不抛错
    "A4_success_pending_default",    # success 无标记恒 pending 禁猜
    "A5_kg_effective_intersection",  # effective=declared∩served；dropped 非空即 triggered
    "A6_cooldown_skip_traced",       # 冷却 skip 留痕非静默
)


class AgentRuntimeError(KernelError):
    code = "CONTRACT_VIOLATION"
    """agent_runtime 判据核参数错误（未知触发源/非法层级等）。fail-closed。"""


__all__ = [
    "TRIGGER_SOURCES", "TRIGGER_SOURCE_DEFAULT", "TRIGGER_ROW_FIELDS",
    "DEDUP_EMPTY_SENTINEL", "DEFAULT_COOLDOWN_MS", "COOLDOWN_VERDICTS",
    "TRIGGER_SKIP_REASONS",
    "GLASSBOX_FIELDS", "GLASSBOX_TRACE_FIELDS", "GLASSBOX_AXIS_DEFAULT",
    "GLASSBOX_NO_SIGNAL_SENTINEL",
    "COMPLIANCE_DIMENSIONS", "COMPLIANCE_PENDING", "COMPLIANCE_SUCCESS_MARKERS",
    "COMPLIANCE_JOIN_PRIORITY", "COMPLIANCE_SKILL_PHASES", "COMPLIANCE_MEMORY_PHASE",
    "KG_LAYER_ORDER", "KG_GATE_FIELDS", "KG_TARGET_UNBOUNDED",
    "ASSEMBLY_GUARD_NAMES", "AGENT_RUNTIME_INVARIANTS", "AgentRuntimeError",
]
