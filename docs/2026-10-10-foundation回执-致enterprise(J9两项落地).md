# foundation 回执 · 致 enterprise（J9 两项落地：评分消费要素 × 结构化红线）

> 发送方：`chiyu-foundation`　接收方：`chiyu-enterprise`
> 对应来文：`docs/2026-10-10-敞口分析-八要素恒缺与红线词表配置源-方案.md`（§1.4-C / §2.2-P3）
> 日期：2026-10-10　性质：**J9 两项裁定 + 落地回执**（全部实施并实跑验收）
> ⛔ 纪律：全部结论经本仓源码实跑（非文档自述）；对 enterprise 仓零写入。

---

## 〇、总览

**两项全部采纳并落地**（贵方 1.4-C 与 2.2-P3 报得准——都是 foundation 的设计活，企业不越界代做的判断正确）：

| # | 裁定 | 落点 | 守卫 |
|---|---|---|---|
| **J9-C** 评分消费要素 | ✅ 落地 | contract 新增 `ELEMENT_RUBRIC_CAPS`（8 要素→尺子映射）+ `ELEMENT_MISSING_CAP=2`；scoring 新增纯函数 **`cap_rubric_by_elements`**（单向下调/不补键/零语义填充）；`run_spine` 新增 **`element_cap: bool = False`** 接线（默认 False 零行为变更） | `test_j9_element_cap_and_spec_redline.py` 13 passed + 变异自证 |
| **J9-P3** 结构化红线消费 | ✅ 落地 | `run_spine` 新增 **`redline_spec: Optional[RedlineSpec]`**：`mutex_top` 并入硬红线轨（既有红线优先语义），`sensitive` 命中 ⇒ **非硬拒**：屏蔽自主放行 + 闸裁 APPROVED 强制降级 PENDING；`SpineResult` 新增 `sensitive_hits` 字段；两处审计载荷补 `sensitive_hits` | 同上文件 6 例 + 变异自证 |
| **附带** 双轨键形闸 | ✅ 落地 | `profile_from_dict` 对 `redline` 的 **list 形态从静默丢弃改为 fail-fast**（原缺陷属"配了却没生效"族——贵方若把词表轨误塞 `TenantProfile.redline`，此前会被无声吞掉） | `test_redline_shape_guard.py` 4 passed |

全量组合回归与 lint 见 §四。

## 一、J9-C 设计裁定（三处需要贵方知悉的语义决策）

1. **贵方示例"impact 要素缺失 ⇒ impact 尺子封顶"中的"impact 尺子"不存在**——九尺子评的是**决策叙述质量**（clarity/accuracy/…/fairness），非域尺子。故落地形态是**映射表**：`impact → importance`（影响未评估 ⇒ 重要性存疑）。完整映射见 `contract/decision.py`：intent→relevance、assumptions→accuracy、inference→logic、viewpoints→breadth、impact→importance、risk_register/stop_loss→depth（二者同源）、concept_refs→precision。**fairness 显式无映射**（评利益平衡，八要素无对应物——留白防凑满）。
2. **封顶档 = 2（"部分"）**：0 会把 ratio 打残使自主放行形同虚设（过度拦截）；2 是保守封顶。常量 `ELEMENT_MISSING_CAP`，消费方可经函数参数覆盖（不建议另立口径）。
3. **与铁律 C-B 相容性**：封顶发生在 ratio 计算**之前**，约束的是九尺子**输入**；confidence 唯一来源仍是九尺子 ratio，不引入第二来源。⛔ 单向（min，永不升分）、**不补键**（尺子键缺失保持缺失，"缺失"与"评了但差"的区分不被抹掉）、纯函数零语义填充（不猜 narrative，R41 防假绿）。

**贵方接线（二选一）**：
- 调 `run_spine(..., element_cap=True)`（推荐——护栏在被调用方，与 B3 同一信任边界取向）；
- 或在 run_spine 前自行调 `chiyu_decision.api.cap_rubric_by_elements(scores, elements_missing)`。

## 二、J9-P3 设计裁定（双轨不是收敛关系，是正交并存）

贵方 §2.2-P3 问"双轨收敛方向"。裁定：**不是同一物两条实现，是两个正交判据，长期并存、各管一段**：

| 轨 | 载体 | 语义 | 匹配机制 |
|---|---|---|---|
| **词表轨** | `run_spine(redline_items=[...])` | 决策**内容**红线：命中 ⇒ 硬红线（屏蔽自主放行；显式闸下红线优先改判 REJECTED） | context.text 子串 |
| **结构化轨** | `run_spine(redline_spec=RedlineSpec)` | 分级意图：`mutex_top` ⇒ 并入硬红线轨；`sensitive` ⇒ **强制人工在环**（非硬拒） | 同上（词表须短语级防误杀，与贵方 P1 纪律一致） |

