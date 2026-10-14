# 回捐首批四模式·消费方采纳要求（foundation 指引 → CRM / APS / enterprise）

- 来源：enterprise 回捐首批（T60 处理回执已裁定：①登记通用判据候选②确认同构③④采纳入 foundation 判据编写规范）
- 日期：2026-10-12
- 目的：把四模式从"回捐记录"变成三仓**可机检的例行判据**——每条模式映射到各仓真实表面，附验收判据与排期挂钩点
- 纪律：foundation 指引落本仓；CRM/APS 分册投放各自仓 docs/；enterprise 为模式来源方，按 T60 裁定维持（本册不另投）

## 四模式通用判据（三仓共担）

| # | 模式 | 通用判据（一句话） |
|---|---|---|
| M1 | 注册面完整性（handler+catalog 双注册） | 凡新增 mutating 动作/回调/MCP 工具，必须同时落**静态差集守卫**（注册表 vs handler 目录），漏登一侧即红 |
| M2 | E2E 深于纯函数判据 | 验收类判据（P0/P1 整改、能力接线、场景迁移）必须以"**生产接线同面**"E2E 闭环，纯函数层判据不算闭环 |
| M3 | fixture 有效性自证先行 | 凡"命中类"fixture（红线/敏感词/闸触发/低置信度），先断言**命中非空**证明 fixture 真命中，再断言 verdict |
| M4 | 变异锚字面量 | 变异自证设计时**逐断言检查锚来源**：断言两侧禁止引用同一可变常量；判据锚用字面量或从权威源程序化提取 |

## 一、CRM（分册已投 `CRM-ai-native/docs/`）

| 模式 | 采纳面（仓内真实表面） | 要求动作 | 验收判据 |
|---|---|---|---|
| M1 | `src/action/seed-actions.js` 动作种子 vs `src/action/` handler 注册；MCP 网关工具清单 vs gateway handler | 新增 1 条 Node 守卫：种子目录 vs handler 差集扫描 | 守卫测试过绿＋变异自证（摘除一注册→恰红） |
| M2 | P2 场景迁移（26 键）验收；N1 映射层接线 | 每场景验收=影子台账对拍＋权威 sidecar E2E，映射层接线同面验证 | 迁移回执附 approval_shadow_log 五级输出 |
| M3 | 报价红线用例（margin_redline 等） | 命中类 fixture 先断言 `redline_reasons` 非空 | 守卫测试内可见自证断言 |
| M4 | 已自发采用（N1 守卫键集从源码提取） | 例行化：新守卫一律照此 | — |

## 二、APS（分册已投 `APS-ai-native/docs/`）

| 模式 | 采纳面 | 要求动作 | 验收判据 |
|---|---|---|---|
| M1 | `ActionDef` 目录（actions.py，surfaces 声明）vs handler 注册（sched_kmd_decide 已是双注册样板） | 新增 1 条 Python 守卫：ActionDef 目录 vs handler 差集 | 守卫过绿＋变异自证；10-20 双轨接线前落 |
| M2 | 10-20 双轨接线（kmd.py S5 拆轨）；10-27 中冶落库 | 接线验收=真编排同面 E2E（三路径 REJECTED/PENDING/APPROVED）；落库回执=真实业务周期 | 回执附 record_kind 双轨计数 |
| M3 | E5 重放判据、双轨测试夹具（红线/低置信度） | 夹具先自证命中 | spike/E5 判据内可见 |
| M4 | E3 突变测试已实践 | 例行化进判据编写 | — |

## 三、enterprise（模式来源方）

按 T60 裁定维持：V/U 编号新判据自查 M3/M4；E2E 同面常态两份判据（R-E4 样板）；复盘闭环上线后按月回捐行业级结论。

## 四、foundation 对应承诺

- M1/M3/M4 已入 foundation 判据编写规范（T60 处理回执为载体），foundation 侧新守卫同样遵循。
- 消费方若需注册面扫描类纯函数底元（如跨仓键集/目录差集比对），可经 RFE 通道申请。
- 验收复核沿用"来文→整改→foundation 实跑复核"通道；下次复核窗口随各仓既有节点（APS 10-20、CRM P2 开工、enterprise 月度回捐）。
