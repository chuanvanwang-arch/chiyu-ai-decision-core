# Foundation 回函 —— Batch-1a 落地：八闸框架（gate_chain）+ 第0闸决策凭证（decision_gate）+ 去重收口接入点（致 CRM / APS / enterprise）

> 裁定方：chiyu-foundation（本仓，AI 原生底座唯一事实源）
> 致：CRM / APS / enterprise（三仓消费方）
> 背景：用户批准启动 Batch-1a 首批（去重收口方向），点名「安全八闸」项；本批把 CRM / APS /
>       enterprise 各自造的**同构写操作闸机制**上收 foundation 单一事实源，消除「分叉成第二
>       事实源」风险（CRM 审定 #2 + Batch-0 结论）。第0闸选型 (a) 轻量决策凭证契约。
> ⛔ 仓边界：本仓**严禁向三仓仓库写任何产物**，故三仓调用点改造由各自仓库完成；
>   本函为调用点改造指引 + 对接面说明。

---

## 一、Batch-1a 落地总览

**新增（域无关、栈无关：L0 契约 + 机制纯函数，与三仓栈无关——CRM Node / APS·enterprise Python 均可消费）**：

| 层 | 文件 | 符号 |
|---|---|---|
| 契约 L0 | `chiyu_kernel/contract/gate.py` | `GATE_CLASSES` / `GATE_CHAIN_INVARIANTS` / `DECISION_CREDENTIAL_FIELDS` / `DecisionRequiredError` / `DecisionCredentialError` / `GateChainError` / `require_decision_id` / `verify_decision_credential` / `GateSpec` |
| 机制层 | `chiyu_kernel/gate/decision_required.py` | `gate_write` |
| 机制层 | `chiyu_kernel/gate/chain.py` | `run_gate_chain` / `evaluate_chain` |
| 门面 | `chiyu_kernel.api` / `chiyu_kernel.contract.__init__` | 双面 re-export（见 §门面登记） |
| 能力登记 | `version.py` CAPABILITIES / `test_api_facade_covers_all_layers.py` LAYERS / 仓库根 `contract/capability-manifest.json` | `gate` 能力 `stable`，三项同步 |

**门面登记（sanctioned 面纪律）**：`api.py` 与 `contract/__init__.py` 双面 re-export 全部 13 个 gate 符号（`GATE_CLASSES` / `GATE_CHAIN_INVARIANTS` / `DECISION_CREDENTIAL_FIELDS` / `DecisionRequiredError` / `DecisionCredentialError` / `GateChainError` / `require_decision_id` / `verify_decision_credential` / `GateSpec` / `gate_write` / `run_gate_chain` / `evaluate_chain`）；`test_facade_import_vs_all.py` 机械守卫确保「门面 import 必进 `__all__`」。

**能力登记（单一事实源纪律）**：`CAPABILITIES` 元组加 `("gate","stable")`；`LAYERS` 加 `"gate"`；`capability-manifest.json` 加 gate 项（语义=写操作安全闸·八闸框架·四分类范式·Batch-1a 落地，进入 1.0 兼容承诺）；三项必须同步，否则 `test_no_undeclared_layer` / `test_manifest_capability_ids_exactly_equal_capabilities` 红。

---

## 二、八闸四分类范式（骨架，零领域字面量铁律）

产品官方「写操作八闸」= 四大类安全范式骨架，本批**只收四分类 + 编排协议**，不收任何具体域闸名。

```python
GATE_CLASSES = ("precheck", "permission", "redline", "traceability")
#   事前校验      权限边界      红线拦截      事后可溯
# 任意 N 级闸挂此四类之一；域闸名（sales_* 等）由消费方 GateSpec.name 注入，内核零领域字面量。
```

**消费方编排范式**（可配置 N 级、串行 fail-closed 链）：

```python
from chiyu_kernel.api import GateSpec, run_gate_chain, DecisionRequiredError

# 域闸名 + check 由消费方注入；cls 必 ∈ GATE_CLASSES
gates = [
    (GateSpec("scope_violation", "precheck"),      lambda p: p["scope"] == p["expected"]),
    (GateSpec("rbac_check",      "permission"),    lambda p: has_role(p["principal"], p["op"])),
    (GateSpec("redline_block",   "redline"),        lambda p: not hits_redline(p["op"], p["target"])),
    (GateSpec("audit_trail",     "traceability"),   lambda p: p.get("audit_ref") is not None),
]
passed = run_gate_chain(payload, gates, on_fail=lambda spec, why: GateChainError(f"{spec.name} 拒: {why}"))
```

