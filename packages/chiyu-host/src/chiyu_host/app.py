"""FastAPI 应用：单一 RPC 路由器 + mux WebSocket + boot manifest 端点。

契约（实测 DSH apiproxy，非早期 SSE 假设）：
- RPC：POST /api/<method>，body=ClientRequest 全形，响应=ServerResponse 全形
- mux：WebSocket /api/events.mux，下行帧=ServerRequest 全形 + MuxFrame payload
- boot：GET /api/boot?base_url=... 返回供 T3 launcher 注入的 manifest
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Set, Tuple

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from . import methods
from .boot import build_boot_manifest
from . import web as web_surface
from . import control as control_api
from . import rpc_control as rpc_control_api


app = FastAPI(title="chiyu-host", version="0.1.0")
app.include_router(control_api.router)          # 只读 /control/*
app.include_router(rpc_control_api.write_router)  # 写 /control/*（dev 隔离 + G0 锚 + confirm）


@app.post("/api/{method:path}")
async def rpc(method: str, request: Request) -> Dict[str, Any]:
    body = await request.json()
    rpc_id = body.get("rpcId")
    method_name = body.get("method") or method
    payload = body.get("payload") or {}
    handler = methods.HANDLERS.get(method_name)
    if handler is None:
        result: Dict[str, Any] = {
            # DSH 官方 rpcErrorSchema 对 bad-request 分支强制 details.issues 数组
            # （discriminatedUnion；details:{} 会使 client 端 union 解析失败并在 UI
            # 上露出原始 zod 报错串——M0-T3 真渲染验证实测）。
            "ok": False,
            "error": {
                "code": "bad-request",
                "message": f"未知方法：{method_name}",
                "details": {"issues": []},
            },
        }
    else:
        try:
            value = handler(payload)
            result = {"ok": True, "value": value}
        except methods.RpcError as e:
            details = e.details
            if e.code == "bad-request" and "issues" not in details:
                details = {**details, "issues": []}
            result = {"ok": False, "error": {"code": e.code, "message": e.message, "details": details}}
        except Exception as e:  # noqa: BLE001 — 捕获一切转 internal 错误分支
            result = {"ok": False, "error": {"code": "internal", "message": str(e), "details": {}}}
    return {"type": "server-response", "rpcId": rpc_id, "result": result}


@app.get("/api/boot")
async def boot(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    return build_boot_manifest(base_url)


# ── Web 表面：同源托管 DSH client（重建 clientModules）──
# DSH client API base = window.location.origin → 必须由 chiyu-host 同源提供，
# 页面 origin 即 chiyu-host，零 base-URL 覆写对接。
@app.get("/")
async def index() -> HTMLResponse:
    try:
        return HTMLResponse(web_surface.index_html())
    except FileNotFoundError:
        return HTMLResponse(
            "<h1>chiyu-host</h1><p>DSH client 未构建：先 pnpm install + "
            "build:lib:client + build:web（apps/web/dist/index.html 缺失）。</p>",
            status_code=503,
        )


@app.get("/plugins/{pkg_path:path}")
async def plugin_bundle(pkg_path: str) -> Response:
    # 包名含 '/'（如 @deepseek-ai/dsh-client-ui-conversation），故用 :path 捕获后剥离后缀
    if not pkg_path.endswith("/client.js"):
        return Response("not found", status_code=404, media_type="text/plain")
    pkg_id = pkg_path[: -len("/client.js")]
    path = web_surface.plugin_path(pkg_id)
    if path is None or not Path(path).exists():
        return Response("not found", status_code=404, media_type="text/plain")
    return Response(Path(path).read_bytes(), media_type="text/javascript")


_assets = web_surface.assets_dir()
if _assets is not None:
    app.mount("/assets", StaticFiles(directory=_assets), name="assets")


def _serve_dist_root_file(name: str) -> Response:
    """serve apps/web/dist 根级静态文件（favicon.svg / manifest.webmanifest 等）。"""
    import os
    root = os.environ.get("DSH_CLIENT_DIR") or web_surface.DEFAULT_DSH_CLIENT_DIR
    p = Path(root) / "apps" / "web" / "dist" / name
    if not p.exists():
        return Response("not found", status_code=404, media_type="text/plain")
    return Response(p.read_bytes())


@app.get("/favicon.svg")
async def favicon() -> Response:
    return _serve_dist_root_file("favicon.svg")


@app.get("/manifest.webmanifest")
async def webmanifest() -> Response:
    return _serve_dist_root_file("manifest.webmanifest")


@app.websocket("/api/events.mux")
async def mux_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    queue: "asyncio.Queue[str]" = asyncio.Queue()

    def sync_send(text: str) -> None:
        queue.put_nowait(text)

    methods._mux.add_connection(sync_send)
    try:
        while True:
            receive_task = asyncio.create_task(websocket.receive_text())
            send_task = asyncio.create_task(queue.get())
            done, pending = await asyncio.wait(
                {receive_task, send_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if send_task in done:
                text = send_task.result()
                await websocket.send_text(text)
            if receive_task in done:
                try:
                    receive_task.result()
                except WebSocketDisconnect:
                    break
                # 客户端上行（responded 等）M0 忽略
            for t in pending:
                t.cancel()
    finally:
        methods._mux.remove_connection(sync_send)
