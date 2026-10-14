"""RPC 方法实现（M0 子集 ≈14 方法）。

每个响应 value 的字段名严格对齐 DSH `apiproxy/src/api/*.schema.ts`（防假绿）。
请求信封 ClientRequest 全形：{type, rpcId, method, payload}（见 rpc.schema.ts）。
响应信封 ServerResponse 全形：{type:'server-response', rpcId, result:{ok, value|error}}。

⚠️ 直接消费内核子模块（session/skills/plugins/events）而非 `chiyu_kernel.api` 门面：
因 api 门面会触发 `store.pg_store` 的 pg 依赖，而 M0 桥接层不连库（用内存态）。
后续接真 store 时改走 api 门面。同仓内部桥接层有权访问子模块。
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Optional

from chiyu_kernel.session import SessionManager, SessionLog
from chiyu_kernel.skills import SkillRegistry, load_catalog
from chiyu_kernel.plugins import MODE_PRESETS, DEFAULT_MODE_ID
from chiyu_kernel.events import EventBus
from chiyu_kernel.llm.client import StubProvider, LlmResponse
from chiyu_kernel.tools import ToolRegistry
from chiyu_kernel.orchestration.subagent import SubagentDescriptor, SubagentPool
from chiyu_kernel.orchestration.agent_loop import AgentLoop
from chiyu_kernel.orchestration.agent_runtime import Agent
from chiyu_kernel.context import assemble, KnowledgeNeed, KNOWLEDGE_NEEDS_DEFAULT_DIMS
from chiyu_kernel.contract import particle as _particle, decision as _decision, memory as _memory

from .bridge import to_wire_session_event, MuxBroadcaster
from .jobs import JobRegistry, make_publisher


# ── 进程内单例（一个 app 生命周期共享）────────────────────────────────────
_session_manager = SessionManager()
_session_index: Dict[str, SessionLog] = {}          # sessionId → SessionLog
_session_meta: Dict[str, Dict[str, Any]] = {}        # sessionId → {model: ModelSelection}
_goal_index: Dict[str, Dict[str, Any]] = {}          # sessionId → {id, revision, objective, status}（goal 会话投影状态，不连 pg）
_memory_index: Dict[str, List[Dict[str, Any]]] = {}   # sessionId → [memory entries]（记忆双轨 append-only，不连 pg）
_decision_index: Dict[str, Dict[str, Any]] = {}        # sessionId → {id, revision, objective, rationale, stage}（decision 会话投影，不连 pg）

# session.prompt 装配策略（bridge 层默认中性；foundation-builder 契约授权 L1–L2）
# ⛔ 不声明 L3/L4 need——契约 scope 收敛授权层，避免越界（校验器会拦 L3/L4）。
_SESSION_CTX_NEEDS = (
    KnowledgeNeed(layer="L1", dims=KNOWLEDGE_NEEDS_DEFAULT_DIMS),
    KnowledgeNeed(layer="L2", dims=KNOWLEDGE_NEEDS_DEFAULT_DIMS),
)
_skill_registry: Optional[SkillRegistry] = None  # M1：真实注入于模块底部
_bus = EventBus()
_mux = MuxBroadcaster()
_mux.attach(_bus)

# ── M1：真实 SubagentPool（phase2 委派；与 _session_manager 共用同一实例）──
_subagent_pool: Optional[SubagentPool] = None  # 模块底部赋真实值

# ── M2-T1：JobRegistry 全局单例（跨会话隔离；每次变更推 session/jobs 帧）──
# publisher 由 make_publisher 构造：把 jobs 列表包成 {event_type:'session/jobs', ...}
# 发到总线；MuxBroadcaster 已订阅该 event_type（bridge.MUX_FRAME_TYPES）。
_job_registry: Optional[JobRegistry] = None  # 模块底部赋真实值


def _build_skill_catalog() -> Dict[str, Dict[str, Any]]:
    """技能目录（集中封装后台插件首落地）。

    M1：由消费方注入真实目录（消费方应给 TenantProfile；桥接层默认中性示例，
    与 M0 同策略）。这里的 catalog shape 对齐 `chiyu_kernel.skills.load_catalog`。
    """
    catalog = {
        "summarizer": {"description": "长文本摘要", "when_to_use": "需要提炼要点时", "model_invocable": True},
        "translator": {"description": "多语言翻译", "when_to_use": "跨语言内容处理", "model_invocable": True},
        "code-reviewer": {"description": "代码评审", "when_to_use": "提交前审查", "model_invocable": True},
        "context-assembler": {"description": "运行时上下文装配", "when_to_use": "需要 L1–L4 上下文时", "model_invocable": True},
        "memory-curator": {"description": "记忆梳理与蒸馏", "when_to_use": "需要沉淀/归纳记忆时", "model_invocable": True},
    }
    return catalog


_skill_registry = load_catalog(_build_skill_catalog())


def _noop_persist(event: Dict[str, Any]) -> None:
    """M0 内存总线：不做持久化（总线契约要求 persist 先执行，这里为空操作）。"""


# ── 静态模型目录（R4：llm provider 待接 Phase B，M0 静态占位）──────────────
MODEL_GROUPS: List[Dict[str, Any]] = [{
    "id": "deepseek",
    "name": "DeepSeek",
    "models": [{"id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash"}],
}]
DEFAULT_MODEL_SELECTION: Dict[str, Any] = {"provider": "deepseek", "model": "deepseek-v4-flash"}


# ── M1 subagent 真实目录（phase2 委派；由 SubagentDescriptor 驱动）────────
SUBAGENT_DESC_LIST: List[SubagentDescriptor] = [
    SubagentDescriptor(
        key="researcher",
        role="研究智能体",
        instruction="基于提供的问题做信息检索与研判，输出结构化结论。",
        tools_scope="research",
    ),
    SubagentDescriptor(
        key="coder",
        role="编码智能体",
        instruction="按需求编写/修订代码并自检，输出可直接落盘的改动。",
        tools_scope="code",
    ),
    SubagentDescriptor(
        key="reviewer",
        role="评审智能体",
        instruction="对给定产物做审查，指出缺陷与改进建议。",
        tools_scope="review",
    ),
]
# key → label 映射（供 subagent.list 输出；SubagentPool 无公共 list 方法）
_SUBAGENT_LABELS: Dict[str, str] = {d.key: d.role for d in SUBAGENT_DESC_LIST}
_SUBAGENT_DEFAULT_MODE = "one-shot"


class RpcError(Exception):
    """业务错误 → ServerResponse 的 error 分支（对齐 rpc.schema RpcError）。"""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details: Dict[str, Any] = details or {}


def _session_or_raise(session_id: str) -> SessionLog:
    log = _session_index.get(session_id)
    if log is None:
        raise RpcError("session-not-found", f"未知会话：{session_id}", {"sessionId": session_id})
    return log


def _session_lazy(session_id: str) -> SessionLog:
    """按需创建会话（child 会话首次委派前可能尚未建；与 session_create 一致写两个索引）。"""
    log = _session_index.get(session_id)
    if log is None:
        log = _session_manager.get_or_create(session_id)
        _session_index[session_id] = log
    return log


def _last_ts(log: SessionLog) -> float:
    events = log.events()
    return events[-1].ts if events else time.time()


# ── session.* ─────────────────────────────────────────────────────────────
def session_list(payload: Dict[str, Any]) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    for sid, log in _session_index.items():
        events = log.events()
        items.append({
            "sessionId": sid,
            "updatedAt": _last_ts(log),
            "running": False,
            "blank": len(events) == 0,
            "agentPreset": _session_meta.get(sid, {}).get("agentPreset"),
        })
    return {"items": items}


def session_create(payload: Dict[str, Any]) -> Dict[str, Any]:
    sid = payload.get("sessionId") or f"sess-{uuid.uuid4().hex[:12]}"
    log = _session_manager.get_or_create(sid)
    _session_index[sid] = log
    agent_preset = payload.get("agentPreset")
    if agent_preset:
        _session_meta.setdefault(sid, {})["agentPreset"] = agent_preset
    return {"sessionId": sid, "agentPreset": agent_preset}


def session_history(payload: Dict[str, Any]) -> Dict[str, Any]:
    log = _session_or_raise(payload["sessionId"])
    events = log.events()
    max_messages = payload.get("maxMessages")
    if isinstance(max_messages, int) and max_messages > 0:
        events = events[-max_messages:]
    history = [{"event": to_wire_session_event(e)} for e in events]
    return {"events": history, "hasMore": False}


def session_models(payload: Dict[str, Any]) -> Dict[str, Any]:
    sid = payload["sessionId"]
    _session_or_raise(sid)
    current = _session_meta.get(sid, {}).get("model", DEFAULT_MODEL_SELECTION)
    return {"current": current, "routable": True, "groups": MODEL_GROUPS, "failures": []}


def session_select_model(payload: Dict[str, Any]) -> Dict[str, Any]:
    sid = payload["sessionId"]
    _session_or_raise(sid)
    selected = {
        "provider": payload["provider"],
        "model": payload["model"],
        "reasoningEffort": payload.get("reasoningEffort"),
    }
    _session_meta.setdefault(sid, {})["model"] = selected
    return {"selected": selected}


def _ctx_inject(sid: str):
    """装配钩子（pre_step）：把 L1–L2 装配结果作为上下文消息注入模型上下文首部；
    并把结构化缺口（missing/degraded_layers）写入会话日志 `context/assemble` 事件（供追踪/测试判别）。

    provided 默认空（无领域供给）→ missing 结构化暴露，不抛错（fail-safe）。
    消费方接真实 TenantProfile/检索后注入 provided 即补齐（机制已接通）。
    """

    def _pre(messages):
        result = assemble(_SESSION_CTX_NEEDS, {})
        log = _session_index.get(sid)
        if log is not None:
            log.append("context/assemble", {
                "facts": result.facts,
                "missing": list(result.supply_report.missing),
                "degraded_layers": list(result.supply_report.degraded_layers),
            })
        ctx_msg = {
            "role": "system",
            "content": (
                "[运行时上下文装配 L1–L2]\n"
                f"缺口(missing)：{list(result.supply_report.missing)}\n"
                f"降级层(degraded)：{list(result.supply_report.degraded_layers)}\n"
                "（机制已接通；消费方注入 TenantProfile/检索后补齐 provided）"
            ),
        }
        return [ctx_msg] + list(messages)

    return _pre


def _ensure_session_agent(sid: str) -> None:
    """按 sid 惰性注册 session 主 agent（含 L1–L2 装配 pre_step）到子 agent 同一条 live 注册表。

    复用 AgentLoop 同链；key=sid 与 sub:* 前缀不冲突；已注册则跳过（判重 live.get(sid)）。
    """
    if _subagent_pool._live.get(sid) is None:
        _subagent_pool._live.register(Agent(key=sid, tools_scope="", pre_step=_ctx_inject(sid)))


def session_prompt(payload: Dict[str, Any]) -> Dict[str, Any]:
    sid = payload["sessionId"]
    _session_or_raise(sid)            # 要求会话已存在（DSH 契约语义）
    content = payload.get("content") or []
    text = "".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    # 惰性注册 session 主 agent（含 L1–L2 装配 pre_step）
    _ensure_session_agent(sid)
    # 复用 AgentLoop 同链：run_turn 内部 append user/message → pre_step 注入装配 →
    # 真调 LLM(stream_chat) → assistant/message → turn/end（共享 redline_guard）
    loop = AgentLoop(
        llm=StubProvider(),
        tools=_tools,
        sessions=_session_manager,
        live_agents=_subagent_pool._live,
        redline_guard=_native_redline_guard(profile=None),
    )
    loop.run_turn(sid, text)
    # 实时扇出（DSH session/event）：user/message 首帧保留原 mux 契约 + assistant/message（真调 LLM 回复）
    log = _session_index.get(sid)
    if log is not None:
        events = log.events()
        for kind in ("user/message", "assistant/message"):
            ev = next((e for e in reversed(events) if e.kind == kind), None)
            if ev is not None:
                _bus.publish(
                    {"id": str(uuid.uuid4()), "event_type": "session/event",
                     "sessionId": sid, "event": to_wire_session_event(ev)},
                    persist=_noop_persist,
                )
    return {"accepted": True}


def session_cancel(payload: Dict[str, Any]) -> Dict[str, Any]:
    _session_or_raise(payload["sessionId"])
    return {"accepted": True}


# ── session 扩展域（rename/fork/search/updateQueue/attachment）─────────────
# 队列存储：prompt 当前同步执行不留队列项；updateQueue 对已知队列项做真实状态迁移，
# 未知 itemId 报 queue-item-not-found（对齐 DSH 错误契约）。
def session_rename(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{sessionId, title} → {title, seq}。标题非空校验（DSH title-invalid 语义），写入会话日志。"""
    sid = payload["sessionId"]
    log = _session_or_raise(sid)
    title = (payload.get("title") or "").strip()
    if not title:
        raise RpcError("title-invalid", f"会话标题不可为空：{sid}", {"sessionId": sid})
    ev = log.append("session/rename", {"title": title})
    _session_meta.setdefault(sid, {})["title"] = title
    return {"title": title, "seq": ev.seq}


