# foundation 收编确认 · APS 实证窗口台账（2026-10-09）

> 收编方：chiyu-foundation（基座，唯一事实源）｜ 来源：APS-实证窗口台账（APS 治理改造第三步落地跟踪实体）
> 收编日期：2026-10-09 ｜ 性质：foundation 对 APS 生产实证接入窗口的**事实锚点核验 + 收口意见**
> 仓边界：本文落本仓 `docs/`，不回写 APS 仓；APS 台账仍归 APS 维护。

---

## 一、foundation 侧事实锚点核验（逐条 `file:line`）

台账多处引用 foundation 内部能力，全部经源码级核实，结论：**一致，无虚报**。

| 台账引用 | foundation 实际 | 核验结果 |
|---|---|---|
| 升级演练 #1：`api_version()=='1.0.0'` | `API_VERSION="1.0.0"`（`version.py:54`） | ✅ |
| 升级演练 #3：`require_capabilities({decision:stable,persist:stable,memory:experimental})` | `CAPABILITIES` 含 `("decision","stable")`（:94）、`("persist","stable")`（:72）、`("memory","experimental")`（:96） | ✅ |
| 升级演练 #1/#3：`require_capabilities` 闸实现 | `require_capabilities` 在 `api`（:108）+ 定义 `version.py:136` | ✅ |
| 升级演练 #4：`foundation.py:166` 绑定 `aggregate_confidence=_k_decision.aggregate_confidence` | `aggregate_confidence` 在 `chiyu_decision.api.__all__`（`api.py:12,21`） | ✅ 绑定合法，import 期不红 |
| 第二步·#1 判别力探针（run_spine 接管评估维持现状） | `run_spine` S1 无装配器注入面（`:67-70`）、S4 目录子串红线无回调面（`:83`/`redline.py:26`） | ✅ 与 foundation 回信 N1–N3 裁定一致 |
| 能力档位 `memory:experimental` 须显式声明 | `version.py:15,96` 注释 + 元组双锁定 | ✅ 满足 memory 实验态披露铁律 |

> 说明：L0/L1 全量回归 `1555/0`、第二步 #1 `1565/0`、真库 E2E `-m pg 13 passed`、SLO 实测值（p50 51–72ms 等）属 **APS 实测计数**，foundation 不重跑、按 APS 报告口径接受（与既有约定「APS 真跑次之、CRM 生产最强」一致）。

---

## 二、升级演练 fail-fast 语义确认（正确）

台账第四节 4 场景全 fail-fast（版本不符 / 能力档位不符 / 符号缺失三类破坏性变更在 **import 期即红**），层位正确：

- 版本/能力档位闸在 **import 期硬断言**（`foundation.py:225/229`），早于任何运行时调用 —— 符合「带病基座不启动」原则。
- 符号缺失闸依赖 `aggregate_confidence = _k_decision.aggregate_confidence` 的 import 期绑定（:166），缺失即 `AttributeError` —— 与 R12 机械守卫（`STORE_REQUIRED` 由 `store.__all__` 推导）同源思路，互补。

foundation 认可该防护分层，建议 APS 长期保留；若 foundation 后续调整 `CAPABILITIES` 或弃用别名（`DEPRECATIONS`），会先在 `CHANGELOG` 标注并在门面保留过渡别名（严格加法），APS 的 import 期闸不会被误触发。

---

## 三、SLO 非确定性处理（D10）确认正确

台账第六节对两次采集 p50 落在 51–72ms 区间，明确「不引用单点、取 ≥3 次 [min,p50,max] 区间」并标注「单机基线 ≠ 生产宿主」。该处理符合铁律 D10（非确定性提示），foundation 认可，并补充：

- 生产 SLA 回填值**必须**在真实宿主 + 真实负载下复采，单机便携 PG 值仅作窗口内基线，不对外承诺。
- S5 落库段占全链 ~96–97% 的实测，印证 N3（`shared()`/`connect()` 驱动解耦）的价值方向 —— 连接复用与落库吞吐仍是后续优化重点。

---

## 四、遗留待确认项裁决（台账「附·待确认项」）

