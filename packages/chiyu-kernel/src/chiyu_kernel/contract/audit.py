"""审计契约 —— L0 单一事实源。

⛔ 链式哈希：每条审计记录的 hash = sha256(prev_hash + canonical(record))，
   首条 prev_hash = "0" * 64。任一**契约字段**改动 ⇒ 后续全链失配（防篡改）。
   为什么链式而不是逐条哈希：逐条哈希只能证明"这条没被改"，链式还能证明
   "没有中间记录被删掉"——后者才是审计被绕过的常见形式。

⛔ 字段集必须覆盖**载荷值字段**（from_value / to_value / verdict / prescription_id），
   不只是元数据：自进化审计记录的本质是"平台把标尺从 A 改成 B"，若只哈希元数据，
   篡改 B 值（即实际生效的改值）不会被检出——审计链形同虚设。
"""
from __future__ import annotations

from typing import Tuple

AUDIT_HASH_ALGO = "sha256"
AUDIT_GENESIS_HASH = "0" * 64

# 审计记录的必填字段（顺序参与 canonical 序列化，不可重排）。
# 前 6 项为元数据；后 4 项为**载荷值字段**（自变动作的真实改值，漏掉即审计无鉴别力）。
AUDIT_REQUIRED_FIELDS: Tuple[str, ...] = (
    "audit_id", "ts", "domain", "action", "subject_id", "decision_id",
    "prescription_id", "from_value", "to_value", "verdict",
)

# 可证伪探针的三种断言形态（SKILL #10：探针本身也会骗人）
PROBE_ASSERTIONS: Tuple[str, ...] = ("count_exact", "field_equals", "chain_continuous")

# ══ D6 审计 canonical schema（三支柱批次二；跨仓 record 毕业对账面）═══════
# enterprise Q1.3 P1「record_kind + rubric_scores + elements 三键毕业」：
# 跨仓审计记录对账的最小 canonical 键集 = 基座必填字段（AUDIT_REQUIRED_FIELDS）
# + 三毕业键。canonical 序列化顺序 = 本元组顺序（不可重排，重排即全链失配）。
# ⛔ 域特有动作字段的 canonical 组装留消费方（接线后各仓只余适配层）。
AUDIT_CANONICAL_SCHEMA: Tuple[str, ...] = AUDIT_REQUIRED_FIELDS + (
    "record_kind",    # 记录种类（基座值见 AUDIT_RECORD_KIND="audit"；域值须显式扩展）
    "rubric_scores",  # 九尺子得分快照（评分可回放）
    "elements",       # 八要素声明快照（判据可回放）
)

# 链式哈希规则（机器可检常量；实现单一事实源，消除各仓同名异实 SHA-256 链）
AUDIT_CHAIN_RULE = "hash = sha256(prev_hash + canonical(record))"

# ══ D6 墓碑擦除语义（GDPR vs 禁 DELETE 的基座层裁决）═════════════════════
# 软删标记，不物理删（对齐 CRM append-only 墓碑）：被擦除记录**留在链上**，
# 载荷字段置空但 hash 链不断——既满足「可被遗忘」的擦除申报，又保全
# 「无中间记录被删」的链式证明。物理 DELETE 在审计轨上恒非法。
AUDIT_TOMBSTONE_FIELD = "tombstoned"          # True = 已墓碑（载荷已擦除）
AUDIT_TOMBSTONE_REASON_FIELD = "tombstone_reason"  # 擦除依据（GDPR 条款/工单号，必填非空）
AUDIT_TOMBSTONE_INVARIANTS: Tuple[str, ...] = (
    "tombstone_never_physical_delete",  # 墓碑 ≠ 物理删（记录本体与链位恒在）
    "tombstone_stays_in_chain",         # 墓碑后链连续（擦除不改 prev_hash 指向）
    "tombstone_requires_reason",        # 墓碑必带依据（无因擦除 = 审计旁路）
)

# ══ D6+ 链加固（Batch-1b-2 prov_chain；对拍 CRM provenance.js
#    OK/TAMPERED/FORKED/BROKEN_HEAD 四态 + seal 封条语义）══════════════════
# 链校验状态闭集（域无关化：CRM 的 BROKEN_HEAD/FORKED 在基座线性链上分别投影为
# tampered(锚点失配) 与 find_forks 的分叉检出；闭集保跨仓对判口径一致）。
CHAIN_VERIFY_STATUSES: Tuple[str, ...] = ("ok", "tampered", "forked", "broken_head")

# 封条字段（seal：对链的一次"钉桩"。CRM exportSeal/verifySeal 同语义）：
# ⛔ 头哈希与条数**必须成对**——只钉头哈希，攻击者可截尾重算自洽链；
#   只钉条数，可就地篡改后重算出自洽链（CRM L255 同判据）。
CHAIN_SEAL_FIELDS: Tuple[str, ...] = ("head_checksum", "entry_count")

PROV_CHAIN_INVARIANTS: Tuple[str, ...] = (
    "seal_binds_head_and_count",              # 封条同时钉头哈希与条数（成对，缺一即绕过）
    "same_count_head_mismatch_is_tampered",   # 条数同而头变 ⇒ 就地篡改（重算自洽也拦）
    "tail_verification_continues_from_anchor",  # 增量校验必须从已知锚续链，禁只验自身
    "fork_is_same_prev_two_children",         # 分叉 = 同一 prev 锚点出现两条不同后继
)

__all__ = [
    "AUDIT_HASH_ALGO", "AUDIT_GENESIS_HASH",
    "AUDIT_REQUIRED_FIELDS", "PROBE_ASSERTIONS",
    # D6（三支柱批次二）
    "AUDIT_CANONICAL_SCHEMA", "AUDIT_CHAIN_RULE",
    "AUDIT_TOMBSTONE_FIELD", "AUDIT_TOMBSTONE_REASON_FIELD",
    "AUDIT_TOMBSTONE_INVARIANTS",
    # D6+ 链加固（Batch-1b-2）
    "CHAIN_VERIFY_STATUSES", "CHAIN_SEAL_FIELDS", "PROV_CHAIN_INVARIANTS",
]
