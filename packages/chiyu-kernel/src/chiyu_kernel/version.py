"""版本与能力清单出口。

消费方需要**机检**底座的版本与能力状态，而不是靠 `hasattr` 嗅探符号、
或靠读注释推断某子系统是否实验态。本模块把这两件事实显式化。

设计约束：
- 严格加法：本模块只提供只读出口，不改变任何既有行为。
- 状态位三值：`stable` / `experimental` / `deprecated`，非法值即判红。
- 能力清单是**可枚举**的，新增层未登记即被守卫检出（防"能力悄悄上线但无人知"）。

1.0 兼容冻结声明（v1.0-发布判据 §1-A）：
- 状态为 `stable` 的能力层自 0.1.0 起进入 **1.0 兼容承诺**——此后任何 BREAKING
  变更必须先走完整 deprecation 周期（先 warn 一版再移除，
  见 `docs/versioning-and-deprecation.md`）。
- `memory` 已于 2026-10-10 毕业（T40–T44：双轨 PG 落库 / 召回接入 run_spine /
  RRF 融合 / 真库 E2E / 单源裁定），转入 stable，进入 1.0 兼容承诺。
- `evolution` 已于 2026-10-13 毕业（T78：readiness 十闸全绿验收——§12.3 七闸 +
  §12.4 G1/G2/G3 护栏，10/10 含对抗判别力；判据面 = 7 个 evolution 测试文件
  （knob/replay/prescription/guard/readiness/chain/skill_draft）+ 毕业守卫
  `test_evolution_graduation.py`（G1-G5，变异自证 A/B 双向）），转入 stable，
  进入 1.0 兼容承诺。至此 CAPABILITIES 无 experimental 层（34 层全 stable；
  Batch-2b 起 GAP-6~9 上迁 feedback/capability_audit/connectors/promotion 四层）。
"""
from __future__ import annotations

from typing import Dict, Mapping, Tuple

__all__ = [
    "API_VERSION", "CONTRACT_VERSION", "VALID_STATUSES",
    "CAPABILITIES", "DEPRECATIONS",
    "__version__", "PACKAGE_VERSION",
    "api_version", "capabilities", "capability_status", "deprecations",
    "require_capabilities",
]

#: 分发包版本兜底值（`pyproject.toml` 未安装时取此值）。
PACKAGE_VERSION = "0.1.0"


def _distribution_version() -> str:
    """取已安装分发包的版本；未安装（源码直跑）时回退到 `PACKAGE_VERSION`。

    ⛔ 为什么不当常量写死：`__version__` 的价值是**与分发物一致**（N1：消费方
       构建期 `assert 版本 >= 基线`）。写死会出现"包已升版、门面仍报旧版"的静默漂移。
    """
    try:
        from importlib.metadata import PackageNotFoundError, version
        try:
            return version("chiyu-kernel")
        except PackageNotFoundError:
            return PACKAGE_VERSION
    except Exception:                       # pragma: no cover - 元数据不可用时兜底
        return PACKAGE_VERSION


#: 分发包版本（N1：消费方可版本钉与构建期断言）。
__version__ = _distribution_version()

#: 公开门面版本（语义化版本）。门面导出面发生**不兼容**变化时升主版本号。
API_VERSION = "1.0.0"

#: L0 契约版本。契约常量取值或形状变化时升级。
CONTRACT_VERSION = "1.0.0"

#: 允许的能力状态。
VALID_STATUSES: Tuple[str, ...] = ("stable", "experimental", "deprecated")