| # | 项 | foundation 收口意见 |
|---|---|---|
| 1 | 窗口起止 = 2026-10-09（同日收口） | ✅ 接受；foundation 侧 R2–R14 收尾 + N1–N3 均已于 10.9 落地（T9a–T9e），窗口期内无障碍 |
| 2 | `-m pg` 13 例是否纳入 APS 正式回归口径 / 或作专用真库巡检集 | **建议：作 APS 专用真库巡检集，不并入 foundation 回归口径。** 理由：① 13 例依赖 APS 真库（`APS_PG_DSN_TEST` + DECIDED_ON 单边图装配），foundation 仓无该 DB 与图接线，无法复跑；② foundation 回归守「零领域字面量 + 可离线全绿」纪律，真库用例归消费方是自洽边界；③ APS 应保持 `-m pg` 为独立入口，每次基座升级前跑一遍作为兼容证据（即台账第四节用法） |

> 裁决 #2 不改变「窗口内零 P0–P3」结论；13 例归属 APS 巡检集是职责清晰化，非降级。

---

## 五、foundation 收口结论

1. **窗口收口**：APS 实证窗口 2026-10-09 起止同日，缺陷台账零 P0–P3、升级演练全 fail-fast、真库 E2E 13 例全绿 —— foundation **确认收口**，结果回编本仓。
2. **事实锚点**：台账引用的 foundation 能力（`api_version`/`capabilities`/`require_capabilities`/`aggregate_confidence`/run_spine 注入面）全部与基座实际一致，无虚报。
3. **后续衔接（S1/S4 钩子收敛边界）**：
   - **收敛原则**：S4 域红线回调钩子（`redline_callback: (context)→RedlineVerdict` 通用可选形参）属 foundation **公共能力**——任何消费方都可能用回调式域红线替代目录子串匹配，应收敛到本项目、一次做成多次复用；S1 装配钩子（`context_factory` 可选形参）仅当 APS 要 `run_spine` 自身持有装配编排、与自建 `KmdSpine` 形状对称时才需，属**可选**架构对称诉求，非功能必需。
   - **领域逻辑不收敛**：钩子内填入的域逻辑（`ContextAssembler` 装配内容、`redline_callback` 的 `tier∈(barrier,redline)` 分档 + 强制人工在环）归 APS 取值与执行，本仓"零领域字面量"铁律不破。
   - **触发条件（caveat）**：当前 APS 用自建 `KmdSpine` 组合器 + 复用基座机制函数（`score_rubric`/`check_elements`/`autonomous_release`）已是**符合分层铁律的正确消费**，"改用 `run_spine`"非技术必需、是 APS 可选架构选择；上述钩子**仅当 APS 主动选择统一、version-gated 脊柱编排时才成为 foundation 待办**，否则不收敛、不新建（APS 今天即能用 `run_spine`，S1 在调用前自行装配传入即可）。
   - **已落地（2026-10-09 T10）**：用户授权按上述收敛边界收编，S4 域红线回调钩子（必需）+ S1 装配钩子（可选）已加为 `run_spine` 通用可选形参（`spine.py`）；`test_spine_injection.py`（5 例）覆盖回调替代目录匹配 / 域红线命中 / 严格加法回归 / 装配生效 / 装配缺失回归，变异自证删分支即转红；组合回归 749 passed / 0 failed。设计、收敛边界与对 APS 的迁移意义见 `docs/2026-10-09-foundation-run_spine注入缺口落地.md`。
   - foundation 后续任何 `CAPABILITIES`/`API_VERSION`/`DEPRECATIONS` 变更，优先在门面保留过渡别名 + `CHANGELOG` 标注，保障 APS import 期闸稳定。

---

## 六、本仓对应落地记录

- `docs/2026-10-09-客户建议逐项回顾.md`（R2–R14 对账）
- `docs/2026-10-09-foundation回执-致APS(回信核验).md`（N1–N3 裁定 + 待办，T9a–T9e 已落地）
- `docs/2026-10-09-foundation收编-APS实证窗口台账.md`（本文件）
