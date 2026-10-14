"""粒子 / 属性 / 谓词契约 —— L0 单一事实源（零领域字面量）。

⛔ 准入闸（本模块的铁律）
────────────────────────
内核**不得**出现任何具体业务枚举值。判据（2026-08-24 立）：凡出现真实业务系统的
对象名 / 阶段名 / 谓词名，即为污染 → 外移 L4 profile。

本模块只声明**形态**，不声明**取值**：

    进内核（形态）                        外移 L4 profile（取值）
    ────────────────────────────         ────────────────────────────────
    19 种属性类型（通用）                  粒子类型的具体名字（各域一等对象名）
    边分层 K/M · 边来源 6 值 · 基数 4 值    知识谓词的具体名字
    核心语义角色 5 个                      红线事项目录 · 评分配置
    受控谓词的数据结构

CORE_ROLES 的准入标准：该角色在**任意**业务领域都成立。
    ⛔ 反面例：「地点」看似通用，但 A 域以地点为一等对象、B 域以板坯为一等对象
       —— 一旦纳入某个具体对象名，下一步就是为它的同族开绿灯，内核退化为单域框架。
被 `tests/test_contract_no_domain_literals.py` 强制（黑名单见 config/domain-literal-denylist.json）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple

# ── 属性类型：19 种有穷集（attio 风格，与具体业务无关）──────────────────
ATTR_TYPES: Tuple[str, ...] = (
    "text", "rich_text", "number", "percent", "currency", "rating",
    "select", "multi_select", "status", "boolean", "timestamp", "date",
    "location", "record_reference", "actor_reference", "interaction",
    "url", "email", "phone",
)

# ── 边与属性的元数据枚举（形态）────────────────────────────────────────
EDGE_LAYERS: Tuple[str, ...] = ("K", "M")
EDGE_SOURCES: Tuple[str, ...] = ("human", "rule", "ai", "llm", "engine", "manual")
ATTR_SOURCES: Tuple[str, ...] = ("human", "rule", "ai", "llm", "engine")
CARDINALITIES: Tuple[str, ...] = ("1:1", "1:N", "N:1", "N:M")

# 属性值槽位（列化存储的五个物理列，禁自由 JSON —— 见 store/ddl.py）
VALUE_SLOTS: Tuple[str, ...] = (
    "value_text", "value_num", "value_bool", "value_ts", "value_set",
)

# 知识分层（粒子归属）
LAYERS: Tuple[str, ...] = ("L1", "L2")

# ── 核心语义角色（跨域恒定，不接受扩展）────────────────────────────────
CORE_ROLES: Tuple[str, ...] = (
    "unstructured_asset",   # 任意域都有非结构化来件（文档 / 工单 / 报告）
    "entity",               # 任意域都有参与主体
    "decision",             # 任意域都有决策记录
    "memory",               # 任意域都有记忆
    "knowledge",            # 任意域都有知识条目
)

# 向量维度：384 补零到 1024（余弦等价）。⛔ 补零是**落库方**的职责，
# 原始维度由 vector/index_vector.py 原样返回（见该模块 triple 契约）。
HASH_DIM = 384
VECTOR_DIM = 1024

_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class ParticleTypeSet:
    """消费方声明的粒子类型全集（L4 取值 + L0 形态约束）。

    ⛔ 必须包含全部 CORE_ROLES —— 否则内核机制（记忆七边依赖 decision/memory/
       knowledge）会在运行期缺锚点，而这属于"配了却没生效"族缺陷（须构造期发现）。
    """

    names: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.names:
            raise ValueError("ParticleTypeSet 不得为空")
        if len(set(self.names)) != len(self.names):
            dup = sorted({n for n in self.names if self.names.count(n) > 1})
            raise ValueError(f"粒子类型重复：{dup}")
        bad = [n for n in self.names if not _IDENT.match(n)]
        if bad:
            raise ValueError(f"粒子类型须匹配 [a-z][a-z0-9_]*：{bad}")
        missing = [r for r in CORE_ROLES if r not in self.names]
        if missing:
            raise ValueError(f"粒子类型集缺少核心语义角色：{missing}")

    def sql_check(self, dialect: str = "postgres") -> str:
        """生成 DDL 的 IN 列表。⛔ 由本方法生成，禁止在 store 层手写枚举。"""
        if dialect != "postgres":
            raise ValueError(f"暂不支持的方言：{dialect}")
        return ", ".join(f"'{n}'" for n in self.names)

    def covers(self, role: str) -> bool:
        return role in self.names


@dataclass(frozen=True)
class PredicateSpec:
    """受控谓词的一条定义（形态；取值由 profile 提供）。"""

    predicate: str
    from_type: str
    to_type: str | None
    cardinality: str | None = None
    source: str = "rule"
    layer: str = "K"

    def __post_init__(self) -> None:
        if not _IDENT.match(self.predicate) and not self.predicate.isupper():
            raise ValueError(f"谓词名须为小写下划线式或全大写：{self.predicate!r}")
        if self.layer not in EDGE_LAYERS:
            raise ValueError(f"layer 须 ∈ {EDGE_LAYERS}：{self.layer!r}")
        if self.source not in EDGE_SOURCES:
            raise ValueError(f"source 须 ∈ {EDGE_SOURCES}：{self.source!r}")
        if self.cardinality is not None and self.cardinality not in CARDINALITIES:
            raise ValueError(f"cardinality 须 ∈ {CARDINALITIES}：{self.cardinality!r}")


# ── M 层：记忆上下文图谱七边（跨域通用；to_type 为领域者置 None 由 profile 填）
MEMORY_PREDICATES: Tuple[PredicateSpec, ...] = (
    PredicateSpec("DECIDED_ON", "decision", None, layer="M", source="engine"),
    PredicateSpec("REFERENCED_PRECEDENT", "decision", None, layer="M", source="engine"),
    PredicateSpec("DERIVED_FROM_EXCEPTION", "decision", "knowledge", layer="M", source="engine"),
    PredicateSpec("ESTABLISHES_FRAME", "decision", None, layer="M", source="engine"),
    PredicateSpec("OVERRIDES", "decision", "decision", layer="M", source="engine"),
    PredicateSpec("CAUSED", "decision", None, layer="M", source="engine"),
    PredicateSpec("INFLUENCED", "decision", "decision", layer="M", source="engine"),
)


@dataclass(frozen=True)
class PredicateSet:
    """知识谓词（L4 取值）与记忆谓词（内核常量）的合并视图。"""

    knowledge: Tuple[PredicateSpec, ...] = ()
    memory: Tuple[PredicateSpec, ...] = MEMORY_PREDICATES

    def __post_init__(self) -> None:
        for p in self.memory:
            if p.layer != "M":
                raise ValueError(f"记忆谓词 layer 必须为 'M'：{p.predicate}")
        for p in self.knowledge:
            if p.layer != "K":
                raise ValueError(f"知识谓词 layer 必须为 'K'：{p.predicate}")

    def all(self) -> Tuple[PredicateSpec, ...]:
        return tuple(self.knowledge) + tuple(self.memory)

    def names(self) -> Tuple[str, ...]:
        return tuple(p.predicate for p in self.all())


__all__ = [
    "ATTR_TYPES", "EDGE_LAYERS", "EDGE_SOURCES", "ATTR_SOURCES", "CARDINALITIES",
    "VALUE_SLOTS", "LAYERS", "CORE_ROLES", "HASH_DIM", "VECTOR_DIM",
    "ParticleTypeSet", "PredicateSpec", "PredicateSet", "MEMORY_PREDICATES",
]
