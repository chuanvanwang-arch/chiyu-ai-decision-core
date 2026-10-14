"""决策可审计性「四问」契约（Batch-1b-3 audit_4q；上迁自 CRM decision/auditability.js）。

⛔ L0 纪律：零第三方依赖、零 IO、零领域字面量。

四问（对单个决策的可审计性体检，评分核纯函数 + 证据注入）：
  Q1 能否解释直接原因 —— 上下文维度供给 ≥ Q1_MIN_SUPPLIED_DIMS；
  Q2 能否追溯到源头 —— 溯源链完整**且**覆盖上下文操作（空链不可自称 OK）；
  Q3 能否发现冲突事实 —— 无未裁决冲突（零实体扫描同样无证据 ⇒ warn）；
  Q4 能否看下游影响 —— 影响计算失败=fail；孤立决策=warn（合法但需关注）。
⛔ 图/溯源/冲突证据由消费方注入；判据算法与口径常量在基座（评分口径永不漂移）。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Tuple

AUDIT4Q_KEYS: Tuple[str, ...] = ("Q1", "Q2", "Q3", "Q4")

# 单问状态闭集（health.score = pass 计数，total 恒 4）
AUDIT4Q_STATUSES: Tuple[str, ...] = ("pass", "warn", "fail")

# §7.1 Q1 门槛（设计文档字面口径）：维度供给 ≥5/7 才 pass。
# 冷启动豁免（S2 先例召回 / S3 冲突探测允许合法 empty）后剩余 5 维须真实供给；
# 未达 → warn（诚实暴露缺口，禁用「有理由」掩盖——反假绿铁律）。
Q1_MIN_SUPPLIED_DIMS = 5

AUDIT4Q_INVARIANTS: Tuple[str, ...] = (
    "q1_missing_evidence_is_warn",       # 快照缺失/被篡改 = 无证据 ⇒ warn（禁 rationale 顶替）
    "q2_empty_chain_never_ok",           # 空链不可自称 OK：证据条目>0 且 context_supply>0
    "q2_events_not_evidence",            # 生命周期事件条目（event:* 形态）不入证据口径
    "q3_zero_entities_scanned_is_warn",  # 零实体扫描 = 无证据 ⇒ warn（非 pass）
    "q4_fail_only_on_error",             # 影响计算失败才 fail；孤立决策 warn 不 fail
    "empty_window_pct_null",             # 聚合空窗口 pct=null（不报错、不报 0 充数）
)


class Audit4QError(KernelError):
    code = "CONTRACT_VIOLATION"
    """四问评分输入非法（未知问键 / 非法状态值）。"""


__all__ = [
    "AUDIT4Q_KEYS", "AUDIT4Q_STATUSES", "Q1_MIN_SUPPLIED_DIMS",
    "AUDIT4Q_INVARIANTS", "Audit4QError",
]
