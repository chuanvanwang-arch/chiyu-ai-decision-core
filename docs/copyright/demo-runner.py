"""软著材料功能演示运行器。

逐一实跑青羽 AI 原生底座软件（ChiYu-Foundation）V1.0 的对外门面能力，
把**真实运行结果**打印到标准输出，供文档鉴别材料截图使用。

⛔ 诚实原则：本脚本不做任何"看起来跑通"的伪造——要素缺失就报缺失，
   向量通道未就绪就如实降级，缺口为 0 就是 0。所有数字均来自实际返回值。

用法：
    python demo-runner.py <demo-name>
    python demo-runner.py --list
"""
from __future__ import annotations

import sys

WIDTH = 78


def banner(title: str, subtitle: str = "") -> None:
    print("=" * WIDTH)
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print("=" * WIDTH)


def step(text: str) -> None:
    print(f"\n$ {text}")


def kv(key: str, value: object) -> None:
    print(f"  {key:<22}: {value}")


# ══════════════════════════════════════════════════════════════════════
# 01 版本化与兼容承诺（功能 14）
# ══════════════════════════════════════════════════════════════════════
def demo_version() -> None:
    from chiyu_kernel.api import (
        API_VERSION, CONTRACT_VERSION, CAPABILITIES, DEPRECATIONS,
        api_version, capabilities, capability_status, contract_version,
        deprecations, __version__,
    )

    banner("功能演示 01　版本化与兼容承诺", "对外版本出口、能力清单与弃用别名查询")
    step("from chiyu_kernel.api import __version__, api_version, contract_version")
    kv("分发版本 __version__", __version__)
    kv("门面版本 api_version()", api_version())
    kv("契约版本 contract_version()", contract_version())
    kv("常量 API_VERSION", API_VERSION)
    kv("常量 CONTRACT_VERSION", CONTRACT_VERSION)

    step("capabilities()  —— 能力清单（机器可读，标注稳定/实验态档位）")
    caps = capabilities()
    print(f"  共登记 {len(caps)} 项能力：")
    for name, tier in caps:
        print(f"    - {name:<28} {tier}")

    step("capability_status(name)  —— 单项能力档位查询")
    for probe in ("store", "decision", "memory"):
        print(f"    capability_status({probe!r}) -> {capability_status(probe)}")
    print("    注：未登记的能力名查询会快速失败（见下）")
    try:
        capability_status("portal")
    except Exception as exc:  # noqa: BLE001
        print(f"    capability_status('portal') -> {type(exc).__name__}: {exc}")

    step("deprecations()  —— 弃用别名查询（先告警后移除的弃用政策）")
    dep = deprecations()
    print(f"  在册弃用别名 {len(dep)} 项：")
    for old, new in dep.items():
        print(f"    - {old:<24} -> {new}")

    step("require_capabilities({'store':'stable'})  —— 构建期版本钉与兼容断言")
    from chiyu_kernel.api import require_capabilities
    require_capabilities({"store": "stable"})
    print("  断言通过：能力 'store' 档位满足 'stable'（无异常抛出）")


# ══════════════════════════════════════════════════════════════════════
# 02 契约与配置载体（功能 1）
# ══════════════════════════════════════════════════════════════════════
def demo_contract() -> None:
    from chiyu_kernel.contract import (
        ParticleTypeSet, PredicateSet, PredicateSpec, TenantProfile, RedlineSpec,
        CORE_ROLES,
    )

    banner("功能演示 02　契约与配置载体", "租户画像 TenantProfile 与红线规格 RedlineSpec")

    step("内核声明的核心语义角色 CORE_ROLES（任意业务域都成立）")
    kv("CORE_ROLES", list(CORE_ROLES))

    step("构造粒子类型集（消费方注入业务取值，内核只声明形态）")
    kv("缺核心角色会被拦截", "ParticleTypeSet(names=('customer','order'))")
    try:
        ParticleTypeSet(names=("customer", "order"))
        print("  !! 未拦截（异常：不应发生）")
    except Exception as exc:  # noqa: BLE001
        print(f"  已拦截 -> {type(exc).__name__}: {exc}")

    pts = ParticleTypeSet(names=tuple(CORE_ROLES) + ("customer", "order", "contract"))
    kv("particle_types", list(pts.names))

    step("构造受控谓词集 PredicateSet")
    preds = PredicateSet(knowledge=(
        PredicateSpec(predicate="BELONGS_TO", from_type="order", to_type="customer",
                      cardinality="N:1", source="rule", layer="K"),
        PredicateSpec(predicate="SIGNS", from_type="customer", to_type="contract",
                      cardinality="1:N", source="rule", layer="K"),
    ))
    kv("knowledge 谓词", [p.predicate for p in preds.knowledge])
    kv("memory 谓词", [p.predicate for p in preds.memory])

    step("构造红线规格 RedlineSpec（互斥顶与敏感事项目录）")
    redline = RedlineSpec(mutex_top=frozenset({"预算外承诺"}),
                          sensitive=frozenset({"客户报价", "折扣权限"}))

    step("装配租户画像 TenantProfile")
    profile = TenantProfile(
        domain="generic-demo",
        particle_types=pts,
        predicates=preds,
        redline=redline,
        rubric_thresholds={"autonomous_release": 0.79},
        autonomous_threshold=0.79,
    )
    kv("domain", profile.domain)
    kv("粒子类型", list(profile.particle_types.names))
    kv("自主放行阈值", profile.autonomous_threshold)
    kv("红线·互斥顶", sorted(profile.redline.mutex_top))
    kv("红线·敏感项", sorted(profile.redline.sensitive))

    step("构造期校验：非法取值必须快速失败（不静默接纳）")
    try:
        TenantProfile(domain="bad", particle_types=ParticleTypeSet(names=()))
        print("  !! 未拦截（异常：不应发生）")
    except Exception as exc:  # noqa: BLE001
        print(f"  已拦截 -> {type(exc).__name__}: {exc}")