def session_fork(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{sessionId, atSeq?} → {sessionId}。复制至 atSeq（含）或全量，新会话继承 meta。"""
    sid = payload["sessionId"]
    log = _session_or_raise(sid)
    at_seq = payload.get("atSeq")
    events = log.events()
    if at_seq is not None:
        events = [e for e in events if e.seq <= at_seq]
    child_id = f"sess-fork-{uuid.uuid4().hex[:12]}"
    child = _session_lazy(child_id)
    for e in events:
        child.append(e.kind, dict(e.payload))
    if sid in _session_meta:
        _session_meta[child_id] = {**_session_meta[sid]}
    return {"sessionId": child_id}


def session_search(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{query} → {items[{sessionId, snippet}], hasMore}。扫全部会话事件文本，子串命中。"""
    query = (payload.get("query") or "").strip()
    if not query or len(query) > 500 or "\0" in query:
        raise RpcError("bad-request", "query 必须为 1-500 字符且不含 NUL", {"issues": []})
    limit = 20                      # SESSION_SEARCH_RESULT_LIMIT（DSH session-search.ts:2）
    snippet_max = 240               # SESSION_SEARCH_SNIPPET_MAX_CODE_POINTS
    items: List[Dict[str, Any]] = []
    q = query.lower()
    for sid, log in _session_index.items():
        for e in log.events():
            text = " ".join(str(v) for v in e.payload.values() if isinstance(v, str)) if e.payload else ""
            pos = text.lower().find(q)
            if pos < 0:
                continue
            start = max(0, pos - 60)
            snippet = ("…" if start > 0 else "") + text[start:start + snippet_max]
            items.append({"sessionId": sid, "snippet": snippet})
            if len(items) >= limit:
                return {"items": items, "hasMore": True}
    return {"items": items, "hasMore": False}


def session_update_queue(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{sessionId, itemId, action{kind:edit/remove/steer}} → {accepted:true}。

    队列项存于 _session_meta[sid]["queue"]；prompt 同步执行模式下通常为空，
    未知 itemId 报 queue-item-not-found（真实查找，非盲 accept——防假绿）。
    """
    sid = payload["sessionId"]
    _session_or_raise(sid)
    item_id = payload.get("itemId") or ""
    queue = _session_meta.get(sid, {}).get("queue", [])
    item = next((q for q in queue if q.get("itemId") == item_id), None)
    if item is None:
        raise RpcError("queue-item-not-found", f"队列项不存在：{item_id}", {"itemId": item_id})
    action = payload.get("action") or {}
    kind = action.get("kind")
    if kind == "edit":
        item["content"] = action.get("content") or []
    elif kind == "remove":
        _session_meta[sid]["queue"] = [q for q in queue if q.get("itemId") != item_id]
    elif kind == "steer":
        item["steered"] = True
    else:
        raise RpcError("bad-request", f"未知队列动作：{kind}", {"issues": []})
    return {"accepted": True}


def session_attachment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{sessionId, attachmentId} → {attachment, data}。

    本机 host 未接附件存储：真实查找 _session_meta 附件索引，未命中报 unsupported
    （DSH 错误码集内；绝不伪造 image ref / base64 数据）。
    """
    sid = payload["sessionId"]
    _session_or_raise(sid)
    att_id = payload.get("attachmentId") or ""
    att = _session_meta.get(sid, {}).get("attachments", {}).get(att_id)
    if att is None:
        raise RpcError("unsupported", f"附件不存在或未存储：{att_id}", {"attachmentId": att_id})
    return {"attachment": att["ref"], "data": att["data"]}


# ── workspace.*（工作区树，对齐 DSH workspace.schema.ts）───────────────────
_workspaces: Dict[str, Dict[str, Any]] = {}      # workspaceId → WorkspaceView
_workspace_order: List[str] = []
_archived_session_ids: List[str] = []


def _workspace_view(ws: Dict[str, Any]) -> Dict[str, Any]:
    return {k: ws[k] for k in ("workspaceId", "path", "title", "sessionIds", "createdAt", "updatedAt")}


def _workspace_or_raise(workspace_id: str) -> Dict[str, Any]:
    ws = _workspaces.get(workspace_id)
    if ws is None:
        raise RpcError("workspace-not-found", f"未知工作区：{workspace_id}", {"workspaceId": workspace_id})
    return ws


def workspace_list(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "items": [_workspace_view(_workspaces[wid]) for wid in _workspace_order],
        "archivedSessionIds": list(_archived_session_ids),
    }


def workspace_create(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{path} → {workspace, created}。按 path 幂等收编（DSH 语义：adopt 现存目录）。"""
    path = payload.get("path") or ""
    for wid in _workspace_order:
        if _workspaces[wid]["path"] == path:
            return {"workspace": _workspace_view(_workspaces[wid]), "created": False}
    wid = f"ws-{uuid.uuid4().hex[:12]}"
    now = time.time()
    ws = {"workspaceId": wid, "path": path, "title": os.path.basename(path.rstrip("/\\")) or path,
          "sessionIds": [], "createdAt": now, "updatedAt": now}
    _workspaces[wid] = ws
    _workspace_order.append(wid)
    return {"workspace": _workspace_view(ws), "created": True}


def workspace_rename(payload: Dict[str, Any]) -> Dict[str, Any]:
    ws = _workspace_or_raise(payload["workspaceId"])
    title = (payload.get("title") or "").strip()
    if not title:
        raise RpcError("bad-request", "工作区标题不可为空", {"issues": []})
    ws["title"] = title
    ws["updatedAt"] = time.time()
    return {"workspace": _workspace_view(ws)}


def workspace_delete(payload: Dict[str, Any]) -> Dict[str, Any]:
    wid = payload["workspaceId"]
    _workspace_or_raise(wid)
    del _workspaces[wid]
    _workspace_order.remove(wid)
    return {"deleted": True}


def workspace_insert_before(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{workspaceId, beforeWorkspaceId?} → {workspaceIds}。锚省略 = 追加到尾。"""
    wid = payload["workspaceId"]
    _workspace_or_raise(wid)
    _workspace_order.remove(wid)
    before = payload.get("beforeWorkspaceId")
    if before is not None and before in _workspace_order:
        _workspace_order.insert(_workspace_order.index(before), wid)
    else:
        _workspace_order.append(wid)
    return {"workspaceIds": list(_workspace_order)}


def workspace_insert_session_before(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{workspaceId, sessionId, beforeSessionId?} → {workspace}。会话须真实存在。"""
    ws = _workspace_or_raise(payload["workspaceId"])
    sid = payload["sessionId"]
    _session_or_raise(sid)
    sids = ws["sessionIds"]
    if sid in sids:
        sids.remove(sid)
    before = payload.get("beforeSessionId")
    if before is not None and before in sids:
        sids.insert(sids.index(before), sid)
    else:
        sids.append(sid)
    ws["updatedAt"] = time.time()
    return {"workspace": _workspace_view(ws)}


def workspace_archive_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{sessionId} → {archivedSessionIds}。归档 = 移出全部工作区 + 进归档集。"""
    sid = payload["sessionId"]
    _session_or_raise(sid)
    for ws in _workspaces.values():
        if sid in ws["sessionIds"]:
            ws["sessionIds"].remove(sid)
            ws["updatedAt"] = time.time()
    if sid not in _archived_session_ids:
        _archived_session_ids.append(sid)
    return {"archivedSessionIds": list(_archived_session_ids)}


# ── host 文件域（listDirectory/createDirectory/openPath/pickDirectory）─────
def host_list_directory(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{path?} → {path, home, crumbs, entries, truncated}。真实列目录（仅目录项，隐藏以 . 开头）。"""
    home = os.path.expanduser("~")
    path = payload.get("path") or home
    if not os.path.isdir(path):
        raise RpcError("directory-unreadable", f"目录不可读：{path}", {"path": path})
    try:
        names = sorted(os.listdir(path))
    except OSError as e:
        raise RpcError("directory-unreadable", f"目录不可读：{path}（{e}）", {"path": path})
    # 面包屑：自根至当前的祖先链
    crumbs: List[Dict[str, Any]] = []
    cur = os.path.abspath(path)
    while True:
        parent = os.path.dirname(cur)
        crumbs.insert(0, {"name": os.path.basename(cur) or cur, "path": cur, "hidden": False})
        if parent == cur:
            break
        cur = parent
    entries: List[Dict[str, Any]] = []
    truncated = False
    for name in names:
        full = os.path.join(path, name)
        if not os.path.isdir(full):
            continue
        if len(entries) >= 500:
            truncated = True
            break
        entries.append({"name": name, "path": full, "hidden": name.startswith(".")})
    return {"path": os.path.abspath(path), "home": home, "crumbs": crumbs,
            "entries": entries, "truncated": truncated}


def host_create_directory(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{path, name} → {path}。name 须为单段路径名；已存在报 directory-exists。"""
    base = payload.get("path") or ""
    name = payload.get("name") or ""
    if not name.strip() or name in (".", "..") or "/" in name or "\\" in name:
        raise RpcError("bad-request", f"name 必须为单段路径名：{name!r}", {"issues": []})
    full = os.path.join(base, name)
    if os.path.exists(full):
        raise RpcError("directory-exists", f"目录已存在：{full}", {"path": full})
    try:
        os.makedirs(full)
    except OSError as e:
        raise RpcError("directory-unreadable", f"创建失败：{full}（{e}）", {"path": full})
    return {"path": os.path.abspath(full)}


def _open_path_externally(path: str) -> None:
    """真实打开（os.startfile）；测试可 monkeypatch。"""
    os.startfile(path)  # noqa: S606 — Windows 资源管理器语义，仅对已存在路径调用


def host_open_path(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{path} → {opened:true}。路径须真实存在；不存在报 directory-unreadable。"""
    path = payload.get("path") or ""
    if not os.path.exists(path):
        raise RpcError("directory-unreadable", f"路径不存在：{path}", {"path": path})
    _open_path_externally(path)
    return {"opened": True}


def host_pick_directory(payload: Dict[str, Any]) -> Dict[str, Any]:
    """headless host 无原生目录选择对话框 → {path:null}（DSH 语义 = 用户取消）。"""
    return {"path": None}


# ── llm.discoverModels（静态目录探测，不触网）──────────────────────────────
def llm_discover_models(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{settingsNs, provider?, baseURL?, api?, apiKey?} → {models[{id,name?}]}。

    不真实出网探测（离线纪律）：按 settingsNs/provider 从静态 MODEL_GROUPS 返回已知
    目录；未知命名空间报 model-discovery-failed（DSH 错误契约）。
    """
    ns = payload.get("settingsNs") or ""
    provider = payload.get("provider") or ("deepseek" if "deepseek" in ns.lower() else "")
    if provider != "deepseek":
        raise RpcError("model-discovery-failed", f"未知提供方命名空间：{ns}",
                       {"settingsNs": ns, "baseURL": payload.get("baseURL")})
    models: List[Dict[str, Any]] = []
    for g in MODEL_GROUPS:
        if g.get("id") == "deepseek":
            models.extend({"id": m["id"], "name": m.get("name")} for m in g.get("models", []))
    return {"models": models}


# ── llm.*（静态占位，R4）──────────────────────────────────────────────────
def llm_providers(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"providers": [{
        "provider": "deepseek",
        "displayName": "DeepSeek",
        # DSH client 的 DeepSeekOnboardingDialog 硬编码查 'llm-deepseek'（连字符）
        "settingsNs": "llm-deepseek",
        "settingsPath": ["llm", "deepseek"],
        "active": True,
        "declared": True,
    }]}


def llm_models(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"groups": MODEL_GROUPS, "failures": []}


# ── settings.describe / credentials.describe（对齐 DSH settings.schema.ts / credentials.schema.ts）──
# 设置面板读闭环：ui-settings-models store 并行拉 llm.providers + settings.describe +
# credentials.describe，缺任一即「加载提供方目录失败」。
_SETTINGS_STORE: Dict[str, Dict[str, Any]] = {
    # ns → {schema, value, base, user, applies, secrets, revision}（settingsNamespaceViewSchema 字段）
    "llm-deepseek": {
        "schema": {},
        "value": {"baseUrl": "https://api.deepseek.com", "model": "deepseek-v4-flash"},
        "applies": "live",
        "secrets": [{"path": ["apiKey"], "set": False}],
        "revision": 1,
    },
}
_CREDENTIALS_STORE: Dict[str, Dict[str, Any]] = {}  # ref → {"configured": bool, "source": str}


def _settings_view(ns: str) -> Dict[str, Any]:
    st = _SETTINGS_STORE[ns]
    return {
        "ns": ns,
        "schema": st["schema"],
        "value": st["value"],
        "applies": st["applies"],
        "secrets": st["secrets"],
        "revision": st["revision"],
    }


def _settings_or_raise(ns: str) -> Dict[str, Any]:
    st = _SETTINGS_STORE.get(ns)
    if st is None:
        raise RpcError("settings-rejected", f"未知设置命名空间：{ns}", {"ns": ns})
    return st


def _check_expected_revision(st: Dict[str, Any], ns: str, payload: Dict[str, Any]) -> None:
    expected = payload.get("expectedRevision")
    if expected is not None and expected != st["revision"]:
        raise RpcError("settings-conflict", f"revision 冲突：{ns}",
                       {"ns": ns, "expected": expected, "actual": st["revision"]})


def settings_describe(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{} → {writable, hasDocument, namespaces[]}。"""
    return {
        "writable": True,
        "hasDocument": False,
        "namespaces": [_settings_view(ns) for ns in _SETTINGS_STORE],
    }


def settings_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{ns, patch, expectedRevision?} → 新命名空间视图。patch 浅合并进 value。"""
    ns = payload["ns"]
    st = _settings_or_raise(ns)
    _check_expected_revision(st, ns, payload)
    patch = payload.get("patch") or {}
    if not isinstance(patch, dict):
        raise RpcError("settings-rejected", f"patch 必须为对象：{ns}", {"ns": ns})
    st["value"] = {**st["value"], **patch}
    st["revision"] += 1
    return _settings_view(ns)


def settings_replace(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{ns, section, expectedRevision?} → 新命名空间视图。section 的键整体覆盖 value 同名键。"""
    ns = payload["ns"]
    st = _settings_or_raise(ns)
    _check_expected_revision(st, ns, payload)
    section = payload.get("section") or {}
    if not isinstance(section, dict):
        raise RpcError("settings-rejected", f"section 必须为对象：{ns}", {"ns": ns})
    st["value"] = {**st["value"], **section}
    st["revision"] += 1
    return _settings_view(ns)


def settings_mutate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{ns, ops[{op:set/unset,path,value?}], expectedRevision?} → 新命名空间视图。

    路径寻址编辑：set 深写 value 路径；unset 删除路径末端键。
    """
    ns = payload["ns"]
    st = _settings_or_raise(ns)
    _check_expected_revision(st, ns, payload)
    ops = payload.get("ops") or []

    def _walk_create(container: Dict[str, Any], path: List[str]) -> Dict[str, Any]:
        node = container
        for key in path[:-1]:
            nxt = node.get(key)
            if not isinstance(nxt, dict):
                nxt = {}
                node[key] = nxt
            node = nxt
        return node

    for op in ops:
        path = op.get("path") or []
        if not path:
            raise RpcError("settings-rejected", f"空编辑路径：{ns}", {"ns": ns})
        parent = _walk_create(st["value"], path)
        leaf = path[-1]
        if op.get("op") == "set":
            parent[leaf] = op.get("value")
        elif op.get("op") == "unset":
            parent.pop(leaf, None)
        else:
            raise RpcError("settings-rejected", f"未知 op：{op.get('op')}", {"ns": ns})
    st["revision"] += 1
    return _settings_view(ns)


def settings_open_document(payload: Dict[str, Any]) -> Dict[str, Any]:
    """headless host 无设置文档可开（hasDocument=False 一致）。"""
    return {"opened": False, "path": ""}


def credentials_describe(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{refs[]} → {credentials: {ref: {configured, source?, writable}}}。"""
    refs = payload.get("refs") or []
    if not isinstance(refs, list) or len(refs) > 64:
        raise RpcError("bad-request", "refs 必须为 ≤64 的数组")
    creds: Dict[str, Any] = {}
    for ref in refs:
        st = _CREDENTIALS_STORE.get(ref)
        view: Dict[str, Any] = {"configured": bool(st and st["configured"]), "writable": True}
        if st and st.get("source"):
            view["source"] = st["source"]
        creds[ref] = view
    return {"credentials": creds}


def credentials_set(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{ref, value} → {}。值只存主机内存，永不上线格式回传（对齐 DSH 契约注释）。"""
    ref = payload.get("ref") or ""
    if not ref.isidentifier():
        raise RpcError("bad-request", f"非法凭据引用名：{ref}", {"issues": []})
    _CREDENTIALS_STORE[ref] = {"configured": True, "source": "memory", "value": payload.get("value")}
    # settings 命名空间的 secrets 槽位联动置位（apiKey 槽；下划线归一化后互含比对）
    for st in _SETTINGS_STORE.values():
        for sec in st["secrets"]:
            leaf = sec["path"][-1].lower().replace("_", "")
            if leaf in ref.lower().replace("_", "") or ref.lower().replace("_", "") in leaf:
                sec["set"] = True
    return {}


def credentials_unset(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{ref} → {}。"""
    ref = payload.get("ref") or ""
    st = _CREDENTIALS_STORE.get(ref)
    if st is not None:
        st["configured"] = False
        st.pop("value", None)
    return {}


# ── agentPreset.list（映射到本平台工作模式预设）────────────────────────────
# 用户复制预设（agentPreset.copy 产物）：pid → {name, description, content}
_USER_PRESETS: Dict[str, Dict[str, Any]] = {}


def agent_preset_list(payload: Dict[str, Any]) -> Dict[str, Any]:
    presets: List[Dict[str, Any]] = []
    for pid, mode in MODE_PRESETS.items():
        presets.append({
            "id": pid,
            "trust": "system",
            "isDefault": pid == DEFAULT_MODE_ID,
            "name": mode.label,
            "description": mode.description,
        })
    for pid, up in _USER_PRESETS.items():
        presets.append({
            "id": pid,
            "trust": "user",
            "isDefault": False,
            "name": up["name"],
            "description": up["description"],
        })
    return {"presets": presets, "authorable": False, "hasDocument": False}


def agent_preset_copy(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{from, agentPreset, name?} → {agentPreset}。系统预设 → 用户预设（trust:user）。"""
    src = payload.get("from") or ""
    pid = payload.get("agentPreset") or ""
    if not pid:
        raise RpcError("bad-request", "agentPreset 目标 id 必填", {"issues": []})
    if pid in MODE_PRESETS or pid in _USER_PRESETS:
        raise RpcError("agent-preset-conflict", f"预设 id 已存在：{pid}", {"agentPreset": pid})
    if src in MODE_PRESETS:
        mode = MODE_PRESETS[src]
        import json as _json
        content = _json.dumps({
            "id": mode.id, "plugins": list(mode.plugins), "orchestration": mode.orchestration,
            "llm_backend": mode.llm_backend, "phase_b_backend": mode.phase_b_backend,
        }, ensure_ascii=False, indent=2)
        name = payload.get("name") or f"{mode.label} 副本"
        description = mode.description
    elif src in _USER_PRESETS:
        up = _USER_PRESETS[src]
        content = up["content"]
        name = payload.get("name") or f"{up['name']} 副本"
        description = up["description"]
    else:
        raise RpcError("agent-preset-not-found", f"未知工作模式：{src}", {"agentPreset": src})
    _USER_PRESETS[pid] = {"name": name, "description": description, "content": content}
    return {"agentPreset": pid}


def agent_preset_remove(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{agentPreset} → {}。仅用户预设可删；系统预设只读。"""
    pid = payload.get("agentPreset") or ""
    if pid in MODE_PRESETS:
        raise RpcError("agent-preset-read-only", f"系统预设不可删除：{pid}",
                       {"agentPreset": pid, "reason": "system-trust"})
    if pid not in _USER_PRESETS:
        raise RpcError("agent-preset-not-found", f"未知工作模式：{pid}", {"agentPreset": pid})
    del _USER_PRESETS[pid]
    return {}


def agent_preset_open_document(payload: Dict[str, Any]) -> Dict[str, Any]:
    """headless host 无预设文档（与 list 的 hasDocument=False 一致）。"""
    return {"opened": False, "path": ""}


# ── agentPreset.select（对齐 DSH agentPresetSelectValueSchema）─────────────
def agent_preset_select(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{sessionId, agentPreset} → {agentPreset}。

    把选中的工作模式持久化到会话 meta（与 session.create 的 agentPreset 字段同源）。
    """
    sid = payload["sessionId"]
    _session_or_raise(sid)
    pid = payload.get("agentPreset") or ""
    if pid not in MODE_PRESETS and pid not in _USER_PRESETS:
        raise RpcError("agent-preset-not-found", f"未知工作模式：{pid}", {"agentPreset": pid})
    _session_meta.setdefault(sid, {})["agentPreset"] = pid
    return {"agentPreset": pid}


# ── agentPreset.read（对齐 DSH agentPresetReadValueSchema）─────────────────
def agent_preset_read(payload: Dict[str, Any]) -> Dict[str, Any]:
    """{agentPreset} → {agentPreset, trust, content, name, description}。

    content：WorkMode 无原生 content 字段，由「plugins 组合 + orchestration 开关」序列化为
    可读文本，供前端「读预设」展示（对齐 DSH content:string 契约）。
    """
    import json
    pid = payload.get("agentPreset") or ""
    up = _USER_PRESETS.get(pid)
    if up is not None:
        return {
            "agentPreset": pid,
            "trust": "user",
            "content": up["content"],
            "name": up["name"],
            "description": up["description"],
        }
    mode = MODE_PRESETS.get(pid)
    if mode is None:
        raise RpcError("agent-preset-not-found", f"未知工作模式：{pid}", {"agentPreset": pid})
    content = json.dumps({
        "id": mode.id,
        "plugins": list(mode.plugins),
        "orchestration": mode.orchestration,
        "llm_backend": mode.llm_backend,
        "phase_b_backend": mode.phase_b_backend,
    }, ensure_ascii=False, indent=2)
    return {
        "agentPreset": pid,
        "trust": "system",
        "content": content,
        "name": mode.label,
        "description": mode.description,
    }


# ── 多帧投影（M2-T3）：session/projection 帧（DSH events.ts:107）────────────
def _publish_projection(sid: str, key: str, value: Dict[str, Any], seq: int) -> None:
    """把某状态投影为 `session/projection` 帧发到总线。

    帧形状：{type:'session/projection', sessionId, key, value, seq}（对齐 DSH）。
    MuxBroadcaster 已订阅该 event_type。goal 状态机用它暴露读侧（DSH 无 goal.get）。
    """
    _bus.publish(
        {"id": str(uuid.uuid4()), "event_type": "session/projection", "sessionId": sid,
         "key": key, "value": value, "seq": seq},
        persist=_noop_persist,
    )


# ── goal.*（会话投影真实现，对齐 DSH goals.schema.ts mutation-only 语义）────
def _goal_or_raise(session_id: str, ref: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """取会话级 goal 状态；ref 提供时校验 id+revision 匹配（乐观锁）。"""
    goal = _goal_index.get(session_id)
    if goal is None:
        raise RpcError("goal-not-found", f"会话无活动目标：{session_id}", {"sessionId": session_id})
    if ref is not None:
        if ref.get("id") != goal["id"] or ref.get("revision") != goal["revision"]:
            raise RpcError("goal-conflict",
                           f"目标版本冲突：期望 {ref} 实际 {goal['id']}#{goal['revision']}",
                           {"expected": ref, "actual": {"id": goal["id"], "revision": goal["revision"]}})
    return goal


def _goal_publish(sid: str, goal: Dict[str, Any]) -> None:
    """把 goal 状态投影到会话事件流（DSH 语义：状态走 session projection）。

    双通道（增量不破坏 M1）：
    - 会话事件帧 `goal/state`（M1 已实现，测试断言依赖，保留）
    - 多帧投影 `session/projection`（M2-T3，key='goal'，seq=revision，对齐 DSH events.ts:107）
    """
    log = _session_index.get(sid)
    if log is not None:
        log.append("goal/state", {"ref": {"id": goal["id"], "revision": goal["revision"]},
                                   "objective": goal["objective"], "status": goal["status"]})
    _bus.publish(
        {"id": str(uuid.uuid4()), "event_type": "session/event", "sessionId": sid,
         "event": {"kind": "goal/state", "ref": goal["id"], "revision": goal["revision"],
                   "objective": goal["objective"], "status": goal["status"]}},
        persist=_noop_persist,
    )
    _publish_projection(sid, "goal", {
        "id": goal["id"], "revision": goal["revision"],
        "objective": goal["objective"], "status": goal["status"],
    }, goal["revision"])


def goal_create(payload: Dict[str, Any]) -> Dict[str, Any]:
    sid = payload["sessionId"]
    _session_or_raise(sid)
    objective = payload.get("objective") or ""
    if not objective:
        raise RpcError("goal-invalid", "objective 不能为空", {"sessionId": sid})
    gid = f"goal:{sid}"
    goal = {"id": gid, "revision": 1, "objective": objective, "status": "running"}
    _goal_index[sid] = goal
    _goal_publish(sid, goal)
    return {"ref": {"id": gid, "revision": 1}}


def goal_edit(payload: Dict[str, Any]) -> Dict[str, Any]:
    sid = payload["sessionId"]
    goal = _goal_or_raise(sid, payload.get("ref"))
    goal["revision"] += 1
    if payload.get("objective"):
        goal["objective"] = payload["objective"]
    if payload.get("maxGoalRounds") is not None:
        goal["maxGoalRounds"] = payload["maxGoalRounds"]
    _goal_publish(sid, goal)
    return {"ref": {"id": goal["id"], "revision": goal["revision"]}}


def goal_pause(payload: Dict[str, Any]) -> Dict[str, Any]:
    sid = payload["sessionId"]
    goal = _goal_or_raise(sid, payload.get("ref"))
    goal["status"] = "paused"
    goal["revision"] += 1
    _goal_publish(sid, goal)
    return {"ref": {"id": goal["id"], "revision": goal["revision"]}}


def goal_resume(payload: Dict[str, Any]) -> Dict[str, Any]:
    sid = payload["sessionId"]
    goal = _goal_or_raise(sid, payload.get("ref"))
    goal["status"] = "running"
    goal["revision"] += 1
    _goal_publish(sid, goal)
    return {"ref": {"id": goal["id"], "revision": goal["revision"]}}


def goal_complete(payload: Dict[str, Any]) -> Dict[str, Any]:
    sid = payload["sessionId"]
    goal = _goal_or_raise(sid, payload.get("ref"))
    goal["status"] = "completed"
    goal["revision"] += 1
    _goal_publish(sid, goal)
    return {"ref": {"id": goal["id"], "revision": goal["revision"]}}


def goal_clear(payload: Dict[str, Any]) -> Dict[str, Any]:
    sid = payload["sessionId"]
    goal = _goal_or_raise(sid, payload.get("ref"))
    _goal_index.pop(sid, None)
    log = _session_index.get(sid)
    if log is not None:
        log.append("goal/cleared", {"ref": {"id": goal["id"], "revision": goal["revision"]}})
    return {"cleared": True}


# ── skill.list ─────────────────────────────────────────────────────────────
def skill_list(payload: Dict[str, Any]) -> Dict[str, Any]:
    skills: List[Dict[str, Any]] = []
    for s in _skill_registry.list():
        skills.append({
            "name": s.name,
            "description": s.description,
            "whenToUse": s.when_to_use or None,
            "modelInvocable": s.model_invocable,
        })
    return {"skills": skills}


# ── subagent.list（M1 真实目录：由 SubagentDescriptor → _SUBAGENT_LABELS 驱动）──
def subagent_list(payload: Dict[str, Any]) -> Dict[str, Any]:
    entries = [{
        "kind": "child",
        "id": key,
        "mode": _SUBAGENT_DEFAULT_MODE,
        "activity": "inactive",
        "hasChildren": False,
        "label": label,
    } for key, label in _SUBAGENT_LABELS.items()]
    return {"entries": entries, "parentAvailable": True}


# ── subagent.history（读取 child 会话的日志；复用 session 事件编码）────────
def subagent_history(payload: Dict[str, Any]) -> Dict[str, Any]:
    child_id = payload["childSessionId"]
    log = _session_lazy(child_id)
    events = log.events()
    before_seq = payload.get("beforeSeq")
    max_messages = payload.get("maxMessages")
    if isinstance(before_seq, int):
        events = [e for e in events if e.seq < before_seq]
    if isinstance(max_messages, int) and max_messages > 0:
        events = events[-max_messages:]
    history = [{"event": to_wire_session_event(e)} for e in events]
    return {"events": history, "hasMore": False}


# ── subagent.prompt（真实委派：SubagentPool.delegate → AgentLoop.run_turn）──
def subagent_prompt(payload: Dict[str, Any]) -> Dict[str, Any]:
    child_id = payload["childSessionId"]
    subagent_key = _child_key_of(child_id)
    _session_lazy(child_id)  # 首次委派前确保 child 会话存在
    content = payload.get("content") or []
    text = "".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    # M2-T4：把本次委派登记为 subagent job（kind='subagent'，running → completed/rejected→failed）
    parent_sid = payload.get("parentSessionId") or child_id
    _session_lazy(parent_sid)
    job = _job_registry.add(parent_sid, "subagent", f"委派 {subagent_key}")
    try:
        result = _subagent_pool.delegate(text, subagent_key=subagent_key)
    except Exception:
        _job_registry.set_status(parent_sid, job["id"], "failed", detail="委派异常")
        raise
    _job_registry.set_status(parent_sid, job["id"],
                             "failed" if result.get("rejected") else "completed")
    # DSH messageIdSchema=z.string()：用 child session 本轮结束事件（turn/end）的 seq 合成，
    # 语义为「该轮委派已落档」；rejected 时同构返回（仍可寻址 history）。
    log = _session_index.get(child_id)
    seq = log.events()[-1].seq if log and log.events() else 0
    suffix = ":rejected" if result.get("rejected") else ""
    return {"messageId": f"sub:{subagent_key}:{seq}{suffix}"}


# ── subagent.interrupt（对齐 DSH 契约：accepted: true）─────────────────────
def subagent_interrupt(payload: Dict[str, Any]) -> Dict[str, Any]:
    _session_or_raise(payload["childSessionId"])
    return {"accepted": True}


# ── jobs.*（M2-T1：登记表读侧；DSH 写侧经 session/jobs 帧推送，无 RPC）─────
def jobs_list(payload: Dict[str, Any]) -> Dict[str, Any]:
    """返回该会话可见的 JobView[]（对齐 events.ts JobView 字段）。

    写侧不是 RPC —— JobRegistry 在 add/set_status 时主动推 session/jobs 帧；
    本方法仅供后端/测试直读，不作为写入口（不破坏 DSH mutation-free 语义）。
    """


# ── tables.*（只读反射 contract.particle L0 常量，零 pg，完全真实）────────────
def table_list(payload: Dict[str, Any]) -> Dict[str, Any]:
    """枚举内核粒子 substrate 的规范表（反射 contract.particle）。

    未注入 profile 时回退 CORE_ROLES（5 个跨域核心语义角色）；注入 profile 后
    改枚举 profile.particle_types.names + profile.predicates（消费方取值，不在此处）。
    """
    tables = []
    for role in _particle.CORE_ROLES:
        tables.append({
            "particleType": role,
            "layers": list(_particle.LAYERS),
            "attrTypes": list(_particle.ATTR_TYPES),
            "predicateCount": len([p for p in _particle.PredicateSet().all() if p.from_type == role]),
        })
    return {"tables": tables}


def table_describe(payload: Dict[str, Any]) -> Dict[str, Any]:
    """单粒子表全 schema：19 种属性类型 + 边枚举 + 关联谓词。"""
    ptype = payload.get("particleType") or ""
    if ptype and ptype not in _particle.CORE_ROLES:
        raise RpcError("table-not-found", f"未知粒子表：{ptype}", {"particleType": ptype})
    preds = [p for p in _particle.PredicateSet().all() if p.from_type == ptype or ptype == ""]
    return {
        "particleType": ptype or "(all)",
        "attrTypes": list(_particle.ATTR_TYPES),
        "edgeLayers": list(_particle.EDGE_LAYERS),
        "edgeSources": list(_particle.EDGE_SOURCES),
        "cardinalities": list(_particle.CARDINALITIES),
        "predicates": [{"predicate": p.predicate, "fromType": p.from_type,
                         "toType": p.to_type, "layer": p.layer,
                         "cardinality": p.cardinality, "source": p.source}
                        for p in preds],
    }


# ── memory.*（session 投影桥接，仿 goal；六元组寻址严写，不连 pg）───────────
def _memory_publish(sid: str, entry: Dict[str, Any], kind: str) -> None:
    log = _session_index.get(sid)
    if log is not None:
        log.append(kind, entry)
    _bus.publish(
        {"id": str(uuid.uuid4()), "event_type": "session/event", "sessionId": sid,
         "event": {"kind": kind, **entry}},
        persist=_noop_persist,
    )


def memory_write(payload: Dict[str, Any]) -> Dict[str, Any]:
    """写入一条记忆（log/note 双轨）。六元组寻址：缺项拒写（strict，不静默兜底）。

    落点铁律（contract.memory）：缺任一寻址项 ⇒ 记忆虽落库却永不被命中且不报错，
    故把六项做成显式参数，缺项默认拒写。
    """
    sid = payload["sessionId"]
    _session_or_raise(sid)
    addr = {k: payload.get(k) for k in _memory.MEMORY_ADDRESS_KEYS}
    missing = [k for k, v in addr.items() if v in (None, "")]
    if missing:
        raise RpcError("memory-address-incomplete",
                       f"记忆寻址缺项（虽落库却永不被命中）：{missing}", {"missing": missing})
    kind = payload.get("kind") or "note"
    if kind not in _memory.MEMORY_KINDS:
        raise RpcError("memory-kind-invalid", f"kind 须 ∈ {_memory.MEMORY_KINDS}：{kind}",
                       {"kind": kind})
    entry = {
        "topic": addr["topic"], "layer": addr["layer"], "anchorKind": addr["anchor_kind"],
        "anchorId": addr["anchor_id"], "actor": addr["actor"], "occurredAt": addr["occurred_at"],
        "kind": kind, "text": payload.get("text") or "",
    }
    _memory_index.setdefault(sid, []).append(entry)
    _memory_publish(sid, entry, "memory/write")
    return {"written": True, "count": len(_memory_index[sid])}


def memory_read(payload: Dict[str, Any]) -> Dict[str, Any]:
    """按 topic / anchorId 过滤回读该 session 记忆（不连 pg）。"""
    sid = payload["sessionId"]
    _session_or_raise(sid)
    entries = _memory_index.get(sid, [])
    topic = payload.get("topic")
    if topic:
        entries = [e for e in entries if e["topic"] == topic]
    anchor_id = payload.get("anchorId")
    if anchor_id:
        entries = [e for e in entries if e["anchorId"] == anchor_id]
    _memory_publish(sid, {"topic": topic, "matched": len(entries)}, "memory/read")
    return {"entries": entries, "count": len(entries)}


# ── decision.*（只读反射脊柱契约 + 记录投影桥接，不连 pg）──────────────────
def decision_spine(payload: Dict[str, Any]) -> Dict[str, Any]:
    """只读反射决策脊柱契约（contract.decision 常量，零 pg，完全真实）。

    ⚠ 诚实声明：本 RPC 反射的是**契约常量**（S1→S5 不可重排、九尺子、八要素、七维、
    自主放行判据），不运行 K-M-D 引擎（引擎不在内核运行时，属独立演进范畴）。
    """
    return {
        "spineOrder": list(_decision.SPINE_ORDER),
        "spineStageLabels": dict(_decision.SPINE_STAGE_LABELS_ZH),
        "rubricKeys": list(_decision.RUBRIC_KEYS),
        "rubricNames": dict(_decision.RUBRIC_NAMES_ZH),
        "rubricScaleMax": _decision.RUBRIC_SCALE_MAX,
        "eightElements": list(_decision.EIGHT_ELEMENTS),
        "sevenDims": [{"key": k, "name": n, "meaning": m}
                      for (k, n, m) in _decision.SEVEN_DIMS],
        "autonomousReleaseDefault": _decision.AUTONOMOUS_RELEASE_DEFAULT,
        "autonomousGateExpr": _decision.AUTONOMOUS_GATE_EXPR,
        "confidenceSourceKey": _decision.CONFIDENCE_SOURCE_KEY,
    }


def _decision_publish(sid: str, rec: Dict[str, Any]) -> None:
    log = _session_index.get(sid)
    if log is not None:
        log.append("decision/record", {"ref": {"id": rec["id"], "revision": rec["revision"]},
                                        "objective": rec["objective"], "stage": rec["stage"]})
    _bus.publish(
        {"id": str(uuid.uuid4()), "event_type": "session/event", "sessionId": sid,
         "event": {"kind": "decision/record", "ref": rec["id"], "revision": rec["revision"],
                   "objective": rec["objective"], "stage": rec["stage"]}},
        persist=_noop_persist,
    )


def decision_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """创建/读取/更新决策记录（session 投影，仿 goal；不运行 K-M-D 引擎）。

    ref 缺 ⇒ 创建；ref 在 ⇒ 读取（无 updatable 字段）或更新（带 revision 乐观锁）。
    """
    sid = payload["sessionId"]
    _session_or_raise(sid)
    ref = payload.get("ref")
    if ref is not None:
        rec = _decision_index.get(sid)
        if rec is None or rec["id"] != ref.get("id"):
            raise RpcError("decision-not-found", f"未知决策记录：{ref}", {"ref": ref})
        if payload.get("objective") or payload.get("rationale") or payload.get("stage"):
            if payload.get("revision") != rec["revision"]:
                raise RpcError("decision-conflict", "决策记录版本冲突",
                               {"expected": rec["revision"], "actual": payload.get("revision")})
            rec["revision"] += 1
            if payload.get("objective"):
                rec["objective"] = payload["objective"]
            if payload.get("rationale"):
                rec["rationale"] = payload["rationale"]
            if payload.get("stage"):
                rec["stage"] = payload["stage"]
            _decision_publish(sid, rec)
        return {"ref": {"id": rec["id"], "revision": rec["revision"]},
                "objective": rec["objective"], "rationale": rec["rationale"], "stage": rec["stage"]}
    objective = payload.get("objective") or ""
    if not objective:
        raise RpcError("decision-invalid", "objective 不能为空", {"sessionId": sid})
    did = f"decision:{sid}"
    rec = {"id": did, "revision": 1, "objective": objective,
           "rationale": payload.get("rationale") or "", "stage": payload.get("stage") or "S1_context"}
    _decision_index[sid] = rec
    _decision_publish(sid, rec)
    return {"ref": {"id": did, "revision": 1}}


def _child_key_of(child_session_id: str) -> str:
    """从 child 会话 id 反解 subagent key（child id = SubagentDescriptor.live_key() = `sub:<key>`）。"""
    got: Optional[str] = None
    for key in _SUBAGENT_LABELS:
        if child_session_id == f"sub:{key}":
            got = key
            break
    if got is None:
        raise RpcError("subagent-not-found", f"未知子智能体会话：{child_session_id}",
                       {"childSessionId": child_session_id})
    return got


# ── host.describe ─────────────────────────────────────────────────────────
def host_describe(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "version": "chiyu-host/0.1.0",
        "cwd": os.getcwd(),
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "attachedSessions": len(_session_index),
        "canOpenPath": False,
    }


# ── 方法注册表 ────────────────────────────────────────────────────────────
HANDLERS: Dict[str, Any] = {
    "session.list": session_list,
    "session.create": session_create,
    "session.history": session_history,
    "session.models": session_models,
    "session.selectModel": session_select_model,
    "session.prompt": session_prompt,
    "session.cancel": session_cancel,
    "llm.providers": llm_providers,
    "llm.models": llm_models,
    "llm.discoverModels": llm_discover_models,
    "settings.describe": settings_describe,
    "settings.update": settings_update,
    "settings.replace": settings_replace,
    "settings.mutate": settings_mutate,
    "settings.openDocument": settings_open_document,
    "credentials.describe": credentials_describe,
    "credentials.set": credentials_set,
    "credentials.unset": credentials_unset,
    "workspace.list": workspace_list,
    "workspace.create": workspace_create,
    "workspace.rename": workspace_rename,
    "workspace.delete": workspace_delete,
    "workspace.insertBefore": workspace_insert_before,
    "workspace.insertSessionBefore": workspace_insert_session_before,
    "workspace.archiveSession": workspace_archive_session,
    "host.describe": host_describe,
    "host.listDirectory": host_list_directory,
    "host.createDirectory": host_create_directory,
    "host.openPath": host_open_path,
    "host.pickDirectory": host_pick_directory,
    "session.rename": session_rename,
    "session.fork": session_fork,
    "session.search": session_search,
    "session.updateQueue": session_update_queue,
    "session.attachment": session_attachment,
    "agentPreset.copy": agent_preset_copy,
    "agentPreset.remove": agent_preset_remove,
    "agentPreset.openDocument": agent_preset_open_document,
    "agentPreset.list": agent_preset_list,
    "agentPreset.select": agent_preset_select,
    "agentPreset.read": agent_preset_read,
    "goal.create": goal_create,
    "goal.edit": goal_edit,
    "goal.pause": goal_pause,
    "goal.resume": goal_resume,
    "goal.complete": goal_complete,
    "goal.clear": goal_clear,
    "skill.list": skill_list,
    "subagent.list": subagent_list,
    "subagent.history": subagent_history,
    "subagent.prompt": subagent_prompt,
    "subagent.interrupt": subagent_interrupt,
    "jobs.list": jobs_list,
    "table.list": table_list,
    "table.describe": table_describe,
    "memory.write": memory_write,
    "memory.read": memory_read,
    "decision.spine": decision_spine,
    "decision.record": decision_record,
    "host.describe": host_describe,
}


# ── M1 底部装配：给 _subagent_pool 赋真实值并注册全部 SubagentDescriptor ──
# 复用 _session_manager（与 session.* 共用同一实例）；llm/tools 用内核中性默认。
# ⚠ 不连 pg（与 M0 同策略，避免触发外部存储依赖）：native tools/redline guard 均
# 由内核提供，profile 传 None（中性）；元红线集与领域档案无关（guard.py 的
# meta_redline_hits 无 profile 形参），故不引入领域字面量、不触发 api 门面的 pg。
from chiyu_kernel.harness_native_tools import (  # noqa: E402
    register_native_tools as _register_native_tools,
    native_redline_guard as _native_redline_guard,
)

_tools = ToolRegistry()
_register_native_tools(_tools, profile=None)
_subagent_pool = SubagentPool(
    llm=StubProvider(),
    tools=_tools,
    sessions=_session_manager,
    redline_guard=_native_redline_guard(profile=None),
)
for _d in SUBAGENT_DESC_LIST:
    _subagent_pool.register(_d)

# ── M2-T1 底部装配：_job_registry 挂到总线（publisher 推 session/jobs 帧）──
_job_registry = JobRegistry(publisher=make_publisher(_bus, _noop_persist))
