"""派发器运行参数的**单一事实源**（对齐 `decision/retro_cfg.py` 的范式）。

内核实测版：demo `src/chiyu_group/orchestration/dispatch_cfg.py` 逐字保留，
仅改包路径 `chiyu_group.orchestration` → `chiyu_kernel.orchestration`，**不增不改**。

为什么要有这个模块
------------------
派发器的四个旋钮（并发上限 / 退避基数 / 抖动 / 派发尝试上限）如果写成模块常量，
就同时违反两条已有铁律：

① **阈值配置化**：代码只存出厂建议值，业务阈值一律可配；
② **单一事实源**：`pipeline._SECTION_KEYS` 与"代码里的默认值"若是两份清单，
   下一个动作一定是口径分叉（本项目已记录多次同族事故）。

故：本模块是唯一定义处，`pipeline.py` 只**引用**（`tuple(DISPATCH_CFG_DEFAULTS)`），
不另抄一份键名表。

⛔ 依赖方向（刻意）：本模块**只 import 标准库**，不 import `pipeline` / `store` /
   `dispatcher`。任何反向依赖都会在"pipeline 导入 orchestration"时成环。

读配置的三条硬化（照抄 `retro_cfg.read_retro_cfg` 语义）
-------------------------------------------------------
① **只读白名单键**：遍历 `DEFAULTS` 的键，配置里多出来的键**一律忽略**
   （配置面 ≠ 隐式接口面）；
② **逐个校验、非法即回落出厂兜底**（不抛错、不就地裁剪），并把被拒项**留痕**；
③ **脏配置不崩跑批，但必须出声** —— `rejected` 非空即"配置写错了"与"配置没问题"
   在外观上不再一致。
"""
from __future__ import annotations

import math
from typing import Any

# 配置段名（必须与 `pipeline.DEFAULT_CONFIG` 的顶层键一致，否则写通道回 400）。
DISPATCH_CFG_SECTION = "orchestration"

# ── 出厂兜底 ──────────────────────────────────────────────────────────────
# 为什么 `max_inflight` 默认只有 2（而不是拍个大数）：
#   SKILL #6 踩坑记录原文 —— "一次性 13 并发触发 Out of credits 误报（限流特征不是
#   欠费）"。并发上限是**硬约束**（下游 LLM 额度），默认必须保守，且必须可配。
DISPATCH_CFG_DEFAULTS: dict[str, Any] = {
    # 单个派发批次内允许同时在跑的 worker 数。硬下限 1（0 = 派发器停摆，等于把
    #   "关掉派发"伪装成"配置"，那种开关必须显式存在而不是被误配出来）。
    "max_inflight": 2,
    # 指数退避基数（秒）：第 n 次重试前等 `backoff_base * 2**n`（再乘抖动）。
    "backoff_base": 0.5,
    # 抖动比例 ∈ [0, 1]：`delay * (1 ± jitter)`。防"同一秒一起重试"造成同相位撞限流。
    "jitter": 0.25,
    # 单任务派发尝试上限；超限即 `fail()`，交由 `FAILURE_LIMIT` 熔断接管。
    "max_dispatch_attempts": 3,
    # 派发锁 TTL（秒）。锁带心跳，故 TTL 只负责"持有者崩了以后多久能被接管"。
    "lock_ttl_seconds": 300,
    # 抢不到派发锁时的等待上限（秒）。0 = 不等待，直接报 `lock-held` 不执行。
    #   为什么默认大于 0：本 DEMO 的夜批是**同步返回**语义，抢不到锁就静默不执行
    #   会让调用方拿到一个"没有结果的报告"（比抛错更难查）。故默认等一小会儿。
    "lock_wait_seconds": 30,
}

# 数值型键的解析口径（int 键不接受小数；float 键接受 int）。
_INT_KEYS = ("max_inflight", "max_dispatch_attempts", "lock_ttl_seconds",
             "lock_wait_seconds")
_FLOAT_KEYS = ("backoff_base", "jitter")
_RATIO_KEYS = ("jitter",)          # ∈ [0, 1]
_POSITIVE_KEYS = ("max_inflight", "max_dispatch_attempts", "lock_ttl_seconds")
# `lock_wait_seconds` 允许 0（显式"不等待"）；其余正数键不接受 0。


def read_dispatch_cfg(cfg: Any) -> tuple[dict[str, Any], list[dict]]:
    """从策略配置中读派发参数。**永不抛异常**（顶层 catch 是最高层防线）。

    返回 `(值, rejected)`：`rejected[i] = {"key", "value", "why"}`。
    """
    out = dict(DISPATCH_CFG_DEFAULTS)
    rejected: list[dict] = []
    raw: Any = None
    try:
        raw = (cfg or {}).get(DISPATCH_CFG_SECTION)
    except Exception as e:                                       # noqa: BLE001
        return out, [{"key": DISPATCH_CFG_SECTION, "value": None,
                      "why": f"读配置段失败：{type(e).__name__}: {e}"}]
    if raw is None:
        return out, rejected                    # 段缺失 = 全用出厂值（不是错误）
    if not isinstance(raw, dict):
        return out, [{"key": DISPATCH_CFG_SECTION, "value": type(raw).__name__,
                      "why": "配置段必须是对象"}]

    for key in DISPATCH_CFG_DEFAULTS:            # ⓪ 只读白名单键：多余的键忽略
        if key not in raw:
            continue
        v = raw[key]
        if key in _INT_KEYS:
            # ⛔ 不用 `int(v)`：`int(True) == 1`、`int("2") == 2`，
            #   把"配错了类型"悄悄当成合法值 = 静默丢弃的变体。
            if isinstance(v, bool) or not isinstance(v, int):
                rejected.append({"key": key, "value": repr(v), "why": "必须是整数"})
                continue
        elif key in _FLOAT_KEYS:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                rejected.append({"key": key, "value": repr(v), "why": "必须是数值"})
                continue
            if not math.isfinite(float(v)):
                rejected.append({"key": key, "value": repr(v), "why": "必须有限"})
                continue
            v = float(v)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if key in _POSITIVE_KEYS and v < 1:
                rejected.append({"key": key, "value": repr(v),
                                 "why": "必须 ≥ 1（0 会让派发器停摆" "，请用显式开关而非误配）"})
                continue
            if key not in _POSITIVE_KEYS and v < 0:
                rejected.append({"key": key, "value": repr(v), "why": "不得为负"})
                continue
            if key in _RATIO_KEYS and v > 1:
                rejected.append({"key": key, "value": repr(v), "why": "必须在 [0,1]"})
                continue
        out[key] = v
    return out, rejected


def dispatch_cfg_report(cfg: Any) -> dict[str, Any]:
    """给体检器/观测面用的报告：当前生效值 + 出厂值 + 被拒项（口径与 `retro_cfg_report` 同型）。"""
    val, rejected = read_dispatch_cfg(cfg)
    return {"section": DISPATCH_CFG_SECTION, "effective": val,
            "defaults": dict(DISPATCH_CFG_DEFAULTS), "rejected": rejected,
            "is_default": val == DISPATCH_CFG_DEFAULTS}


__all__ = ["DISPATCH_CFG_SECTION", "DISPATCH_CFG_DEFAULTS",
           "read_dispatch_cfg", "dispatch_cfg_report"]
