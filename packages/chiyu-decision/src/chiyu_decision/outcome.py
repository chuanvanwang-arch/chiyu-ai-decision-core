"""结局采集 API —— 决策→执行→结局→复盘 闭环第一环的**内核实现**（D1.5，P-1）。

⛔ 边界：契约在 ``chiyu_kernel.contract.outcome``（L0 单一事实源，只收枚举机制）；
本模块是 foundation 内核级采集实现，提供 ``append_outcome`` / ``list_outcomes``：
  - 校验六必填字段（OUTCOME_REQUIRED_FIELDS）+ outcome_kind ∈ OUTCOME_KINDS ∪ extra_kinds；
  - 落 foundation 内核 **append-only 结局台账**（按 decision_id 索引的不可变链）；
  - 供消费方对齐闭环：CRM ``writeOutcome``（won/lost/paid 时间序列结局）、
    APS ``reflux_record_outcome``、enterprise 复盘证据面。

⛔ 持久化边界：本台账为**进程内**内核 ledger（与 foundation ``persister`` 鸭子类型
哲学一致——内核校验 + 落账，落库耐久由消费方经返回记录自行承接）。不引入 PG 耦合。

设计来源：docs/plans/2026-10-13-foundation三大支柱详细设计.md D1.5（签名契约）；
T79 实现排期 P-1；CRM 同步确认 writeOutcome 六字段适配卡在 P-1（本实现即解药）。
"""
from __future__ import annotations

from typing import Mapping, Tuple

from chiyu_kernel.contract.outcome import (
    OUTCOME_REQUIRED_FIELDS, validate_outcome_kind,
)

# ── 内核 append-only 结局台账（进程内）────────────────────────────────────
# _OUTCOMES: outcome_id -> 不可变记录（dict 副本，防外部篡改）
# _BY_DECISION: decision_id -> [outcome_id, ...]（按采集顺序的链，支持多结局并存）
_OUTCOMES: dict = {}
_BY_DECISION: dict = {}


def append_outcome(
    outcome: Mapping[str, object],
    *,
    extra_kinds: Tuple[str, ...] = (),
) -> str:
    """采集一条结局，返回 outcome_id；落内核 append-only 台账。

    校验（fail-fast，构造期断言，非文档纪律）：
      - OUTCOME_REQUIRED_FIELDS 六字段齐备且非空（outcome_id / decision_id /
        outcome_kind / recorded_ts / recorded_by / evidence_ref）；
      - outcome_kind ∈ OUTCOME_KINDS ∪ extra_kinds（域扩展须显式声明，禁裸字符串）；
      - outcome_id 唯一（重复 ⇒ 抛错，幂等防护：同一结局不得二次落账）。

    ⛔ 与铁律 C-B 相容：本 API 只收结局**事实**，绝不回写置信度 ratio 源
    （校准方向 OUTCOME_CONFIDENCE_DIRECTION 由消费方在闭环轨使用）。
    """
    missing = tuple(f for f in OUTCOME_REQUIRED_FIELDS if not outcome.get(f))
    if missing:
        raise ValueError(
            f"append_outcome 缺必填字段：{missing!r}（须齐备 OUTCOME_REQUIRED_FIELDS 六字段）")
    oid = str(outcome["outcome_id"])
    kind = str(outcome["outcome_kind"])
    if not validate_outcome_kind(kind, extra_kinds):
        raise ValueError(
            f"outcome_kind 非法：{kind!r} ∉ OUTCOME_KINDS ∪ extra_kinds={extra_kinds!r}"
            "（域扩展须经 extra_kinds 显式声明，禁裸字符串）")
    if oid in _OUTCOMES:
        raise ValueError(
            f"outcome_id 重复：{oid!r}（结局台账 append-only，幂等防护；"
            "同一结局请勿二次落账）")
    _OUTCOMES[oid] = dict(outcome)
    _BY_DECISION.setdefault(str(outcome["decision_id"]), []).append(oid)
    return oid


def list_outcomes(decision_id: str) -> Tuple[Mapping[str, object], ...]:
    """返回某 decision_id 的全部结局（按采集顺序）；无记录返回 ``()`` 诚实降级。

    ⛔ 多结局并存语义：同一 decision 可有多条结局（CRM won/lost/paid 时间序列），
    默认按 recorded_ts 最新者为准的统计口径由消费方在度量层（D5）裁定，
    本 API 只保证返回的链完整、顺序稳定。
    """
    return tuple(_OUTCOMES[oid] for oid in _BY_DECISION.get(str(decision_id), ()))


def clear_outcomes() -> None:
    """测试/重置用：清空内核台账（非生产 API，仅供隔离测试调用）。"""
    _OUTCOMES.clear()
    _BY_DECISION.clear()
