#!/usr/bin/env python
"""生成 `contract/capability-manifest.json` —— 机器可读能力清单（CRM R1）。

CRM 回信 R1（2026-10-09）：跨仓用稳定 capability_id 取代 `file:line` 锚点作契约，
字段至少含 capability_id / package / status / semantics / verify_entry / since_version。
本脚本从 `chiyu_kernel/version.py` 的 `CAPABILITIES` 枚举能力与状态（机械单一事实源），
叠加本文件内的语义与验证入口映射，生成 JSON；由守卫测试
`packages/chiyu-kernel/tests/test_capability_manifest.py` 校验一致性（新增能力不登记即红）。

口径声明：
- capability_id = 能力名（`CAPABILITIES` 的第一元素，稳定、不随重构变）。
- package   = 承载该能力的分发子包（kernel / decision）。
- status    = `VALID_STATUSES` 之一（stable / experimental / deprecated）；与 CAPABILITIES 同一来源。
- semantics = 一句功能语义（人可读；不写内部代号，§13）。
- verify_entry = 可复跑的验证入口（命令或测试路径；与 Makefile 分闸对齐）。
- since_version = 首个稳定发行版口径（当前 0.1.0；精确到能力的历史首现见 git log --diff-filter=A）。
"""
from __future__ import annotations

import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packages", "chiyu-kernel", "src"))

from chiyu_kernel.version import CAPABILITIES, VALID_STATUSES  # noqa: E402

VERIFY: dict = {  # 验证入口映射（对齐 Makefile 分闸：kernel+tools / decision / portal / examples / cli）
    "contract": "make lint",
    "vector": "pytest packages/chiyu-kernel/tests -k vector",
    "ontology": "pytest packages/chiyu-kernel/tests -k ontology",
    "context": "pytest packages/chiyu-kernel/tests -k context",
    "actions": "pytest packages/chiyu-kernel/tests -k action",
    "domain": "pytest packages/chiyu-kernel/tests -k domain",
    "persist": "pytest packages/chiyu-kernel/tests -k persist",
    "approval": "pytest packages/chiyu-kernel/tests -k approval",
    "graph": "pytest packages/chiyu-kernel/tests -k graph",
    "mcpserver": "pytest packages/chiyu-kernel/tests -k mcpserver",
    "canary": "pytest packages/chiyu-kernel/tests -k canary",
    "orchestration": "pytest packages/chiyu-kernel/tests -k orchestration",
    "evolution": "make test",
    "events": "pytest packages/chiyu-kernel/tests -k event",
    "audit": "pytest packages/chiyu-kernel/tests -k audit",
    "llm": "pytest packages/chiyu-kernel/tests -k llm",
    "plugins": "pytest packages/chiyu-kernel/tests -k plugin",
    "session": "pytest packages/chiyu-kernel/tests -k session",
    "tools": "pytest tools/tests",
    "skills": "pytest packages/chiyu-kernel/tests -k skill",
    "plan": "pytest packages/chiyu-kernel/tests -k plan",
    "mcp": "pytest packages/chiyu-kernel/tests -k mcp",
    "hooks": "pytest packages/chiyu-kernel/tests -k hook",
    "interaction": "pytest packages/chiyu-kernel/tests -k interaction",
    "workflow": "pytest packages/chiyu-kernel/tests -k workflow",
    "scenario": "pytest packages/chiyu-kernel/tests/test_scenario_registry.py",
    "store": "pytest packages/chiyu-kernel/tests -k store",
    "gate": "pytest packages/chiyu-kernel/tests -k gate",
    "feedback": "pytest packages/chiyu-kernel/tests -k feedback",
    "capability_audit": "pytest packages/chiyu-kernel/tests -k capability_audit",
    "connectors": "pytest packages/chiyu-kernel/tests -k connector",
    "promotion": "pytest packages/chiyu-kernel/tests -k promotion",
    "iam": "pytest packages/chiyu-kernel/tests -k iam",
    "conflict_resolver": "pytest packages/chiyu-kernel/tests -k conflict",
    "attribution": "pytest packages/chiyu-kernel/tests -k attribution",
    "audit_4q": "pytest packages/chiyu-kernel/tests -k audit_4q or -k audit4q",
    "ab_experiment": "pytest packages/chiyu-kernel/tests -k ab_experiment or -k judge_arms or -k close_decision",
    "quota_gate": "pytest packages/chiyu-kernel/tests -k quota",
    "param_health_check": "pytest packages/chiyu-kernel/tests -k param_health or -k recommend_prescription or -k red_line",
    "observability": "pytest packages/chiyu-kernel/tests -k observability or -k classify_attribution or -k negative_predicate",
    "agent_runtime": "pytest packages/chiyu-kernel/tests -k agent_runtime or -k match_trigger or -k glass_box or -k kg_convergence",
    "scheduler_core": "pytest packages/chiyu-kernel/tests -k scheduler_core or -k catchup or -k next_run_at or -k run_segments",
    "nightly_report": "pytest packages/chiyu-kernel/tests -k nightly_report or -k retro_metrics or -k render_nightly",
    "decision": "pytest packages/chiyu-decision/src/chiyu_decision/tests",
    "memory": "make test",
}

