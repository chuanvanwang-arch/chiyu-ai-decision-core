# ChiYu AI Native Foundation

AI 原生基础底座。把「已验证的内核机制」抽成可安装包，让新项目不必重走 KMD 构建、
本地模型接入、粒子库设计、离线向量栈的路。

## 包结构

| 包 | 层 | 授权 | 状态 |
|---|---|---|---|
| `chiyu-kernel` | L0 契约 + L1 基础设施 | 基础 | 本期（阶段 P1） |
| `chiyu-decision` | L2 决策脊柱（KMD S1→S5 / 九尺子 / 红线） | **核心（最贵）** | 阶段 P2 |
| `chiyu-portal` | L3 门户运行时 | 可选装 | 阶段 P2 |
| `chiyu-init` | 问答式脚手架 | 随基础包 | 阶段 P3 |
| `chiyu-host` | DSH 桥接层（M0） | 随基础包 | **已弃用**（2026-09-26 并入 `chiyu-enterprise` 企业 host `enterprise.host.dsh_adapter`） |

## 分层铁律

1. **内核零领域字面量**：粒子类型的取值、知识谓词、红线事项目录全部由消费方
   注入 `TenantProfile`。内核只声明形态。
2. **单向依赖**：消费方只许 import `chiyu_kernel.contract` 与 `chiyu_kernel.api`。
3. **L3 可选**：不装 `chiyu-portal` 时 L0–L2 功能完整。

## Phase A · 插件化与工作模式（对标 DeepSeek Harness 桌面版）

借鉴 DeepSeek Harness 桌面版的「四种工作方式 + 插件化架构 + 引导式页面导航」工程思路，
落成本仓的「Everything is a Plugin」内核能力。路线图分两阶段：

- **Phase A（已落地）**：内核 `chiyu_kernel.plugins` 注册表 + 6 个内置插件 + 4 种工作模式
  预设 + 双端入口（`chiyu-cli --mode` / `chiyu-portal` 引导式导航）。本仓当前为**确定性运行时**，
  故四模式先以「编排契约 + 入口 + 确定性桩」落地。
- **Phase B（待接）**：把 `deepseek-ai/DeepSeek-V4-Flash`（llm/tier.py 已预留云端端点）作为
  「标准 / PTC / 创造」模式的真 LLM 引擎，激活 PTC「先写小程序」与创造「写插件」行为。

### 内核落点（`chiyu_kernel.plugins`）

| 概念 | 类型 | 说明 |
|---|---|---|
| `PluginSpec` | dataclass(frozen) | 一个插件 = 一组能力槽位（particle_types/actions/page_types/tools/orchestration_hooks/input_adapters） |
| `PluginRegistry` | 类 | 注册 / 发现 / 校验（范式对齐 `ActionRegistry`，审计返回 errors/warnings） |
| `BUILTIN_PLUGINS` + `register_builtins` | 6 个 | terminal / loop / subagent / web_search / team / voice，映射到既有内核能力 |
| `WorkMode` + `MODE_PRESETS` | 4 个预设 | standard / ptc / minimal / creative = 插件组合 + 编排开关 |
| `resolve_work_mode` | 函数 | 解析模式，**永不抛**（未知/缺失回落默认并留 warning） |

⛔ 插件仅声明能力槽位、零领域字面量；消费方经 `chiyu_kernel.api` 门面访问，不 import 内部路径。

### 四种工作模式

| 模式 | 启用插件 | 编排开关 | Phase B 后端 |
|---|---|---|---|
| standard（默认） | terminal, loop, subagent, web_search, team | portal 开 | deepseek-ai/DeepSeek-V4-Flash |
| ptc | terminal, loop, web_search | 开 script_plan_slot | deepseek-ai/DeepSeek-V4-Flash |
| minimal | terminal | portal 隐藏 | 无需 LLM |
| creative | 全部 + voice | 开放自定义插件注册 / 模式声明 | deepseek-ai/DeepSeek-V4-Flash |

### CLI 用法

    chiyu modes                       # 列出四模式及启用插件
    chiyu modes --mode ptc            # 查看单个模式详情
    chiyu decide --topic "..." --mode minimal
    chiyu portal render --nl "..." --mode standard
    chiyu shell --mode creative       # 受限命令壳按模式装配
    chiyu portal onboarding --out nav.html   # 生成引导式导航页（选方向→选工作流→选模式→进工作台）

⛔ 引导式导航的菜单与可选工作流全部从 `PluginRegistry` / `MODE_PRESETS` 动态生成；
方向（行业/租户）经 `TenantProfile` 注入，门户零领域字面量。