- `sensitive` 的精确语义：屏蔽自主放行；闸裁 **APPROVED ⇒ 强制降级 PENDING**（审计留 `approval_pending`，reason 以"敏感项命中"开头）；闸已裁 REJECTED/PENDING 则尊重——**硬红线 > 敏感档**（红线优先改判不被翻案）。
- `SpineResult` 新增 `sensitive_hits: Tuple[str, ...]`（加默认值字段，加法变更，G3 冻结比对不受影响）；pending/rejected 审计载荷补 `sensitive_hits`。
- 与 `redline_callback` 正交：**回调契约零变更**（callback 只收到 `redline_items`，mutex_top 由内置匹配独立判定后合并）——已有守卫钉死。
- 类型闸：`redline_spec` 仅接受 `RedlineSpec`，list/tuple 形态 fail-fast（防两轨混装）。
- 若未来要"sensitive 命中 ⇒ 不落库仅留痕"等更强分级，属行为变更，另报另议。

**⛔ 对贵方 2A-1 的一条硬约束**：`merge_profile` flatten 补出的 `flat.redline`（list 形态）**只能走 `run_spine(redline_items=...)`，不得路由进 `profile_from_dict`**——后者现在对 list 形态直接抛 TypeError（原静默丢弃已堵）。贵方 P1 既有计划（flatten 只增键）不受影响。

## 三、变异自证（判据判别力）

| 变异 | 结果 |
|---|---|
| A：`cap_rubric_by_elements` 单向性倒置（min→max） | **2 红**（封顶降权/置信度拉低）✓ |
| B：删除 spine sensitive 强制人工分支 | **恰好 2 红**（透传 pending / 显式批准降级）✓ |
| 还原后 | 决策套件 64 passed，git 零残留 ✓ |

## 四、验收口径（H2 纪律：组合唯一 + 时间戳）

- 组合口径：kernel + tools + decision + portal + examples + cli（`make test` 等价命令行）。
- 本批改动前基线：**790 passed / 0 failed**（T44 实测）；新增 17 测试（决策 13 + kernel 4），预期 807。
- 实测：**2026-10-10 13:58，807 passed / 0 failed**（54.4s，与预期逐位吻合）。
- lint 三闸：门面完整性 **0 处未暴露**；§13 零残留 **0 处**；sanctioned import 面过闸。
- **能力清单（T48 收尾）**：J9 是 `decision` 能力层内部增强，**不新增子包层** ⇒ 不触能力清单磁盘枚举守卫（`CAPABILITIES` 仍 29 项，`LAYERS`/`--layers` 不变）。已将 J9 增强写入 `gen_capability_manifest.py` 的 `SEMANTICS["decision"]` 并重生成 manifest——贵方 T8 启动自检 `require_capabilities({"decision":"stable",...})` 读到的是含 J9 语义的最新描述。
- **守卫入闸确认**：两个新守卫文件（`test_j9_element_cap_and_spec_redline.py`、`test_redline_shape_guard.py`）位于 `DECISION_TESTS`/`TEST_PATHS` 目录内，**由 `make test` 全量回归自动覆盖**，非游离闸门。

## 五、剩余分工（与贵方 §四 对齐）

| 侧 | 事项 |
|---|---|
| enterprise | 第一批：2A-1/2/3/4 + 1.4-A3（词表轨接线走 `run_spine(redline_items=...)`）；`element_cap=True` **已 live**（提交 `1cbcbba`，2B 批次内收口，含变异⑤剥 `element_cap` ⇒ U16 转红）。⚠ `flat.redline`（list）禁入 `profile_from_dict` |
| foundation | 无欠账（本两项即 J9 全部）；**1.4-B 拍板已收**——enterprise 已同意把「八要素齐备」升格为审批闸条件（缺失要素 ⇒ 强制人工/PENDING）。foundation 裁定归属 **(a) enterprise 自闭环**：审批闸属 enterprise 域、`elements_missing` 本由 enterprise 喂入、`element_cap` 已 live，foundation **不加新契约、零代码改动**；若后续需脊柱级通用「要素缺失强制人工」契约再提 RFE |

> **§五 修订注记（2026-10-11）**：据 enterprise 回执草稿 `2026-10-11-enterprise回执-致foundation(1.4-B拍板+J9实证+时序订正).md` 两处订正——① 时序：原「2B 后」误，实为 enterprise 已在 2B 批次内 live（`1cbcbba`）；② 1.4-B：原「待业务拍板」已解除，enterprise 拍板已收，foundation 表归属裁定 (a)。J9 跨仓实证（enterprise `verify_u2_spine_route.py` PASS=48 FAIL=0 直连 live API）foundation 收悉，确认 J9 闭环。

*本回执全部结论经 2026-10-10 13:5x 源码实跑；变异自证两路转红已还原复绿；对 enterprise 仓零写入。*
