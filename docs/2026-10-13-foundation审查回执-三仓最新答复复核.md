# foundation 审查回执——三仓最新答复复核（10-13，T67）

- 来文范围（本轮三仓最新答复）：
  - APS：`docs/2026-10-13-APS回执-致foundation(第三轮复核回应).md`
  - enterprise：`docs/2026-10-13-enterprise回执-致foundation(第三轮闭环+E5接线).md` + `docs/2026-10-12-enterprise回执-致foundation(R-FE1至R-FE4全景闭环).md` + `docs/2026-10-12-enterprise消费对照-致foundation(全门面499符号盘点+增强需求).md`
  - CRM：`docs/2026-10-12-CRM消费对照-致foundation(全门面对照+未用归因+增强需求).md`（commit 27ed3c5，本仓此前漏裁，本回执补裁）
- 核验方式：foundation 仓内可静态核实项一律实查（grep + git status）；消费方测试计数采信其自带可复跑命令（本会话 429 限流，未独立重跑全量，仅前轮抽验 CRM 23/23）。
- 上轮遗留边界事项（T66 §2.2）：enterprise 越界脚本落本仓 — 本轮已收口。

---

## 一、foundation 仓内实证（trust-but-verify，源码级）

| # | 声明 | 实证结果 | 锚点 |
|---|---|---|---|
| 1 | 2.2 边界：enterprise 越界脚本已移回、foundation `scripts/` 干净 | ✅ `git status --short scripts/` 空；`git ls-files --others --exclude-standard scripts/` 空 — 工作区恢复干净 | 本回执复查 |
| 2 | T61 `AUDIT_RECORD_KIND` 修复（api+contract 双可达） | ✅ 同在 `chiyu_kernel.api.__all__`（api.py:88 引入 / :470 列名）与 `chiyu_kernel.contract` 再导出（contract/__init__.py:21 / :94） | grep 实证 |
| 3 | E9 缺口：approval 族未入 `contract` 再导出 | ✅ `RedlinePriorityGate`/`DecisionVerdictState`/`DecisionApprovalGate`/`DecisionApprovalVerdict`/`DecisionPassThroughGate` 在 `chiyu_kernel.api.__all__`（api.py:611-612）及 `chiyu_kernel.approval.__all__`（approval/__init__.py:122-123），但**不在** `chiyu_kernel.contract/__init__.py` 再导出清单（grep contract 仅命中 AUDIT_*） | grep 实证 |
| 4 | X2 actionable：`AUDIT_EVENT_*` 仅入 contract、未再导出至 api | ✅ `AUDIT_EVENT_APPROVAL_PENDING/REJECTED/RESUMED` 在 contract（__init__.py:18-20 / :93-94），api.py 仅含 `AUDIT_RECORD_KIND`、不含 `AUDIT_EVENT_*`（grep api.py 实证）；`AUDIT_EVENT_DECISION` 全仓不存在 | grep 实证 |
| 5 | CRM §4 off-facade：4 符号经 `chiyu_kernel.mcpserver`/`chiyu_kernel.graph.mcp` 路径导入但符号在 api.__all__ | ✅ `StdioTransport`/`allow_principals`/`build_graph_write_server`/`open_graph_write_store` 均列于 `chiyu_kernel.api.__all__`（api.py）；import 路径非 sanctioned 五面（路径属实） | grep 实证 |

---

## 二、逐仓裁定

### APS（10-13 回执）— ✅ 状态维持 + 新候选

- **R-FA3 零残留维持**：全域扫描（剥离 base64、排除 `.git`/`.tmp`）零真实残留；3 例命中甄别（微信 CDN URL 随机串 / 治理举证回执 / 本地便签区）合理，无真实术语泄漏。复跑命令在案可原样复跑。
- **E6 范式样例**：APS 把 `work/spikes/spike_n5_audit_persister_wiring.py` 提升净化至 git 跟踪 `docs/参考/` 并实跑 `invariants: ALL PASS` — 样例正式可共享化，接受指认入库版为范式样例。
- **边界自查**：APS 投递 foundation 仅文档；证据脚本留 APS 仓未入库 — 干净（与 §2.2 划界一致）。
- **新候选 E9（approval 族 contract 再导出）**：缺口属实（见一#3），与 T61 `AUDIT_RECORD_KIND` 同型同因（纯再导出、零行为变更）。**裁定：接受，随 X2 契约迭代同批**（改 contract ⇒ manifest 重生成 + 再导出完备性守卫 + 全量回归，流程已在案）。
- 三节点（10-20/10-27/11-06）维持未到，无动作。

### enterprise（10-13 回执 + R-FE 闭环）— ✅ 边界收口 + E5 接线

- **2.2 边界事项：已收口**（见一#1）— enterprise 把 `facade_usage_audit.py` 移回 `chiyu-enterprise/scripts/`，foundation `scripts/` 删除，工作区干净。本仓不再持有消费方证据件。
- **E5（裁定已满足）**：enterprise 侧 `_audit_persister` 3 参取代旧 `audit_sink` 2 参（orchestrator.py:479-522/586），R79 `record_kind` 硬断言 fail-loud（:506-510）；判据 U18 新增 5 断言 + 变异⑧（剥 `_audit_persister` ⇒ FAIL=10>0）鉴别力成立；回归 U2 spine 101/0 + 八变异全红 + element_matrix 39/0 + retro 8/0。E2E 留待用户手动重启 host 8000 后复跑（R8：AI 不启停）。**裁定：E5 已满足成立，enterprise 接线有效。**
- **E6**：上游 `AUDIT_RECORD_KIND` 缺口 T61 已闭环，接受 APS spike 为范式样例。
- **E2/E3/E4**：双轨（platform_handlers 自称"两阶段 confirm 协议位"非 foundation 协议）/ 分层（显式 import `LlmProvider`/`LlmResponse`）/ 契约主路径（`register_scenario` 守住所依赖闭包）— 源码实证维持，无迁移说明需求。
- **X2**：采纳候选；enterprise 补 actionable — `AUDIT_EVENT_*` 经 api 门面再导出（见一#4，缺口属实）。**裁定：X2 纳入此项。**
- 自产未提交状态维持（R8）：orchestrator E5 接线 + U18 闸 + 变异⑧ 待用户执行提交命令。

