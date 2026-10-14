"""知识升格与回流管道机制层（GAP-9，Batch-2b）—— 纯函数，零 IO。

上迁源：APS ``platform/promotion.py`` + ``platform/reflux.py`` 的裁决逻辑。
落库 / 事件发射 / 策略配置文件路径 / 域键白名单 / 域真值表留消费方；
本包只提供升格闸门、候选抽取、漂移判定、覆盖守卫、产物载荷、
回流通道路由、后见之明决策核心与处方守卫的纯函数。

⛔ 处方**状态机**（PENDING→…）在 ``chiyu_kernel.evolution.prescription``；
    本包的 ``reflux_prescribe_guard`` 只裁决"能不能出方"，不落库、不改配置。
"""
from .candidates import (
    audit_drift,
    build_promotion_payload,
    drift_detected,
    extract_numeric_candidates,
    promotion_overwrite_guard,
)
from .channels import kind_to_channel, proposal_channel, route_kind
from .gate import promote_gate
from .hindsight import (
    default_reflux_policy,
    deviation,
    deviation_rate,
    should_prescribe,
    window_status,
)
from .policy import load_json_policy, positive_float, positive_int, unit_float
from .reflux import reflux_prescribe_guard

__all__ = [
    # 升格
    "promote_gate", "extract_numeric_candidates", "drift_detected", "audit_drift",
    "promotion_overwrite_guard", "build_promotion_payload",
    # 回流
    "kind_to_channel", "route_kind", "proposal_channel",
    "reflux_prescribe_guard",
    # 后见之明
    "default_reflux_policy", "deviation", "should_prescribe",
    "window_status", "deviation_rate",
    # 策略
    "load_json_policy", "positive_int", "positive_float", "unit_float",
]
