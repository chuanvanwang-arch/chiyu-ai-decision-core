"""参考消费层的**领域内容**（L4）—— 消费方持有，内核零领域字面量。

⛔ 纪律：
  - 这里的一切取值都是**示例**（中性通用域：文档 / 任务 / 决策），真实项目替换成自己的域。
  - 这些取值**不进内核**；唯一入口是 `inject_domain()` 注入。
  - 内核只认「形态约束」（粒子类型须含全部核心角色、谓词端类型须 ∈ 粒子类型、
    场景受控边须 ∈ profile 谓词集），不认任何具体业务词。

改动指引：换掉 PARTICLE_TYPES / KNOWLEDGE_PREDICATES / ACTIONS / SCENARIO 即可，
内核与本包其余代码无需改动 —— 这正是「不再为底层浪费时间」的含义。
"""
from __future__ import annotations

from chiyu_kernel.contract.particle import CORE_ROLES

# ── 1. 粒子类型：核心角色（强制）+ 本域自有类型 ──────────────────────────────
# CORE_ROLES = unstructured_asset / entity / decision / memory / knowledge（跨域恒定）
PARTICLE_TYPES: tuple = tuple(CORE_ROLES) + ("document", "task")

# ── 2. 受控谓词（知识层 K；记忆层 M 七边由内核常量 MEMORY_PREDICATES 提供）────
KNOWLEDGE_PREDICATES: tuple = (
    {"predicate": "DESCRIBES", "from_type": "knowledge",
     "to_type": "document", "layer": "K", "source": "rule"},
    {"predicate": "BLOCKS", "from_type": "task",
     "to_type": "task", "layer": "K", "source": "rule"},
)

# ── 3. 注入用的 profile（dict 形态，经 profile_from_dict 进内核）──────────────
PROFILE: dict = {
    "domain": "reference",
    "particle_types": {"names": list(PARTICLE_TYPES)},
    "predicates": {"knowledge": list(KNOWLEDGE_PREDICATES)},
    "autonomous_threshold": 0.79,
}

# ── 4. Action（R1–R6 校验：verb_object 命名 / R5 一能力一表面 / R6 高危带 force）──
ACTIONS: list = [
    {"name": "read_document", "capability": "document_read"},
    {"name": "submit_review", "capability": "review_submit", "mutating": True},
    {"name": "approve_release", "capability": "release_approve",
     "high_risk": True, "has_force": True},
    {"name": "export_report", "capability": "report_export"},
]

# ── 5. 场景包（受控边须 ∈ profile 谓词集，否则「配了却没生效」构造期即红）──────
SCENARIO: dict = {
    "id": "review-flow",
    "name": "文档评审流",
    "level": "single",
    "direction": "inbound",
    "mode": "standard",
    "workflow": {"steps": [{"name": "triage", "prompt": "归类并抽取要点"}]},
    "controlled_edges": [
        {"predicate": "DESCRIBES", "from_type": "knowledge", "to_type": "document"},
    ],
}

SCENARIOS: list = [SCENARIO]

__all__ = [
    "PARTICLE_TYPES", "KNOWLEDGE_PREDICATES", "PROFILE", "ACTIONS",
    "SCENARIO", "SCENARIOS",
]
