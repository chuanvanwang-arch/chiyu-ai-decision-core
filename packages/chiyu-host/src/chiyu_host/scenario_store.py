"""平台场景包存储 + RBAC 简单角色表（本仓 host 作为可替换 8000 的平台侧）。

⛔ 双模型映射：平台模型 = {pkg/namespace/tenant/actions/assets/integrations/status}。
kernel ScenarioPack 校验闸在 scenario_mapper（单一校验逻辑，不重复）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# 平台包存储目录：优先环境变量，退到 <host>/scenario_packs
DEFAULT_PACKS_DIR = Path(__file__).resolve().parent.parent / "scenario_packs"

# RBAC 权威角色表（与 8000 /control/rbac 语义一致；真实源可替换）
ROLL_ROLES: Dict[str, List[str]] = {
    "admin": ["scenario.read", "scenario.write", "action.run"],
    "finance": ["scenario.read", "action.run"],
    "sales_manager": ["scenario.read", "action.run"],
    "dev.admin": ["scenario.read", "scenario.write", "action.run"],
}


def packs_dir() -> Path:
    env = os.environ.get("CHIYU_PACKS_DIR")
    return Path(env) if env else DEFAULT_PACKS_DIR


class PlatformScenarioStore:
    """平台场景包目录存储：扫描/读写/锁定。锁定 = 写操作（confirm 由调用层把关）。"""

    def __init__(self, directory: str | os.PathLike[str] | None = None) -> None:
        self._dir = Path(directory) if directory else packs_dir()
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, pkg: str) -> Path:
        if not pkg or "/" in pkg or "\\" in pkg or pkg.startswith("."):
            raise ValueError(f"非法 pkg：{pkg!r}")
        return self._dir / f"{pkg}.json"

    def save(self, pack: Dict[str, Any]) -> Path:
        pkg = pack.get("pkg")
        if not pkg:
            raise ValueError("pack.pkg 必填")
        p = self._path(pkg)
        # 深拷贝以免调用方后续改动污染
        payload = json.loads(json.dumps(pack))
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    def get(self, pkg: str) -> Optional[Dict[str, Any]]:
        p = self._path(pkg)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def list(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for f in sorted(self._dir.glob("*.json")):
            try:
                items.append(json.loads(f.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        return items

    def lock(self, pkg: str, holder: str) -> Dict[str, Any]:
        pack = self.get(pkg)
        if pack is None:
            raise KeyError(f"场景包不存在：{pkg}")
        cur = pack.get("locked_by")
        if cur is not None and cur != holder:
            raise PermissionError(f"场景包已由 {cur} 锁定")
        pack["locked_by"] = holder
        pack["status"] = "active"
        self.save(pack)
        return pack

    def unlock(self, pkg: str, holder: str, *, force: bool = False) -> Dict[str, Any]:
        pack = self.get(pkg)
        if pack is None:
            raise KeyError(f"场景包不存在：{pkg}")
        cur = pack.get("locked_by")
        if cur is not None and cur != holder and not force:
            raise PermissionError(f"场景包由 {cur} 锁定，非 {holder} 不能解锁")
        pack.pop("locked_by", None)
        pack["status"] = "draft"
        self.save(pack)
        return pack