**机制层不变量（fail-closed，`GATE_CHAIN_INVARIANTS`）**：
- `empty_chain_denied` —— 空链 = 不通过（`run_gate_chain` 直接抛 `GateChainError`）；
- `short_circuit_on_first_deny` —— 任一闸拒即整体拒（短路）；
- `class_in_enum` —— `GateSpec.cls` 必 ∈ `GATE_CLASSES`（`__post_init__` 校验，非法即 `GateChainError`）；
- `all_pass_required` —— 全过才放行（返回通过闸名列表）；`evaluate_chain` 纯函数对账形态。

> 守纪律：内核不持有、不约束任何域闸名（`GateSpec.name` 任意字符串，内核只透传）；具体 check 实现由消费方注入；四分类用词（`precheck`/`permission`/`redline`/`traceability`）已核验**不在** `domain-literal-denylist.json` 黑名单（redline 亦不在），守住零领域字面量铁律。

---

## 三、第0闸：轻量决策凭证契约（选型 a）

与 D1 `OUTCOME_REQUIRED_FIELDS.decision_id` 同源（写操作必须锚定一个决策，**无决策不写**）。消费方签发、内核只验结构、不产决策。

```python
DECISION_CREDENTIAL_FIELDS = ("decision_id", "issuer", "issued_at", "ttl", "checksum")
#  决策标识        签发主体    签发时间戳   有效期秒    结构校验和（消费方签发，内核只验形态不验算法）
```

**两种接入形态**（消费方任选）：

```python
from chiyu_kernel.api import gate_write, require_decision_id, verify_decision_credential

# 形态 A：payload 直接带 decision_id（最简）
did = gate_write(payload)                       # 缺 decision_id ⇒ DecisionRequiredError（fail-closed）

# 形态 B：显式决策凭证（含 issuer/checksum，结构校验）
cred = {"decision_id": d, "issuer": "aps", "issued_at": now, "ttl": 3600, "checksum": h}
did = gate_write(payload, decision_cred=cred)  # 形态非法 ⇒ DecisionCredentialError
```

- `require_decision_id(payload, *, field="decision_id")` —— 第0闸原语，缺/空即 `DecisionRequiredError`；
- `verify_decision_credential(cred)` —— 验 `DECISION_CREDENTIAL_FIELDS` 全在 + `decision_id`/`issuer` 非空 + `checksum` 非空字符串，返回 `decision_id`；内核**不校验 checksum 算法**（消费方职责）；
- `gate_write(payload, *, decision_cred=None, on_missing="raise")` —— 统一入口：`decision_cred` 优先走凭证校验，否则走 `require_decision_id`；`on_missing="return_none"` 可降级返回 `None`。

---

## 四、去重收口接入点（三仓各自改造，本仓不写产物）

**核心指令**：三仓现有各自造的同构写操作闸机制 → 改为**消费 foundation 契约**（`chiyu_kernel.contract.gate` + `chiyu_kernel.gate`），**禁改消费方源码语义、禁在消费方保留第二套实现**。据 Batch-0 对等基线审计锚点：

| 仓 | 现有同构机制（据 Batch-0 锚点） | 收口动作 |
|---|---|---|
| **CRM** | `src/action/executor.js` 八闸串行 + `src/decision/autonomyEngine.js` requireDecision 第0闸 + `src/mcp/gateway.js` | ① executor 八闸改为用 `GateSpec` + `run_gate_chain` 编排（域闸名保留为 `GateSpec.name`，check 实现保留在 CRM 消费方层）；② autonomyEngine 第0闸改用 `require_decision_id` / `gate_write`；③ 删 executor 内自造闸链遍历逻辑（消除第二事实源） |
| **APS** | `src/aps/actions.py:79` decision_gate 第0闸 + `src/aps/actions.py:708` 硬编码闸 | ① `actions.py:79` 第0闸改用 `gate_write`（或 `require_decision_id`）；② 硬编码闸改为 `GateSpec` + `run_gate_chain` 注册式编排（四分类对齐）；③ 删 actions.py 内自造闸校验分支 |
| **enterprise** | `guard.py:146` decision_gate 第0闸 + `guard.py:8-15` 八闸 + `confirm.py:59` 双阶段令牌雏形 | ① `guard.py:146` 第0闸改用 `gate_write`；② `guard.py:8-15` 八闸改为 `GateSpec` + `run_gate_chain`（四分类映射）；③ `confirm.py:59` 双阶段令牌雏形暂留（属 Batch-1a 去重清单第 4 项 `two_phase_token`，下一子批收口，本批先不动） |

