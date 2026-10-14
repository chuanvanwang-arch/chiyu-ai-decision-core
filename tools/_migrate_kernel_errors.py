"""一次性迁移脚本：将内核契约层 (ValueError) 错误类改为继承 KernelError（Batch-7a）。

仅作用于下列已知错误类所在文件；不改其它任何逻辑。
运行：python tools/_migrate_kernel_errors.py
"""
from __future__ import annotations

import re
from pathlib import Path

BASE = Path("packages/chiyu-kernel/src/chiyu_kernel")

FILES = [
    "contract/scheduler.py",
    "contract/security.py",
    "contract/quota.py",
    "contract/observability.py",
    "contract/param_health.py",
    "contract/nightly_report.py",
    "contract/gate.py",
    "contract/promotion.py",
    "contract/evolution.py",
    "contract/ab_experiment.py",
    "contract/feedback_loop.py",
    "contract/attribution.py",
    "contract/audit_4q.py",
    "contract/capability_audit.py",
    "contract/agent_runtime.py",
    "contract/conflict_resolver.py",
    "workflow/__init__.py",
    "approval/hitl.py",
    "evolution/guard.py",
    "plan/__init__.py",
    "evolution/skill_draft.py",
    "evolution/knob.py",
    "skills/__init__.py",
    "evolution/prescription.py",
    "orchestration/agent_registry.py",
    "orchestration/state_machine.py",
]

IMPORT_LINE = "from chiyu_kernel.errors import KernelError"
CLASS_RE = re.compile(r"^class\s+(\w+)\(ValueError\):\s*(#.*)?$")
SPECIAL_CODE = {"DecisionRequiredError": "CONFIRM_REQUIRED"}


def transform(text: str) -> tuple[str, int, int]:
    lines = text.split("\n")
    out: list[str] = []
    inserted_import = False
    n_class = 0
    for line in lines:
        if not inserted_import and line.strip() == "from __future__ import annotations":
            out.append(line)
            out.append(IMPORT_LINE)
            inserted_import = True
            continue
        m = CLASS_RE.match(line)
        if m:
            name = m.group(1)
            code = SPECIAL_CODE.get(name, "CONTRACT_VIOLATION")
            out.append(f"class {name}(KernelError):")
            out.append(f'    code = "{code}"')
            n_class += 1
            continue
        out.append(line)
    if not inserted_import:
        # 兜底：所有目标文件均含 __future__，正常情况下不会走到这里。
        out.insert(0, IMPORT_LINE)
    return "\n".join(out), n_class, 1 if inserted_import else 0


def main() -> None:
    total_classes = 0
    for rel in FILES:
        p = BASE / rel
        text = p.read_text(encoding="utf-8")
        new, n_c, n_i = transform(text)
        p.write_text(new, encoding="utf-8")
        total_classes += n_c
        print(f"  {rel}: classes={n_c} import_inserted={n_i}")
    print(f"TOTAL classes migrated: {total_classes}")


if __name__ == "__main__":
    main()
