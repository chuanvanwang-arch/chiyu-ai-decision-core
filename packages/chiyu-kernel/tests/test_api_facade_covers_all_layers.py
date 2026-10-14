"""门面接线完整性守卫 —— 「模块已建好但门面没暴露」是一种**零报错**缺陷。

背景（2026-09-21 T5 收口时的实测）：`audit`/`events`/`llm`/`orchestration` 四模块
源码已写好且能 import，但 `api.py` **没有暴露它们**。这种缺陷不会让任何测试变红 ——
消费方要么违约 import 内部路径（A3 违约），要么**以为内核没有这个能力**。
故把"门面必须覆盖每个内层子包的 `__all__` 全集"写成可执行判据。

⛔ 判据不是"看一眼 api.py 顺眼"，而是**逐层比对集合**。本文件自带判别力自证
   （喂一个少一个符号的假门面，断言它能检出）。
"""
from __future__ import annotations

import importlib

from chiyu_kernel import api

# 门面改名表：`(层, 层内原名) -> 门面名`。理由见 api.py 尾部注释（读性 + 防静默覆盖）。
RENAMES: dict[tuple[str, str], str] = {
    ("vector", "available"): "vector_available",
    ("vector", "backend"): "vector_backend",
    ("vector", "info"): "vector_info",
    ("vector", "resolve"): "vector_resolve",
    ("vector", "is_available"): "vector_is_available",
    # scenario：裸名 from_dict / build_in_memory_server 语义不明且易与未来符号
    # 静默冲突（与 vector 前缀同理由），门面加 scenario_ 前缀。
    ("scenario", "from_dict"): "scenario_from_dict",
    ("scenario", "build_in_memory_server"): "scenario_build_in_memory_server",
}

# ⛔ `store` 层的公共符号**机械推导**，不再人工枚举。
#   此前 `STORE_REQUIRED` 是人工清单：新增 store 公共符号若忘了同步，
#   守卫**静默放行**（既不在清单里、也不报错）⇒ 与 `evolution` 漏登记同族。
#   现在以 `store.__all__` 为唯一事实源，差异即红。
def store_public_symbols() -> tuple[str, ...]:
    """从 `chiyu_kernel.store.__all__` 机械推导该层全部公共符号。"""
    store = importlib.import_module("chiyu_kernel.store")
    return tuple(n for n in store.__all__ if not n.startswith("_"))


# 确不应进门面的符号须在此登记并写明理由（不得为了变绿而放宽判据）。
STORE_EXEMPT: dict[str, str] = {}

STORE_REQUIRED = store_public_symbols()

LAYERS = ("vector", "ontology", "context", "actions", "domain", "persist",
         "approval", "gate", "graph", "mcpserver", "canary", "orchestration", "evolution",
         "events", "audit", "llm", "plugins", "session", "tools", "skills",
         "plan", "mcp", "hooks", "interaction", "workflow", "scenario",
         "feedback", "capability_audit", "connectors", "promotion", "iam",
         "conflict_resolver", "attribution", "audit_4q",
         "ab_experiment", "quota_gate", "param_health_check",
         "observability", "agent_runtime", "scheduler_core", "nightly_report")

# ⛔ 清单是硬编码的 ⇒ 新增子包若忘了加进 `LAYERS`，本守卫会**静默放行**
#   （2026-09-22 实测：`evolution` 包已建好 24 个符号、门面一个没暴露，守卫却全绿）。
#   故此处显式登记"不在清单内"的子包及其理由；`test_no_undeclared_layer` 会核对
#   磁盘上的真实子包 —— 新增包要么进 `LAYERS`，要么在此登记，**没有第三条路**。
EXEMPT_LAYERS: dict[str, str] = {
    "contract": "L0 契约层，消费方直接 import `chiyu_kernel.contract`，"
                "门面只透出构造 profile 所需的最小面（见 api.__all__ 首段）",
    "store": "无 `__all__`（子模块直连），改由 `STORE_REQUIRED` 显式登记",
}


def _facade_name(layer: str, name: str) -> str:
    return RENAMES.get((layer, name), name)


def missing_names(layer: str, layer_all, facade) -> list[str]:
    """返回该层 `__all__` 里**未被门面暴露**的符号（已按改名表映射）。"""
    out: list[str] = []
    for name in layer_all:
        target = _facade_name(layer, name)
        if not hasattr(facade, target):
            out.append(f"{layer}.{name} → api.{target}")
    return out


def test_no_undeclared_layer():
    """磁盘上的每个子包都必须在 `LAYERS` 或 `EXEMPT_LAYERS` 里 —— 二选一。

    没有这条，新增子包忘了加进 `LAYERS` 时，上面所有用例仍全绿（守卫对漏检
    完全失明）。本用例把"漏登记"变成红灯。
    """
    import os
    import pkgutil

    import chiyu_kernel

    root = os.path.dirname(chiyu_kernel.__file__)
    on_disk = {m.name for m in pkgutil.iter_modules([root]) if m.ispkg}
    declared = set(LAYERS) | set(EXEMPT_LAYERS)
    undeclared = sorted(on_disk - declared)
    assert undeclared == [], (
        "下列子包既不在 LAYERS 也不在 EXEMPT_LAYERS ⇒ 其导出无人核验："
        f"{undeclared}"
    )
    # 反向：登记了却不存在的层同样要红（防止清单腐烂）
    ghost = sorted(declared - on_disk)
    assert ghost == [], f"清单登记了磁盘上不存在的子包：{ghost}"
    # 豁免必须带理由（空理由 ⇒ 等于没说）
    for name, why in EXEMPT_LAYERS.items():
        assert why.strip(), f"{name} 的豁免缺理由"


