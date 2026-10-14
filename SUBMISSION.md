# 企业级 AI 决策中枢 · ChiYu 青羽

> 上海开源软件应用创新大赛 · 参赛作品开源代码快照
> 对应项目：ChiYu AI-Native Foundation（AI 原生基础底座 + 决策脊柱）

## 一句话定位

一套**可运行、可审计、可复用**的 AI 原生决策基础设施：把已被验证的内核机制
（知识—记忆—决策 K-M-D 管道、契约化能力协商、场景包机制、插件化工作模式、
统一存储与审计链）抽成可安装的开源包，使新业务场景不必重走底座构建之路，
只需注入领域参数即可接入一套企业级决策中枢。

当前已支撑两条独立产品线共用同一套内核：
- **智排生产智能排程系统**（钢铁热轧多工序协同排程，已通过真实赛题数据实测）
- **企业 AI 销售决策平台**（CRM 领域，源程序逾 6 万行，软件著作权已提交申请并获受理）

“一底座、多产品、零复制内核”不是愿景陈述，而是已运行的工程事实。

## 目录结构

| 路径 | 说明 |
|---|---|
| `packages/chiyu-kernel/` | L0 契约 + L1 基础设施（能力注册表、决策脊柱、场景包、插件） |
| `packages/chiyu-decision/` | L2 决策智能内核（K-M-D / 九尺子 / 红线） |
| `packages/chiyu-portal/` | L3 门户运行时（可选装） |
| `packages/chiyu-cli/` | 命令行入口（modes / decide / portal / shell） |
| `examples/reference_consumer/` | 参考消费方（演示如何接入底座） |
| `docs/` | 设计文档（决策智能平台概念设计、底座抽取设计、场景包设计等） |
| `tests/` `packages/*/tests/` | 守卫测试（含变异自证） |
| `tools/` | 工程工具（导出本地模型、门面覆盖检查等） |

## 快速开始

```bash
# 1. 准备隔离环境（推荐）
cd code
python -m venv .venv
.venv/Scripts/activate        # Windows
#   source .venv/bin/activate  # Linux/macOS

# 2. 安装核心包（含开发依赖）
pip install -e packages/chiyu-kernel[dev]

# 3. 运行守卫测试
make test

# 4. 体验核心流程（自然语言 → 决策 → 可审计结果）
python -m chiyu_kernel.cli modes            # 列出四工作模式
python -m chiyu_kernel.cli decide --topic "为热轧排程生成一组可行计划" --mode minimal
python -m chiyu_kernel.cli portal onboarding --out nav.html   # 生成引导式导航页
```

## 运行依赖说明

- Python ≥ 3.10
- 核心求解/编排依赖：`ortools`、`PyYAML`（决策场景）
- 离线路由测试依赖本地模型 `models/bge-small-zh-v1.5/`（缺省时相关 4 例在
  本机跳过，非回归；可用 `python tools/export_bge_onnx.py --check-only` 复现）
- 前端演示（`web/`）需 `node_modules`（见 `web/README` 或 `npm install`）

## 设计原则（分层铁律）

1. **内核零领域字面量**：领域取值、红线目录由消费方经 `TenantProfile` 注入。
2. **单向依赖**：消费方只许 `import chiyu_kernel.contract` 与 `chiyu_kernel.api`。
3. **L3 可选**：不装 `chiyu-portal` 时 L0–L2 功能完整。

## 诚实边界

- 本仓库为**底座与决策脊柱**的开源快照；消费方（APS / CRM）的专有业务逻辑不在本仓库内。
- “是否已规模化商用”一律以“实测 / 设计已落地 / 概念已成型”三档如实标注，不作无法核验的宣称。
- 跨域实证覆盖离散制造 FJSP 与钢铁热轧；流程工业其他工序（炼铁/炼钢/连铸）的
  端到端实证仍在推进，相关约束以“上游齐套门禁”形式接入，未在本轮求解实例中激活为硬约束。

## 知识产权

- 许可证：Apache-2.0
- 底座内核机制均为自研，无第三方受限代码依赖。
- 参赛主体：北京青羽智行科技有限公司；知识产权归属清晰，无质押、纠纷或侵权诉讼。