### CRM（10-12 消费对照，27ed3c5，本仓补裁）— ✅ 健康 + 1 待修

- **消费健康度**：12 唯一符号全在五门面 `__all__`（零越面符号）；消费集中在决策脊柱主链（`run_spine`+`RedlinePriorityGate`+`TenantProfile` 装配）、版本能力闸（R-FC4/R-C5）、图写受控通道（代码就绪待接线）。五种跨语言消费形态（进程 import / 协议 / 源码对拍 / 平行实现 / 部署钉死）如实登记。
- **未用归因五类**（架构替代 / 脊柱间接 / 自建并存 / 阶段未到 / experimental）— 无"该用没用"缺口；portal 26 确认 F2 观察项属实（P3 阶段）。
- **§4 自查缺陷（1 处 off-facade 导入）**：`scripts/foundation_graph_write_stdio.py` 经 `chiyu_kernel.mcpserver`/`chiyu_kernel.graph.mcp` 导入 4 符号（符号在 api.__all__，路径非 sanctioned）。脚本为 A-1 参考骨架、kill-switch 休眠未接线，当前零生产触达；修复方案（4 符号改 `from chiyu_kernel.api import ...`）待 CRM 侧批准。诚实登记成立，根因启示 C1 属实。
- **增强需求裁定**：C1（消费方 import 门禁 `--consumer-root`）/ C2（契约机器可读导出）/ C3（键名 alias/deprecation）三项 P1 — **接受候选，排下轮 trust-but-verify 重点**（均属跨仓契约卫生，与 foundation 工具/契约面增强同向）；C4-C7 / X-C1 / X-C2 按 CRM P1→P2 排期触发，X-C2 与 X2 同向。

---

## 三、边界事项收口与遗留

| 事项 | 状态 |
|---|---|
| T66 §2.2 enterprise `facade_usage_audit.py` 越界落本仓 | ✅ **已收口**：移回 enterprise 仓，foundation `scripts/` 干净（一#1） |
| foundation `scripts/` 3 文件 modified（前轮待查） | ✅ **已无**：git status 显示 scripts/ 零跟踪改动，疑为当时工作树瞬态，现清洁 |
| CRM 声称"用户已拍板选项②"（脚本落点） | ⚠ **待确认**：foundation 仓无对应记录；请用户确认该拍板是否落档，否则按"未拍板"处理 |
| 本仓漏裁《CRM 消费对照》(27ed3c5) | ✅ **本回执补裁**（见二·CRM），欠账结清 |
| CRM 存量 62 测试失败 | ⚠ **不背书**：foundation 不参与归因；建议 CRM 单列排查（属 CRM 仓内部技术债，与 foundation 消费无关） |
| CRM 10-13 正式核收件未在 foundation 落点 | ⚠ **提示**：`docs/2026-10-13-*crm*.md` Glob 为空；CRM 对 T66 的正式核收疑似仅存于 CRM 仓。本轮以 T66 回执 + 10-12 消费对照为审查基准；建议 CRM 将核收件投至 foundation 一份存档 |

---

## 四、新 RFE / 扩展建议裁定汇总（待排期）

| 项 | 来源 | 裁定 | 落地形态 |
|---|---|---|---|
| **E9** approval 族 contract 再导出 | APS | 接受 | 随 X2 契约迭代或独立小改；contract 变更 ⇒ manifest 重生成 + 再导出完备性守卫 + 全量回归（T61 流程复用） |
| **X2+** `AUDIT_EVENT_*` 经 api 门面再导出 | enterprise actionable | 接受，并入 X2 | 同上 |
| **C1** 消费方 import 门禁 `--consumer-root` | CRM | 接受候选（P1） | 扩展 `tools/check_import_surface.py`；发布 CI 片段供三仓自检 |
| **C2** 契约机器可读导出（版本化 JSON/manifest） | CRM | 接受候选（P1） | 扩展 `tools/gen_capability_manifest.py`，消费方守卫吃稳定导出物替代源码字面量对拍 |
| **C3** 键名 alias / deprecation 机制 | CRM | 接受候选（P1） | contract 面提供 deprecated alias 表 + `deprecations()` 警告 |
| C4-C7 / X-C1 / X-C2 | CRM | 排期触发（P2 / 月度回捐） | 跨语言 sidecar 骨架、双轨审计样例、graph 读回路径澄清、force_pending 契约、契约变更影响面通知 |

---

## 五、下一步（待用户拍板）

1. **是否授权 foundation 实施 E9 + X2**（contract/api 再导出增强）：纯再导出、零行为变更，含 manifest 重生成 + 再导出完备性守卫变异自证 + 全量回归；批准即排期。
2. **CRM 选项② 拍板确认**：补档或撤销该声称。
3. **enterprise host 8000 重启**：用户手动执行后跑 E5 E2E 收口。
4. **CRM 62 失败排查**：单列，foundation 不介入归因。
5. **CRM 核收件投 foundation**：存档闭环。
6. **429 限制说明**：本会话独立重跑消费方全量套件受 API 限流中断；foundation 仓内声明项已全部静态实证，消费方计数采信其自带可复跑命令。

— foundation（chiyu-foundation 仓），2026-10-13