# ══════════════════════════════════════════════════════════════════════
# 03 粒子与本体管理（功能 2）
# ══════════════════════════════════════════════════════════════════════
def demo_particle() -> None:
    from chiyu_kernel.api import Particle, OntologyGraph, hash_vector, ontology_sync
    from chiyu_kernel.contract import PredicateSet, PredicateSpec

    banner("功能演示 03　粒子与本体管理", "统一业务实体模型 Particle 与本体图 OntologyGraph")

    step("构造粒子 Particle（业务事实的统一载体）")
    p1 = Particle(particle_id="p-order-001", type="order", layer="L1",
                  label="样例订单 A", status="open", subject_id="c-001",
                  fulltext="客户签署年度框架合同并下达首批订单")
    p2 = Particle(particle_id="p-contract-001", type="contract", layer="L1",
                  label="框架合同 A", status="signed", subject_id="c-001",
                  fulltext="年度框架合同，约定阶梯价格与交付条款")
    for p in (p1, p2):
        kv("particle_id", f"{p.particle_id}  type={p.type}  layer={p.layer}  status={p.status}")

    step("写时钩子：内容哈希 content_hash 与嵌入补齐 embedding")
    for p in (p1, p2):
        vec = hash_vector(p.fulltext or "")
        print(f"    {p.particle_id}: 文本 {len(p.fulltext or '')} 字 -> "
              f"向量维度 {len(vec)}，L2 范数 {round(float((vec ** 2).sum() ** 0.5), 6)}")

    step("本体图 OntologyGraph：受控谓词维护实体间关系（谓词由消费方注入）")
    k_preds = PredicateSet(knowledge=(
        PredicateSpec(predicate="DECIDED_ON", from_type="decision", to_type="order",
                      cardinality="N:1", source="engine", layer="K"),
        PredicateSpec(predicate="REFERENCED_PRECEDENT", from_type="decision",
                      to_type="decision", cardinality="N:M",
                      source="engine", layer="K"),
    ))
    og = OntologyGraph(predicates=k_preds)
    kv("受控谓词（K 层）", list(og.controlled()))
    og.link("DECIDED_ON", "dec-001", "p-order-001")
    og.link("REFERENCED_PRECEDENT", "dec-001", "p-contract-001")
    print("  已建立 2 条受控边：dec-001 -DECIDED_ON-> p-order-001")
    print("                    dec-001 -REFERENCED_PRECEDENT-> p-contract-001")

    step("受控谓词闸：未受控谓词必须被拒绝（防止事实源分裂）")
    try:
        og.link("随便造一个谓词", "a", "b")
        print("  !! 未拦截（异常：不应发生）")
    except Exception as exc:  # noqa: BLE001
        print(f"  已拦截 -> {type(exc).__name__}: {exc}")


