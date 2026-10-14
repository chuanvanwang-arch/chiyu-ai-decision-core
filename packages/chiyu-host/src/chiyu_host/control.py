"""chiyu-host 只读控制面：/control/scenarios(读)、/control/scenario/{name}、
/control/rbac、/control/agents/{role}。写接口在 rpc_control.py（分离读写文件）。
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from .scenario_store import ROLL_ROLES, PlatformScenarioStore

router = APIRouter(prefix="/control", tags=["control-readonly"])

_users = [
    {"user": "admin", "role": "admin"},
    {"user": "finance-1", "role": "finance"},
    {"user": "sales-mgr", "role": "sales_manager"},
    {"user": "dev.alice", "role": "dev.admin"},
]


@router.get("/scenarios")
async def list_scenarios() -> Dict[str, Any]:
    store = PlatformScenarioStore()
    return {"items": store.list()}


@router.get("/scenario/{name}")
async def get_scenario(name: str) -> Dict[str, Any]:
    store = PlatformScenarioStore()
    pack = store.get(name)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"场景包不存在：{name}")
    return pack


@router.get("/rbac")
async def rbac() -> Dict[str, Any]:
    users = [
        {**u, "permissions": ROLL_ROLES.get(u["role"], [])} for u in _users
    ]
    return {"users": users}


@router.get("/agents/{role}")
async def agents_by_role(role: str) -> Dict[str, Any]:
    perms = ROLL_ROLES.get(role)
    if perms is None:
        raise HTTPException(status_code=404, detail=f"未知角色：{role}")
    users = [u["user"] for u in _users if u["role"] == role]
    return {"role": role, "permissions": perms, "users": users}
