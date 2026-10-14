"""平台账号（token）持久化与真实校验（web/backend 本地文件，不改内核）。

token 形态与 chiyu-enterprise host/author.py 规约一致：
  `t-<tenant-id>-<role>-<id>`（3+ 段，含角色）或 `t-<tenant-id>-<id>`（2 段，无角色）。
⛔ tenant/role 只从 token 解析，绝不信任客户端自报（与 host 零信任纪律一致）。

登录校验：真实探测企业 host 只读端点 GET /rpc/{tenant}/desktop/control-plane
（带 Bearer；200 = token 有效，401 = token 无效，连接失败 = 平台不可达 →
如实标注「未验证」，不假绿）。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_PATH = Path(__file__).resolve().parent / "account.local.json"

ENTERPRISE_BASE = os.environ.get("ENTERPRISE_API_BASE", "http://127.0.0.1:8000").rstrip("/")


def load() -> Dict[str, Any]:
    """读本地账号文件；不存在/损坏返回空 dict。"""
    if not CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save(data: Dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                           encoding="utf-8")


def clear() -> None:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()


def mask_token(token: str) -> str:
    if not token:
        return "未登录"
    return (token[:5] + "…" + token[-4:]) if len(token) > 12 else "已配置"


def parse_token(token: str) -> Optional[Dict[str, str]]:
    """token → {tenantId, role}；无 `t-` 前缀或租户段为空 → None（不可信）。

    规则对齐 chiyu-enterprise auth.py：
    - tenant-id = `t-` 后到下一个 '-' 前的段；
    - role = 段数 >=3 时的第 2 段；2 段旧形态无 role。
    """
    token = (token or "").strip()
    if not token.startswith("t-"):
        return None
    rest = token[2:]
    segs = rest.split("-")
    tenant_id = segs[0] if segs else ""
    if not tenant_id:
        return None
    role = segs[1] if len(segs) >= 3 and segs[1] else ""
    return {"tenantId": tenant_id, "role": role}


def probe_enterprise(token: str, tenant_id: str) -> Dict[str, Any]:
    """真实探测企业 host：token 是否被平台接受。只读端点，无副作用。"""
    url = f"{ENTERPRISE_BASE}/rpc/{tenant_id}/desktop/control-plane"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return {"reachable": True, "verified": True, "http": resp.status,
                    "detail": ""}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"reachable": True, "verified": False, "http": 401,
                    "detail": "平台拒绝该 token（401）：token 无效或已过期"}
        return {"reachable": True, "verified": False, "http": e.code,
                "detail": f"平台返回 HTTP {e.code}"}
    except Exception as e:
        return {"reachable": False, "verified": False, "http": 0,
                "detail": f"平台不可达（{ENTERPRISE_BASE}）：{e}"}


def status() -> Dict[str, Any]:
    """当前登录态（token 脱敏；绝不回传明文）。"""
    data = load()
    token = (data.get("token") or "").strip()
    parsed = parse_token(token) if token else None
    return {
        "loggedIn": bool(token and parsed),
        "tenantId": parsed["tenantId"] if parsed else "",
        "role": parsed["role"] if parsed else "",
        "tokenMasked": mask_token(token) if token else "",
        "verified": bool(data.get("verified")),
        "verifiedDetail": data.get("verifiedDetail", ""),
        "enterpriseBase": ENTERPRISE_BASE,
        "configFile": str(CONFIG_PATH),
    }


def login(token: str) -> Dict[str, Any]:
    """token 登录：本地解析 + 真实探测平台；结果如实落盘并返回。"""
    token = (token or "").strip()
    parsed = parse_token(token)
    if not parsed:
        raise ValueError("token 格式无效：须为 t-<租户>-<角色>-<id> 形式（以 t- 开头）")
    probe = probe_enterprise(token, parsed["tenantId"])
    save({
        "token": token,
        "verified": probe["verified"],
        "verifiedDetail": probe["detail"],
        "enterpriseBase": ENTERPRISE_BASE,
    })
    st = status()
    st["probe"] = {k: probe[k] for k in ("reachable", "verified", "http", "detail")}
    return st


def logout() -> None:
    clear()


__all__ = ["CONFIG_PATH", "load", "save", "clear", "mask_token",
           "parse_token", "probe_enterprise", "status", "login", "logout"]