SEMANTICS: dict = {
    "contract": "L0 契约面（含 profile / particle / memory 谓词 / manifest 完整性校验）",
    "vector": "向量持久化（pgvector 单一事实源；维度由 TenantProfile.vector_dim 注入）",
    "ontology": "本体/粒子（写时三钩子 + 受控关系图）",
    "context": "情境装配与降级召回（L1–L4 + 三级降级语义）",
    "actions": "动作注册与执行（ActionRegistry + 执行闸）",
    "domain": "领域注入 SDK（TenantProfile / DomainBundle / inject_domain；机制非清单）",
    "persist": "决策落库标准 persister（SpineResult→event/particle 映射 shim）",
    "approval": "决策审批闸（DecisionApprovalGate；红线/审批必经闸）",
    # R9（CRM P0 回执）：显式声明读写边界 —— 图读 stable（GraphStore 只读协议），
    # 图写【无对等可写协议】：受控写仅 OntologyGraph.link（谓词∈profile.predicates K 层）；
    # 消费方若需建节点/关系边（如 CRM ageGraph MERGE/SET），本能力不提供通用写接口（见 docs R9 决策）。
    "graph": "图存储抽象（GraphStore 只读协议；InMemory/PgCte 只读实现）。读 stable；受控边写提供（T47：persist.write_controlled_edges——谓词闭集 M∪K 写入端 fail-fast、悬空边拒绝不隐式建顶点、upsert 幂等，graph_edge 唯一落库点经单源裁定守卫机检）；**可消费通道提供（T50：graph.mcp.build_graph_write_server 经 McpServer.expose(risk='write') 暴露 write_controlled_edges 端点，走 WS7 两阶段确认；CRM 镜像写唯一合法通道经此端点，禁 SQL 直写）；补 store（T54：graph.mcp.make_graph_write_profile 封装内核不变量 CORE_ROLES 构造 TenantProfile、open_graph_write_store 惰性取 PgVectorStore——消费方零领域猜测即可注入 build_graph_write_server）**；顶点写不提供（顶点归宿=粒子写；通用可写协议 WritableGraph 仍按 R9 排期 1.0 后裁定）",
    "mcpserver": "MCP 服务端骨架（工具注册守卫 + 零信任鉴权 + 两阶段确认）",
    "canary": "决策落库三判据统一判定式（canary_probe）",
    "orchestration": "多智能体编排（AgentRegistry / AgentSpec）",
    "evolution": "自进化（stable，2026-10-13 毕业于 T78：readiness 十闸全绿验收——§12.3 七闸 + §12.4 G1/G2/G3 护栏，10/10 含对抗判别力；判据面 = 7 个 evolution 测试文件 + 毕业守卫 test_evolution_graduation.py G1-G5，变异自证 A/B 双向。进入 1.0 兼容承诺，BREAKING 须先走完整 deprecation 周期。Batch-1b-4 增补配套：assemble_prescription 处方组装核——守卫命中不出方 / 白名单外 knob 不自动产出 / 重放同源可调用对象 / 幂等键确定性派生 / 预期影响必须前后对照 / from_value 取当前配置禁猜回滚目标）",
    "events": "事件总线（EventBus / 订阅分发）",
    "audit": "审计（审计事件契约常量 AUDIT_* 闭集）",
    "llm": "LLM 客户端抽象（ToolCall / LlmProvider / 构建工厂）",
    "plugins": "插件系统（Plugin 注册 / 装载）",
    "session": "会话（session context layering）",
    "tools": "治理工具集（check_facade_coverage / check_zero_residue / check_import_surface / dev）",
    "skills": "技能装载（Skill 注册）",
    "plan": "计划（Plan 原语）",
    "mcp": "MCP 协议抽象（McpTransport 协议 + InMemory 桥；真 transport 由消费方实现）",
    "hooks": "钩子（hook 注册/触发）",
    "interaction": "交互（工具执行前人工确认 ApprovalGate）",
    "workflow": "工作流（Workflow 原语）",
    "scenario": "决策场景注册表（register_scenario 单一事实源；键格式闸可插拨 set_key_format）",
    "store": "存储抽象（PgVectorStore / dsn 校验 / 驱动解耦 connect_factory）",
    "gate": "写操作安全闸（八闸框架：四分类范式 precheck/permission/redline/traceability 可配置 N 级 fail-closed 闸链；第0闸轻量决策凭证契约 decision_id/issuer/checksum，内核只验结构不产决策）；域闸名由消费方注入（零领域字面量铁律）。Batch-1a（2026-10-13）落地，进入 1.0 兼容承诺。",
    "feedback": "反馈闭环纯函数核心（GAP-6，Batch-2b 上迁自 APS feedback_loop：指标模板七要素资格断言 / runtime-seed 双口径 / 三档加权评估含 undecidable 第三态 / 拒绝出方守卫 / HITL 校准闸 pending→approved；落库与事件发射留消费方）",
    "capability_audit": "能力落地审计（GAP-7，Batch-2b 上迁自 APS capability_audit：三查法 grep 定位 / 零命中最优先分级 / 定义≠调用点计数 / 零外部入口判 partial / 审计包四件套缺件显式标注 / 鉴别力自证探针；域能力映射由消费方注入）",
    "connectors": "连接器传输层（GAP-8，Batch-2b 上迁自 APS connectors：无状态工厂接口 SourceConnector / 结果载体 rows 外部字段名 / csv·json·xlsx 文件传输 / 注册表注册即承诺；域连接器如 legacy_aps 与 DB·消息传输留消费方）",
    "promotion": "知识升格与回流管道（GAP-9，Batch-2b 上迁自 APS promotion+reflux：升格三态闸门白名单→证据→一致性 / 产物恒 PENDING+PARAMS_SOURCE_PROMOTED 红线 / calibrated 不可覆盖 / 漂移不可比即告警 / 回流四通道未知 kind 拒绝 / 处方白名单外直接拒绝 / 后见之明 AND 条件+no_data≠healthy+空转停方；处方状态机在 evolution，域键白名单与真值表留消费方）",
    "iam": "身份与访问判定核（Batch-1b-1，上迁自 CRM rbac/grantStore/grantSweeper + mcpserver 提升：RBAC 判定核别名归一 fail-closed / 租户域限定 / 权限矩阵全函数查询 / 常驻授权凭证覆盖·用量熔断·巡检判决（零 DELETE 状态机语义）/ 两阶段确认令牌三重绑定；角色矩阵内容、别名表内容、凭证存储与审批流挂接留消费方）",
    "conflict_resolver": "多源事实冲突仲裁判决核（Batch-1b-3，上迁自 CRM conflict.js G4：五策略 winner 选择（最新/源优先级/可信加权/合并/人工）+ 采用标记不物理删 + 保留分歧置待裁决 + 人工裁决必须挂第0闸决策行 + 未知策略抛错；断言存储与租户隔离留消费方）",
    "attribution": "决策质量归因分类核（Batch-1b-3，上迁自 CRM attribution.js T29 + rootCauseClassifier.js：十一态根因词汇 / R0-R3 命中即止分类树（粒子三检→维度缺→边缺→先例污染→优化次序）/ E 缺只认应连未连显式证据（未查实不判缺）/ 人工推翻回写（已七态保留不覆盖、全齐仍推翻=推理偏差）/ 业务结果滞后回填；旋钮映射与边规格留消费方注入）",
    "audit_4q": "决策可审计性四问评分核（Batch-1b-3，上迁自 CRM auditability.js：Q1 维度供给门槛（缺证据=warn 禁顶替）/ Q2 空链不可自称 OK+事件不入证据口径 / Q3 未裁决冲突与零实体扫描=warn / Q4 影响失败才 fail 孤立决策=warn / 聚合空窗口 pct=null；判据算法与口径常量在基座，图/溯源/冲突证据由消费方注入）",
    "ab_experiment": "A/B 实验判据与收口核（Batch-1b-4，上迁自 CRM routingReview.js + routingExperiment.js：三取二判据 ΔQ/ΔO/ΔR 至少两项显著且符号一致 + 方向以 ΔQ 为准 + 样本不足显式 insufficient_evidence 不硬凑 / 轨道投影 on 加入 off 移除 fail-open 原样 / 收口分流：证据不足排反向臂补对照 append-only 禁删原行、显著且偏好==baseline 维持现状、否则产 PENDING 处方 to_value=完整轨道数组 from_value=当前配置原值禁猜回滚目标；判据阈值常量在基座，实验登记与处方落库留消费方）",
    "quota_gate": "Token 配额闸判决核（Batch-1b-4，上迁自 CRM quotaGate.js：block/bill 双模式 + bill 缺省安全上限 included×3 + block 上限= included 本身 + -1 不限哨兵 + 豁免直通 + deny 必带闭集 reason；加固差异报备：CRM 未知 mode 静默放行、基座 fail-closed 抛错；套餐域值与豁免名单留消费方注入）",
    "param_health_check": "参数健康诊断核（Batch-1b-4，上迁自 CRM diagnosis.js：recommend 三档（HIGH+失败率>0.3→approve / MEDIUM+失败率>0→approve / 其余 reject，LOW 无自动放行通道）+ 红线前缀过滤（包含匹配大小写不敏感、分离不是丢弃——display_only 仍可见禁静默吞）；红线前缀域清单留消费方注入）",
    "observability": "监控底座判据核（Batch-4a，上收自 CRM monitor/*+events/busFailures.js：归因四类交叉 classify_attribution（inference_bias/input_error/input_missing/context_insufficient，良性=None 不计入）/ accuracy 三态桶（CONFIRMED·APPROVED→accurate，OVERRIDDEN·CORRECTED→inaccurate，余 pending）/ 闸门指标聚合（AUTONOMOUS·HUMAN·REQUIRED+ESCALATED）/ 投递成功率（无尝试→null 防假绿）/ 负向判据两级（delivery_silent 真静默才参与出口闸·delivery_undelivered 有归因附首位原因·gen_silent 恒判）/ 富集命中率（分母恒真实）/ 边来源双口径（NULL 不计供给·演示边零 DELETE）/ 失败计数器（单一实现防判据分裂）；渠道名/闸门名/来源名留消费方注入）",
    "agent_runtime": "agent 运行时判据核（Batch-4b，上收自 CRM agent/*：三源触发匹配（event/timer/external·source 缺省 event·只读白名单 fail-closed 非白名单拒绝留痕）/ 去重键（entity_id:intent:val 空值→new）/ 冷却判决（窗口内 skip 留痕·首见 dispatch DB 去重为主）/ glassBox 可解释链（脏信号过滤 trace=有效信号数·无信号不抛错）/ 契约合规三维（skill_ok/memory_ok/success 无标记恒 pending 禁猜）/ KG 收敛闸门（effective=declared∩served·dropped 非空即 triggered·运行时只注入 effective 防契约层静默误判）；agent 名/skill 白名单/矩阵行/KG 服务层留消费方注入）",
    "scheduler_core": "定时调度判决核（Batch-5，上收自 CRM scheduler/timers.js：next_run_at 每日时点顺延（时点参数化=运维调度配置非业务阈值）/ catchup_verdict 三态判决（stale>24h 补跑·fresh 天然限流重启不重跑·near_schedule 30min 护栏防补跑定时双跑·首启无记录视为 stale）/ run_segments 段隔离编排范式（每段独立 catch 互不传染+失败必留痕禁裸 catch+收尾段独立兜底 catch）；任务名/时区/callable/最新 run_at 查询留消费方注入）",
    "nightly_report": "零 LLM 夜报判据核（Batch-5，上收自 CRM report/nightlyReport.js：collect_segments 三段 null 容错归一防渲染崩+param.items 贯穿九尺子明细 / extract_retro_metrics 双形态兼容（实时 vs 落库回读持久化——summary.* 权威 clusters 明细缺失回退顶层防回读计数恒 0）/ render_nightly_markdown 纯模板渲染零额外 LLM（R1）+漂移口径诚实（drift>0 无建议显示需人工研判禁误报全部健康 R4）/ aggregate_report_metrics 聚合公式（insufficient 计入 total 失败行不计入 drift）；失败原因过滤阈值独立注入缺省 0.7 与 D3 同源禁与 0.79 互替（R5）；报告标题/日期/落盘留消费方注入）",
    "decision": "决策脊柱（chiyu_decision.api：run_spine / score_rubric / evaluate_redline / 审批三态；J9 增强：element_cap 要素缺失映射尺子封顶 + redline_spec 结构化红线消费/敏感项强制人工在环 + cap_rubric_by_elements；audit-first 增强：run_spine(audit_persister=) 审计轨落库 REJECTED/PENDING（record_kind=audit，不产生正向边、不影响 resume），APPROVED 走 persister 业务轨。D2/D4 裁定登记 2026-10-14·CRM 为源仓：score_rubric 严格等权=基座缺省聚合，CRM per-key weights/focus×1.5/enabled 真子集为 CRM 增强面**非基座语义**（parity 只锁默认等权形态）；ELEMENT_RUBRIC_CAPS 是 J9-C 新增机制（缺失封顶）非 CRM 既有语义（deps 输入依赖），两套要素映射**禁互证**）",
    "memory": "记忆网（stable，2026-10-10 毕业于 T40–T44：双轨 LOG/NOTE PG 落库 + 召回接入 run_spine + RRF 多源融合 + 真库 E2E + 单源裁定守卫）",
}

