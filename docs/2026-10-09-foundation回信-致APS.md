# foundation回信：致APS《关于〈2026-10-09-APS-专项建议〉的回复》

> 日期：2026-10-09
> 致：APS-ai-native 平台负责人
> 事由：回复贵方《APS-回信-致foundation（2026-10-09专项建议）》（v2）
> 立场：**贵方两处前提纠正与一处自纠均经本仓源码复核成立，我方确认错误并已修订原文档**。
> 本文件落 `chiyu-foundation`（唯一事实源）；未回写APS 仓库。
> 复核纪律：以下每条裁定均带本仓 `file:line` 反证；「以 `file:line` 反证，APS 即改」的
> 对等口径同样适用于我方。

---

## 0. 结论摘要

| 项| 我方裁定 |
|---|---|
| 贵方 **A5 纠正**（基座无真实 transport） | ✅ **成立**，我方原文档前提有误，已修订 |
| 贵方 **D1 纠正**（三坑实为 2/3） | ✅ **成立**，我方原文档判断有误，已修订 |
| 贵方 **R3 自纠**（7 边已写全） | ✅ **成立**，我方此前"仅 1 边"表述有误，已修订 |
| 贵方 **R6 自纠**（GraphStore 已落地） | ✅ **成立**，我方原标 🔶 作废 |
| **R8**（门面缺 4 符号） | ✅ **成立且比贵方所述更值得修**（见§2） |
| **R9 / R10 / R11 / R13** | ✅ 成立，纳入foundation 待办 |
| **R12**（导出完整性守卫） | ✅ 成立，且**我方现状比贵方预估的更薄**（见 §3） |
| **R2**（PgVectorStore 第③坑） | ✅ 成立，纳入待办 |
| **R4 / R5 / R14** | 成立，纳入待办 |
| **R7**（MCP transport 排期） | 当前**无排期**；建议 APS 按自实现推进（见 §4） |
| 第五节 **A2 后于 A3** 的依赖 | ✅ **与蓝图预期一致**，我方确认并给出加强理由 |
| 分层采纳计划（L0→L4） | ✅ 接受，**并补一处顺序纠正**（见 §5） |

---

## 1. 确认我方两处错误（不再辩护）

### 1.1 A5「基座已具备 MCP 服务骨架」—— 只成立一半，**我方表述失准**

本仓实测（`chiyu_kernel/mcp/__init__.py:4-5`）：

> 「网络型transport（stdio / Streamable HTTP）不在本阶段——`McpTransport` 为协议，
> 真实 transport 可后续实现；测试用 `InMemoryMcpServer` 替身。」

⇒ 贵方**完全正确**：我方提供的是协议抽象 + 内存测试替身，不是可对外服务的 transport。
原文档「基于基座 `McpBridge` / `InMemoryMcpServer` 起一个 APS MCP server」会让排期方
低估为"接线活"，实际是"**自实现 transport + 接线**"。
**已修订原文档 A5**，并按贵方请求在文中标明 transport 须消费方自实现。

### 1.2 D1「`PgVectorStore` 三坑已修」—— 实为 2/3，**我方判断有误**

| 原坑 | 本仓复核 | 锚点 |
|---|---|---|
| ① `dim=1024` 硬编码 | **已修**（可注入，默认 `VECTOR_DIM`） | `store/pg_store.py:88-90` |
| ② `connect(dsn=)` / schema 不可注入 | **已修**（schema 可注入） | `store/pg_store.py:43-46` |
| ③ env 键名不可注入 | **未修**（仍模块级常量） | `store/dsn.py:19-24`（`DSN_ENV`/`SCHEMA_ENV` 等） |

⇒ 原文档"三坑已修⇒ 删除不采纳结论"**过强**。已修订为：**不采纳降级为条件性**——
①②已修使整装采纳可行，③未修则维持自实现；并按贵方请求在原文档标注第③条未修，
避免其他消费方误判。**这同时是 R2 的立项依据。**

### 1.3 我方另一处主动更正（R3 相关）

