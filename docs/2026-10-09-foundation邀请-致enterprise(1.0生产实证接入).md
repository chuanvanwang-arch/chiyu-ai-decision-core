# foundation 邀请致 enterprise：1.0 生产实证接入

> 落本仓 docs 唯一事实源，不回写 enterprise 仓。回复请沿用既有回信机制。

## 背景

foundation 准备从 v0.1.0 升至 v1.0.0（发布判据见本仓 `docs/release/v1.0-发布判据.md`）。1.0 硬门槛 = 消费方 wheel 化接入 + 真实运行证据。enterprise 三轮反馈（B1–B3 / N1–N7 / G2–G6+H1–H3 / R1–R3）已全部落地——本轮邀请是把既有"评审对拍"关系升级为"版本化消费"关系。

## 交付物

| 交付物 | 说明 |
|---|---|
| 双 wheel | `chiyu-kernel` 0.1.0 + `chiyu-decision` 0.1.0（B2 裁定：交付面独立分发，构建件由 enterprise 仓配套） |
| 构建配套 | `prep_build_context` 路径 + decision wheel 进 dist（T17 已落） |
| 接入门禁 | `tools/check_import_surface.py`（接入自跑；易冲突名清单见 sanctioned 面文档） |
| 能力自检 | `require_capabilities` + `contract/capability-manifest.json`（29 项机器可读，R1） |
| 发布包四件套 | SLA / 接口参考（机械生成零漂移）/ 使用指南 / 发布说明，见 `docs/release/` |

## 请求 enterprise 做的三步

1. **clean-room 安装**：新 venv `pip install` 双 wheel → `require_capabilities(["decision","persist","approval","store","contract","canary"])` 冒烟（此步同时是 foundation 发布闸的验证项）。
2. **试点场景真跑**：选一个真实业务场景走通 `run_spine` → 审批闸 → 三表落库 → 读回/图视图；只 import sanctioned 面。
3. **证据回传**：接入回执 + 缺陷台账；若窗口内有 0.1.x 升级，配合一次升级演练。

## 证据约定

- enterprise 侧**测试环境**真跑即可计入证据；真库用便携 PG `chiyu_test`，⛔ 绝禁指向生产实例（`81.70.184.198` 红线不变）。
- 缺陷按 SLA 分级响应（P0 ≤1 工作日）；回执落 enterprise 仓或回信均可，foundation 侧收编存档。

## 边界

- 历轮裁定不变：B2 构建件归 enterprise 仓；`memory` / `evolution` 维持 experimental，排除出 1.0 兼容承诺。
- 本邀请不改变既有约定：对消费方的建议/回信一律落 foundation 仓 docs。