**跨仓纪律（硬性）**：
- ⛔ 本仓不向三仓写任何产物；三仓调用点改造由各仓在其仓库完成、各自提交。
- ⛔ 域闸名 / check 实现 / 业务语义**留在消费方**；foundation 只供骨架 + 编排 + 第0闸凭证校验。
- ⛔ 改造后各仓跑对应 parity 守卫（§五）全绿即达去重收口；禁止在消费方保留与 foundation 同构的第二套闸链实现。

---

## 五、验收（trust-but-verify，junitxml 直读）

- **新增守卫**：`test_decision_credential.py`（11 用例，覆盖 `require_decision_id` 缺/空/有、`verify_decision_credential` 缺字段/空 checksum/空 issuer/有效、`gate_write` payload/credential/missing/return_none 形态）；`test_gate_chain.py`（10 用例，覆盖 `GateSpec` 非法类/空名、空链拒、短路拒、全过返名、check 异常拒、`evaluate_chain` 全过/空/含拒、parity 消费方四分类编排含拒用例）。
- **变异自证 ×4**（载荷点验证，删判据→转红→还原；会话回显污染以解释器/TaskOutput/XML 真值裁定）：
  1. 删 `require_decision_id` 校验 → `test_require_decision_id_missing_raises` 转红 → 还原；
  2. 删 `verify_decision_credential` checksum 形态校验 → `test_verify_credential_bad_checksum_raises` 转红 → 还原；
  3. 删 `run_gate_chain` 空链 `GateChainError` → `test_run_chain_empty_denied` 转红 → 还原；
  4. 删 `run_gate_chain` 短路（ok 恒 True 放行）→ `test_run_chain_short_circuit_on_deny` 转红 → 还原。
- **收尾核验**：`grep -rn "MUTANT"` 确认零变异残留；`contract/manifest.json` 重生成含 `gate.py` sha256。
- **组合全量回归**：**819 passed / 0 failed**（chiyu-kernel 690 + chiyu-decision 82 + chiyu-cli 13 + 根 tests 12 + 新增 22 守卫：11 credential + 10 chain + 1 LAYERS + manifest 重同步）；较 T81 基线 797 +22。

---

## 六、三仓对齐动作表

| 仓 | Batch-1a 动作 | 不在此批（后续批次） |
|---|---|---|
| **CRM** | ① executor 八闸改消费 `GateSpec`+`run_gate_chain`；② autonomyEngine 第0闸改 `gate_write`；③ 删自造闸链第二实现 | `two_phase_token`（T75 双阶段令牌）、`rbac_core`、监控底座、夜批复盘调度 |
| **APS** | ① `actions.py:79` 第0闸改 `gate_write`；② 硬编码闸改 `GateSpec`+`run_gate_chain` 注册式 | `standing_credential`（APS 缺口）、审批流升格、定时调度（APS 缺口）、`two_phase_token` 升格 |
| **enterprise** | ① `guard.py:146` 第0闸改 `gate_write`；② `guard.py:8-15` 八闸改 `GateSpec`+`run_gate_chain` | `confirm.py:59` 双阶段令牌（下一子批）、`conflict_resolver`（enterprise 缺口）、`attribution_rules`（enterprise 缺口） |

> 本函为对接面说明；三仓源码改造由各仓在其仓库完成（本仓不越界写产物）。三仓接入后跑对应
> parity 守卫全绿，即满足「消除第二事实源、域无关机制统一收口 foundation」的 Batch-1a 验收标准。
> 后续推进 Batch-1b（共有缺口补齐：shadow_replay / ab_experiment_close / quota_gate /
> param_health_check / conflict_resolver / attribution_rules + audit_4q 口径统一）。