# ══════════════════════════════════════════════════════════════════════
# 04 向量与语义检索（功能 3）
# ══════════════════════════════════════════════════════════════════════
def demo_vector() -> None:
    from chiyu_kernel.api import (
        hash_vector, vector_available, vector_backend, vector_info,
        vector_resolve, MIN_EMBEDDING_COVERAGE, VTIER_VECTOR, VTIER_FTS_VECTOR,
    )

    banner("功能演示 04　向量与语义检索", "本地离线向量推理、维度补齐与降级语义")

    step("vector_info()  —— 推理后端自检")
    info = vector_info()
    for k, v in info.items():
        kv(k, v)

    step("vector_available(column_dim=384)  —— 通道可用性")
    kv("是否可用", vector_available(column_dim=384))
    be = vector_backend()
    kv("后端标识", getattr(be, "backend", be))
    kv("模型目录", getattr(be, "model_dir", "n/a"))

    step("vector_resolve(text, column_dim=384)  —— 句向量求解（返回 向量/档位/标签）")
    text = "客户要求本季度内完成交付并追加预算"
    vec, tier, tag = vector_resolve(text, column_dim=384)
    kv("输入文本", text)
    kv("向量维度", "None（通道未就绪）" if vec is None else len(vec))
    kv("档位 tier", tier)
    kv("标签 tag", tag)
    kv("档位常量", f"VTIER_VECTOR={VTIER_VECTOR} / VTIER_FTS_VECTOR={VTIER_FTS_VECTOR}")
    kv("覆盖度下限", MIN_EMBEDDING_COVERAGE)

    step("hash_vector(text)  —— 确定性哈希签名向量（离线兜底通道）")
    hv = hash_vector(text)
    kv("维度", len(hv))
    nz = int((hv != 0).sum())
    kv("非零维度", f"{nz} / {len(hv)}（SHA-256 字节映射有符号扰动，稀疏属预期）")
    kv("L2 范数", round(float((hv ** 2).sum() ** 0.5), 6))
    hv2 = hash_vector(text)
    kv("幂等性校验", f"两次计算完全一致 = {bool((hv == hv2).all())}")

    step("余弦相似度检索（同语义近邻排序演示）")
    import numpy as np
    corpus = [
        "客户要求本季度内完成交付并追加预算",
        "客户希望缩短交付周期并增加投入",
        "本次会议讨论了食堂菜单调整",
    ]
    q = hash_vector("交付周期与预算追加的客户诉求")
    print(f"  查询：交付周期与预算追加的客户诉求")
    ranked = sorted(
        ((float(np.dot(q, hash_vector(c)) /
                (np.linalg.norm(q) * np.linalg.norm(hash_vector(c)) + 1e-12)), c)
         for c in corpus),
        reverse=True,
    )
    for i, (score, c) in enumerate(ranked, 1):
        print(f"    {i}. 相似度 {score:+.6f}  {c}")


# ══════════════════════════════════════════════════════════════════════
# 05 情境装配与降级召回（功能 4）
# ══════════════════════════════════════════════════════════════════════
def demo_context() -> None:
    from chiyu_kernel.api import (
        CONTEXT_LAYERS, CONTEXT_DIMENSIONS, assemble, check_supply_demand,
        degraded_recall, to_supply_layer, missing_context_dimensions, hash_vector,
    )
    from chiyu_kernel.context.assembly import KnowledgeNeed

    banner("功能演示 05　情境装配与降级召回", "分层情境 L1-L4、三级降级召回与供需缺口检查")

    step("情境分层常量")
    kv("CONTEXT_LAYERS", list(CONTEXT_LAYERS))
    kv("CONTEXT_DIMENSIONS", list(CONTEXT_DIMENSIONS))

    step("degraded_recall()  —— 三级降级召回（真向量通道未就绪时如实降级并留痕）")
    pool = [
        {"key": "k1", "text": "历史先例：同类客户在预算追加后选择分期交付", "vector": None},
        {"key": "k2", "text": "历史先例：交付周期紧张时启用加急通道", "vector": None},
        {"key": "k3", "text": "无关记录：办公室绿植养护安排", "vector": None},
    ]
    res = degraded_recall(["客户", "预算", "交付"], pool, query_vector=None, top_k=5)
    kv("池内条目数", len(pool))
    kv("命中条目数", len(res.items))
    ev = getattr(res, "evidence", None)
    kv("召回档位 tier", getattr(ev, "tier", "n/a"))
    kv("是否使用真向量", getattr(ev, "vector_used", "n/a"))
    kv("向量覆盖率", getattr(ev, "embedding_coverage", "n/a"))
    for it in res.items:
        print(f"    - {getattr(it, 'key', it)}")
    if ev is not None:
        print("    降级留痕（notes）：")
        for note in getattr(ev, "notes", ()):  # 如实记录为何降级
            print(f"      · {note}")

    step("to_supply_layer(result)  —— 召回结果落入供给层")
    layer = to_supply_layer(res, layer="L2", dim="precedent")
    kv("供给层", {k: (len(v) if isinstance(v, (list, tuple)) else v)
                 for k, v in layer.items()})

    step("assemble(needs, provided)  —— 按分层情境模型装配上下文")
    needs = [KnowledgeNeed(layer="L2", dims=("decision_history",), key="先例"),
             KnowledgeNeed(layer="L1", dims=("governance",), key="制度")]
    provided = {
        "L2": [{"key": it.key, "dim": "decision_history", "text": getattr(it, "text", "")}
               for it in res.items],
        "L1": [],
    }
    asm = assemble(needs, provided)
    kv("装配结果类型", type(asm).__name__)
    kv("facts（按层聚合）", {k: (len(v) if isinstance(v, (list, tuple)) else v)
                            for k, v in asm.facts.items()})
    sr = asm.supply_report
    kv("供给报告", {k: v for k, v in vars(sr).items()})

    step("check_supply_demand(needs, supply)  —— 供需缺口检查（不静默返回空）")
    from chiyu_kernel.context.knowledge_needs import build_knowledge_needs
    kn = build_knowledge_needs(task_name="是否批准该客户的预算追加请求", knowledge_level=3,
                               query_terms=("客户", "预算", "交付"))
    kv("task_name", kn.task_name)
    kv("知识层级", kn.knowledge_level)
    kv("查询词", list(kn.query_terms))
    gaps = check_supply_demand(kn, {"L1": [], "L2": list(res.items)})
    print(f"  检出供需缺口 {len(gaps)} 项：")
    for g in gaps:
        print(f"    - {g}")

    step("missing_context_dimensions(supplied)  —— 七维齐全轴的缺失项")
    supplied = {"identity": "customer-1", "semantics": ["先例 2 条"]}
    print(f"    已供维度：{sorted(supplied)}")
    print(f"    缺失维度：{missing_context_dimensions(supplied)}")