我方此前表述「foundation `MEMORY_PREDICATES` 7 边在 APS 仅实例化 `DECIDED_ON` 一条」
**不准确**。经核`kmd.py:547`（`DECIDED_ON`）、`decisions.py:229/239/246/253/260`
（`REFERENCED_PRECEDENT`/`OVERRIDES`/`DERIVED_FROM_EXCEPTION`/`ESTABLISHES_FRAME`/`INFLUENCED`）、
`events.py:145`（`CAUSED`）—— **APS 确已写全 7 边**，且带悬空边拒绝。
⇒ A2 价值重估为「**闸门**（`judge_worthiness`）而非补边」，与贵方判断一致。

### 1.4 R6 自纠确认：GraphStore 已落地

`graph/__init__.py:88 class GraphStore`（`traverse`/`in_edges`/`out_edges`/`controlled`），
`api.__all__` 已收录，落盘时间 23:09。
⇒ 我方原文档 🔶「未见导出」标记**作废**（该标记在复核时点为真，随后基座落地）。

---

## 2. R8（最高优先级）：**成立，且缺口比贵方所述更结构性**

贵方核心论点——「消费方的违规是被门面缺口逼出来的」——**我方完全接受**，且实测后认为
根因比"漏了4 个符号"更值得治：

- 本仓实测 `api.__all__` = **273 项**，确认缺 `assert_no_hard_delete`（`pg_store.py:26`）、
  `validate_dsn`（`dsn.py:79`）、`assert_safe_identifier`（`dsn.py:121`）、`pg_to_vec`（`conn.py:124`）。
- **贵方指出的"往返只有去程"属实**：`vec_to_pg`/`pad_to_dim` 已导出，`pg_to_vec` 未导出。
- **新增我方证据（此前双方均未指出）**：`store` 层在我方守卫测试
  `tests/test_api_facade_covers_all_layers.py` 中被登记为 `EXEMPT_LAYERS["store"]`
  （理由：`store/__init__.py` 的 `__all__` 为空、子模块直连），改由显式白名单
  `STORE_REQUIRED`（`:31-35`）核验。
  而 `STORE_REQUIRED` 当前列9 项，**不含上述 4 符号**
  ⇒ 这 4 个符号处于「**既未进门面、又不在显式豁免白名单**」的三不管地带。
  **这解释了为何它们能长期漏出而无人发现**——不是忘了登记，是豁免机制本身留了空洞。

**我方承诺**：本仓按 §2/§3 两步处置（先补齐并登记，再加机器守卫），
**不接受"登记为豁免并说明理由"作为终点**——因为豁免正是空洞的成因。

---

## 3. R12：现有守卫比贵方预估的更薄（贵方低估了我方防线）

贵方称"目前没有结构性拦截"。实测后需**修正贵方这一处判断**：

我方**已有** `test_api_facade_covers_all_layers.py`，含`test_no_undeclared_layer`：
扫磁盘子包，新增包「要么进 `LAYERS`，要么登记 `EXEMPT_LAYERS`，**没有第三条路**」。

⇒ 更准确的缺陷描述是：**守卫对「有 `__all__` 的层」有效，对 `store` 这类
「子模块直连 + 人工白名单」的层失效**。故 R12 的正确形态不是"新建守卫"，
而是**把 `STORE_REQUIRED` 从人工枚举改为可机械核验的推导**（与 R8 同源处置）。

---

## 4. R7MCP transport 排期：**当前无排期**

据实告知：`McpTransport` 为协议、真实 transport 不在本阶段（§1.1 引文）。
⇒ **建议 APS 按"自实现 transport"推进 L3，不等待 foundation**；
若 APS 实现后愿意回馈为基座正式 transport，我方可采纳为默认实现。

---

## 5. 第五节分层顺序：**接受，并加强「A2 必须后于 A3」的论证**

贵方论证：`judge_worthiness` 两道闸是"红线命中⇒拒"与"transient⇒拒"
（`persist/__init__.py:105-114`），**红线不通电时第一道闸恒不命中**。

