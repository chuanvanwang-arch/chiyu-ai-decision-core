"""本地 stdio MCP server —— 开发阶段把场景包写入平台（chiyu-host）。

工具面（3 个动作，防 CRUD 爆炸）：
  scenario-pack-write   收 kernel ScenarioPack dict → 调平台 POST /control/scenarios
  scenario-pack-list    读平台 GET /control/scenarios
  scenario-pack-lock    锁定（confirm:true 必须，HITL）

用法：<py> mcp_scenario_server.py          # 标准 stdio MCP（读 stdin 写 stdout）
平台 base：环境变量 CHIYU_PLATFORM（默认 http://127.0.0.1:8000）
开发身份 token：环境变量 CHIYU_DEV_TOKEN（默认 t-default-dev.admin）

⚠️ import 约定：本脚本可能被「文件加载」方式导入（tests 用 importlib），
   也作为独立入口运行；chiyu_kernel / chiyu_host 依赖由执行环境提供
   （仓根 venv 或 conftest 注入 sys.path），因此业务 import 放在函数内并兜底。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict

PLATFORM = os.environ.get("CHIYU_PLATFORM", "http://127.0.0.1:8000")
DEV_TOKEN = os.environ.get("CHIYU_DEV_TOKEN", "t-default-dev.admin")


def _ensure_chiyu_paths() -> None:
    """把仓根 packages/*/src 加入 sys.path（独立运行 / 文件加载两种场景兜底）。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("chiyu-kernel", "chiyu-host"):
        src = os.path.join(root, "packages", name, "src")
        if os.path.isdir(src) and src not in sys.path:
            sys.path.insert(0, src)


def _http(method: str, path: str, body: Any = None) -> Dict[str, Any]:
    url = PLATFORM + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {DEV_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:200]
        raise RuntimeError(f"HTTP {e.code} {path}: {detail}") from e


def _tool_write(args: Dict[str, Any]) -> Dict[str, Any]:
    pack = args.get("pack")
    if not isinstance(pack, dict) or not pack.get("id"):
        raise ValueError("pack 必填且含 id（kernel ScenarioPack 形态）")
    _ensure_chiyu_paths()
    from chiyu_kernel.api import scenario_from_dict  # noqa: PLC0415
    from chiyu_host.scenario_mapper import pack_to_platform  # noqa: PLC0415
    scenario_from_dict(pack)  # 写前本地校验（同闸）
    platform = pack_to_platform(pack, tenant=args.get("tenant") or "t-default")
    return _http("POST", "/control/scenarios", platform)


def _tool_list(_args: Dict[str, Any]) -> Dict[str, Any]:
    return _http("GET", "/control/scenarios")


def _tool_lock(args: Dict[str, Any]) -> Dict[str, Any]:
    pkg = args.get("id") or args.get("pkg")
    confirm = args.get("confirm") is True
    if not confirm:
        raise ValueError("scenario-pack-lock 为写操作：须 confirm:true（HITL）")
    return _http("POST", f"/control/scenario/{pkg}/lock",
                 {"holder": args.get("holder") or "dev", "confirm": True})


def build_server():
    from chiyu_kernel.mcp import InMemoryMcpServer  # noqa: PLC0415
    _ensure_chiyu_paths()
    return InMemoryMcpServer({
        "scenario-pack-write": ("写场景包到平台（kernel ScenarioPack）", _tool_write),
        "scenario-pack-list": ("列平台场景包", _tool_list),
        "scenario-pack-lock": ("锁定场景包（需 confirm:true）", _tool_lock),
    })


def main() -> None:
    _ensure_chiyu_paths()
    server = build_server()
    # 标准 stdio MCP：逐行读 JSON-RPC，逐条 reply
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        req_id = req.get("id")
        method = req.get("method")
        result: Any
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05",
                      "serverInfo": {"name": "chiyu-scenario", "version": "0.1.0"}}
        elif method == "tools/list":
            result = {"tools": [
                {"name": t.raw_name, "description": t.description}
                for t in server.list_tools()]}
        elif method == "tools/call":
            name = req.get("params", {}).get("name")
            args = req.get("params", {}).get("arguments") or {}
            try:
                out = server.call_tool(name, args)
                result = {"content": [{"type": "text",
                                       "text": json.dumps(out, ensure_ascii=False)}]}
            except KeyError:
                result = {"isError": True,
                          "content": [{"type": "text", "text": f"未知工具：{name}"}]}
            except Exception as e:  # noqa: BLE001
                result = {"isError": True,
                          "content": [{"type": "text", "text": str(e)}]}
        else:
            result = {}
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result},
                                    ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
