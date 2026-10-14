# foundation 回函 · 致三仓（Batch-3：跨仓包级去重启动函）

> 回函对象：CRM-ai-native / APS-ai-native / chiyu-enterprise
> 事项：Batch-3（跨仓包级去重）**foundation 侧已就绪**：只读盘点完成 + 原清单 12 项就绪核验 **12/12** + 唯一缺口（llm provider）已补齐（T93 `dd501da`）。施工图见 `docs/2026-10-14-Batch-3-跨仓包级去重规格(盘点+就绪核验+三仓接入施工图).md`（T94 `136b16b`）。
> 边界纪律不变：本仓不向你仓写任何产物；切换动作由你仓自完成，**每删一处跑一处 parity 守卫全绿即收口，禁保留第二事实源**。

---

## 一、盘点结论（一句话版）

- **APS**：foundation 消费浅（仅 5 文件），本批主体 = GAP-6~9 五模块 + 六大契约域词汇，共 **11 项待切换**；域值（`aps.*` 事件/DDL/域键白名单/域真值表/psycopg3 接线/legacy_aps 连接器/scenario_packs 域包）全部留你仓。
- **enterprise**：已深度消费（52 文件、import 面零违规），原清单 12 项中 9 项已完成采用；本批只拆 **4 处残留 + 1 处回赠**。
- **CRM**：无需删本地件（你是源）；你的 parity 测试即跨仓对拍基准，foundation 机制一有变更你即哨兵。

## 二、T93 已落地：llm provider 补全（enterprise 回赠收敛）

- 你的 `llm/openai_compat.py`（85 行真实现）已上迁为 `chiyu_kernel.llm.openai_compat`：`OpenAICompatProvider` / `http_sender` / `parse_tool_calls`，纪律原样保留（空 api_key fail-closed / sender 注入零真网 / api_key 只过内存 / 畸形 tool_calls 空 args 不抛不猜）。
- `DeepSeekProvider` 由 NotImplementedError 桩升为真实现（委托同一类，**禁两套 HTTP 逻辑**）；`build_provider` 补 `openai` 分支（显式 model，不吃 tier 回落——档位表 model 是 llama.cpp 部署名，禁冒充云端端点）。
- **enterprise 动作（E4）**：删本地 `openai_compat.py`，`platform_provider.py` 工厂改构造 foundation 类（租户凭据解析/ProviderSwitch 留你仓）；接口不变，你仓现有 llm 单测应直接全绿。

## 三、三波切换顺序与闸门

1. **第一波（A 类纯重造，先建守卫后删）**：APS A1~A5（connectors 传输层 / promotion / reflux / feedback_loop / capability_audit——机制刚上迁、parity 锚点最新鲜）；enterprise E1（删 `tenant/store.py` 双键层 + host 两处回避，T86 已修根因，收益高风险低）。
2. **第二波（聚合段/词汇对拍，零行为变更）**：enterprise E2（rubric 聚合段改消费 `score_rubric`，逐尺域启发式保留）/ E3（审批核态改消费 `APPROVAL_CORE_STATES`+扩展规则）；APS A7~A10（context/embedding/llm/orchestration 契约词汇对拍）。
3. **第三波（回赠收口）**：enterprise E4（T93 已就绪）/ E5（host CRM 种子残留外置核查，多为注释级，不阻塞）。
4. **闸门**：每项 = ① parity 守卫先绿后删 ② 该仓全量回归绿 ③ 回函标注完成项。**删而不切 = 断链，切而不删 = 双源**，两者都算未收口。
5. **依赖**：若需增补契约闭集（档位表/后端集/回流 kind 等），先回函 foundation 修订并同步 manifest，再切换。

## 四、请三仓回复

- **APS**：确认第一波五项排期；对 A1 的 `legacy_aps` 自注册方案（`ConnectorRegistry.register` 后经 `default_registry()` 取用）有无异议。
- **enterprise**：确认 E1 切换窗口（需先同步 foundation ≥ T86）；E2 的聚合对拍基准是否以 APS `kmd.py` 现成消费形态为范本。
- **CRM**：确认九尺子聚合/审批五态/回流四通道的 parity 基准测试可作跨仓对拍源；如某项你的实现与 foundation 机制有语义差，请指出（以你为源修订 foundation，禁双源）。

## 五、状态

Batch-0 ✅ → 1a ✅ → 2a/2b ✅（T86/T88~T91）→ **Batch-3 foundation 侧就绪（T93/T94，三仓切换进行中）** → Batch-4/5 → Batch-6 → Batch-7；另 **Batch-1b（P0 去重收口其余：prov_chain/two_phase_token/rbac_core/standing_credential/approval_engine/patch_state_machine/shadow_replay 等）仍待启**，与 Batch-3 无依赖冲突，可并行。