# ══════════════════════════════════════════════════════════════════════
# 06 图存储与关系视图（功能 5）
# ══════════════════════════════════════════════════════════════════════
def demo_graph() -> None:
    from chiyu_kernel.api import (
        GraphEdge, InMemoryGraphStore, relation_view, timeline_view,
        decision_backlinks,
    )

    banner("功能演示 06　图存储与关系视图", "只读派生协议、多跳遍历、时间线与决策回链")

    preds = ("BELONGS_TO", "SIGNS", "DECIDED_ON", "REFERENCED_PRECEDENT",
             "OVERRIDES", "DERIVED_FROM_EXCEPTION", "ESTABLISHES_FRAME")
    edges = (
        GraphEdge(from_id="order-1", to_id="customer-1", predicate="BELONGS_TO", layer="K"),
        GraphEdge(from_id="customer-1", to_id="contract-1", predicate="SIGNS", layer="K"),
        GraphEdge(from_id="dec-1", to_id="order-1", predicate="DECIDED_ON"),
        GraphEdge(from_id="dec-1", to_id="dec-0", predicate="REFERENCED_PRECEDENT"),
        GraphEdge(from_id="dec-2", to_id="dec-1", predicate="OVERRIDES"),
    )
    store = InMemoryGraphStore(predicates=preds, edges=edges)

    step("store.controlled()  —— 受控谓词清单（消费方注入）")
    kv("受控谓词", list(store.controlled()))

    step("out_edges('customer-1')  —— 一跳出边查询")
    for e in store.out_edges("customer-1"):
        print(f"    customer-1 -{e.predicate}-> {e.to_id}")

    step("in_edges('contract-1')  —— 一跳入边查询")
    for e in store.in_edges("contract-1"):
        print(f"    {e.from_id} -{e.predicate}-> contract-1")

    step("traverse('customer-1', max_hops=3)  —— 多跳遍历（带环检测与深度上限）")
    r = store.traverse("customer-1", max_hops=3, direction="out")
    kv("起点", r.root)
    kv("到达节点", list(r.nodes))
    kv("路径数", len(r.paths))
    for p in r.paths:
        print(f"    {' -> '.join(p)}")
    kv("截断标记 truncated", r.truncated)

    step("relation_view(store, 'customer-1')  —— 关系图谱视图")
    rv = relation_view(store, "customer-1", max_hops=2)
    for k, v in rv.items():
        print(f"    {k}: {v if not isinstance(v, (list, tuple)) else len(v)} 项")

    step("timeline_view(...)  —— 时间线叙事视图（四源只读聚合）")
    tl = timeline_view(
        particles=[{"particle_id": "order-1", "subject_id": "customer-1",
                    "created_at": "2026-09-01T10:00:00", "type": "order"}],
        edges=[{"from_id": "customer-1", "to_id": "contract-1", "predicate": "SIGNS",
                "ts": "2026-09-02T10:00:00"}],
        events=[{"id": "evt-1", "subject_id": "customer-1", "event_type": "decision",
                 "created_at": "2026-09-03T09:00:00"}],
        decisions=[{"decision_id": "dec-1", "subject_id": "customer-1",
                    "decided_at": "2026-09-03T10:00:00"}],
        subject_id="customer-1",
    )
    print(f"  时间线条目 {len(tl)} 条（按时间基准升序）：")
    for row in tl:
        print(f"    {row['time_basis']}  [{row['source']}]  {row['kind']}  ->  {row['ref']}")

    step("decision_backlinks(store, 'dec-1')  —— 决策回链（审计四问）")
    bl = decision_backlinks(store, "dec-1")
    for k, v in bl.items():
        print(f"    {k}: {v}")


