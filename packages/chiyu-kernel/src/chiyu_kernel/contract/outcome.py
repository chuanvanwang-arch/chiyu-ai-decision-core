"""结局采集契约 —— 决策→执行→结局→复盘 闭环的第一环（L0 单一事实源）。

⛔ L0 纪律：零第三方依赖（除 dataclasses）、零 IO、零领域字面量。
   消费方**只许** import 本层与 `chiyu_kernel.api`，import 内部实现即违约
   （守 tests/test_app_imports_contract_only.py，T2 建）。

设计来源：三仓回执（CRM outcome.js / APS decisions.py / enterprise 复盘证据面缺口）
   一致 P0 —— 三仓各自造结局采集、口径漂移，缺统一契约。本契约只收
   "枚举机制"，不收"具体枚举值"（won/lost/paid 是销售语义，制造/医疗租户
   可按域扩展 OUTCOME_KINDS，见 CRM Q1.4 边界）。

⛔ 与铁律 C-B 相容：结局校准是**闭环反馈轨**，**不得**污染 `S3_aggregate` 的
   `ratio` 唯一置信度来源（`CONFIDENCE_SOURCE_KEY="ratio"`）。本模块提供的
   `OUTCOME_CONFIDENCE_DIRECTION` 只定校准**方向**语义，量值与映射表由消费方
   domain 注入、在闭环轨使用，永不作为 S3 的输入源。
"""
from __future__ import annotations

from typing import Mapping, Tuple

# ── 结局枚举机制（值可扩展，机制由本契约统一）────────────────────────
# 三仓共同最小面；消费方可在其域内追加合法 kind（经 validate_outcome_kind 的
# `extra` 显式声明，避免拼错进闭集却静默通过 —— 对齐 G4 禁裸字符串纪律）。
OUTCOME_KINDS: Tuple[str, ...] = (
    "success",    # 成功 / 赢单 / 达标
    "failure",    # 失败 / 丢单
    "partial",    # 部分达成 / 局部
    "stalled",    # 停滞
    "other",      # 其他（域自定义入口）
)

# ── 结局记录的必填字段（顺序参与 canonical 序列化，不可重排）──────────
# 与 `AUDIT_REQUIRED_FIELDS`（audit.py）同规：字段既覆盖元数据又覆盖载荷，
# 保证结局作为审计链一环时不漏掉证明"系统对了/错了"的关键载荷。
OUTCOME_REQUIRED_FIELDS: Tuple[str, ...] = (
    "outcome_id",    # 结局记录 id
    "decision_id",   # 关联决策（闭环锚点，追溯链关键）
    "outcome_kind",  # 结局类型（∈ OUTCOME_KINDS ∪ 域扩展）
    "recorded_ts",   # 采集时间（ISO-8601）
    "recorded_by",   # 采集者（人工 user_id / 系统 principal，追责到个人）
    "evidence_ref",  # 证据引用（回放依据：订单 id / 结算单 id 等）
)

# ── 结局→置信度校准方向映射（P0 提供机制；量值由消费方 domain 注入）────
# 结尾对"当时决策置信度"的校准方向：up（正向印证决策） / down（质疑） /
# neutral（无对错信息，不校准）。保守单边：partial 记 down（弱质疑），
# 不在无对错信息时升分（避免过度校准噪声）。
OUTCOME_CONFIDENCE_DIRECTION: Mapping[str, str] = {
    "success": "up",
    "failure": "down",
    "partial": "down",       # 部分达成：弱质疑（保守单边）
    "stalled": "neutral",    # 停滞：无对错信息，不校准
    "other":   "neutral",
}


def validate_outcome_kind(kind: str, extra: Tuple[str, ...] = ()) -> bool:
    """构造期校验：`kind` ∈ `OUTCOME_KINDS` ∪ 域扩展值。

    - `extra`：消费方显式声明的域扩展合法值（如 ("won", "lost", "paid")）；
      未声明即判定非法 —— 杜绝拼错值进闭集却静默通过。
    - 纯判定器（返回 bool），供采集前校验；**不抛错**（机制定位，是否 fail-fast
      由调用方决定）。域扩展值须同时落 `OUTCOME_CONFIDENCE_DIRECTION` 的对应
      方向（方向机制由本契约定，量值域注入）。
    """
    return kind in OUTCOME_KINDS or kind in extra


__all__ = [
    "OUTCOME_KINDS", "OUTCOME_REQUIRED_FIELDS",
    "OUTCOME_CONFIDENCE_DIRECTION", "validate_outcome_kind",
]
