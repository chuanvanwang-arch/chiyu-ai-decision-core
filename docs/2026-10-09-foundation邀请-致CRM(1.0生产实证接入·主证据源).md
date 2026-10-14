# foundation 邀请致 CRM：1.0 生产实证接入（主证据源）

> 落本仓 docs 唯一事实源，不回写 CRM 仓。CRM 是 1.0 判据的**主证据源**——唯一拥有生产环境与真实决策流量的消费方。

## 背景

foundation 准备从 v0.1.0 升至 v1.0.0（发布判据见 `docs/release/v1.0-发布判据.md`）。判据 §2-2 的硬门槛"真实负载 + 真库下连续运行 ≥4 周、P0/P1 清零"只有 CRM 生产环境能提供。APS/enterprise 走测试环境证据，**CRM 才是决定 1.0 时点的消费方**。

## 为什么对 CRM 划算

1. **红线能力直接受益**：零硬删除拦截（store 层可执行）、BANT 阶段门控对应的审批闸三态（PENDING 不落正边）、MCP 写入两阶段 confirm token——均为 CRM 关心的治理件；
2. **升级路径有保障**：wheel 化接入后，sanctioned 面 semver 冻结 + deprecation 政策生效，CRM 的升级成本从"重验全库"降为"跑兼容断言"；
3. **成本可控**：不需要改业务语义，只替换底座接缝（决策/落库层）。

## 接入三步

1. **试点接缝**：选 CRM 一条真实决策链路（建议报价审批流——与三态审批闸天然对应），以 wheel + sanctioned 面（`chiyu_kernel.api` / `chiyu_kernel.contract` / `chiyu_kernel.approval` / `chiyu_decision.api`）替换现有接缝；生产库隔离红线不变（开发/测试环境绝禁指向 `81.70.184.198`）。
2. **生产灰度**：试点链路生产运行 ≥4 周；期间照常使用，只多记一份缺陷台账。
3. **证据回传**：接入回执 + P0/P1 台账 + SLO 实测（spine 延迟/落库吞吐）+ 一次 0.1.x 升级演练；真库场景沉淀为 `@pytest.mark.pg` 用例回流本仓（参照 `packages/chiyu-kernel/tests/test_pg_e2e.py` 范式）。

## foundation 侧承诺

- 试点期缺陷按 SLA 响应（P0 ≤1 工作日）；
- 每轮回信/回执落本仓 docs，缺陷修复带变异自证测试；
- `memory` / `evolution` 维持 experimental，不进入 CRM 试点范围（划界明确，试点面最小化）。

## 判定

CRM 试点窗口满 4 周 + P0/P1 清零之日 = v1.0.0 打 tag 之时（详见判据 §5 速查表）。