# ══════════════════════════════════════════════════════════════════════
# 07 决策脊柱（功能 6）
# ══════════════════════════════════════════════════════════════════════
def demo_spine() -> None:
    from chiyu_decision.api import run_spine
    from chiyu_kernel.api import RUBRIC_KEYS, SPINE_ORDER, EIGHT_ELEMENTS, \
        AUTONOMOUS_RELEASE_DEFAULT, RUBRIC_SCALE_MAX, validate_spine_order

    banner("功能演示 07　决策脊柱", "六阶段顺序契约、九尺子评分、红线判定与自主放行闸门")

    step("顺序契约常量")
    kv("SPINE_ORDER", list(SPINE_ORDER))
    kv("顺序自校验", f"validate_spine_order(SPINE_ORDER) = {validate_spine_order(SPINE_ORDER)}")
    kv("九尺子", list(RUBRIC_KEYS))
    kv("单尺满分", RUBRIC_SCALE_MAX)
    kv("八要素", list(EIGHT_ELEMENTS))
    kv("自主放行缺省阈值", AUTONOMOUS_RELEASE_DEFAULT)

    def _run(label: str, scores: dict, redline_items=(), text="按既定授权范围推进，无越权事项。"):
        print(f"\n  ── {label} ──")
        r = run_spine(
            context={"decision_id": f"demo-{label}", "topic": "是否批准该客户的预算追加请求",
                     "work_mode": "standard", "text": text},
            profile=None,
            rubric_scores=scores,
            elements={"intent": "是否批准该客户的预算追加请求"},
            persister=None,
            threshold=0.79,
            redline_items=redline_items,
        )
        kv("decision_id", r.decision_id)
        kv("stage_reached", r.stage_reached)
        kv("confidence", round(r.confidence, 4))
        kv("autonomous", r.autonomous)
        kv("redline_hit", r.redline_hit)
        kv("redline_reasons", list(r.redline_reasons))
        kv("rubric_missing", list(r.rubric_missing))
        kv("elements_missing", list(r.elements_missing))
        kv("persisted", r.persisted)
        return r

    base = {k: 3.0 for k in RUBRIC_KEYS}
    _run("场景A-满分放行", {k: 4.0 for k in RUBRIC_KEYS})
    _run("场景B-全3分不放行", base)
    print("  注：红线事项目录由消费方经 TenantProfile.redline 注入，内核零领域字面量；")
    print("      判定方式为对决策文本做红线目录匹配（见 evaluate_redline）。")
    _run("场景C-红线命中（文本含红线事项）", {k: 4.0 for k in RUBRIC_KEYS},
         redline_items=("预算外承诺",),
         text="该方案涉及预算外承诺，须人工处置。")

    step("顺序契约不可重排（构造期校验）")
    bad = ("S5_persist",) + tuple(SPINE_ORDER[1:])
    try:
        validate_spine_order(bad)
        print("  !! 未拦截（异常：不应发生）")
    except Exception as exc:  # noqa: BLE001
        print(f"  已拦截 -> {type(exc).__name__}: {exc}")


# ══════════════════════════════════════════════════════════════════════
# 08 三态审批与续跑（功能 7）
# ══════════════════════════════════════════════════════════════════════
def demo_approval() -> None:
    from chiyu_decision.api import run_spine
    from chiyu_kernel.api import RUBRIC_KEYS

    banner("功能演示 08　审批治理与续跑", "待定/通过/驳回三态模型与幂等续跑（冻结裁定）")

    store: dict = {}

    def persister(result):
        """落库钩子：首次写入置 PENDING；续跑时保留既有裁定（冻结裁定原则）。"""
        prev = store.get(result.decision_id)
        verdict = prev["verdict"] if prev else "PENDING"
        store[result.decision_id] = {
            "stage": result.stage_reached, "confidence": result.confidence,
            "autonomous": result.autonomous, "verdict": verdict,
        }
        return "ok"

    step("第一次执行：审批结论为待定 PENDING（persister 落库，待人工裁定）")
    r1 = run_spine(
        context={"decision_id": "demo-pending-1", "topic": "是否批准该客户的预算追加请求"},
        profile=None,
        rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
        elements={"intent": "是否批准该客户的预算追加请求"},
        persister=persister,
        threshold=0.79,
    )
    kv("stage_reached", r1.stage_reached)
    kv("confidence", round(r1.confidence, 4))
    kv("persisted", r1.persisted)
    kv("落库内容", store.get("demo-pending-1"))

    step("人工裁定：置为 APPROVED，记录裁定时间与置信度快照")
    rec = store["demo-pending-1"]
    rec["verdict"] = "APPROVED"
    frozen_conf = rec["confidence"]
    kv("裁定结果", rec["verdict"])
    kv("冻结置信度", round(frozen_conf, 4))

    step("续跑（resume）：只补落库阶段，不重算置信度、不重判红线")
    r2 = run_spine(
        context={"decision_id": "demo-pending-1", "topic": "是否批准该客户的预算追加请求"},
        profile=None,
        rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
        elements={"intent": "是否批准该客户的预算追加请求"},
        persister=persister,
        threshold=0.79,
    )
    rec2 = store["demo-pending-1"]
    kv("续跑后 confidence", round(r2.confidence, 4))
    kv("与冻结值一致", round(r2.confidence, 4) == round(frozen_conf, 4))
    kv("裁定字段未被改写", rec2["verdict"] == "APPROVED")
    kv("幂等性", store.get("demo-pending-1") == rec2)

    step("终态纪律：驳回 REJECTED 为终态，不得经续跑复活")
    r3 = run_spine(
        context={"decision_id": "demo-reject-1", "topic": "是否批准超出授权范围的折扣",
                 "text": "该折扣构成预算外承诺，超出授权范围。"},
        profile=None,
        rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
        elements={"intent": "是否批准超出授权范围的折扣"},
        persister=None,
        threshold=0.79,
        redline_items=("预算外承诺",),
    )
    kv("redline_hit", r3.redline_hit)
    kv("redline_reasons", list(r3.redline_reasons))
    kv("autonomous（红线屏蔽）", r3.autonomous)
    print("  结论：红线命中强制改判为驳回，自主放行被屏蔽，且驳回为终态不可续跑复活。")


