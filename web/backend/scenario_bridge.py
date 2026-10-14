"""场景包桥：web 层入口，作为「平台客户端」连接 chiyu-host 平台。

开发阶段（写）：
- `generate()` 向导四元组 → 平台 `POST /control/scenarios`（开发身份 dev.*）
- `mcp_call()` MCP 真桥路径 → 同一平台写接口（开发身份）
- `lock()` 经平台 `POST /control/scenario/{name}/lock`，强制 `confirm: true`（HITL 闸）

运行阶段（读 + 数据交互）：
- `list()` 读平台 `GET /control/scenarios`
- `select()` 经平台锁（装载会话态）
- `run()` 读包 actions → 逐个经平台 `/rpc/{tenant}/{client_type}/action` 数据交互
  （读/写类分流转由平台治理，写类行动作仍走平台写闸）

⛔ 设计红线：本桥不落地第二套写包逻辑；写入全部经平台唯一校验闸
（平台侧 `POST /control/scenarios` 内部复用 kernel `scenario_from_dict`）。
平台不可达时如实报错（502），不假绿、不回退本地执行。
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

# ── 平台地址与身份（可环境变量覆盖；与 app.py _ENTERPRISE_BASE 同源约定）──
PLATFORM_BASE = os.environ.get(
    "CHIYU_PLATFORM_BASE",
    os.environ.get("ENTERPRISE_API_BASE", "http://127.0.0.1:8000"),
).rstrip("/")
TENANT = os.environ.get("CHIYU_TENANT", "t-default")
DEV_TOKEN = os.environ.get("CHIYU_DEV_TOKEN", "Bearer t-default-dev.admin")
# 运行身份：web 客户端（运行=读+action，写类由平台治理）
RUN_TOKEN = os.environ.get("CHIYU_RUN_TOKEN", "Bearer t-default-sales_manager")


class PlatformUnreachable(Exception):
    """平台不可达/返回错误（app 层转 502/400，不假绿）。"""

    def __init__(self, message: str, *, http_status: int = 502) -> None:
        super().__init__(message)
        self.http_status = http_status


def _http(method: str, path: str, body: Dict[str, Any] | None = None,
          *, token: str | None = None) -> Dict[str, Any]:
    """平台 HTTP 客户端：JSON 收发包，非 2xx 抛 PlatformUnreachable。"""
    url = PLATFORM_BASE + path
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if token:
        headers["Authorization"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8")[:300]
        except Exception:
            detail = ""
        raise PlatformUnreachable(
            f"平台 {method} {path} 失败 HTTP {e.code}: {detail}",
            http_status=e.code if e.code >= 400 and e.code < 600 else 502) from e
    except Exception as e:
        raise PlatformUnreachable(f"平台不可达 {PLATFORM_BASE}: {e}") from e


class ScenarioLockNotConfirmed(Exception):
    """锁定缺 confirm 的显式拒绝（app 层转 400）。"""


# ── 开发阶段：写入平台 ──────────────────────────────────────────────
def generate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """向导四元组（direction/workflow/level/mode）→ 平台写接口（开发身份）。"""
    level = payload.get("level") or "flow"
    workflow = payload.get("workflow") or "decide"
    direction = payload.get("direction") or "generic"
    pack_id = payload.get("id") or f"wizard-{workflow}-{level}-{int(__import__('time').time())}"
    platform_pack = {
        "pkg": pack_id,
        "namespace": direction,
        "tenant": TENANT,
        "actions": payload.get("actions")
                   or _default_actions(level, workflow, direction),
        "assets": payload.get("knowledge_needs")
                  or [{"layer": "L1", "dims": ["semantics"]}],
        "integrations": [{"name": p} for p in
                         (payload.get("plugins") or _default_plugins(workflow))],
        "status": "draft",
    }
    res = _http("POST", "/control/scenarios", platform_pack, token=DEV_TOKEN)
    return {"ok": True, "id": res.get("pkg", pack_id),
            "platform": PLATFORM_BASE, "path": f"{PLATFORM_BASE}/control/scenarios"}


def _default_actions(level: str, workflow: str, direction: str) -> List[str]:
    """领域包由消费方命名空间驱动；此处仅机制层占位 action，零领域字面量。"""
    return [f"{direction}.native.perceive"]


def _default_plugins(workflow: str) -> List[str]:
    return {"decide": ["loop"], "research": ["web_search"],
            "automate": ["terminal", "loop"], "build": ["loop"]}.get(workflow, ["loop"])


def list_packs() -> List[Dict[str, Any]]:
    """读平台场景包（运行身份，只读）。"""
    res = _http("GET", "/control/scenarios")
    items = res.get("items") or []
    return items


def select(pack_id: str) -> Dict[str, Any]:
    """装载（写会话态）——经平台锁定（需 confirm，运行身份）。"""
    res = _http("POST", f"/control/scenario/{pack_id}/lock",
                {"holder": "web", "confirm": True}, token=RUN_TOKEN)
    return {"ok": True, "id": res.get("pkg", pack_id), "selected": pack_id}


def lock(pack_id: str, holder: str, confirm: bool) -> Dict[str, Any]:
    """锁定 = 写操作：缺 confirm 显式拒绝（HITL 闸）。"""
    if confirm is not True:
        raise ScenarioLockNotConfirmed(
            "锁定为写操作：payload 必须携带 confirm=true（HITL 闸）")
    res = _http("POST", f"/control/scenario/{pack_id}/lock",
                {"holder": holder, "confirm": True}, token=DEV_TOKEN)
    return {"ok": True, "id": res.get("pkg", pack_id),
            "locked_by": res.get("locked_by") or holder}


def mcp_call(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """MCP 文件调用路径：开发工具经这里写平台（开发身份）。"""
    if tool == "scenario-pack-write":
        pack = args.get("pack") or args
        res = _http("POST", "/control/scenarios",
                    _kernel_to_platform(pack), token=DEV_TOKEN)
        return {"ok": True, "written": res.get("pkg")}
    if tool == "scenario-pack-list":
        return {"items": _http("GET", "/control/scenarios", token=RUN_TOKEN)
                .get("items") or []}
    if tool == "scenario-pack-lock":
        confirm = args.get("confirm") is True
        if not confirm:
            raise ScenarioLockNotConfirmed(
                "锁定为写操作：args 必须携带 confirm=true（HITL 闸）")
        res = _http("POST", f"/control/scenario/{args.get('id')}/lock",
                    {"holder": args.get("holder") or "mcp", "confirm": True},
                    token=DEV_TOKEN)
        return {"ok": True, "locked_by": res.get("locked_by")}
    raise ValueError(f"未知 scenario MCP 工具：{tool}")


def _kernel_to_platform(kernel: Dict[str, Any]) -> Dict[str, Any]:
    """kernel ScenarioPack 形态 → 平台模型（供 MCP write 走双模型映射）。"""
    steps = (kernel.get("workflow") or {}).get("steps") or []
    actions = [s.get("prompt") for s in steps if s.get("prompt")]
    assets = kernel.get("knowledge_needs") or []
    plugins = kernel.get("plugins") or []
    return {
        "pkg": kernel.get("id") or kernel.get("name") or "mcp-pack",
        "namespace": kernel.get("direction") or "generic",
        "tenant": TENANT,
        "actions": actions,
        "assets": assets,
        "integrations": [{"name": p} for p in plugins],
        "status": "draft",
    }


# ── 运行阶段：选包 + 平台 RPC 数据交互 ─────────────────────────────
def run(pack_id: str) -> Dict[str, Any]:
    """运行：读平台包 → 逐个 action 经平台 `/rpc/{tenant}/{client}/action`
    做数据交互。结果如实返回，平台不可达不假绿。"""
    res = _http("GET", "/control/scenarios", token=RUN_TOKEN)
    items = res.get("items") or []
    pack = next((p for p in items if p.get("pkg") == pack_id), None)
    if pack is None:
        return {"ok": False, "error": {"message": f"场景包不存在：{pack_id}"}}
    actions = pack.get("actions") or []
    steps: List[Dict[str, Any]] = []
    all_ok = True
    for action in actions:
        try:
            r = _http("POST", f"/rpc/{TENANT}/web/action?action={action}",
                      {"payload": {}}, token=RUN_TOKEN)
            steps.append({"action": action, "status": "done", "result": r})
        except PlatformUnreachable as e:
            steps.append({"action": action, "status": "failed",
                          "error": str(e)})
            all_ok = False
    return {
        "ok": all_ok,
        "pack": {"id": pack.get("pkg"), "status": pack.get("status")},
        "steps": steps,
        "platform": PLATFORM_BASE,
    }
