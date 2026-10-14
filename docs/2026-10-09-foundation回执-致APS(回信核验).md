# foundation回执：致APS《对〈2026-10-09-客户建议逐项回顾〉的核验回执》

> 日期：2026-10-09
> 致：APS-ai-native 平台负责人
> 事由：回复贵方《APS-回执-致foundation（2026-10-09客户建议逐项回顾）》
> 立场：贵方三项独立观察与三项新需求 N1–N3，**均经本仓源码复核成立**；我方对 N1–N3 逐项裁定。
> 本文件落 `chiyu-foundation`（唯一事实源）；未回写 APS 仓库。
> 复核纪律：以下每项裁定均带本仓 `file:line` 反证；「以 `file:line` 反证，APS 即改」对等口径适用。

---

## 0. 结论摘要

| 项 | 贵方诉求 | 我方裁定 |
|---|---|---|
| §2.1 ONNX 4 失败环境依赖 | 标注/说明 | ✅ **确认环境基线**，见 §1.1 |
| §2.2 facade 测试已转绿 | 更新回顾 §4 遗留项 | ✅ **确认**，已更新回顾文档 §4 |
| §2.3 tokens 路径勘误 | `packages/chiyu-kernel/tools/` → `tools/` | ✅ **确认属实**，见 §1.3 |
| **N1** 门面补 `ns()` 或易冲突名清单 | 二选一 | ✅ **接受补"易冲突名清单"**（§2.1），`ns()` 暂不加 |
| **N2** store/api 登记一致性单测 | 加断言 | ⚠️ **已被 R12 机械推导更严格覆盖**（§2.2），认可其 intent，补充显式一致性断言 |
| **N3** `connect()`/`shared()` 统一走 `connect_factory` | `shared()` 透传 | ✅ **接受**（§2.3），纳入待办批次 |

---

## 1. 对贵方三项独立观察的确认

### 1.1 ONNX 4 例失败 —— 确为环境基线，非改造回归

贵方实测 `4 failed, 535 passed`，失败均为 `test_offline_onnx_backend.py` 的 `test_auto_picks_local_onnx`
等 4 例，原因 ONNX 模型文件缺失。**判定与贵方一致**：属环境依赖，非 R2–R14 引入。

- 本仓 `models/` 下确需 `bge-small-zh-v1.5/model.safetensors` + `tokenizer.json` 才能跑通；
  模型由 `tools/export_bge_onnx.py` 在本地生成（`--check-only` 验证 cos≥0.9999），**不入库**（`models/**/*.safetensors` gitignore）。
- **处置**：接受贵方建议 —— 在 `README.md` 单测章节注明 `test_offline_onnx_backend.py` 需先
  `python tools/export_bge_onnx.py` 生成/验证模型，否则 4 例环境依赖失败属预期。详见 §3 待办 2。

### 1.2 `test_consumer_facade_stability.py` 已转绿 —— 更新回顾 §4

贵方在规范解释器实测 `4 passed in 0.48s`，确认该文件已通过（应系并发会话修正）。我方据此**更新
`docs/2026-10-09-客户建议逐项回顾.md` §4 遗留项表**，将该项从"2 失败待修正"改为"已解决"。

### 1.3 `zero_residue.tokens` 位置勘误 —— 确认属实

贵方勘误正确：**`tools/zero_residue.tokens` 位于仓库根 `tools/`**（非 `packages/chiyu-kernel/tools/`），
且内容已含 `违约 / 内部路径 / 内部路径即违约` 3 token（R5 补）。我方回顾文档 §2.9 表述不精确，
已修正为指向仓库根路径。感谢按图索骥式复核。

---

## 2. 对贵方 N1–N3 的裁定

### 2.1 N1（中）—— 门面补 `ns()` 命名空间出口 或 易冲突名清单

**裁定：接受"易冲突名清单"，`ns()` 暂不加。** 理由：

1. **`ns()` 会新增一个"容器符号"，与 sanctioned 面"显式导出真实符号"的纪律张力。** 门面的价值是
   让消费方 `from chiyu_kernel.api import <真实名>` —— 若引入 `ns` 容器，等于给"扁平名冲突"开一个
   旁路出口，会稀释门面对符号的审计（R12 守卫按真实符号登记，`ns` 内对象不在守卫覆盖）。
2. **APS 所述场景的根本解是"冲突名清单 + 机械门禁"**，而非提供旁路容器：消费方真正需要的是
   "知道哪些符号容易和自己的域取值撞名"，从而选择是否降级为命名空间导入。这靠**文档 + 门禁**解决。

**落地方案（采纳贵方建议二并加强）**：
- `docs/sanctioned-import-surface.md` 新增一节 **"易冲突名清单"**，逐条列出会与常见消费方域取值
  （`Particle` / `normalize` / `canonical` / `LAYERS` / `ATTR_TYPES` / `vector` 层 `available/embed` 等）
  同名/近义的门面符号，并标注建议用法（扁平导入 or 显式重命名）；
- 在 `tools/check_import_surface.py` 门禁中登记这批"高风险同名符号"，当消费方按扁平名导入时给出
  **警告级提示**（非阻断），使"靠踩坑总结"变为"导入即提示"。

**验收判据**：① 文档含冲突名清单节且每项有建议；② 门禁对清单中符号的扁平导入产生可见提示
（变异自证：删清单一项 ⇒ 门禁对该符号提示消失）。

### 2.2 N2（低）—— store/api 登记一致性单测

**裁定：认可该诉求，但需说明 —— 该缺口已被 R12 以更严格形式覆盖。**

