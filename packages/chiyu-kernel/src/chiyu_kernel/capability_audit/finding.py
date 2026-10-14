"""审计发现结构（分级结论载体）。

上迁源：APS ``platform/capability_audit.py:CapabilityFinding``（C2：每条结论带
file:line 证据；C1：判据源动态引用，路径由消费方注入，不内嵌）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = ["CapabilityFinding"]


@dataclass
class CapabilityFinding:
    """单条能力审计结论。``evidence`` 为 ``file:line`` 列表（C2）。"""

    capability: int
    name: str
    verdict: str                 # landed / partial / missing
    priority: Optional[str]      # P0 / P1 / P2
    evidence: List[str] = field(default_factory=list)
    skill_ref: Optional[str] = None   # C1 判据源（消费方动态引用，可空）
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability, "name": self.name,
            "verdict": self.verdict, "priority": self.priority,
            "evidence": list(self.evidence), "skill_ref": self.skill_ref,
            "note": self.note,
        }
