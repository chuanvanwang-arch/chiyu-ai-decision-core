"""chiyu-host Web 表面：离线重建 DSH clientModules 服务（boot 图合成 + 静态托管）。

DSH client 的 API base = window.location.origin（connection/src/client/rpc.ts:52），
故必须由 chiyu-host 同源托管 client，使其 origin 即 chiyu-host，从而零 base-URL 覆写对接。

__DSH_BOOT__ 由 DSH host 运行时合成（packages/client/modules/src/index.ts compose()），
此处离线复刻：扫描声明 dsh.client.platform==='web' 的包，每条
{id, url:'/plugins/<id>/client.js?rev=<sha1-12>', rev, inject?, immediately?}。
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DSH_CLIENT_DIR = r"D:\system\reference\deepseek-harness-master"

_SURFACE_CACHE: Dict[str, Tuple[Dict[str, Any], Dict[str, str]]] = {}


def _short_hash(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()[:12]


def _client_export_of(pkg: Dict[str, Any]) -> Optional[str]:
    exp = pkg.get("exports")
    if not isinstance(exp, dict):
        return None
    client = exp.get("./client")
    if isinstance(client, str):
        return client
    if isinstance(client, dict):
        default = client.get("default")
        return default if isinstance(default, str) else None
    return None


def _scan_web_boot_rows(dsh_root: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """扫描 packages/* /* 中 dsh.client.platform==='web' 的包 → (boot 行, id→包体路径)。

    - 仅收录已构建（lib/client.js 存在）的包，避免 404 行导致白屏。
    - id_to_path 供 GET /plugins/<id>/client.js 直接寻址（包名含 '/'，故用映射而非路径拼接）。
    """
    root = Path(dsh_root)
    rows: List[Dict[str, Any]] = []
    id_to_path: Dict[str, str] = {}
    for pkg_json in sorted(root.glob("packages/*/*/package.json")):
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
        except Exception:
            continue
        dsh = pkg.get("dsh")
        decl = dsh.get("client") if isinstance(dsh, dict) else None
        if not isinstance(decl, dict) or decl.get("platform") != "web":
            continue
        name = pkg.get("name")
        client_rel = _client_export_of(pkg)
        if not name or not client_rel:
            continue
        client_path = pkg_json.parent / client_rel
        if not client_path.exists():
            # 包体未构建（build:lib:client 未跑）→ 跳过
            continue
        rev = _short_hash(client_path.read_bytes())
        row: Dict[str, Any] = {
            "id": name,
            "url": f"/plugins/{name}/client.js?rev={rev}",
            "rev": rev,
        }
        inject = decl.get("inject")
        if isinstance(inject, list) and inject:
            row["inject"] = inject
        if decl.get("immediately") is True:
            row["immediately"] = True
        rows.append(row)
        id_to_path[name] = str(client_path)
    return rows, id_to_path


def compose_boot_graph(dsh_root: str) -> Dict[str, Any]:
    rows, _ = _scan_web_boot_rows(dsh_root)
    return {"rev": _short_hash(json.dumps(rows, sort_keys=True).encode()), "entries": rows}


def get_surface(dsh_root: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """返回 (boot 图, id→包体路径)，按 dsh_root 缓存。"""
    root = dsh_root or os.environ.get("DSH_CLIENT_DIR") or DEFAULT_DSH_CLIENT_DIR
    cached = _SURFACE_CACHE.get(root)
    if cached is None:
        rows, id_to_path = _scan_web_boot_rows(root)
        graph = {"rev": _short_hash(json.dumps(rows, sort_keys=True).encode()), "entries": rows}
        cached = (graph, id_to_path)
        _SURFACE_CACHE[root] = cached
    return cached


def inject_boot_manifest(html: str, graph: Dict[str, Any]) -> str:
    """同 DSH injectBootManifest：< 转义防插件字符串逃逸 script 元素。"""
    payload = json.dumps(graph).replace("<", "\\u003c")
    script = f"<script>window.__DSH_BOOT__ = {payload}</script>"
    idx = html.find("<head>")
    if idx != -1:
        return f"{html[:idx + 6]}{script}{html[idx + 6:]}"
    return f"{script}{html}"


def index_html(dsh_root: Optional[str] = None) -> str:
    root = dsh_root or os.environ.get("DSH_CLIENT_DIR") or DEFAULT_DSH_CLIENT_DIR
    web_dist = Path(root) / "apps" / "web" / "dist"
    html = (web_dist / "index.html").read_text(encoding="utf-8")
    graph, _ = get_surface(root)
    return inject_boot_manifest(html, graph)


def plugin_path(pkg_id: str, dsh_root: Optional[str] = None) -> Optional[str]:
    _, id_to_path = get_surface(dsh_root)
    return id_to_path.get(pkg_id)


def assets_dir(dsh_root: Optional[str] = None) -> Optional[str]:
    root = dsh_root or os.environ.get("DSH_CLIENT_DIR") or DEFAULT_DSH_CLIENT_DIR
    d = Path(root) / "apps" / "web" / "dist" / "assets"
    return str(d) if d.is_dir() else None
