"""ChiYu Portal 后端：把 chiyu_kernel 门面 + chiyu_portal 渲染层暴露为 Web API。

- /api/bootstrap       → 内核真实能力（四种模式 / 原生工具）
- /api/chat            → composer 发送，真实调用内核原生工具（mini agent loop）
- /api/portal/onboarding   → 复用 chiyu_portal.render_onboarding 的真实 HTML
- /api/portal/conversation → 复用 chiyu_portal.render_conversation 的真实 HTML
- /                    → 生产环境托管构建产物 web/dist（开发由 Vite 负责）

⛔ 消费方仅经 chiyu_kernel.api / chiyu_portal.api 门面，不碰内核内部路径。
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import llm_bridge
import account_store
from kernel_bridge import (
    get_bootstrap, run_turn,
    portal_onboarding_html, portal_conversation_html,
)
import scenario_bridge
from scenario_bridge import ScenarioLockNotConfirmed, PlatformUnreachable
from chiyu_kernel.api import ScenarioPackError, ScenarioPackLockDenied

app = FastAPI(title="ChiYu Portal API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_TAG = "api"


@app.get("/api/health", tags=[API_TAG])
def health() -> Dict[str, Any]:
    return {"status": "ok", "kernel": "chiyu_kernel.api", "portal": "chiyu_portal.api"}


@app.get("/api/bootstrap", tags=[API_TAG])
def bootstrap() -> Dict[str, Any]:
    return get_bootstrap()


@app.get("/api/llm/status", tags=[API_TAG])
def llm_status() -> Dict[str, Any]:
    """Phase B LLM 可用性（如实：key 是否配置、联网搜索是否接通）。"""
    return llm_bridge.llm_status()


# ── LLM 设置（UI 可写；文件 llm_config.local.json 持久化，env 兜底）──────────
class LlmConfigRequest(BaseModel):
    provider: str = "deepseek"
    baseUrl: str = ""
    apiKey: str = ""
    modelChat: str = ""
    modelReasoner: str = ""


@app.get("/api/llm/config", tags=[API_TAG])
def llm_config_get() -> Dict[str, Any]:
    """当前 LLM 配置（apiKey 一律脱敏；keySource 标明来源 file/env/none）。"""
    import llm_config
    c = llm_config.get_effective()
    return {
        "provider": c["provider"],
        "baseUrl": c["baseUrl"],
        "apiKeyMasked": llm_config.mask_key(c["apiKey"]),
        "modelChat": c["modelChat"],
        "modelReasoner": c["modelReasoner"],
        "keySource": c["keySource"],
        "available": bool(c["apiKey"]),
        "configFile": str(llm_config.CONFIG_PATH),
    }


@app.put("/api/llm/config", tags=[API_TAG])
def llm_config_put(req: LlmConfigRequest) -> Dict[str, Any]:
    """保存 LLM 配置到本地文件（apiKey 可留空表示不动已有值）。"""
    import llm_config
    cur = llm_config.load()
    incoming = req.model_dump()
    # apiKey 为空 → 保留文件中已有值（避免 UI 回显脱敏值把 key 冲掉）
    if not incoming.get("apiKey", "").strip():
        incoming["apiKey"] = cur.get("apiKey", "")
    saved = llm_config.save(incoming)
    eff = llm_config.get_effective()
    return {
        "ok": True,
        "apiKeyMasked": llm_config.mask_key(eff["apiKey"]),
        "keySource": eff["keySource"],
        "available": bool(eff["apiKey"]),
        "configFile": str(llm_config.CONFIG_PATH),
        "saved": {k: (llm_config.mask_key(v) if k == "apiKey" and v else v)
                  for k, v in saved.items()},
    }


@app.post("/api/llm/test", tags=[API_TAG])
def llm_test() -> Dict[str, Any]:
    """连通性实测（真实最小请求），成败如实返回——不假绿。"""
    return llm_bridge.llm_test()


# ── 平台账号（token 登录）：真实探测企业 host 校验，本地持久化，脱敏回显 ──────
@app.get("/api/account/status", tags=[API_TAG])
def account_status() -> Dict[str, Any]:
    """当前平台账号登录态（token 脱敏；tenant/role 由 token 解析，非客户端自报）。"""
    return account_store.status()


class AccountLoginRequest(BaseModel):
    token: str = ""


@app.post("/api/account/login", tags=[API_TAG])
def account_login(req: AccountLoginRequest) -> Dict[str, Any]:
    """token 登录：语法解析 + 真实探测企业 host（只读端点）；平台不可达时如实标注未验证。"""
    if not req.token.strip():
        raise HTTPException(status_code=400, detail="token 不能为空")
    try:
        return account_store.login(req.token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/account/logout", tags=[API_TAG])
def account_logout() -> Dict[str, Any]:
    account_store.logout()
    return {"ok": True}


# ── 企业控制面桥：把 chiyu-enterprise host(:8000 /control/*) 聚合进本前端 ────
# 8123 是该看板的纯静态服务器（python -m http.server）；/control/* 真实数据在
# enterprise.host.app（默认 :8000，可用 ENTERPRISE_API_BASE 覆盖）。此处后端代理，
# 避免浏览器跨域，并如实上报不可达（不假绿）。
_ENTERPRISE_BASE = os.environ.get("ENTERPRISE_API_BASE", "http://127.0.0.1:8000").rstrip("/")
_CONTROL_ALLOWED = {
    "dashboard", "tenants", "scenarios", "providers",
    "approvals", "redline", "audit", "rbac", "governance",
}


@app.get("/api/enterprise/control/{name}", tags=["enterprise"])
def enterprise_control(name: str) -> Response:
    if name not in _CONTROL_ALLOWED:
        raise HTTPException(status_code=404, detail=f"未知控制面端点：{name}")
    target = f"{_ENTERPRISE_BASE}/control/{name}"
    req = urllib.request.Request(target, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read()
            return Response(content=body, media_type="application/json",
                            headers={"X-Enterprise-Base": _ENTERPRISE_BASE})
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"reachable": False, "target": target, "error": str(e)},
        )


class ChatRequest(BaseModel):
    text: str
    mode: str = "standard"
    deep_think: bool = False
    web_search: bool = False
    # 向导选择透传（向后兼容：缺省视为未选择）
    direction: Optional[str] = None
    workflow: Optional[str] = None
    level: Optional[str] = None


@app.post("/api/chat", tags=[API_TAG])
def chat(req: ChatRequest) -> Dict[str, Any]:
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="text 不能为空")
    return run_turn(req.text, req.mode, req.deep_think, req.web_search,
                    direction=req.direction, workflow=req.workflow, level=req.level)


# ── 门户渲染层「打通」端点：直接返回 chiyu_portal 的真实 HTML ──────────────
@app.get("/api/portal/onboarding", tags=["portal"])
def portal_onboarding() -> HTMLResponse:
    return HTMLResponse(portal_onboarding_html())


class ConversationRenderRequest(BaseModel):
    goal: str = ""
    messages: List[Dict[str, str]] = []


@app.post("/api/portal/conversation", tags=["portal"])
def portal_conversation(req: ConversationRenderRequest) -> HTMLResponse:
    return HTMLResponse(portal_conversation_html(req.goal, req.messages))


# ── 导出：当前对话 → chiyu_portal.render_conversation 真实 HTML 下载 ────────
@app.post("/api/export/conversation", tags=["portal"])
def export_conversation(req: ConversationRenderRequest) -> Response:
    html = portal_conversation_html(req.goal, req.messages)
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"chiyu-conversation-{stamp}.html"
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── 场景包（ScenarioPack）：双入口生成 + 选择/锁定 + WorkflowRunner 真运行 ──
class ScenarioGenerateRequest(BaseModel):
    direction: str = "generic"
    workflow: str = "decide"
    level: str = "flow"
    mode: str = "standard"
    id: Optional[str] = None
    name: Optional[str] = None


@app.get("/api/scenario/list", tags=[API_TAG])
def scenario_list() -> Dict[str, Any]:
    try:
        return {"packs": scenario_bridge.list_packs()}
    except PlatformUnreachable as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))


@app.post("/api/scenario/generate", tags=[API_TAG])
def scenario_generate(req: ScenarioGenerateRequest) -> Dict[str, Any]:
    try:
        return scenario_bridge.generate(req.model_dump())
    except ScenarioPackError as e:
        raise HTTPException(status_code=400, detail=f"[{e.code}] {e}")
    except PlatformUnreachable as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))


class ScenarioSelectRequest(BaseModel):
    id: str


@app.post("/api/scenario/select", tags=[API_TAG])
def scenario_select(req: ScenarioSelectRequest) -> Dict[str, Any]:
    try:
        return scenario_bridge.select(req.id)
    except ScenarioPackError as e:
        raise HTTPException(status_code=404, detail=f"[{e.code}] {e}")
    except PlatformUnreachable as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))


class ScenarioLockRequest(BaseModel):
    id: str
    holder: str = "web"
    confirm: bool = False


@app.post("/api/scenario/lock", tags=[API_TAG])
def scenario_lock(req: ScenarioLockRequest) -> Dict[str, Any]:
    try:
        return scenario_bridge.lock(req.id, req.holder, req.confirm)
    except ScenarioLockNotConfirmed as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ScenarioPackError as e:
        raise HTTPException(status_code=409, detail=f"[{e.code}] {e}")
    except PlatformUnreachable as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))


class ScenarioMcpCallRequest(BaseModel):
    tool: str
    args: Dict[str, Any] = {}


@app.post("/api/scenario/mcp-call", tags=[API_TAG])
def scenario_mcp_call(req: ScenarioMcpCallRequest) -> Dict[str, Any]:
    try:
        return scenario_bridge.mcp_call(req.tool, req.args)
    except ScenarioPackError as e:
        raise HTTPException(status_code=400, detail=f"[{e.code}] {e}")
    except ScenarioPackLockDenied as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PlatformUnreachable as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))


class ScenarioRunRequest(BaseModel):
    id: str


@app.post("/api/scenario/run", tags=[API_TAG])
def scenario_run(req: ScenarioRunRequest) -> Dict[str, Any]:
    try:
        return scenario_bridge.run(req.id)
    except ScenarioPackError as e:
        raise HTTPException(status_code=404, detail=f"[{e.code}] {e}")
    except PlatformUnreachable as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))


# ── 生产环境：托管前端构建产物（开发由 Vite dev server 负责）────────────────
_DIST = Path(__file__).resolve().parent.parent / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")


if __name__ == "__main__":
    import os
    import uvicorn
    # 默认 8011，避免与已运行的 enterprise.host.app(:8000) 冲突
    _port = int(os.environ.get("CHIYU_API_PORT", "8011"))
    uvicorn.run(app, host="127.0.0.1", port=_port)
