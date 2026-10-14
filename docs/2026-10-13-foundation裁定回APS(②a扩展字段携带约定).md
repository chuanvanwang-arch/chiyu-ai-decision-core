# Foundation 裁定回 APS —— T79 开放项 ②a：`would_deny` 语义与扩展字段携带约定

> 裁定方：chiyu-foundation（本仓，AI 原生底座唯一事实源）
> 致：APS（crm-native / chiyu-decision 消费方）
> 闭环：T75 设计落地核查（T79 兼致三仓通知）中 APS 留的 ②a 开放项
> 结论：**采纳 APS 提议选项②** —— 消费方统一采用基座 `SecurityDecision` 5 字段形，留痕字段经 `extensions` 携带；`would_deny` 在 `enforced` 下的语义按 D2 防漂移不变量**钉死**，不可放宽。

---

## 一、裁定结论（一句话）

APS 自有判定载体（`action/namespace/required_perm` 三个留痕字段）**不再作为第二份判定结构**，统一收敛为基座 `SecurityDecision` 5 字段形；多出的留痕字段经新增的 `extensions: Mapping[str, object]` 槽携带。该约定已在契约层落地（见第三节），manifest 已同步，守卫已绿。

---

## 二、冲突回顾与裁定依据

同一「强制拒绝」场景：

| 维度 | 基座 `SecurityDecision` | APS 既往 `SecurityDecision` |
|---|---|---|
| `mode=enforced, allowed=False` | `would_deny` **必填 True**（结构保证 `would_deny == not allowed`） | `would_deny` 恒 **False**（仅 advisory 观测，enforced 下视作无意义） |
| 字段集 | 5 字段（mode/allowed/would_deny/reason/scope） | 5 + 3 留痕（action/namespace/required_perm） |
| 互换性 | — | 直喂基座 → 不守恒 → `ValueError` |

**裁定依据**：D2「三档安全防漂移」铁律要求 `enforced` 是真拦、判定单对象内自洽，这是底座级安全不变量，**不可为消费方便利而放松**。因此 APS 既往「enforced 下 `would_deny` 恒 False」模式必须**作废**；其多出的 3 个留痕字段属审计留痕面、不上收，改为挂 `extensions`。

---

## 三、契约层约定（已落地，可机检）

符号位置：`packages/chiyu-kernel/src/chiyu_kernel/contract/iam.py`
双面 re-export：`chiyu_kernel.contract`（L0）与 `chiyu_kernel.api`（sanctioned 门面）均已导出。

1. **扩展槽**：`SecurityDecision.extensions: Mapping[str, object] = field(default_factory=dict)`
   - `frozen` dataclass 仍保持**可哈希**（已显式定义 `__hash__`，基于五字段 + `frozenset(extensions.items())`）。
2. **结构性守卫**（`__post_init__` 保证，非文档纪律）：
   - `extensions` 必须为 `Mapping`（非 Mapping → `ValueError`）；
   - 键集 ∩ `SECURITY_DECISION_FIELDS` 必须为空（撞核心字段 → `ValueError`）；
   - 基座**不解释** `extensions` 内容，不参与任何判定不变量。
3. **导出常量**：`SECURITY_DECISION_EXTENSION_RULE`（契约层书面约定，随门面导出）。
4. **`would_deny` 语义钉死**：
   - `enforced`：`would_deny == (not allowed)` **强制**（违则 `ValueError`）；
   - `advisory`/`off`：`would_deny` 语义由判定执行器保证，基座不强约束；
   - APS 既往「enforced 下 `would_deny` 恒 False」模式**作废**；如需保留 advisory 观测值，改挂 `extensions["aps_advisory_would_deny"]`。

---

## 四、APS 侧 swap 迁移指引

1. 构造判定结果时改用基座 5 字段形：`SecurityDecision(mode, allowed, would_deny, reason, scope)`；
2. 将 `action/namespace/required_perm` 移入 `extensions={"action": ..., "namespace": ..., "required_perm": ...}`；
3. `enforced` 拒绝场景：`allowed=False` 且 `would_deny=True`（满足不变量）；原 advisory 观测值挂 `extensions`；
4. 把「各用各的 → 统一 5 字段形 + extensions 留痕」做成 APS 侧回归守卫，防未来漂移（与基座 `test_iam_security_extension.py` 对锚）。

---

## 五、验收（trust-but-verify，junitxml 直读）

- 新增守卫：`packages/chiyu-kernel/tests/test_iam_security_extension.py`（extensions 结构 / 键冲突 / 哈希 / enforced 不变量）；
- 组合回归：chiyu-kernel **689** + chiyu-cli **13** + 根 tests **12** = **714 passed / 0 failed**；
- `contract/manifest.json` 已随 iam.py 变更重生成（sha256 同源对账绿）。

---

## 六、三仓对齐进度更新

| 仓 | T79 状态 | ②a 状态 |
|---|---|---|
| enterprise | 已闭环（16:55） | 不涉及（企业侧用基座 5 字段形 + 自有 extension 参考实现） |
| APS | 已闭环（17:00） | **本裁定闭合**（采纳选项②，待 APS swap 并回 hold-good） |
| CRM | 缺整盘核收回执 | 设计期 2 修订已在 T77 吸收，待催 T79 整盘确认 |

> 本裁定为 T79 三仓对齐的收口项之一；APS swap 完成并回 hold-good 后，②a 即完全闭合。