def test_layer_namespaces_live_in_the_package():
    for layer in LAYERS:
        mod = importlib.import_module(f"chiyu_kernel.{layer}")
        assert getattr(mod, "__all__", None), f"{layer} 缺 __all__（无法核验接线）"


def test_facade_covers_every_layer_export():
    problems: list[str] = []
    for layer in LAYERS:
        mod = importlib.import_module(f"chiyu_kernel.{layer}")
        problems.extend(missing_names(layer, mod.__all__, api))
    assert problems == [], "门面未覆盖下列符号 ⇒ 消费方只能违约 import 内部路径：\n  " + \
        "\n  ".join(problems)


def test_facade_covers_store_required_symbols():
    # 反恒绿：推导结果非空（若 store.__all__ 被清空，本守卫会静默失效）
    assert len(STORE_REQUIRED) >= 20, \
        f"store 公共面仅 {len(STORE_REQUIRED)} 项 ⇒ 机械推导失效"
    missing = [n for n in STORE_REQUIRED
               if n not in api.__all__ and n not in STORE_EXEMPT]
    assert missing == [], f"门面未暴露 store 公共符号：{missing}"
    for n, why in STORE_EXEMPT.items():
        assert why.strip(), f"豁免 {n} 未写理由"
        assert n in STORE_REQUIRED, f"豁免 {n} 不在 store 公共面（失效条目）"


def test_store_facade_names_map_same_object():
    """N2：`store.__all__` 的每个公开符号在门面同名可达，且指向**同一对象**。

    R12 已机械推导 `set(store.__all__) ⊆ set(api.__all__)`（上一条判据），但那只保证
    "名在"，不保证"名→对象"映射一致 —— 若有人在 `api.py` 把某 store 符号 re-export
    时误绑到别的对象，集合守卫仍绿。此条断言"同名且同一对象"，堵住改名映射断裂。
    """
    store = importlib.import_module("chiyu_kernel.store")
    bad: list[str] = []
    for n in store_public_symbols():
        if not hasattr(api, n):
            bad.append(f"{n} 缺失于门面")
            continue
        if getattr(api, n) is not getattr(store, n):
            # ⛔ 允许 RENAMES 表里的已知改名（门面名 ≠ 层内原名），其余必须同对象
            if n not in [r for (lr, ln), r in RENAMES.items() if lr == "store"]:
                bad.append(f"{n} 门面对象 ≠ store 对象（疑似错误 re-export）")
    assert bad == [], "store↔门面映射不一致：\n  " + "\n  ".join(bad)


def test_store_all_equals_submodule_union():
    """反假绿：store sanctioned 面须恒等于四个子模块 `__all__` 的并集。

    否则有人从 `store.__all__` 删一项，上一条守卫就静默放行了
    （与 `evolution` 漏登记同族：判据存在但可被绕过）。
    """
    union: set[str] = set()
    for m in ("ddl", "dsn", "conn", "pg_store"):
        mod = importlib.import_module(f"chiyu_kernel.store.{m}")
        union |= {n for n in mod.__all__ if not n.startswith("_")}
    declared = set(store_public_symbols())
    assert declared == union, (
        "store.__all__ 与子模块并集不一致 ⇒ 守卫可被绕过："
        f" 少列={sorted(union - declared)} 多列={sorted(declared - union)}")


def test_facade_all_is_consistent():
    """`__all__` 不得有重复；且每个名字都必须真的可解析（否则 `from api import *` 会炸）。"""
    assert len(api.__all__) == len(set(api.__all__)), [
        n for n in api.__all__ if api.__all__.count(n) > 1
    ]
    unresolvable = [n for n in api.__all__ if not hasattr(api, n)]
    assert unresolvable == [], f"__all__ 列了不存在的名字：{unresolvable}"


def test_experimental_flag_is_exposed():
    # T44（2026-10-10）：memory 已毕业转 stable，标志翻转；保留机器可检出口。
    assert api.MEMORY_EXPERIMENTAL is False
    assert "MEMORY_EXPERIMENTAL" in api.__all__
    # T78（2026-10-13）：evolution 毕业同族——标志翻转 + 机器可检出口。
    assert api.EVOLUTION_EXPERIMENTAL is False
    assert "EVOLUTION_EXPERIMENTAL" in api.__all__


def test_guard_discriminates_a_missing_symbol():
    """判别力自证：喂一个少一个符号的假门面，`missing_names` **必须**检出它。

    没有这条，上面的用例可能是空跑（本项目已踩过同族假绿）。
    """
    class _Stub:
        pass

    stub = _Stub()
    for name in ("compute_coverage", "backfill_plan"):
        setattr(stub, name, None)
    # 假层：三个符号，门面只暴露两个
    assert missing_names("vector", ("compute_coverage", "backfill_plan", "cosine"),
                         stub) == ["vector.cosine → api.cosine"]
    # 改名表同样被核验：裸名 `available` 不算暴露，必须 `vector_available`
    setattr(stub, "available", None)
    assert missing_names("vector", ("available",), stub) == [
        "vector.available → api.vector_available"
    ]
    setattr(stub, "vector_available", None)
    assert missing_names("vector", ("available",), stub) == []