贵方建议 `set(store.__all__) ⊆ set(api.__all__)` 且改名映射一致。核验本仓 `test_api_facade_covers_all_layers.py`：

- `:35-43` `store_public_symbols()` **从 `store.__all__` 机械推导**（不再人工枚举 `STORE_REQUIRED`）；
- `:117 test_facade_covers_store_required_symbols`：`store` 公共符号缺失于 `api.__all__` 即红；
- `:129 test_store_all_equals_submodule_union`：`store.__all__` 与子模块并集不一致即红（防"从 `__all__` 删项绕过"）；
- `:159 test_guard_discriminates_a_missing_symbol`：反假绿（故意删符号必须转红）。

⇒ **`set(store.__all__) ⊆ set(api.__all__)` 已是 `:117` 的判据**，且机械推导比"人眼对照两文件"更牢固
（新增 store 符号忘记同步即红，无需人工维护白名单）。贵方担心的"两处人工对照漂移"已不复存在。

**响应**：采纳贵方加强意图 —— 在 `:117` 测试补一条**显式映射一致性断言**：`store.__all__` 中每个符号
在 `api` 处的导入名与 `store` 同名（防改名映射断裂）。此为增量加固，非解决已存在缺口（缺口已被 R12 覆盖）。

### 2.3 N3（低）—— `connect()`/`shared()` 统一走 `connect_factory`

**裁定：接受，纳入待办。** 核验属实：

- `connect()`（`store/conn.py:183-215`）支持 `connect_factory` 注入（`:185`）；
- 但 `shared()`（`:218-230`）内部 `conn = connect(dsn=dsn, schema=schema)`（`:228`）**不传 `connect_factory`**，
  且 `:220` 仍直接检查 `_pg is None` ⇒ psycopg3 下进程级单连接无法复用隔离机制。

**落地方案**：`shared(*, testing=None, connect_factory=None)`，内部把 `connect_factory` 透传给 `connect()`；
`:220` 的 `_pg` 守卫改为"仅当未传 `connect_factory` 时检查"（传入则跳过内建驱动可用性检查）。
**严格加法**：不传时行为与现状完全一致。

**验收判据**：注入 fake `connect_factory` 调 `shared()` ⇒ 单连接由此 factory 建立（而非内建 `_pg`）；
变异自证：删透传 ⇒ 断言转红。

---

## 3. foundation 侧待办（对贵方四项遗留项 + N1/N2/N3）

| # | 事项 | 归属 | 处置 |
|---|---|---|---|
| 1 | R7 MCP transport 无排期 | APS/foundation | 维持：不建议 APS 等待，按自实现推进 L3；实现后愿回馈即采纳为默认 |
| 2 | ONNX 测试环境基线 | foundation | ✅ **已落地** T9d（`562be5d`）：`README.md` 注明需先 `export_bge_onnx.py` 生成模型 |
| 3 | 回顾 §4 遗留项表更新 | foundation | ✅ 已更新（facade 测试转绿） |
| 4 | §2.9 tokens 路径勘误 | foundation | ✅ 已修正为仓库根 `tools/` |
| 5 | **N1** 易冲突名清单 | foundation | ✅ **已落地** T9c（`66b6990`）：`sanctioned-import-surface.md` §6 成文 + 门禁 `CONFLICTING_NAMES` 机械提示（警告级不阻断），单测 9 绿 + 2 变异转红 |
| 6 | **N2** store/api 映射一致性断言 | foundation | ✅ **已落地** T9b（`f58c3e2`）：`test_facade_covers_store_required_symbols` 后补同名同对象断言，判别力模拟错绑已验证 |
| 7 | **N3** `shared()` 透传 connect_factory | foundation | ✅ **已落地** T9a（`f8a6337`）：`shared(*, testing, connect_factory)` 严格加法透传，变异自证删透传 2 红→还原 12 绿 |

> 待办 5/6/7 已按 TDD（失败测试→实现→变异自证→组合回归）落地；组合回归 **699 passed / 0 failed**（T9a–T9d 后复跑确认）。

---

## 4. 对贵方 §三/§五的确认

- **§三 职责边界**：认同"能力出口在基座侧、消费在 APS 侧，各守各仓"。贵方 L0–L4 分层采纳计划我方无异议，
  尤其 **A2 必须后于 A3（红线通电）** 的依赖论证成立 —— 这与基座"护栏判据放被调用方"纪律同源：
  `judge_worthiness` 依赖 `redline_hit` 输入，红线不通电则第一道闸结构上不可触发。贵方把 A2 从 P1 后移正确。
- **§五 L0 切 `aggregate_confidence` + D1 更新理由 + U1 注释 / L1 A3+A4+U4 / L2 A2-minimal / L3 A5 / L4 A1**：
  全部接受，无异议。唯 L1 内提醒一处（此前已提，复述）：`dispatch` 接入 `security.require()` 时应
  **同步接入 `Principal` 来源**，否则 `enforced` 档因主体不明而全量拒绝。

---

## 5. 复核记录（本仓侧）

| 批次 | 结论 |
|---|---|
| 收回报执后复核（10-09） | 三项观察全部成立；N1 采纳"易冲突名清单"路径、N2 已由 R12 覆盖、N3 接受待办。N1/N2/N3 均经源码 `file:line` 确认 |

> 声明：本文件所有裁定均基于本仓源码实测快照。贵方若对任何裁定有异议，请以 `file:line` 反证，我方即改。
> 本仓完成待办 5/6/7 后，将更新本文件状态并回告。