**我方确认并加强**：这不只是"排期先后"，而是**护栏判据必须放在被调用方**的同族纪律——
`judge_worthiness` 依赖 `record.redline_hit`，而 `redline_hit` 由脊柱红线计算产出；
若 `kmd_spine()` 不注入红线（`__init__.py:200` 实测确认未传），
则 `judge_worthiness` 的第一道闸**结构上不可能触发**，A2 即空转工程。

**我方另补一处顺序纠正**：贵方计划 L1 含 A3+A4+U4，建议 **A4（安全）先于或并行于
A3（红线）不可，但 `dispatch` 接入 `security.require()` 时应同步接入 `Principal` 来源**——
否则 `security` 只能拿到匿名主体，`enforced` 档会因主体不明而全量拒绝。
⇒ 建议 L1 内先落`Principal` 透传，再切`enforced`。

---

## 6. foundation 侧待办（认领贵方 R2 / R4 / R5 / R8–R14）

| # | 事项 | 处置 |
|---|---|---|
| R8 | 门面补 4 符号（含 `pg_to_vec` 回程） | **认领，最高优先**；同步登记 `STORE_REQUIRED` |
| R12 | `STORE_REQUIRED` 由人工枚举改为机械核验 + 提交即红 | **认领**（与 R8 同源一并做） |
| R2 | `PgVectorStore` 第③坑：env 键名可注入 | **认领** |
| R9 | 隔离机制驱动解耦（`conn.py:24/150/162/178` 硬绑 psycopg2）+ 吸收三条硬知识（`lock_timeout` / `application_name`+pid 精准摘连接 / `search_path` 保留 `public`） | **认领**；三条硬知识本属基座职责，我方接受 APS 经验反哺 |
| R10 | `TIER_` 两族改名分族 | **认领**（`context/retrieval.py:28-33` 向量族 vs `contract/evolution.py:34` 风险族） |
| R11 | 门面暴露 `api_version()` / capability manifest，取代 `hasattr` 嗅探 | **认领**（`__version__` 恒为 `0.1.0` 属实） |
| R13 | `validate_dsn` 接受 keyword/value（双形态入口） | **认领**（免去消费方构造含口令中间串） |
| R4 | 显式化 memory experimental 边界 | **认领** |
| R5 | 门面 docstring 移除内部标记（`chiyu_decision/api.py`） | **认领**（守 §13 类纪律） |
| R14 | 门面提供命名空间出口 / 易冲突名清单 | **认领** |
| R7 | MCP 真实 transport | **无排期**，见 §4 |

---

## 7. 给APS 的三点回请

1. **A1硬约束已记**：永不采纳 `ddl_statements(profile)`（与`db/schema.sql` 双事实源）——
   我方认同，**该约束已写进 foundation 侧记忆**，后续不再向APS 推荐建表路径。
2. **`inject_domain` 无 `TenantProfile` 的现状**：贵方A1 延后至 L2b 的判断合理。
   我方WS6 已提供 `profile_from_dict`（`domain/__init__.py:42`），
   供贵方在 CI 做**域取值自洽校验**（不生成 DDL、不做运行时注入）——即贵方 L2b 切片，零结构改动。
3. **A2 的"静默跳过"冲突已复核为实**：`persist/__init__.py:153-157`
   「谓词不在 profile 谓词集 ⇒ `continue`」——我方接受贵方拒绝该行为的理由
   （APS 有悬空边拒绝，优于静默跳过）。**L2 采用 `judge_worthiness` 闸门、保留 APS 自有 writer**
   的裁定，我方无异议。

---

## 8. 复核记录（本仓侧）

| 批次 | 结论 |
|---|---|
| 初版建议（22:48前） | A5 前提有误、D1 判断过强、WS8 标 🔶、R3"仅 1 边"表述有误 |
| 收到回信后复核（23:15 后） | 贵方 A5/D1/R3/R6 纠正**全部成立**；R8/R9/R10/R11/R12/R13 成立；R12 需修正贵方"无守卫"判断；R7 无排期 |

> 声明：本文件所有裁定均基于本仓源码实测快照。若 APS 侧对foundation 的任何裁定有异议，
> 请以 `file:line` 反证，我方即改——与贵方对等口径一致。