#: 能力清单：`(能力名, 状态)`。
#: ⛔ 新增层必须登记，否则 `test_version_and_capabilities.py` 判红
#: （判据由层的磁盘枚举机械推导，不靠人记）。
CAPABILITIES: Tuple[Tuple[str, str], ...] = (
    ("contract", "stable"),
    ("vector", "stable"),
    ("ontology", "stable"),
    ("context", "stable"),
    ("actions", "stable"),
    ("domain", "stable"),
    ("persist", "stable"),
    ("approval", "stable"),
    ("graph", "stable"),
    ("mcpserver", "stable"),
    ("canary", "stable"),
    ("orchestration", "stable"),
    # 自进化层：T78（2026-10-13）毕业验收 = readiness 十闸全绿（§12.3 七闸 +
    # §12.4 G1/G2/G3，10/10 含对抗判别力），转 stable，进入 1.0 兼容承诺。
    # 自进化层：T78（2026-10-13）毕业验收 = readiness 十闸全绿（§12.3 七闸 +
    # §12.4 G1/G2/G3 护栏，10/10 含对抗判别力），转 stable，进入 1.0 兼容承诺。
    ("evolution", "stable"),
    ("events", "stable"),
    ("audit", "stable"),
    ("llm", "stable"),
    ("plugins", "stable"),
    ("session", "stable"),
    ("tools", "stable"),
    ("skills", "stable"),
    ("plan", "stable"),
    ("mcp", "stable"),
    ("hooks", "stable"),
    ("interaction", "stable"),
    ("workflow", "stable"),
    ("scenario", "stable"),
    # Batch-2b（2026-10-14）：GAP-6~9 上迁（APS 盘点 §四 第三波）。
    # feedback = 反馈闭环纯函数核心（指标模板/双口径/三档评估/拒绝出方/HITL 校准闸）。
    ("feedback", "stable"),
    # capability_audit = 能力落地审计（三查法判定次序/调用点计数/四件套装配）。
    ("capability_audit", "stable"),
    # connectors = 连接器传输层（无状态工厂 + 文件传输 + 注册表；域连接器留消费方）。
    ("connectors", "stable"),
    # promotion = 知识升格 + K-M-D 回流管道（三态闸门/产物红线/覆盖守卫/四通道/后见之明）。
    ("promotion", "stable"),
    ("store", "stable"),
    # 决策层在兄弟包 `chiyu_decision.api`（sanctioned 面之一，见 N2）。
    ("decision", "stable"),
    # 写操作安全闸（八闸框架 + 第0闸决策凭证，Batch-1a，2026-10-13）：L0 契约 +
    # 机制层双重落地，进入 1.0 兼容承诺。
    ("gate", "stable"),
    # 记忆网：T40–T44 已验收（PG 落库 + 召回接入 + RRF + 真库 E2E + 单源裁定），
    # 2026-10-10 转 stable，进入 1.0 兼容承诺。
    ("memory", "stable"),
    # Batch-1b-1（2026-10-14）：rbac_core 判定核（别名归一 fail-closed / 角色相等与
    # 成员判定 / 租户域限定 / 权限矩阵全函数查询；别名表与矩阵内容留消费方注入）。
    ("iam", "stable"),
    # Batch-1b-3（2026-10-14）：决策支撑三能力（上迁自 CRM，判据算法在基座、
    # 证据与域词表留消费方注入）。
    ("conflict_resolver", "stable"),
    ("attribution", "stable"),
    ("audit_4q", "stable"),
    ("ab_experiment", "stable"),
    ("quota_gate", "stable"),
    ("param_health_check", "stable"),
    ("observability", "stable"),
    ("agent_runtime", "stable"),
    ("scheduler_core", "stable"),
    ("nightly_report", "stable"),
)

#: 弃用别名映射：`旧名 -> 建议新名`。旧名仍可导入（严格加法，不破坏）。
DEPRECATIONS: Dict[str, str] = {
    "TIER_FTS_VECTOR": "VTIER_FTS_VECTOR",
    "TIER_VECTOR": "VTIER_VECTOR",
    "TIER_FTS": "VTIER_FTS",
    "TIER_NONE": "VTIER_NONE",
    "TIER_ORDER": "VTIER_ORDER",
}

_MAP: Mapping[str, str] = {name: status for name, status in CAPABILITIES}


def api_version() -> str:
    """返回公开门面版本。"""
    return API_VERSION


def contract_version() -> str:
    """返回 L0 契约版本。"""
    return CONTRACT_VERSION


def capabilities() -> Tuple[Tuple[str, str], ...]:
    """返回能力清单 `(能力名, 状态)` 只读元组。"""
    return CAPABILITIES


def capability_status(name: str) -> str:
    """查单个能力状态；未登记抛 `KeyError`（有界，不静默返回空）。"""
    return _MAP[name]


def deprecations() -> Dict[str, str]:
    """返回弃用别名映射的只读副本。"""
    return dict(DEPRECATIONS)


def require_capabilities(required: Mapping[str, str]) -> None:
    """启动期能力自检（G5，enterprise 第二轮诉求的机检落地）。

    断言"某个能力存在**且状态符合期望**"，比版本钉更精确。消费方在建链/
    启动期调用（对应其 T8）：

        require_capabilities({"decision": "stable", "persist": "stable"})

    - 能力未登记 ⇒ 报入 mismatch（不是 KeyError 静默）；
    - 状态不符（如把 experimental 当 stable 用）⇒ 报入 mismatch；
    - 任一 mismatch ⇒ `RuntimeError` 一次性列全（fail-fast，不逐个炸）。
    ⛔ 推荐断言语态见 `docs/versioning-and-deprecation.md` §启动期能力自检。
    """
    mismatches = []
    for name, want in required.items():
        have = _MAP.get(name)
        if have is None:
            mismatches.append(f"{name}: 能力未登记（期望 {want}）")
        elif have != want:
            mismatches.append(f"{name}: 期望 {want}，实际 {have}")
    if mismatches:
        raise RuntimeError(
            "底座能力自检失败（require_capabilities）：" + "；".join(mismatches))