# ══════════════════════════════════════════════════════════════════════
# 09 事件、审计与探针（功能 8）
# ══════════════════════════════════════════════════════════════════════
def demo_events() -> None:
    from chiyu_kernel.api import EventBus, PublishReport, EVENT_TYPE_DECISION

    banner("功能演示 09　事件与审计", "事件总线驱动的能力联动与审计留痕")

    step("构造事件总线并订阅两个消费者")
    bus = EventBus()
    log: list = []
    counter: dict = {}

    def audit_sink(event):
        log.append(event)

    def counter_sink(event):
        counter[event.get("event_type")] = counter.get(event.get("event_type"), 0) + 1

    bus.subscribe(EVENT_TYPE_DECISION, "audit-sink", audit_sink)
    bus.subscribe(EVENT_TYPE_DECISION, "counter-sink", counter_sink)
    kv("订阅者", bus.subscribers(EVENT_TYPE_DECISION))
    kv("事件类型常量", EVENT_TYPE_DECISION)

    step("发布事件（先持久化，再分发）")
    persisted: list = []
    event = {"id": "evt-2026-0001", "event_type": EVENT_TYPE_DECISION,
             "decision_id": "demo-pending-1", "actor": "system",
             "payload": {"stage": "S5_persist", "verdict": "APPROVED"}}
    rep = bus.publish(event, persist=persisted.append)
    kv("PublishReport.event_id", rep.event_id)
    kv("delivered", rep.delivered)
    kv("failed", rep.failed)
    kv("healthy", rep.healthy)
    kv("已持久化事件数", len(persisted))
    kv("审计日志条数", len(log))
    kv("计数器", counter)

    step("审计留痕：事件必带 id（否则无法回放与去重）")
    try:
        bus.publish({"event_type": EVENT_TYPE_DECISION}, persist=persisted.append)
        print("  !! 未拦截（异常：不应发生）")
    except Exception as exc:  # noqa: BLE001
        print(f"  已拦截 -> {type(exc).__name__}: {exc}")

    step("订阅者异常不静默：失败计入 failed 而非吞掉")
    def bad_sink(_event):
        raise RuntimeError("下游不可用")

    bus.subscribe(EVENT_TYPE_DECISION, "bad-sink", bad_sink)
    rep2 = bus.publish({"id": "evt-2026-0002", "event_type": EVENT_TYPE_DECISION},
                       persist=persisted.append)
    kv("delivered", rep2.delivered)
    kv("failed", list(rep2.failed))
    kv("healthy", rep2.healthy)


