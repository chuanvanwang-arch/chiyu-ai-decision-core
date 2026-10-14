# 消费方接入手册（CRM / APS / enterprise 三册）

> 日期：2026-10-13 ｜ 配套：`2026-10-13-foundation功能成熟度与消费侧接入指南.md` + `2026-10-13-foundation逐符号成熟度映射表.md`
> 仓边界：本仓为唯一事实源；本手册为**接入指引**，消费方据其落地，不回写本仓。
> 强制纪律：仅 `chiyu_kernel.api` / `chiyu_kernel.contract`（含子树） / `chiyu_kernel.approval` / `chiyu_decision.api` / `chiyu_portal.api` 五门面可 import；违反即失去兼容性保护。

---

## 总纲：三册共用纪律

1. **启动即自检**（G5 范式，替代 hasattr 嗅探）：
   ```python
   from chiyu_kernel import api, require_capabilities
   assert api.api_version() == "1.0.0"          # 注意：API_VERSION=1.0.0，非文件标签 v0.1.0
   require_capabilities(["decision", "persist", "approval", "store", "contract", "canary"])
   # 未登记 / 状态不符 → RuntimeError 一次性列全
   ```
2. **只走 sanctioned 五面**；撞名符号（`register_scenario` / `Particle` 等）全限定引用。
3. **版本断言用 `api_version()` + `require_capabilities`**，禁 hasattr 嗅探。
4. **弃用别名**（如 `TIER_*`→`VTIER_*`）会在下一版移除，升级前跑 DeprecationWarning 扫描。
5. **实验态**（`evolution` 27 符号，经 `chiyu_kernel.api` 可 import）**不得写进硬验收判据**、不得对外宣称端到端跑通。

---

## 册一 · CRM（CRM-ai-native）

### 1. 必选能力清单

| 能力层 | 关键符号 | 用途 | 成熟度 |
|---|---|---|---|
| `decision` | `run_spine` / `SpineResult` / `resume_spine` | 决策脊柱主链 + PENDING 续跑 | stable |
| `approval` | `RedlinePriorityGate` | 红线优先审批闸（硬约束先于置信度） | stable |
| `domain` | `TenantProfile` / `profile_from_dict` | 领域注入（粒子/动作/场景装配） | stable |
| `contract` | `EIGHT_ELEMENTS` / `RUBRIC_KEYS` / `AUDIT_RECORD_KIND` | 八要素 / 九尺子 / 审计双轨常量 | stable |
| `version` | `api_version` / `require_capabilities` | 启动自检 + 能力闸（R-FC4/R-C5） | stable |
| `graph`（受控写通道） | `open_graph_write_store` / `build_graph_write_server` / `allow_principals` | 受控图写（MCP 工具，两阶段 confirm） | stable（代码就绪，待接线） |

### 2. 接入步骤（推荐顺序）

1. **启动自检**：`require_capabilities(["decision","approval","contract","domain","store"])`。
2. **领域装配**：`profile_from_dict({...})` 注入粒子/动作/场景（受控边 predicate 必须在 profile 内，否则构造期 fail-fast）。
3. **决策主链**：`run_spine(context, profile, rubric_scores, elements, redline_items, approval_gate=RedlinePriorityGate())`。
4. **审批续跑**：PENDING 结果经异步编排后 `resume_spine(result, persister=..., audit_sink=..., approval_ref=...)`；REJECTED 为终态不可复活。
5. **受控图写**（待接线）：kill-switch 休眠中，脚本改经 `chiyu_kernel.api` 导入（见 §4 坑①）。

### 3. 已知坑 / 边界

- **坑① off-facade 导入**（27ed3c5 消费对照 §4，已诚实登记）：`scripts/foundation_graph_write_stdio.py` 经 `chiyu_kernel.mcpserver` / `chiyu_kernel.graph.mcp` 导入 4 符号（`StdioTransport` / `allow_principals` / `build_graph_write_server` / `open_graph_write_store`）——**符号本身在 `chiyu_kernel.api.__all__`，路径非 sanctioned**。修复：4 处改 `from chiyu_kernel.api import ...`。当前零生产触达，待 CRM 侧批准。
- **portal 未启用**：26 符号确认 F2 观察项属实，CRM 到 **P3 阶段**才启（页面生成）。
- **存量 62 测试失败**：属 CRM 仓技术债，foundation 不介入归因，建议单列排查。

