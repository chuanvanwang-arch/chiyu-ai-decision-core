"""ScenarioPackStore —— 包落盘 / 目录扫描 / 选择与锁定状态。

锁定语义（设计 §2）：
- `lock(pack_id, holder)` 幂等；已锁再锁须同 holder，异 holder 抛错。
- `unlock(pack_id, holder)` 仅 holder 本人可解锁；`force=True` 显式强制（供管理面）。
- 锁定状态随包 JSON 持久化（`locked_by` 字段），跨进程重启不丢。

目录约定：`*.json` 一包一文件；非 .json 与子目录忽略。损坏文件**显式报错**
（禁静默跳过——静默丢包与「禁静默中间态」同族）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .model import ScenarioPack, ScenarioPackError, from_dict

__all__ = ["ScenarioPackStore"]


class ScenarioPackStore:
    """包存储：扫描目录 + 注册 + 选择/锁定状态（单实例持有）。"""

    def __init__(self, directory: str | os.PathLike[str]) -> None:
        self._dir = Path(directory)
        self._packs: Dict[str, ScenarioPack] = {}
        self._selected: Optional[str] = None

    # ── 落盘与扫描 ────────────────────────────────────────────────────────────
    @property
    def directory(self) -> Path:
        return self._dir

    def _path(self, pack_id: str) -> Path:
        return self._dir / f"{pack_id}.json"

    def save(self, pack: ScenarioPack) -> Path:
        """写盘并登记（校验闸由调用方 from_dict 承担；save 只负责落盘一致）。"""
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._path(pack.id)
        path.write_text(
            json.dumps(pack.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        self._packs[pack.id] = pack
        return path

    def scan(self) -> List[str]:
        """扫描目录装载全部 `*.json` 包；返回本次装载的 pack id（排序）。"""
        self._packs.clear()
        if not self._dir.exists():
            return []
        for path in sorted(self._dir.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            pack = from_dict(raw)
            self._packs[pack.id] = pack
        return sorted(self._packs)

    # ── 查询 ─────────────────────────────────────────────────────────────────
    def get(self, pack_id: str) -> ScenarioPack:
        pack = self._packs.get(pack_id)
        if pack is None:
            raise ScenarioPackError(f"场景包不存在：{pack_id!r}", "PACK_NOT_FOUND")
        return pack

    def list(self) -> List[Dict[str, Any]]:
        """列包（含 selected 状态徽标，排序稳定）。"""
        out: List[Dict[str, Any]] = []
        for pid in sorted(self._packs):
            d = self._packs[pid].to_dict()
            d["selected"] = pid == self._selected
            out.append(d)
        return out

    @property
    def selected(self) -> Optional[str]:
        return self._selected

    # ── 选择与锁定 ────────────────────────────────────────────────────────────
    def select(self, pack_id: str) -> ScenarioPack:
        """选择装载（会话态，非持久写）。"""
        pack = self.get(pack_id)
        self._selected = pack_id
        return pack

    def lock(self, pack_id: str, holder: str) -> ScenarioPack:
        """锁定：幂等；同 holder 重锁静默成功，异 holder 抛错（PACK_ALREADY_LOCKED）。"""
        pack = self.get(pack_id)
        if pack.locked_by is not None and pack.locked_by != holder:
            raise ScenarioPackError(
                f"场景包已由 {pack.locked_by!r} 锁定，{holder!r} 不得重锁",
                "PACK_ALREADY_LOCKED")
        pack.locked_by = holder
        self.save(pack)  # 锁定状态持久化
        return pack

    def unlock(self, pack_id: str, holder: str, *, force: bool = False) -> ScenarioPack:
        """解锁：仅 holder 本人（或显式 force）。"""
        pack = self.get(pack_id)
        if pack.locked_by is not None and pack.locked_by != holder and not force:
            raise ScenarioPackError(
                f"场景包由 {pack.locked_by!r} 锁定，{holder!r} 无权解锁（force 可强制）",
                "PACK_LOCKED_OTHER")
        pack.locked_by = None
        self.save(pack)
        return pack
