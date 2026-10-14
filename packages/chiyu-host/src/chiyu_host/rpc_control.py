"""chiyu-host 写控制面：POST /control/scenarios（写）、/control/scenario/{name}/lock。

⛔ 权限隔离红线：仅 dev.* 用户名（或 admin）+ 写权限 可写；其他角色 403（运行只读）。
⛔ 写操作 G0 决策锚：本实现以「dev.* 用户名 + confirm 显式确认」作为决策锚占位，
   生产接真实 G0 审批（不在本范围，见设计 §8）。
"""
from __future__ import annotations

import re
from typing import Any, Dict

from fastapi import APIRouter, Body, Header, HTTPException

from .scenario_mapper import ScenarioPackError, validate_platform
from .scenario_store import ROLL_ROLES, PlatformScenarioStore

write_router = APIRouter(prefix="/control", tags=["control-write"])


def _resolve_role(authorization: str | None) -> str:
    """从 Bearer token 解析角色（dev token 约定：t-{tenant}-{role}）。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="缺 Authorization: Bearer <token>")
    token = authorization.split(" ", 1)[1].strip()
    parts = token.split("-")
    # t-default-finance-1 → tenant=default, role=finance, idx=1
    if len(parts) < 3 or parts[0] != "t":
        raise HTTPException(status_code=401, detail="token 格式非法")
    role = parts[2]
    if role not in ROLL_ROLES:
        raise HTTPException(status_code=403, detail=f"未知角色：{role}")
    return role


def _assert_can_write(authorization: str | None) -> None:
    role = _resolve_role(authorization)
    perms = ROLL_ROLES.get(role, [])
    if "scenario.write" not in perms:
        raise HTTPException(status_code=403,
                            detail=f"角色 {role} 无场景包写权限（开发/运行隔离）")


@write_router.post("/scenarios")
async def write_scenario(
    platform: Dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    _assert_can_write(authorization)
    try:
        validate_platform(platform)
    except ScenarioPackError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    store = PlatformScenarioStore()
    store.save(platform)
    return platform


@write_router.post("/scenario/{name}/lock")
async def lock_scenario(
    name: str,
    body: Dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    _assert_can_write(authorization)
    confirm = body.get("confirm") is True
    if not confirm:
        raise HTTPException(status_code=400, detail="锁定为写操作：须 confirm:true（HITL）")
    store = PlatformScenarioStore()
    try:
        return store.lock(name, holder=body.get("holder") or "dev")
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@write_router.post("/scenario/{name}/unlock")
async def unlock_scenario(
    name: str,
    body: Dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    _assert_can_write(authorization)
    store = PlatformScenarioStore()
    try:
        return store.unlock(name, holder=body.get("holder") or "dev",
                            force=body.get("force") is True)
    except (PermissionError, KeyError) as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
