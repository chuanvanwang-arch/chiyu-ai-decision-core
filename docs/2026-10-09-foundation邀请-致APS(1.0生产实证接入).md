# foundation 邀请致 APS：1.0 生产实证接入

> 落本仓 docs 唯一事实源，不回写 APS 仓。回复请沿用既有回信机制。

## 背景

foundation 准备从 v0.1.0 升至 v1.0.0（发布判据见本仓 `docs/release/v1.0-发布判据.md`）。1.0 的硬门槛不是功能而是**生产实证**：需要消费方在真实负载下运行 ≥4 周、P0/P1 清零。APS 是就绪度最高的消费方——R2–R14 十三项（dsn env 注入、双形态校验、驱动解耦、门面稳定守卫、docstring 中性化等）本就是为 APS 的接入诉求落地的。

## 交付物（随 0.1.x 当前基线即刻可用）

| 交付物 | 位置/说明 |
|---|---|
| 双 wheel | `packages/chiyu-kernel/dist/` + `packages/chiyu-decision/dist/`（0.1.0，构建已实跑验证） |
| sanctioned 面 | `docs/sanctioned-import-surface.md`（含撞名清单）；兼容承诺仅覆盖五面 |
| 接入门禁 | `tools/check_import_surface.py`（APS 侧接入自跑，内部路径 import 即拦截） |
| 能力自检 | `require_capabilities([...])`（启动断言，勿用 hasattr 嗅探） |
| 使用指南 | `docs/release/v0.1.0-使用指南.md`（安装→自检→决策回路→三态续跑） |

## 请求 APS 做的三步

1. **切换消费形态**：从拷 src/对拍，切为 **wheel 安装 + 只 import sanctioned 面**（`chiyu_kernel.api` / `chiyu_kernel.contract` / `chiyu_kernel.approval` / `chiyu_decision.api`）。
2. **真跑替换对拍**：测试库从"结果对拍"切为真跑 `run_spine`（含审批闸注入、PENDING 三态、`resume_spine` 续跑）+ 真库落库读回。
3. **证据回传**：按判据 §2 采集——接入回执、缺陷台账、真库场景用例（可回流本仓作 `@pytest.mark.pg`）、SLO 实测。

## 证据约定

- APS 侧**测试环境**真跑即可计入证据（不必是生产）；真库用便携 PG `chiyu_test`，⛔ 绝禁指向生产实例。
- 窗口内发现的缺陷按 SLA 分级（P0 ≤1 工作日响应）；回执与台账落 APS 仓或回信均可，foundation 侧收编存档。
- 若窗口内有 0.1.x 升级，望配合走一次升级演练（判据 §2-4）。

## 边界

- R7 MCP 真 transport 维持既有裁定：APS 自实现，foundation 不排期。
- 本邀请不改变既有约定：对消费方的建议/回信一律落 foundation 仓 docs。
