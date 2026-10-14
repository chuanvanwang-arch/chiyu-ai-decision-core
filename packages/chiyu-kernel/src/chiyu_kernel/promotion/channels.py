"""回流四通道路由（纯函数）。

上迁源：APS ``reflux.route_retro`` 的 kind 分流段 + ``channel_of`` /
``PROPOSAL_CHANNELS`` / ``DEFAULT_CHANNEL``。

★ 反假绿：未知 kind ⇒ **抛错**，不静默丢弃——"事实进来了、没落到任何
  通道、系统还报已处理"是回流最常见的假绿。
"""
from __future__ import annotations

from typing import Mapping, Tuple

from chiyu_kernel.contract.promotion import (
    DEFAULT_CHANNEL,
    KIND_TO_CHANNEL,
    REFLUX_CHANNELS,
    REFLUX_KINDS,
    RefluxChannelError,
)

__all__ = ["kind_to_channel", "route_kind", "proposal_channel"]

_KIND_MAP: Tuple[Tuple[str, str], ...] = KIND_TO_CHANNEL


def kind_to_channel(kind: str) -> str:
    """复盘事实 kind → 回流通道（未知 ⇒ ``RefluxChannelError``）。"""
    k = str(kind or "").strip().lower()
    for name, channel in _KIND_MAP:
        if k == name:
            return channel
    raise RefluxChannelError(
        f"未知回流通道 kind={kind!r}（允许 {list(REFLUX_KINDS)}）；"
        "未知即拒绝——静默丢弃会让『已处理』变成假话"
    )


def route_kind(kind: str) -> str:
    """``kind_to_channel`` 的别名（路由语义名）。"""
    return kind_to_channel(kind)


def proposal_channel(
    kind: str, *, mapping: Mapping[str, str], default: str = DEFAULT_CHANNEL,
) -> str:
    """判定一条**处方** kind 的通道（未登记 ⇒ 默认建议通道 c3p）。

    ★ 分界：``c3`` = 配置处方（键在白名单内、恒 PENDING 待 HITL）；
      ``c3p`` = 建议（无对应配置键，**永远不会被自动 apply**，连"待批"
      都不存在——待批一个改不了的东西 = 制造假的治理动作）。
    """
    k = str(kind or "").strip()
    channel = dict(mapping or {}).get(k, default)
    if channel not in REFLUX_CHANNELS:
        raise RefluxChannelError(
            f"处方 kind={kind!r} 路由到非法通道 {channel!r}（合法 {list(REFLUX_CHANNELS)}）"
        )
    return channel
