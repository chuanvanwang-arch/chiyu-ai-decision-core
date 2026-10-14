"""能力落地审计契约 —— L0 单一事实源（零第三方依赖、零 IO、零领域字面量）。

上迁源（GAP-7，Batch-2b，2026-10-14）：APS ``platform/capability_audit.py``
（design #10 ai-capability-audit：审计以代码为准、三查法、反假绿六判据）。

**机制上迁、域值留消费方**：
    · 上迁：三查法的**判定次序**（零命中最优先）/ 生产调用点计数纪律 /
      分级词汇 / 审计包四件套装配（缺件显式标注）/ 鉴别力自证探针形态；
    · 留 APS：``_CAP_TO_SKILL`` 十大能力映射 / ``_CAP_EVIDENCE`` 域核验点 /
      ``_PRODUCTION_USAGE`` 域检索词 / ``aps.*`` 事件与表。

⛔ 本层只有**词汇与不变式**。三查法的文件遍历（IO）在机制层
   （``chiyu_kernel.capability_audit.three_check``）——审计工具的读取面即其
    sanctioned IO 边界；判定/计数/装配全部纯函数。
"""
from __future__ import annotations
from chiyu_kernel.errors import KernelError

from typing import Tuple

__all__ = [
    "CAPABILITY_VERDICTS", "VERDICT_LANDED", "VERDICT_PARTIAL", "VERDICT_MISSING",
    "CAPABILITY_PRIORITIES",
    "AUDIT_PIECE_KEYS", "PIECE_STATUSES",
    "NON_CALL_LINE_PREFIXES",
    "AUDIT_STATUS_DRAFT", "AUDIT_STATUS_OK", "AUDIT_STATUS_PARTIAL",
    "AUDIT_STATUS_MISSING",
    "CAPABILITY_AUDIT_INVARIANTS",
    "CapabilityAuditError",
]

# ── 分级结论（✅/⚠️/❌）─────────────────────────────────────────────
CAPABILITY_VERDICTS: Tuple[str, ...] = ("landed", "partial", "missing")
VERDICT_LANDED: str = "landed"
VERDICT_PARTIAL: str = "partial"
VERDICT_MISSING: str = "missing"

# ── 优先级 ─────────────────────────────────────────────────────────
CAPABILITY_PRIORITIES: Tuple[str, ...] = ("P0", "P1", "P2")

# ── 审计包四件套（C5）──────────────────────────────────────────────
AUDIT_PIECE_KEYS: Tuple[str, ...] = (
    "traceability_graph", "baseline_diff", "operator_log", "compliance_selfcheck",
)

# ── 件状态 ─────────────────────────────────────────────────────────
#: ``missing`` 必须**带 reason**——显式标注是合规形态，静默省略才判红。
PIECE_STATUSES: Tuple[str, ...] = ("ok", "partial", "missing")
AUDIT_STATUS_OK: str = "ok"
AUDIT_STATUS_PARTIAL: str = "partial"
AUDIT_STATUS_MISSING: str = "missing"

#: 报告状态：C7 —— 未经与用户对话确认前恒 DRAFT，不替用户定稿。
AUDIT_STATUS_DRAFT: str = "DRAFT"

# ── 「定义 ≠ 调用」过滤前缀（反假绿 AFG-4 自检）─────────────────────
#: 纯定义/枚举/注释行不算生产调用点；不过滤则 ``def assemble(`` 被
#: ``assemble(`` 命中 ⇒ 计数虚高 ⇒ 判据再次失真。
NON_CALL_LINE_PREFIXES: Tuple[str, ...] = (
    "def ", "async def ", "class ", "__all__", "@", "#", '"""', "'''", "*",
)

# ── 不变式（每条均有守卫测试，不是注释）─────────────────────────────
CAPABILITY_AUDIT_INVARIANTS: Tuple[str, ...] = (
    "zero_hit_first_missing",     # 零命中最优先判 missing；硬编码分支不得遮蔽
    "zero_entry_is_partial",      # 符号在但生产零调用 ⇒ partial（链内自洽 ≠ 落地）
    "definition_is_not_call",     # def/class/注释行不计调用点
    "missing_piece_declared",     # 缺件必须显式标注 reason，禁静默省略
    "draft_until_user_confirms",  # C7：报告未经用户确认保持 DRAFT
    "operator_never_forged",      # operator 身份 AI 不代填（凭据/身份类不代填）
)


class CapabilityAuditError(KernelError):
    code = "CONTRACT_VIOLATION"
    """审计装配/判定形态非法（如四件套缺件且无 reason）。"""