PACKAGE: dict = {
    "decision": "chiyu-decision",
}
PACKAGE_DEFAULT = "chiyu-kernel"


def build() -> list:
    out = []
    names = [name for name, _ in CAPABILITIES]
    for name, status in CAPABILITIES:
        semantics = SEMANTICS.get(name)
        if not semantics:
            raise SystemExit(f"gen_capability_manifest: {name} 缺 semantics（新增能力必须登记）")
        verify = VERIFY.get(name)
        if not verify:
            raise SystemExit(f"gen_capability_manifest: {name} 缺 verify_entry（新增能力必须登记）")
        if status not in VALID_STATUSES:
            raise SystemExit(f"gen_capability_manifest: {name} status {status!r} 不属于 {VALID_STATUSES}")
        out.append({
            "capability_id": name,
            "package": PACKAGE.get(name, PACKAGE_DEFAULT),
            "status": status,
            "semantics": semantics,
            "verify_entry": verify,
            "since_version": "0.1.0",
        })
    return out


def main() -> int:
    entries = build()
    payload = {
        "schema": "capability-manifest/1",
        "generated_from": "chiyu_kernel.version.CAPABILITIES",
        "audience": "跨仓消费方（CRM / APS / enterprise）；跨仓引用一律用 capability_id",
        "status_vocabulary": list(VALID_STATUSES),
        "since_version_notes": "本次统一口径为首个稳定发行版 0.1.0；能力历史首现见 git log --diff-filter=A",
        "compatibility_notes": "1.0 兼容承诺仅覆盖 status=stable 的能力层：此后 BREAKING 变更必须先走完整 deprecation 周期（先 warn 一版再移除，见 docs/versioning-and-deprecation.md）。memory 已于 2026-10-10 毕业（T40–T44）转入 stable；evolution 已于 2026-10-13 毕业（T78）转入 stable——至此 CAPABILITIES 无 experimental 层。",
        "capabilities": entries,
    }
    out_path = os.path.join(ROOT, "contract", "capability-manifest.json")
    with io.open(out_path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
        fp.write("\n")
    print(f"generated {os.path.relpath(out_path, ROOT)} ({len(entries)} capabilities)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
