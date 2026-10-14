# foundation 批次三毕业回函 —— evolution 层 experimental → stable（致三仓）

> 致：CRM / APS / enterprise
> 自：chiyu-foundation
> 日期：2026-10-13 ｜ 提交：T78 ｜ 依据：三大支柱解决方案（T74=1231caf）· 详细设计（T75=ccebca0）· 批次一（T76=6ed82ae）· 批次二（T77=0faadc0）
> 主题：**支柱③自我进化毕业**。至此三支柱基座面（②安全/HITL → ①决策闭环 → ③进化）全部转入 1.0 兼容承诺，CAPABILITIES 29 层全 stable、无 experimental 层。

---

## 一、毕业事实（一句话）

`evolution` 能力层自 2026-10-13 起转 **stable**，进入 **1.0 兼容承诺**——此后任何 BREAKING 变更必须先走完整 deprecation 周期（先 warn 一版再移除，`docs/versioning-and-deprecation.md`）。**对外表述不再需要声明实验态**；历史上把 evolution 当 experimental 处理的消费方分支须同步更新。

## 二、验收判据（全部机检，变异自证双向）

| 判据 | 内容 | 结果 |
|---|---|---|
| **readiness 十闸** | §12.3 七正确性闸（影子重放空样本即拒 / 拒绝出方守卫 / 事务原子逆写回滚 / 预算+熔断+冷却 / 全链审计防篡改+一键回滚 / verdict 机器可读 fail-safe / 幂等+系统锚）+ §12.4 G1/G2/G3 护栏（放宽永不自动 / 红线命中挂起 / 基线与 L0 物理只读） | **10/10 绿，10/10 含对抗输入判别力** |
| **测试面** | 7 个 evolution 测试文件（knob/replay/prescription/guard/readiness/chain/skill_draft） | 全绿 |
| **毕业守卫** | `test_evolution_graduation.py` G1–G5：CAPABILITIES 翻转且全清单无 experimental / `EVOLUTION_EXPERIMENTAL` 机器可检出口 / require_capabilities 双向判定 / readiness 十闸持续复验 / 门面符号 identity 抽查 | 5/5 绿 |
| **变异自证 A** | 状态回翻 experimental → 毕业守卫 2 判据转红 → 还原复绿 | ✓ 抓到 |
| **变异自证 B** | `EVOLUTION_EXPERIMENTAL=True` 误置 → G2 转红 → 还原复绿 | ✓ 抓到 |
| **全量组合回归** | junitxml 权威计数（875 基线 + 毕业守卫增量，零失败） | 见提交信息 |

## 三、机检形态（对齐 T44 memory 毕业同族，消费方零猜测）

1. **状态出口**：`capability_status("evolution") == "stable"`（`chiyu_kernel.version`）。
2. **标志出口**：`api.EVOLUTION_EXPERIMENTAL is False`（进 `api.__all__`；与 `MEMORY_EXPERIMENTAL` 同形态并存）。
3. **闸哨兵**：`require_capabilities({"evolution": "stable"})` 通过；`require_capabilities({"evolution": "experimental"})` **必抛 RuntimeError**（防毕业态被降级使用而无人知）。
4. **清单同源**：`contract/capability-manifest.json` evolution 条目同步 stable（`test_capability_manifest.py` 同源对账守卫持续保证——本条由全量组合回归抓到补齐，见"诚实申报"）。

消费方接线示例（替换原 experimental 宽容分支）：

```python
from chiyu_kernel.version import require_capabilities
require_capabilities({"evolution": "stable"})
```

## 四、对三仓的具体影响与接线建议

### CRM（icpSelfEvolution 同构收敛）
- CRM 回执确认 `icpSelfEvolution` 与基座 evolution 语义逐字同构（草稿→回测→HITL→生效）。毕业后建议：**把自研同构管道的对外承诺切换到基座 stable 面**（`SkillDraft.validate_draft/promote` + `shadow_replay` + `readiness_report`），保留 CRM 侧 ICP 领域判据为上层扩展，不再自维护第二份状态机判据表。
- 批次二 `assert_hitl_evidence`（无 approve 不可生效结构保证）与本次毕业组合：进化生效链的 HITL 闸在基座已 stable 可用。

### APS（reflux C3 处方通道）
- reflux C3（处方 PENDING）对基座 `Prescription` 状态机（begin_replay → apply_atomic 事务原子 → roll_back 一键回滚）的映射已具备 stable 承诺；G1（放宽永不自动）与 G2（红线命中挂起）护栏随毕业进入 1.0 兼容——APS 三档模式（批次一 D2）× 基座进化护栏的组合语义可写入正式文档。

### enterprise（SkillDraft 消费面）
- `evolution/bridge.py` 消费 SkillDraft 的 experimental 标注同步过时：按本次毕业更新为 stable 口径（同该文件此前对 `MEMORY_EXPERIMENTAL` 的处理方式，改读 `EVOLUTION_EXPERIMENTAL`）。
- `require_capabilities` 启动自检（G5）可把 `{"evolution": "stable"}` 加入推荐必检集。

## 五、三支柱总账（基座侧收敛完成度）

| 支柱 | 基座交付 | 状态 |
|---|---|---|
| ② 企业安全 + 可审计可追溯 | 三档模式（off/advisory/enforced）+ HITL 证据三件套 + resume 证据契约 + assert 结构保证 + 审计 canonical schema/墓碑（批次一/二） | **stable，1.0 承诺** |
| ① 决策有效性 + 闭环追溯 | OutcomeRecord 结局契约 + 校准方向护栏（C-B 铁律）+ 有效性度量诚实降级 + IAM/RBAC 判定接口（批次一/二） | **stable，1.0 承诺** |
| ③ 自我进化（人工可控） | knob/replay/prescription/guard/skill_draft/readiness 全族 + readiness 十闸（**本次毕业**） | **stable，1.0 承诺** |

批次二回函中预留的 D8 排期至此闭合。后续基座侧仅剩：三仓接线对齐支持（按各仓节奏，不强制时限）与文档面统一口径修订。

## 六、诚实申报

- 变异自证执行过程中曾出现一次编辑现场与回显不一致（状态行短暂滞留 experimental），由解释器真值探查发现并按流程走完「变异→转红→还原→复绿」闭环；最终验收以 junitxml + `capability_status` 真值为准。
- 全量组合回归首轮曾抓到 `capability-manifest.json` 未同步（同源对账红）——正是「验收只跑组合命令」纪律的价值实证：局部守卫组 28 绿掩盖不了清单漂移。已补齐后复跑全量，权威计数见提交信息。