## 本地开发

    git init 已完成（零 remote 纪律）
    make test        # 全部守卫测试
    make check       # 可编译友好检查
    make dist        # 源码 wheel（内部项目）
    make dist-release # .pyd 编译 wheel（对外，阶段 P3）

> ⚠️ **ONNX 离线路由测试的环境基线**：`test_offline_onnx_backend.py`（`test_auto_picks_local_onnx` 等
> **4 例**）依赖本地模型文件存在才可通过。若 `models/bge-small-zh-v1.5/` 下缺
> `model.safetensors` + `tokenizer.json`，这 4 例在**本机**会失败（`is_available` 环境依赖），
> **不是 R2–R14 改造的回归**；在模型齐备的 CI 应全绿。生成本地模型：
> `python tools/export_bge_onnx.py`（生成并验证，`--check-only` 对拍 cos≥0.9999）。

## 仓边界（2026-09-21 收口）

**本仓是 AI 原生基础底座的唯一事实源**，与消费方演示项目 `D:\system\BJ-12345`
**仓储分离、互不写入**：

- ✅ 允许：读 `BJ-12345/demo` 作**只读快照**参照（R4 隔离）
- ⛔ 禁止：向 `BJ-12345` 任何路径写入设计、计划、脚本或记忆；本仓产物一律落在本仓

### 本仓产物登记（由 BJ-12345 迁入）

| 本仓路径 | 原位置 | 迁移时 md5 |
|---|---|---|
| `docs/2026-09-21-AI原生基础底座抽取设计.md` | `BJ-12345/docs/` | `35a8d44986542c4ab12d82c90084bf12` |
| `docs/plans/2026-09-21-底座内核抽取T1-T5实施计划.md` | `BJ-12345/docs/superpowers/plans/` | `bcf896b6fdf29c78aa75e2cf91030918` |
| `contract/contract-ids.json` | `BJ-12345/docs/contracts/` | `8af4c7cdad338c3c037aabea44b7d4c5` |
| `tools/mutate_api_facade.py` | `BJ-12345/output/_mutations/` | `f51eefff150b54f3607525ee309571a8` |
| `docs/2026-09-21-决策智能平台概念设计.md` | `BJ-12345/demo/docs/2026-09-21-AI原生平台概念设计.md`（v1） | `8a50a8f0cc8bdda8f71264b6389891b0`（**源 v1 指纹**） |

> 末行为**迁入 + 就地修订**（v1 → v1.1 → v1.2），故表内 md5 是**源 v1** 的指纹；现稿与 v1 不同属预期
> （修订内容见该文件「修订总览」）。迁移依据 = demo 侧 2026-09-21 范围裁定
> 「底座与平台级事项移出 demo、单独立项」；配套 `…概念设计.md.feedback.json` 为闭环回写落点。
> ⛔ **文件名不带版本号**（版本号只在文件头），避免每次修订都改名引起登记与 feedback 路径连锁变动。
> ⚠️ v1.2 含**对已批准铁律的修订**（§12.5 追认请求）——**追认前不得据此实施**。

> 迁移方式：**复制**，源仓副本保留仅作历史留档。
> 上表 md5 为**迁移时**值；迁入后就地修正了 4 处陈旧跨仓自引用
> （`docs/superpowers/` → `docs/plans/`、`output/_mutations/` → `tools/`），
> 故现文件 md5 与上表**已不相同**，属预期。
> 设计稿与计划内的 `BJ-12345` 字样多为**历史范围陈述**（谁抽自谁），非运行时依赖。

## ⛔ pytest 路径纪律（实测踩坑，勿改回）

`pythonpath` ini **相对 rootdir** 解析，而 rootdir 取决于调用方式：
从仓库根跑 `pytest packages/chiyu-kernel/tests` 时 rootdir 落在 `packages/chiyu-kernel`
（因该处 `pyproject.toml` 含 `[tool.pytest.ini_options]`），于是
`-o pythonpath="packages/chiyu-kernel/src"` 会被解析成不存在的嵌套路径。

故：**不要传 `-o pythonpath`**；`packages/chiyu-kernel/pyproject.toml` 的
`pythonpath = ["src"]`（rootdir 相对）+ `tests/conftest.py` 的"仅当不可导入才插入"兜底
共同保证可导入。做 A/B 实验时 `-o pythonpath=<副本>`（**相对 rootdir**）仍优先生效，
因为 conftest 不会覆盖已可导入的副本。