### 4. 自检命令

```bash
# 消费方 import 面门禁（扩展 --consumer-root 见 RFE C1，待排期）
python tools/check_import_surface.py --consumer-root <CRM仓>/src
# 能力闸冒烟
python -c "from chiyu_kernel import api, require_capabilities; require_capabilities(['decision','approval','contract','domain']); print('CRM-GATE-OK')"
```

---

## 册二 · APS（APS-ai-native）

### 1. 必选能力清单

| 能力层 | 关键符号 | 用途 | 成熟度 |
|---|---|---|---|
| `decision` | `run_spine` / `score_rubric` / `aggregate_confidence` / `evaluate_redline` | 脊柱 / 评分 / 置信（C-B 铁律） | stable |
| `contract` | `EIGHT_ELEMENTS` / `RUBRIC_KEYS` / `SPINE_ORDER` / `AUDIT_RECORD_KIND` / `AUDIT_EVENT_APPROVAL_*` | 决策契约 + 审计双轨（**E9 后 approval 族也经 contract 可达**） | stable |
| `approval` | `RedlinePriorityGate` / `DecisionVerdictState` | 审批闸（经 `chiyu_kernel.contract` 导入即可，免直连内部模块） | stable |
| `persist` | `PgVectorStorePersister` / `write_decision_memory_net` | 标准落库 + 记忆网物化 | stable |
| `audit` | `chain_hash` / `verify_chain` | 审计 hash 链（KMD 闭环） | stable |
| `canary` | `canary_probe` | 落库巡检（三判据） | stable |

### 2. 接入步骤（推荐顺序）

1. **纪律锚定**：APS 仅允许 `{chiyu_decision.api, chiyu_kernel.contract}` 两门面（T61/E9 后 approval 经 contract 可达，不直触 `chiyu_kernel.approval` 内部）。
2. **决策主链**：`run_spine(...)` + `score_rubric`（九尺子等权 0-4，按键名遍历零敏感）+ `aggregate_confidence`（**唯一来源=ratio 等权**，非 ratio source_key 抛 `ENGINE_FAULT`——C-B 铁律）。
3. **KMD 闭环**：K→M→D 八边逐边接通（见 `tests/test_kmd_spine.py` + `test_kmd_portal.py`，63/0），非空即绿判据排除。
4. **审计轨**：`run_spine(..., audit_persister=...)`（T58 三参，`REJECTED`/`PENDING` 审计轨 fail-closed）。
5. **巡检**：周期 `canary_probe(...)` 三判据（event+particle 成对 / engine 边恰好相等 / 红线挡落库）。

### 3. 已知坑 / 边界

- **C-B 铁律**：置信度唯一来源=基座等权 ratio，**禁止自做场景权重**（APS S3 纪律）。
- **E9 已接受**（T67 裁定）：approval 五符号经 `chiyu_kernel.contract` 再导出，APS 应改用 contract 面，避免直连 `chiyu_kernel.approval` 内部模块。
- **范式样例**：`work/spikes/spike_n5_audit_persister_wiring.py` 已净化入库为可共享范式样例（E6）。
- 三节点（10-20/10-27/11-06）窗口未到，无动作。

### 4. 自检命令

```bash
python -c "from chiyu_kernel.contract import RedlinePriorityGate, DecisionVerdictState, AUDIT_EVENT_APPROVAL_PENDING; print('APS-E9-OK')"
pytest tests/test_kmd_spine.py tests/test_kmd_portal.py -q
```

---

## 册三 · enterprise（chiyu-enterprise）

### 1. 必选能力清单

