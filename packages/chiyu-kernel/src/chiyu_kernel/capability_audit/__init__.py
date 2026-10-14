"""能力落地审计机制层（GAP-7，Batch-2b）—— 判定纯函数 + 单 IO 边界。

上迁源：APS ``platform/capability_audit.py``（design #10：审计以代码为准）。
三查法文件遍历（``three_check``）是本能力唯一 IO 面；分级/计数/四件套
装配全部纯函数。域能力映射（SKILL 编号/核验点/检索词）由消费方注入。
"""
from .finding import CapabilityFinding
from .four_piece import (
    assemble_four_piece,
    build_baseline_diff,
    build_compliance_selfcheck,
    build_traceability_graph,
    probe_piece_discrimination,
    record_operator_log,
)
from .grading import count_production_calls, grade_capability, is_call_line
from .three_check import three_check

__all__ = [
    "three_check",
    "is_call_line", "count_production_calls", "grade_capability",
    "CapabilityFinding",
    "record_operator_log", "build_baseline_diff", "build_traceability_graph",
    "build_compliance_selfcheck", "probe_piece_discrimination",
    "assemble_four_piece",
]
