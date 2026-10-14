# foundation 收编 run_spine 注入缺口（S1/S4 钩子）

> 关联：`docs/2026-10-09-foundation收编-APS实证窗口台账.md` §5（收敛边界裁定）
> 授权：用户「继续完成相应的缺口开发」（2026-10-09）
> 纪律：TDD → 变异自证 → 组合回归 → 分层提交

## 一、背景与收敛裁定

APS 实证窗口收口后，共识判定 APS 用自建 `KmdSpine` 组合器 + 复用基座机制函数已是合规消费。
但若 APS 主动选择统一、version-gated 脊柱编排（即改用 foundation `run_spine`），则引出两个注入缺口。
收敛边界裁定（见收编文档 §5）：

- **S4 域红线回调钩子** = foundation **公共能力**（任何消费方都可能用回调式域红线替代目录子串匹配）→ **收敛到本项目**
- **S1 装配钩子** = 仅当 APS 要 `run_spine` 持有装配编排、与 `KmdSpine` 形状对称时才需 → **可选**架构对称诉求，也收敛到本项目（形态）
- **钩子内域逻辑**（`ContextAssembler` 内容、`tier` 分档 + 强制人工在环）= 取值与执行 → **不收敛**，归 APS，本仓零领域字面量不破

## 二、实现（`packages/chiyu-decision/src/chiyu_decision/spine.py`）

### S4 域红线回调钩子（必需）
`run_spine` 新增通用可选形参：
```python
redline_callback: Optional[Callable[..., RedlineVerdict]] = None
```
S4 阶段判定：
```python
if redline_callback is not None:
    verdict = redline_callback(context=context, redline_items=redline_items)
else:
    verdict = evaluate_redline(context=context, redline_items=redline_items)
```
- 提供时替代 `evaluate_redline` 的目录子串匹配；域逻辑（tier 分档 / 人工在环）由消费方在回调内实现
- 回调签名对齐 `evaluate_redline`：`(context, redline_items) -> RedlineVerdict`，消费方可用 `functools.partial` 注入域状态
- **严格加法**：不传时行为完全不变（仍走目录匹配）

### S1 装配钩子（可选）
`run_spine` 新增通用可选形参：
```python
context_factory: Optional[Callable[[Mapping], Mapping]] = None
```
S1_context 校验前装配：
```python
if context_factory is not None:
    context = context_factory(context)
if not context:
    raise DecisionError("ENGINE_FAULT", "S1_context 为空：S1 必须先于一切")
```
- 让 `run_spine` 可持有装配编排步骤，与 `KmdSpine` 形状对称
- **严格加法**：不传时直接用传入 `context`（APS 当前做法：调用前自行装配好传入）

## 三、导出面

`run_spine` / `RedlineVerdict` / `evaluate_redline` 已在 `chiyu_decision.api.__all__`（api.py:18/20/21），
消费方经 sanctioned 面 `from chiyu_decision.api import run_spine, RedlineVerdict` 可直接使用，无需新增导出符号。

## 四、测试与判别力（`test_spine_injection.py`，5 例）

| 用例 | 判据 |
|---|---|
| `test_redline_callback_overrides_directory_match` | 回调返回未命中 ⇒ 即使 context 含目录词也不命中（回调替代目录） |
| `test_redline_callback_detects_domain_redline` | 回调基于域逻辑命中 ⇒ `redline_hit=True`（域红线生效） |
| `test_redline_callback_absent_uses_directory` | 不传回调 ⇒ 仍走目录匹配（严格加法回归） |
| `test_context_factory_assembles_before_s1` | `context_factory` 装配的 `decision_id` 被后续阶段使用 |
| `test_context_factory_absent_unchanged` | 不传工厂 ⇒ 直接用传入 context（严格加法回归） |

**变异自证**：删 `if redline_callback is not None:` 分支 ⇒ S4 两用例转红；删 `if context_factory is not None:` 分支 ⇒ S1 用例转红；还原 ⇒ 5 绿。判据有判别力，无假绿。

## 五、验收

- 注入测试：5 passed
- 组合回归（kernel + tools + decision + portal + examples + cli）：**749 passed / 0 failed**
- 提交：`T10` 代码 + 测试；`T11` 本收编文档 §5 落地标记

## 六、对 APS 的意义

APS 若要从自建 `KmdSpine` 迁移到统一 `run_spine`：
- `redline` 回调 `(draft, ctx) -> RedlineVerdict` 适配为 `redline_callback(context, redline_items)`（用 `partial` 注入 draft 等域状态）
- `ContextAssembler` 可适配为 `context_factory`（或维持调用前装配，两种都合规）
- tier 分档 + 强制人工在环等域逻辑仍在 APS 回调内，基座不持领域字面量
