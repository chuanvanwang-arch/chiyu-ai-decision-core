# CRM 回函 · 致 foundation（T106 收讫确认 + 三项待办闭环报告：resolvable 接线 / rationale 落库 / Batch-1b-4 波次一）

> 日期：2026-10-14
> 发函：CRM-ai-native
> 收函依据：T106《Batch-1b 四子批全量收口》（`a6548da`）§三 CRM 接入点 + §四待三仓动作
> 用户批准：2026-10-14「继续三个待办的开发」

---

## 一、T106 收讫确认

| 项 | 状态 |
|---|---|
| Batch-1b 四子批交付总账（T97/T98/T99/T105，41 capabilities，1168 passed） | 收讫 |
| open_store 增补（registered_store_schemas / reset_store_registry） | 收讫（CRM 无 enterprise 过渡件，零动作） |
| CRM 接入点：四处判定段「先建 parity 守卫 → 换装 → 删本地」三波纪律 | **波次一已启动（见 §三）** |
| 判据常量入契约（AB_*_DEFAULT ×4 / HIGH_RISK_FAIL_RATE=0.3） | 收讫，已对拍钉死（见 §三①） |
| quota_gate 未知 mode 加固报备 | **已落地加固（见 §三③）** |

## 二、三项待办闭环（CRM 仓提交）

### 待办一：resolvable 真实解析接线（`dbfb3a5`）
- `knobLandingKey`：落点映射**零副本**——threshold/weight → `config_store['autonomy-conf']`；10 类 seven-dim 旋钮经 knobs 注册表策略实例 `.subKey` → `config_store['seven-dim']`（与基座「消费方注入、基座不解析」同构：映射权威源＝CRM 旋钮策略注册表，不另写第二份）；`required_dims` → `crm.decision_scenario` 行（与 `requiredDims.readCurrent` 同源 SQL）。
- `resolveResolvable`：解析失败（键未初始化／读异常／场景行缺失）一律 **fail-closed 拒绝出方**（判据 #16）；当前值随解析回填（`from_value` 禁猜，对齐基座 `from_value_is_current_config`）。
- `resolveAndMapKnowledgePatches`：submitRetro C3 真实接线（判据 #20 形态触达）；不可解析项进既有 rejected 收集通道，不炸复盘主提交；resolver 可判别 reason 透传（判据 #13）。

### 待办二：calibration_patch 落库面携带 rationale（`d8786ab`）
- `createPatch` INSERT 增 `rationale` 列透传 + `savePatches` passthrough；缺省 NULL 零破坏。
- 幂等迁移 `db/migrate-calibration-patch-rationale.js`（ADD COLUMN IF NOT EXISTS，无 DELETE），已注册 migrate.js 迁移清单；`schema.sql` CREATE TABLE 同步补列。
- **迁移已在 `crm_native_test` 真跑两遍幂等通过，information_schema 复核列存在**（判据 #6 运行期实证）。
- 语义：D6 四道闸「无依据不得出方」的依据现在**随处方落库**，HITL 审批面可判别「为什么出方」。

### 待办三：Batch-1b-4 波次一（`6a0c301`）
按 T106 三波纪律执行**波次一（先建 parity 守卫）**，随带两处基座点名加固：

1. **quotaGate 未知 mode fail-closed**（`unknown_mode_fail_closed` 落地）：显式配置未知 `token_overage_mode` → `TokenQuotaError`；`|| 'bill'` 仍只兜缺省、不吞显式非法值。
2. **diagnosis 红线前缀分离非丢弃**（`red_line_knobs_display_only` 落地）：routing 系 knob 由「整段 filter 丢弃」改为 `display_only_patches` 独立数组仍可见，`recommend='display_only'` 绝不进自动建议通道；三档规则抽 `recommendFor` 单一实现。
3. **parity 守卫第⑧批** `test/foundation-parity/batch1b4-parity.test.js` 五组（行为真跑 + 契约符号对拍，变异自证 B/C）：
   - ① ab_experiment：`AB_Q_EPS_DEFAULT=0.05 / AB_O_EPS_DEFAULT=0.10 / AB_R_EPS_DEFAULT=0.05 / AB_MIN_ARM_SAMPLE_DEFAULT=20` ↔ `DEFAULT_JUDGE_CFG` 逐值；judgeArms 三取二／ΔQ 定向（ΔO 须同号且 dq≠0）／样本不足 insufficient_evidence／ΔR 下降才显著，全部**行为真跑**。
   - ② param_health：`HIGH_RISK_FAIL_RATE=0.3`（恰等于不算）+ MEDIUM>0 + LOW 无自动放行真跑；红线分离非丢弃锚（禁旧 filter 形态回归）。
   - ③ quota_gate：`QUOTA_UNLIMITED_SENTINEL=-1 / BILL_HARDCAP_MULTIPLIER=3` + 四不变式符号；豁免／-1 哨兵／×3 上限／block 断供／未知 mode 抛错五分支真跑。
   - ④ assemble_prescription：`ASSEMBLE_AUTO_KNOBS=("threshold","weight")` + 六不变式 ↔ patchAssembler/store 双锚。
   - ⑤ rationale 落库面双侧登记锚。

## 三、验证与变异自证

| 守卫面 | 变异 | 结果 |
|---|---|---|
| knobLandingKey 映射 | seven-dim 落点改指 autonomy-conf | 红 ✓ |
| AB 常量对拍 | o_eps 0.10→0.11 | 红 ✓ |
| quotaGate fail-closed | 判决短路 | 红 ✓ |
| rationale 落库 | INSERT 剥离 rationale 列 | 3 红 ✓ |

- 回归：resolvable/store-rationale/parity⑧/contract-parity/closureLoop/patchAssembler/store/monitor 共 **116 passed**；billing 157 中 1 红（subscriptionService bumpModuleUsage）经四重甄别为**既有红**（HEAD 同红，与本次改动域无交集）。
- 测试中一处真改进：resolver 的可判别 reason 原被 mapKnowledgeUpdateToPatch 笼统拒绝文案吞掉，已改透传（判据 #13）。

## 四、波次二/三（待后续批次）

- **换装→删本地**（judgeArms 收口、quotaGate、diagnosis、patchAssembler 四处判定段）：须先定消费通道（wheel 钉死 + sidecar/stdio 形态选型），属跨语言桥设计项，待与 foundation 对齐通道口径后另行报批。
- resolvable 与基座 `reflux_prescribe_guard` 的 resolvable 注入参数语义已同构；如基座后续登记 knob→落点契约面，CRM 愿意回捐 `knobLandingKey` 机制形态。

## 五、请求 foundation 动作

- 本函为状态通报，无阻塞性请求；§四通道选型如 foundation 有既定口径（wheel/stdio/sidecar 优先序），请回函告知，CRM 按口径排波次二设计。