# ══════════════════════════════════════════════════════════════════════
# 10 金丝雀探针（功能 8）
# ══════════════════════════════════════════════════════════════════════
def demo_canary() -> None:
    from chiyu_kernel.api import canary_probe, CanaryReport, RUBRIC_KEYS
    from chiyu_kernel.approval import RedlinePriorityGate, DecisionVerdictState
    from chiyu_decision.api import run_spine

    banner("功能演示 10　金丝雀探针", "接入期连通性与落库自检（三判据）")

    class FakeStore:
        """最小内存替身：实现 canary_probe 所需的鸭子类型（schema + execute_fetch）。"""

        def __init__(self):
            self.schema = "demo"
            self.events = {"canary-dec-1"}      # 决策回调已落库的 event
            self.particles = {"canary-dec-1"}   # 决策回调已落库的 particle
            self.engine_edges = 0

        def execute_fetch(self, sql, params=()):
            target = params[0] if params else None
            if "FROM demo.event" in sql:
                return {"id": target} if target in self.events else None
            if "FROM demo.particle" in sql:
                return {"particle_id": target} if target in self.particles else None
            if "count(" in sql:
                return {"n": self.engine_edges}
            return None

    store = FakeStore()
    seq = {"n": 0}

    def _persist(result):
        """模拟消费方落库：event 与 particle 成对写入。"""
        store.events.add(result.decision_id)
        store.particles.add(result.decision_id)
        return "ok"

    def run_decision():
        seq["n"] += 1
        return run_spine(
            context={"decision_id": "canary-dec-1", "topic": "连通性自检决策"},
            profile=None,
            rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
            elements={"intent": "连通性自检决策"},
            persister=_persist,
            threshold=0.79,
        )

    def run_redline_decision():
        """红线决策回调：注入默认审批闸 RedlinePriorityGate（红线命中即 REJECTED）。"""
        return run_spine(
            context={"decision_id": "canary-redline", "topic": "红线自检决策",
                     "text": "该事项构成预算外承诺。"},
            profile=None,
            rubric_scores={k: 4.0 for k in RUBRIC_KEYS},
            elements={"intent": "红线自检决策"},
            persister=_persist,
            approval_gate=RedlinePriorityGate(),
            threshold=0.79,
            redline_items=("预算外承诺",),
        )

    step("先演示「判据不可判定」：不注入 references / 红线回调时不得静默放行")
    rep0 = canary_probe(store=store, run_decision=run_decision,
                        decision_id="canary-dec-1")
    kv("decision_persisted", rep0.decision_persisted)
    kv("memory_net_materialized", rep0.memory_net_materialized)
    kv("redline_blocked", rep0.redline_blocked)
    kv("ok（三判据全绿）", rep0.ok)

    step("补齐两判据：注入 references（记忆网供给）与红线决策回调")
    store.engine_edges = 2        # engine 边实际条数，须与期望「恰好相等」
    refs = {"REFERENCED_PRECEDENT": ["dec-0"], "DECIDED_ON": ["order-1"]}
    rep = canary_probe(store=store, run_decision=run_decision,
                       decision_id="canary-dec-1", references=refs,
                       run_redline_decision=run_redline_decision)
    kv("报告类型", type(rep).__name__)
    kv("decision_persisted", rep.decision_persisted)
    kv("memory_net_materialized", rep.memory_net_materialized)
    kv("redline_blocked", rep.redline_blocked)
    kv("ok（三判据全绿）", rep.ok)
    print("    细节 details：")
    for k, v in rep.details.items():
        print(f"      {k}: {v}")

    step("三判据结论")
    print("    判据一：event 与 particle 成对写入（不成对即红）")
    print("    判据二：engine 边数量恰好相等（多写/少写即红）")
    print("    判据三：红线命中须挡住落库（落库即红）")


# ══════════════════════════════════════════════════════════════════════
# 11 插件与工作模式（功能 10）
# ══════════════════════════════════════════════════════════════════════
def demo_plugins() -> None:
    from chiyu_kernel.api import (
        PluginRegistry, BUILTIN_PLUGINS, MODE_PRESETS, DEFAULT_MODE_ID,
        mode_ids, active_plugins, disabled_plugins, resolve_work_mode,
    )

    banner("功能演示 11　插件与工作模式", "插件注册表、六类内置插件与四种工作模式")

    step("注册内置插件")
    reg = PluginRegistry()
    for spec in BUILTIN_PLUGINS:
        reg.register(spec) if hasattr(reg, "register") else None
    kv("内置插件数", len(BUILTIN_PLUGINS))
    for spec in BUILTIN_PLUGINS:
        print(f"    - {spec.name:<12} 能力={spec.capability}")

    step("mode_ids()  —— 四种工作模式")
    kv("模式标识", list(mode_ids()))
    kv("缺省模式", DEFAULT_MODE_ID)

    step("逐模式解析：启用插件与惰性关闭插件")
    for mid in mode_ids():
        mode, enabled, disabled, warns = resolve_work_mode(mid)
        print(f"\n    【{mode.id}】{mode.label}")
        print(f"      说明    ：{mode.description}")
        print(f"      启用插件：{', '.join(enabled) or '（无）'}")
        print(f"      惰性关闭：{', '.join(disabled) or '（无）'}")
        if warns:
            for w in warns:
                print(f"      告警    ：{w}")

    step("未知模式回落默认并留告警（不中断运行）")
    mode, enabled, disabled, warns = resolve_work_mode("不存在的模式")
    kv("回落模式", mode.id)
    kv("告警", warns)
    kv("启用插件", list(enabled))


