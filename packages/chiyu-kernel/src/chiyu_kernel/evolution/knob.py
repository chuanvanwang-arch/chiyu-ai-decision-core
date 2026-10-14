"""运行参数表（白名单 + 风险分档）—— 照抄 `orchestration/dispatch_cfg` 的三条硬化。

⛔ 为什么白名单外键一律忽略
──────────────────────────
配置面 ≠ 隐式接口面。若允许"配置里写了就认"，自进化通道就能靠**新增键**给自己造权，
而每一步单独看都只是一次合法的配置变更。

⛔ 为什么"放宽方向"必须声明而不能内核推断
────────────────────────────────────────
阈值变小在自主权阈值上是**放宽**，在冷却天数上却是**收紧**。推断必错，错了就是
自我扩权：平台逐步下调自己的阈值，把人工在环静默架空，且每一步都像"小步调参"。
故 `widen_direction` 必须显式声明，**缺失即在构造期抛错**（拦在构造期，而非运行期）。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from chiyu_kernel.contract import (
    DIR_FLAT,
    DIR_TIGHTEN,
    DIR_WIDEN,
    TIER_AUTO,
    TIER_FORBIDDEN,
    TIER_GUARDED,
)


class KnobError(KernelError):
    code = "CONTRACT_VIOLATION"
    """参数表契约违规（未知风险档 / 非法方向 / 重复注册 / 非白名单键）⇒ 抛，不静默。"""


@dataclass(frozen=True)
class KnobSpec:
    name: str
    tier: str = TIER_AUTO
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default: Optional[float] = None
    # 值朝哪边变化算"放宽自主权"："down" = 变小是放宽，"up" = 变大是放宽，None = 无关
    widen_direction: Optional[str] = None
    # 是否与自主权相关 ⇒ 相关者的"放宽"永不自动（护栏 G1）
    autonomy_related: bool = False

    def __post_init__(self) -> None:
        if self.tier not in (TIER_AUTO, TIER_GUARDED, TIER_FORBIDDEN):
            raise KnobError(f"未知风险档：{self.tier!r}（合法集 auto/guarded/forbidden）")
        if self.widen_direction not in (None, "down", "up"):
            raise KnobError(
                f"widen_direction 须为 'down'/'up'/None：{self.widen_direction!r}")
        if self.autonomy_related and self.widen_direction is None:
            raise KnobError(
                f"自主权相关参数必须声明 widen_direction：{self.name!r}"
                "（否则无法判定放宽方向 ⇒ 自我扩权不可检出）")
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                raise KnobError(
                    f"区间倒置：{self.name!r} min={self.min_value} > max={self.max_value}")
        if self.default is not None:
            ok, why = self.clamp_check(self.default)
            if not ok:
                raise KnobError(f"出厂兜底值自身越界：{self.name!r} {why}")

    def clamp_check(self, value: Any) -> Tuple[bool, str]:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False, f"非数值：{value!r}"
        if self.min_value is not None and v < self.min_value:
            return False, f"低于下限 {self.min_value}：{v}"
        if self.max_value is not None and v > self.max_value:
            return False, f"高于上限 {self.max_value}：{v}"
        return True, ""


class KnobTable:
    """参数白名单（消费方构造）。外键一律忽略并留痕 `rejected`。"""

    def __init__(self, specs) -> None:
        self._by_name: Dict[str, KnobSpec] = {}
        for s in specs:
            if s.name in self._by_name:
                raise KnobError(f"重复注册参数：{s.name!r}")
            self._by_name[s.name] = s

    def read(self, cfg: Mapping[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """(生效值, rejected)。

        三条硬化（与 `dispatch_cfg.read_dispatch_cfg` 同口径）：
          ① 只遍历白名单键，配置里多出来的键**一律忽略**并留痕；
          ② 逐个校验，非法即回落 `default`（不抛错、不就地裁剪）；
          ③ `rejected` 非空即"配置写错了"与"配置没问题"外观不再一致 ⇒ 脏配置会出声。
        """
        out: Dict[str, Any] = {}
        rejected: List[str] = []
        for name, spec in self._by_name.items():
            if name in cfg:
                ok, why = spec.clamp_check(cfg[name])
                if ok:
                    out[name] = cfg[name]
                    continue
                rejected.append(f"{name}: {why}")
            if spec.default is not None:
                out[name] = spec.default
        for k in sorted(k for k in cfg if k not in self._by_name):
            rejected.append(f"{k}: 非白名单键，已忽略")
        return out, rejected

    def has(self, name: str) -> bool:
        return name in self._by_name

    def spec(self, name: str) -> KnobSpec:
        if name not in self._by_name:
            raise KnobError(f"非白名单参数：{name!r}（配置面 ≠ 接口面）")
        return self._by_name[name]

    def names(self) -> Tuple[str, ...]:
        return tuple(sorted(self._by_name))


def classify_change(spec: KnobSpec, old: Any, new: Any) -> str:
    """判定变更方向：widen / tighten / flat。非数值或方向未声明 ⇒ flat（保守）。"""
    try:
        o, n = float(old), float(new)
    except (TypeError, ValueError):
        return DIR_FLAT
    if o == n or spec.widen_direction is None:
        return DIR_FLAT
    if spec.widen_direction == "down":
        return DIR_WIDEN if n < o else DIR_TIGHTEN
    return DIR_WIDEN if n > o else DIR_TIGHTEN


def is_forbidden_change(spec: KnobSpec, direction: str, *, redline_hit: bool = False) -> bool:
    """该变更是否**永不自动**（护栏 G1 与红线）。

    forbidden 风险档 / 自主权相关参数的放宽 / 红线命中 —— 任一为真即挂起。
    """
    if spec.tier == TIER_FORBIDDEN:
        return True
    if redline_hit:
        return True
    return bool(spec.autonomy_related and direction == DIR_WIDEN)


__all__ = ["KnobError", "KnobSpec", "KnobTable", "classify_change", "is_forbidden_change"]