| 能力层 | 关键符号 | 用途 | 成熟度 |
|---|---|---|---|
| `domain` | `inject_domain` / `TenantProfile` / `DomainBundle` | 领域注入 SDK（关键石，最高杠杆） | stable |
| `decision` | `run_spine` / `resume_spine` / `SpineResult` | 决策脊柱 + 续跑 | stable |
| `approval` | `RedlinePriorityGate` | 审批闸 | stable |
| `persist` | `PgVectorStorePersister` / `write_decision_memory_net` | 标准落库 + 记忆网 | stable |
| `contract` | `EIGHT_ELEMENTS` / `RUBRIC_KEYS` / `AUDIT_RECORD_KIND` / `AUDIT_EVENT_APPROVAL_*` | 决策契约 + 审计（E9 后 approval 经 contract） | stable |
| `mcpserver` | `McpServer` / `issue_confirm_token` / `verify_confirm_token` | MCP 输出面 + 两阶段零信任写 | stable |
| `orchestration` | `AgentLoop` / `AgentRegistry` / `TeamRegistry` | 多智能体编排 | stable |
| `memory` | `write_decision_memory_net` / `PgNoteStore` / `recall_precedents` | 决策记忆网（bridge.py 接，标 experimental） | stable（网本身） |
| `audit` | `_audit_persister`（3 参） / `chain_hash` | 审计轨（E5 接线有效） | stable |

### 2. 接入步骤（推荐顺序）

1. **领域注入**：`inject_domain(profile=..., actions=..., scenarios=...)` → `DomainBundle`（四道闸，失败聚合 `DomainInjectionError`）。
2. **决策主链**：`run_spine(..., approval_gate=RedlinePriorityGate())`。
3. **记忆网写回**：经 `write_decision_memory_net`（单源裁定守卫钉死 graph_edge 唯一写；`PgNoteStore` 钉死 particle_attribute 唯一写）。
4. **审计轨**：`_audit_persister`（3 参：`record_kind` 硬断言 fail-loud，R79），接 `run_spine(audit_persister=...)`。E5 已满足（U2 spine 101/0 + 八变异全红）。
5. **MCP 输出面**：`McpServer.expose(...)` + 两阶段 `confirm_token`（写类工具首次不执行，二次带 token 才执行）。
6. **编排**：`AgentLoop` / `TeamRegistry` 组合多智能体；`control_plane._element_matrix_of` 三级解析（租户默认 → 场景包 pkg.assets 覆盖 → fail-closed 回退 M1）。

### 3. 已知坑 / 边界

- **memory 标 experimental**：`bridge.py` 接记忆网，对外口径**必须标 experimental**（R-FE1）；毕业须走 RFE（先例 memory T44）。
- **E5 E2E 留待手动**：重启 host 8000 后复跑 E5 E2E（R8：AI 不启停）。
- **边界纪律**：enterprise 脚本须落本仓 `scripts/`，**禁越界写 foundation 仓**（T66 §2.2 已收口，`facade_usage_audit.py` 已移回）。
- **X2 已采纳**：`AUDIT_EVENT_*` 经 `chiyu_kernel.api` 再导出（T68 实施），enterprise 可经 api 门面达审计事件常量。

### 4. 自检命令

```bash
python -c "from chiyu_kernel.api import inject_domain, McpServer, issue_confirm_token, AUDIT_EVENT_APPROVAL_PENDING; print('ENT-OFFICIAL-OK')"
pytest tests/test_*.py -q   # 主判据 39/0 + 92/0（企业侧自带可复跑命令）
```

---

## 三册横向对比

| 维度 | CRM | APS | enterprise |
|---|---|---|---|
| 核心门面 | decision+contract+domain+approval | decision+contract（仅两门面） | decision+contract+domain+mcpserver+orchestration |
| 记忆网 | 未接 | 未接 | 接（标 experimental） |
| MCP 输出面 | 代码就绪待接线 | 直连 import | 接（McpServer） |
| portal | P3 启用 | 未启用 | 未启用 |
| 特别纪律 | off-facade 修复待批 | C-B 等权铁律 | experimental 标注 + 边界勿越界 |

— foundation（chiyu-foundation 仓），2026-10-13
