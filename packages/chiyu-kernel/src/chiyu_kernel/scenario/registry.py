"""决策场景注册表 —— 底座公共契约（单一事实源）。

为什么需要（CRM F-05 / enterprise #6）
────────────────────────────────────
消费方对未注册键**首调即抛**（fail-fast，非运行期静默 throw；对应 CRM 侧
`requireDecision` 的 throw 语义），避免下游键漂移。

铁律（与内核纪律一致）
─────────────────────
- P-A 零领域字面量：注册表只管「键 → 中性 profile」，不写任何业务边/业务词。
- 键格式闸**可插拨**（`KEY_FORMAT`）：`kebab`（默认，历史行为）或 `none`
  （不校验键格式），由 `set_key_format` 显式设置（进程级作用域；测试用
  autouse fixture 复原）。
- ⚠ 2026-10-09 双方核验更正（CRM 回信 §1-1 实锤）：CRM 侧 `config_change`
  （治理留痕）与 `config-change`（配置中心键写入）**语义不同，必须共存**，
  底座**禁止按字符串规范化判重**；强制 kebab 曾把 CRM 22 个 UPPER_SNAKE
  销售域键 + `config_change` 全部判非法 ⇒ 现默认 kebab 保持旧行为，跨语言
  消费方（Node/CRM）按 `set_key_format('none')` 登记自己的命名族。
- 注册表为**进程级全局可变**注册中心（用户明确选择：全局可变注册表）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

# 键格式策略：`kebab`（默认，历史行为）| `none`（不校验键格式，供跨语言消费方登记自己的命名族）。
# ⚠ 2026-10-09 双方核验更正：底座**禁止按字符串规范化判重**——`config_change` ≢ `config-change`
#   （CRM 回信 §1-1 实锤，二者语义不同），规范化会把不同语义键误判为同一键。
KEY_FORMAT_SLOT = ["kebab"]
_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def set_key_format(mode: str) -> None:
    """切换键格式闸（进程级作用域）。

    `kebab`（默认）：沿用历史强校验（`_KEY_RE`，与 `scenario/model._KEBAB_RE` 同源）。
    `none`（宽松）：不校验键格式——供跨语言消费方（Node/CRM）登记
    `config_change` / `LLM_*` 等非 kebab 键，同时保持重复登记判重不变。
    """
    mode = (mode or "").strip().lower()
    if mode not in ("kebab", "none"):
        raise ScenarioRegistryError(
            f"KEY_FORMAT 仅支持 'kebab' / 'none'，得到 {mode!r}")
    KEY_FORMAT_SLOT[0] = mode


def key_format() -> str:
    """当前键格式闸模式（供诊断 / 测试复原）。"""
    return KEY_FORMAT_SLOT[0]


__all__ = [
    "ScenarioRegistryError",
    "DecisionIOField",
    "IO_KINDS",
    "GATE_KINDS",
    "DecisionScenarioProfile",
    "register_scenario",
    "get_scenario",
    "require_scenario",
    "list_scenarios",
    "is_registered",
    "clear_registry",
    "set_key_format",
    "key_format",
]

# I/O 契约的**中性闭集词汇表**（零领域字面量铁律：只给形态，不给业务词）。
#   particle  = 消费/产出的粒子（type 经 TenantProfile 注入）
#   asset     = 场景包 assets 资产（如消费方的 decision_rules 挂点）
#   context   = run_spine 的触发上下文键（S1_context）
#   event     = 产出的事件（EventBus）
#   graph-edge= 产出的知识/记忆边（MEMORY_PREDICATES 族，source="engine"）
IO_KINDS = frozenset({"particle", "asset", "context", "event", "graph-edge"})

# 必经闸的**内核自有词汇**（与 spine 实际闸位一一对应；消费方不得自造闸名）。
GATE_KINDS = frozenset({"redline", "approval"})


class ScenarioRegistryError(Exception):
    """机器可路由的注册表失败（键非法 / 重复登记 / I/O 契约非法）。"""


@dataclass(frozen=True)
class DecisionIOField:
    """决策点 I/O 契约的**单条声明**（enterprise feedback #6）。

    name        kebab-case 键（与场景键同一格式闸）
    kind        必须属于 `IO_KINDS` 闭集（中性形态，非业务词）
    required    False ⇒ 缺供给时允许降级路径（对齐 degraded_recall 语义）
    description 人类可读说明（功能性语义；⛔ 不得写内部代号，§13 同律）
    """

    name: str
    kind: str
    required: bool = True
    description: str = ""


def _check_io_fields(
    fields: Iterable[DecisionIOField], *, side: str
) -> Tuple[DecisionIOField, ...]:
    """校验并规范化一侧 I/O 声明（注册期 fail-fast，非运行期静默）。"""
    normalized: List[DecisionIOField] = []
    seen: set = set()
    for f in fields:
        if not isinstance(f, DecisionIOField):
            raise ScenarioRegistryError(
                f"{side} 项必须是 DecisionIOField，得到 {type(f).__name__}")
        if key_format() == "kebab" and not _KEY_RE.match(f.name or ""):
            raise ScenarioRegistryError(
                f"{side}.name 必须为 kebab-case：{f.name!r}")
        if f.kind not in IO_KINDS:
            raise ScenarioRegistryError(
                f"{side}.kind 必须属于闭集 {sorted(IO_KINDS)}，得到 {f.kind!r}")
        if f.name in seen:
            raise ScenarioRegistryError(
                f"{side} 内 name 重复：{f.name!r}")
        seen.add(f.name)
        normalized.append(f)
    return tuple(normalized)


@dataclass
class DecisionScenarioProfile:
    """中性决策场景描述（零领域字面量；领域经 TenantProfile / 场景包注入）。

    inputs / outputs / required_gates（enterprise feedback #6：决策点契约 schema）
    ────────────────────────────────────────────────────────────────────────
    全部可选（空元组 = 旧式未声明 I/O 的登记，向后兼容）。声明后：
    - `inputs`  本决策消费哪些粒子/资产/上下文键（缺供给 ⇒ 消费方降级判据的依据）
    - `outputs` 本决策产出哪些粒子/事件/边、被谁消费
    - `required_gates` 必经闸（闭集：redline / approval）——注册期即声明治理语义
    """

    key: str
    title: str
    description: str = ""
    version: str = "0.1.0"
    rubric: str = ""
    redline: str = ""
    inputs: Tuple[DecisionIOField, ...] = ()
    outputs: Tuple[DecisionIOField, ...] = ()
    required_gates: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "title": self.title,
            "description": self.description,
            "version": self.version,
            "rubric": self.rubric,
            "redline": self.redline,
            "inputs": [f.__dict__ for f in self.inputs],
            "outputs": [f.__dict__ for f in self.outputs],
            "required_gates": list(self.required_gates),
        }


_REGISTRY: Dict[str, DecisionScenarioProfile] = {}


def _check_key(key: str) -> str:
    if not isinstance(key, str) or not key.strip():
        raise ScenarioRegistryError(
            f"决策场景键必须为非空字符串：{key!r}")
    if key_format() == "kebab" and not _KEY_RE.match(key):
        raise ScenarioRegistryError(
            f"决策场景键必须为 kebab-case（连字符、全小写）：{key!r}")
    return key


def register_scenario(
    key: str,
    *,
    title: str,
    description: str = "",
    version: str = "0.1.0",
    rubric: str = "",
    redline: str = "",
    inputs: Iterable[DecisionIOField] = (),
    outputs: Iterable[DecisionIOField] = (),
    required_gates: Iterable[str] = (),
) -> DecisionScenarioProfile:
    """登记一个决策场景键（单一事实源）。

    重复登记同一键 ⇒ 抛 `ScenarioRegistryError`（强制单一注册，根治三态键分裂）。
    `inputs`/`outputs`/`required_gates` 为可选 I/O 契约（feedback #6）：声明即
    注册期校验（fail-fast）；不声明 = 旧式登记，行为不变。
    """
    _check_key(key)
    if not isinstance(title, str) or not title.strip():
        raise ScenarioRegistryError(f"title 必须为非空字符串：{title!r}")
    if key in _REGISTRY:
        raise ScenarioRegistryError(
            f"决策场景键已注册（单一事实源，禁止重复）：{key!r}。"
            f"已登记：{sorted(_REGISTRY)}")
    in_fields = _check_io_fields(inputs, side="inputs")
    out_fields = _check_io_fields(outputs, side="outputs")
    gates = tuple(required_gates)
    bad_gates = [g for g in gates if g not in GATE_KINDS]
    if bad_gates:
        raise ScenarioRegistryError(
            f"required_gates 必须是内核自有闸的子集 {sorted(GATE_KINDS)}，"
            f"得到非法闸：{bad_gates}")
    if len(set(gates)) != len(gates):
        raise ScenarioRegistryError(f"required_gates 存在重复：{gates}")
    profile = DecisionScenarioProfile(
        key=key, title=title, description=description,
        version=version, rubric=rubric, redline=redline,
        inputs=in_fields, outputs=out_fields, required_gates=gates,
    )
    _REGISTRY[key] = profile
    return profile


def is_registered(key: str) -> bool:
    return key in _REGISTRY


def get_scenario(key: str) -> Optional[DecisionScenarioProfile]:
    return _REGISTRY.get(key)


def require_scenario(key: str) -> DecisionScenarioProfile:
    """取已登记场景；未登记 ⇒ 首调抛 `ValueError`（fail-fast）。

    对应 CRM F-05「未注册键在 produceDecision 首调抛 ValueError」——
    把「键漂移」从运行期静默崩溃前置为启动/首调即红。
    """
    if key not in _REGISTRY:
        raise ValueError(
            f"决策场景键未注册（须先 register_scenario）：{key!r}。"
            f"已登记：{sorted(_REGISTRY)}")
    return _REGISTRY[key]


def list_scenarios() -> List[DecisionScenarioProfile]:
    return list(_REGISTRY.values())


def clear_registry() -> None:
    """清空注册表（测试 / 进程重启重用）。"""
    _REGISTRY.clear()
