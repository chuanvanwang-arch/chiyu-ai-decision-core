"""任务状态机（SKILL `ai-multi-agent-orchestration` 第 2 轮判据的**唯一实现**）。

内核实测版：demo `src/chiyu_group/orchestration/state_machine.py` 逐字保留，
仅改包路径 `chiyu_group.orchestration` → `chiyu_kernel.orchestration`，**不增不改**。

定位（为什么与 `trace` 分家）：
    `bj.event` 回答「**发生了什么**」——数据事实源、append-only 事件流；
    任务状态机回答「**这个任务现在在哪、卡没卡、该不该干预**」。
    二者语义不同 ⇒ 不混表（SKILL #6 反模式 6：任务表存事件，语义混淆）。
    本模块只放**纯逻辑**（状态集 / 转换表 / 熔断参数 / 校验 / 投影），持久化在 `store.py`。

状态集（最小完备集 + 质量闸门）：

    ready → running → done ─(评估 reject)→ reviewing → ready(带评估意见) → running
                    │  └→ failed ─(重试)→ ready
                    │        └→ (连续失败 ≥ FAILURE_LIMIT) → blocked(circuit_break)  ← 熔断
                    └→ (进程死) → zombie → reset → ready
    blocked(block_kind) → ready        # approval=等人批 / circuit_break=熔断 / manual=人工挂起

四条不可回退的约定（**有守卫测试，不是注释**）：
  ① **审批闸门 ≠ 故障**：`blocked(approval)` 不计 failed、不进熔断计数（实践心得 2）。
  ② **无决策不写**：每条状态转换必须带非空 `decision_id`（决策锚，反模式 16）。
     系统自发任务（夜批等）无业务决策可锚，用 `sys-<scope>` 前缀的**系统锚**，
     前缀使来源显式可辨，**不得**冒用业务决策 id（`assert_anchor` 强制）。
  ③ **禁静默中间态**：任务必须能终结到终态（done/failed）；`reviewing` 超 `MAX_REDO`
     升级 `blocked(manual)`（人工兜底），绝不无限停留（反模式 15 引擎未接线=假执行）。
  ④ **熔断计数只在成功或显式复位时清零**（实践心得 1）：重试（failed→ready）**保留**计数。

⛔ Batch-2a（2026-10-14，GAP-5）：状态集/转换表/参数等**词汇闭集**已上收
   `chiyu_kernel/contract/orchestration.py`（sanctioned 契约面单一事实源），
   本模块改为从契约导入（同名符号是同一对象，无双份漂移）；**校验与投影逻辑
   仍在本模块**（机制层）。demo 逐字保留的声明部分随契约归口，逻辑不增不改。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Any, Iterable, Optional

from chiyu_kernel.contract.orchestration import (
    ALLOWED_TRANSITIONS,
    BLOCK_KINDS,
    FAILURE_LIMIT,
    MAX_REDO,
    SYSTEM_ANCHOR_PREFIX,
    SYSTEM_TASK_KINDS,
    TASK_KINDS,
    TASK_STATES,
    TERMINAL_STATES,
    ZOMBIE_STALE_SECONDS,
)


class TaskStateError(KernelError):
    code = "CONTRACT_VIOLATION"
    """状态机**契约违规**（非法转换 / 缺决策锚 / 缺结果引用）。

    刻意与「基础设施故障」分开：契约违规是编程错误，必须**抛**（响亮地红）；
    连接不可用属于环境故障，由 `store.py` fail-open + 留痕，绝不在这里静默。
    """


# ── 校验 ──────────────────────────────────────────────────────────────
def is_terminal(state: str) -> bool:
    return state in TERMINAL_STATES


def assert_state(state: str, *, what: str = "state") -> str:
    if state not in TASK_STATES:
        raise TaskStateError(f"未知{what}：{state!r}（合法集 {TASK_STATES}）")
    return state


def assert_block_kind(block_kind: Optional[str]) -> Optional[str]:
    if block_kind is not None and block_kind not in BLOCK_KINDS:
        raise TaskStateError(f"未知 block_kind：{block_kind!r}（合法集 {BLOCK_KINDS}）")
    return block_kind


def assert_transition(frm: str, to: str, *, block_kind: Optional[str] = None) -> None:
    """转换合法性闸。`reset` 走 `assert_reset`（任何态 → ready，幂等）。"""
    assert_state(frm, what="from_state")
    assert_state(to, what="to_state")
    if to == "blocked":
        if block_kind is None:
            # ⛔ 「blocked 却不说是为什么」= 不可排查；SKILL #6 要求 block_kind 三分类。
            raise TaskStateError("进入 blocked 必须给 block_kind（approval/circuit_break/manual）")
    elif block_kind is not None:
        raise TaskStateError(f"非 blocked 状态不得带 block_kind（收到 {block_kind!r}）")
    allowed = ALLOWED_TRANSITIONS[frm]
    if to not in allowed:
        raise TaskStateError(f"非法转换：{frm} → {to}（允许 {sorted(allowed)}）")


def assert_reset(frm: str) -> None:
    """`reset` 是幂等复位：任何状态 → ready（清 worker_pid / 失败计数 / block）。

    ⚠ 唯一例外是**熔断解阻塞必须由人工发起**——见 `store.TaskStore.unblock`。
    这里只校验源状态合法。
    """
    assert_state(frm, what="from_state")


def assert_anchor(decision_id: Optional[str], *, kind: str) -> str:
    """决策锚强校验（反模式 16「无决策不写」）。

    判据不止「非空」，还要**来源与任务种类一致**：
      · 业务任务（analysis/approval/governance）→ 业务决策锚，**禁** `sys-` 前缀；
      · 系统任务（retro/sweep）→ 系统锚 `sys-<scope>`，且必须点名 scope。
    只查「非空」会放过 `decision_id=""` 之外的另一种坏形状：把系统定时器
    当成决策写进审计，事后无法分辨「谁批的」。
    """
    did = (decision_id or "").strip()
    if not did:
        raise TaskStateError(
            f"缺决策锚：kind={kind!r} 的状态转换不可审计 ⇒ 禁写（SKILL #6 反模式 16）")
    is_sys = did.startswith(SYSTEM_ANCHOR_PREFIX)
    if kind in SYSTEM_TASK_KINDS:
        if not is_sys or len(did) <= len(SYSTEM_ANCHOR_PREFIX):
            raise TaskStateError(
                f"系统任务必须用系统锚 {SYSTEM_ANCHOR_PREFIX}<scope>（收到 {did!r}）")
    elif is_sys:
        raise TaskStateError(
            f"业务任务 kind={kind!r} 不得使用系统锚 {did!r}（必须锚到真实决策）")
    return did


def system_anchor(scope: str) -> str:
    """系统锚构造（唯一入口）：`sys-<scope>`，scope 非空且不含空白。"""
    s = (scope or "").strip()
    if not s or any(c.isspace() for c in s):
        raise TaskStateError(f"系统锚 scope 非法：{scope!r}")
    return f"{SYSTEM_ANCHOR_PREFIX}{s}"


def assert_result_ref(result_ref: Optional[str]) -> str:
    """终态必须带结果引用（结果双写：① 事件流 ② 任务表 result_ref）。"""
    r = (result_ref or "").strip()
    if not r:
        raise TaskStateError("进入终态必须带 result_ref（只写状态不算落盘）")
    return r


# ── 投影：从转换日志独立重算当前态 ─────────────────────────────────────
def fold_history(rows: Iterable[dict]) -> dict:
    """把转换日志（按 seq 升序）折叠成当前态。

    用途不是「替代状态表」，而是给守卫一条**独立读路径**：若状态表写 `running`
    而日志已经走到 `done`，两边不一致就说明有人绕过状态机直改表（本项目
    「单一事实源」纪律下的典型假绿）。两处口径独立 ⇒ 分歧可见。
    """
    cur: Optional[str] = None
    blocked_kind: Optional[str] = None
    terminal: Optional[str] = None
    n = 0
    for r in rows:
        n += 1
        cur = r.get("to_state")
        blocked_kind = r.get("block_kind")
        if cur in TERMINAL_STATES:
            terminal = cur
    return {"state": cur, "block_kind": blocked_kind,
            "terminal_state": terminal, "transitions": n}


def is_stuck(state: str, *, redo_count: int = 0, age_seconds: Optional[float] = None) -> bool:
    """「是否卡住」判据（反模式 15 的反面：假执行）。

    `running` 本身不是「卡」——长时间 running 且无心跳才算；`reviewing` 超重跑上限
    算卡。这里只做**纯判定**，实际巡检在 `store.sweep_zombies`。
    """
    if state == "running":
        return age_seconds is not None and age_seconds > ZOMBIE_STALE_SECONDS
    if state == "reviewing":
        return redo_count >= MAX_REDO
    return False


def summarize() -> dict[str, Any]:
    """参数自述（供设计文档/探针/页面直接取，避免第二份常量表）。"""
    return {"states": list(TASK_STATES), "terminal": list(TERMINAL_STATES),
            "block_kinds": list(BLOCK_KINDS), "task_kinds": list(TASK_KINDS),
            "failure_limit": FAILURE_LIMIT, "max_redo": MAX_REDO,
            "zombie_stale_seconds": ZOMBIE_STALE_SECONDS,
            "system_anchor_prefix": SYSTEM_ANCHOR_PREFIX,
            "transitions": {k: sorted(v) for k, v in ALLOWED_TRANSITIONS.items()}}


__all__ = [
    "TASK_STATES", "TERMINAL_STATES", "BLOCK_KINDS", "TASK_KINDS", "SYSTEM_TASK_KINDS",
    "FAILURE_LIMIT", "MAX_REDO", "ZOMBIE_STALE_SECONDS", "SYSTEM_ANCHOR_PREFIX",
    "ALLOWED_TRANSITIONS", "TaskStateError", "is_terminal", "assert_state",
    "assert_block_kind", "assert_transition", "assert_reset", "assert_anchor",
    "system_anchor", "assert_result_ref", "fold_history", "is_stuck", "summarize",
]