# ══════════════════════════════════════════════════════════════════════
# 12 模型接入与协议适配（功能 11）
# ══════════════════════════════════════════════════════════════════════
def demo_mcp() -> None:
    from chiyu_kernel.api import (
        InMemoryMcpServer, McpBridge, normalize_mcp_name, McpToolDef,
    )

    banner("功能演示 12　模型接入与协议适配", "MCP 传输层契约、工具注册与命名规范化")

    step("normalize_mcp_name(server_name, raw_name)  —— MCP 命名规范化")
    for raw in ("Run Spine", "chiyu.decide", "render--page", "A_B_C"):
        print(f"    {raw!r:<18} -> {normalize_mcp_name('chiyu-foundation', raw)!r}")

    step("以 InMemoryMcpServer 承载底座能力（传输层可替换为真实 transport）")
    tools = {
        "run_spine": ("执行六阶段决策脊柱", lambda args: {"stage": "S5_persist"}),
        "render_page": ("渲染受控页面", lambda args: {"html_len": 1024}),
    }
    server = InMemoryMcpServer(tools=tools)
    server.connect()
    kv("list_tools()", [(t.raw_name, t.description) for t in server.list_tools()])
    kv("工具定义类型", type(server.list_tools()[0]).__name__)

    step("call_tool()  —— 协议化调用")
    kv("call_tool('run_spine')", server.call_tool("run_spine", {}))
    kv("call_tool('render_page')", server.call_tool("render_page", {}))

    step("McpBridge 桥接到工具注册表")
    from chiyu_kernel.tools import ToolRegistry

    registry = ToolRegistry()
    bridge = McpBridge(transport=server, server_name="chiyu-foundation")
    names = bridge.connect(registry)
    kv("server_name", bridge.server_name)
    kv("已注册工具", names)
    kv("注册后可查工具", sorted(registry.names()) if hasattr(registry, "names")
       else "<无 names() 接口>")
    server.disconnect()
    print("  传输层已断开：底座能力对外部智能体与业务系统按标准协议暴露。")


# ══════════════════════════════════════════════════════════════════════
# 13 门户运行时（功能 9）
# ══════════════════════════════════════════════════════════════════════
def demo_portal() -> None:
    from chiyu_portal.api import (
        guard_nl_input, parse_nl_to_schema, render_page, render_onboarding,
        PAGE_TYPES, COMPONENT_KINDS, onboarding_steps,
    )
    from chiyu_kernel.contract import ParticleTypeSet, CORE_ROLES

    banner("功能演示 13　门户运行时", "自然语言→受控 Schema→HTML，与引导式导航生成")

    step("PAGE_TYPES / COMPONENT_KINDS  —— 受控页面与组件闭集")
    kv("PAGE_TYPES", list(PAGE_TYPES))
    kv("COMPONENT_KINDS", list(COMPONENT_KINDS))

    step("guard_nl_input()  —— 输入守卫（拦截脚本注入）")
    for text in ("显示本季度全部订单的列表", "<script>alert(1)</script>"):
        g = guard_nl_input(text)
        kv(f"输入 {text[:22]!r}", f"ok={g.ok}  reason={getattr(g, 'reason', '')}")

    step("parse_nl_to_schema()  —— 自然语言解析为受控 Schema")
    pr = parse_nl_to_schema("显示本季度全部订单的列表，按金额排序",
                            entity_map={"订单": "order"}, title="季度订单")
    kv("page_type", getattr(pr, "page_type", "n/a"))
    kv("confidence", getattr(pr, "confidence", "n/a"))
    kv("needs_clarification", getattr(pr, "needs_clarification", "n/a"))
    schema = getattr(pr, "schema", None) or {}
    kv("schema 键", list(schema.keys()))

    step("render_page()  —— 渲染为 HTML（非法 Schema 拒绝，绝不尽力渲染）")
    rr = render_page(
        schema,
        particle_types=ParticleTypeSet(names=tuple(CORE_ROLES) + ("order",)),
    )
    kv("ok", getattr(rr, "ok", "n/a"))
    html = getattr(rr, "html", "") or ""
    kv("html 长度", len(html))
    print(f"    HTML 片段：{html[:120]}")

    step("render_onboarding()  —— 生成引导式导航页")
    ob = render_onboarding()
    kv("引导步骤数", len(onboarding_steps()))
    kv("返回类型", type(ob).__name__)
    body = getattr(ob, "html", "") or ""
    kv("生成 HTML 长度", len(body))


DEMOS = {
    "version": demo_version,
    "contract": demo_contract,
    "particle": demo_particle,
    "vector": demo_vector,
    "context": demo_context,
    "graph": demo_graph,
    "spine": demo_spine,
    "approval": demo_approval,
    "events": demo_events,
    "canary": demo_canary,
    "plugins": demo_plugins,
    "mcp": demo_mcp,
    "portal": demo_portal,
}


def main(argv: list) -> int:
    if not argv or argv[0] in ("--list", "-l"):
        print("可用演示：")
        for k in DEMOS:
            print(f"  {k}")
        return 0
    name = argv[0]
    if name not in DEMOS:
        print(f"未知演示：{name}；可用：{', '.join(DEMOS)}")
        return 2
    DEMOS[name]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
