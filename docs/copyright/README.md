# 软著申请材料（青羽 AI 原生底座软件 V1.0）

> 用途：计算机软件著作权登记申请材料底稿与生成脚本
> 生成日期：2026-10-09
> 参考：CRM 项目 `CRM-ai-native/doc/copyright` 的材料组织方式（三件套：源程序鉴别材料 + 文档鉴别材料 + 申请表字段）
> ⚠ 本目录为**材料底稿**，不参与本仓 pytest 与 `make lint` 的判据面（`check_zero_residue.py` 默认只扫 `ppt`）

---

## 一、登记信息（已由权利人 2026-10-09 确认）

| 项 | 内容 |
|---|---|
| 软件全称 | 青羽 AI 原生底座软件（ChiYu-Foundation） |
| 版本号 | V1.0 |
| 著作权人 | 北京青羽智行科技有限公司 |
| 源程序范围 | 仅 `packages/` 四个在研包主源码（kernel / decision / portal / cli） |
| 源程序量 | 13,590 行（交存口径，含包定义文件；不含测试、构建产物、已弃用包） |

**排除说明**：`chiyu-host` 已于 2026-09-26 并入企业侧 host，属已弃用包，不作为本软件源程序申报；
测试代码与 `build/`、`dist/` 构建产物同样不纳入。

## 二、材料清单

### 2.1 源程序鉴别材料（一般交存：前 30 页 + 后 30 页，每页 50 行）

| 文件 | 说明 |
|---|---|
| `source-material.pdf` | **交存用**，60 页（A4），页眉含软件名/版本/页码 |
| `source-material.html` | 打印用排版源（A4，每页 50 行） |
| `source-lines.txt` | 交存正文纯文本（前 30 页 + 后 30 页拼接结果） |

### 2.2 文档鉴别材料（用户手册）

| 文件 | 说明 |
|---|---|
| `user-manual-submission.pdf` | **交存用**，60 页（全文正好 60 页，交存即全量，无需截取） |
| `user-manual.pdf` | 全文 **60 页**，含页眉与「第 N 页 / 共 M 页」页码 |
| `user-manual.html` | 手册排版源（封面 + 目录 + 图索引 + 十三章 + 附录 A–E） |
| `screenshots/` | 运行界面截图 **41 张**（门户图形界面 13 张 + 终端运行 28 张） |
| `terminal-output/` | 终端类截图的**原始文本**（28 份，命令真实标准输出，备查） |

**交存形式**：手册全文 **60 页**。按「连续前 30 页 + 连续后 30 页」交存即为第 1–30 页与第 31–60 页，
两者并集正好是全文，因此**交存版与全文一致**，无需截取。

**每页行数**：全文 60 页逐页核验，**每页视觉行数均不少于 30 行**（实测区间 34–107 行，平均 59.9 行）。
核验脚本见 `check-page-lines.py`（按版面上的实际文本行统计，表格单元格内换行与代码行均按行计，
与人工翻页点数的口径一致）：

```bash
python docs/copyright/check-page-lines.py docs/copyright/user-manual.pdf
```

**功能界面覆盖**：申请表单所列 14 项功能均有对应运行界面截图，集中于**附录 E　全功能运行界面与操作说明**，
按功能逐项给出「功能定位 → 操作步骤 → 关键输出摘录 / 界面构成说明 → 界面截图 → 可核对要点」。
全书 41 张截图在**任意交存口径下均完整包含**（因交存 = 全文）。目录后附**本手册图索引**，列出全部图注便于查阅。

### 2.3 申请表单字段

| 文件 | 说明 |
|---|---|
| `application-fields.md` | 申请表字段填报稿（含待确认项标注） |
| `software-functions.txt` | 软件功能说明（14 项功能模块） |
| `software-techfeatures.txt` | 软件技术特点（约 300 字） |

## 三、生成脚本与再生成步骤

| 脚本 | 职责 |
|---|---|
| `gen-source-material.py` | 抽取四包主源码 → 前后各 30 页 → `source-lines.txt` + `source-material.html` |
| `html2pdf.py` | 用本机 Chromium 把打印用 HTML 转 PDF（中文保真）；图片较多时改用 `html2pdf.mjs` |
| `html2pdf.mjs` | 用 Playwright/Chromium 打印 PDF（遵循 HTML 内 `@page` 分页，等图片解码完成再输出） |
| `add-page-numbers.py` | 用 reportlab 叠加页眉与页码（浏览器打印无法生成中文页眉页码） |
| `gen-submission.py` | 页数超 60 的材料按「前 30 + 后 30」截取交存版 |
| `capture-screens.mjs` | 门户图形界面截图第一批（引导、工作台、能力面板、对话执行，A01–A07） |
| `capture-screens-2.mjs` | 门户图形界面截图第二批（会话、能力面板分区、模型设置、决策执行、导出，A08–A13） |
| `demo-runner.py` | 逐功能调用软件公开门面的演示脚本（13 项，输出真实运行结果供截图） |
| `gen-terminal-output.sh` | 真实执行 CLI 子命令与门面演示，把标准输出落盘到 `terminal-output/` |
| `capture-terminal.mjs` | 读取上述落盘输出，渲染为终端运行截图（B/C/D 系列 28 张） |
| `make-appendix-e.py` | 把界面说明章转换为「附录 E」并统一节号（`14.x` → `E.x`）与图号 |
| `insert-appendix-e.py` | 将附录 E 插入手册（目录 + 文末），并校验全部截图引用存在 |
| `cleanup-old-chapter14.py` | 一次性清理：移除早期以「第十四章」形式插入的旧块 |
| `check-page-lines.py` | **核验每页视觉行数**（软著「每页不少于 30 行」要求），退出码 0/1 |
| `insert-output-excerpts.py` | 为终端截图插入对应的真实输出摘录（图前，幂等） |
| `insert-ui-notes.py` / `-2` / `-3` / `-4` | 为门户界面图补「界面构成」「可核对要点」「操作步骤」「相关配置项」 |
| `insert-section-notes.py` | 为附录 E 各节补「使用要点与注意事项」 |
| `insert-fig-index.py` | 生成目录后的「本手册图索引」与文末小结 |
| `insert-extra-notes.py` / `-2` … `-6`、`insert-pin-notes.py` / `-2` / `-3` / `-4` | 定点补足各页文字量（均幂等，重复执行不重复插入） |

### 3.1 源程序材料再生成

```bash
python docs/copyright/gen-source-material.py
python docs/copyright/html2pdf.py docs/copyright/source-material.html docs/copyright/source-material.pdf
```

### 3.2 用户手册再生成

```bash
# ① 正文排版 → PDF（Playwright/Chromium；图片较多时更稳）
node docs/copyright/html2pdf.mjs docs/copyright/user-manual.html docs/copyright/_manual-body.pdf

# ② 叠加页眉页码（需 reportlab）
"C:/Users/wangchuan08/.workbuddy/binaries/python/envs/default/Scripts/python.exe" \
  docs/copyright/add-page-numbers.py docs/copyright/_manual-body.pdf docs/copyright/user-manual.pdf

# ③ 截取交存版（手册 60 页 → 不超 60 页，按规则全量交存）
python docs/copyright/gen-submission.py docs/copyright/user-manual.pdf \
  docs/copyright/user-manual-submission.pdf

# ④ 核验每页行数（必须全部 ≥ 30 行；本脚本依赖 PyMuPDF，需装在所用解释器里）
python docs/copyright/check-page-lines.py docs/copyright/user-manual.pdf
```

> 解释器提示：`add-page-numbers.py` 需 `reportlab`，`check-page-lines.py` 需 `PyMuPDF`；
> 两者未装在同一环境时按各自环境分别调用（本机：`add-page-numbers.py` 用托管 venv，
> `check-page-lines.py` 用 `C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe`）。

### 3.3 截图再生成

```bash
# 一、门户图形界面（需先起前后端）
#   后端：工作目录 web/backend，PYTHONPATH 指向 kernel/decision/portal 三包 src，监听 8015
#   前端：工作目录 web，npm run dev（vite.config.ts 将 /api 代理到 8015，监听 5178）
node docs/copyright/capture-screens.mjs      # A01–A07
node docs/copyright/capture-screens-2.mjs    # A08–A13

# 二、终端运行界面（两段式：先跑真命令落盘，再渲染截图）
bash docs/copyright/gen-terminal-output.sh   # → terminal-output/*.txt（28 份真实输出）
node docs/copyright/capture-terminal.mjs     # → screenshots/B*, C*, D*（28 张）

# 三、把界面说明章合入手册（幂等，可重复执行）
python docs/copyright/make-appendix-e.py
python docs/copyright/insert-appendix-e.py
```

## 四、核对要点（提交前必查）

1. **数字自洽**：申请表「源程序量」13,590 行 = `source-lines.txt` 收录行数口径。若重跑 `gen-source-material.py`，
   须同步核对本表与 `application-fields.md` 的数字。
2. **页码连续**：源程序材料 60 页页码 1–60；手册 60 页页码 1–60（交存即全文）。
3. **每页行数**：手册每一页的**视觉行数须 ≥ 30 行**（软著文档鉴别材料要求）。
   改动 `user-manual.html` 后**必须重跑** `check-page-lines.py` 核验；
   若因增删内容导致某页回落至 30 行以下，应补齐该页文字后再生成。
   手册采用的排版参数为：A4、页边距 16mm、正文 9.5pt / 行高 1.36、门户界面图右浮动（宽 54%）供正文环绕，
   这些参数是在保证截图清晰的前提下满足行数要求的结果，**不建议再放宽行距**。
4. **截图齐备**：`screenshots/` 41 张须全部被 `user-manual.html` 引用（`insert-appendix-e.py` 会校验引用文件存在）。
   若某张终端截图内容出现「执行失败」字样，说明 `gen-terminal-output.sh` 未跑成功，须重跑后再渲染。
5. **能力状态如实**：功能说明与手册均已单列声明「记忆网相关能力处于实验态，未纳入本版本稳定承诺」。
6. **待确认项**：`application-fields.md` 中「开发完成日期」「首次发表日期」涉及法律事实，需权利人核对后填写。

## 五、已知口径说明

- 源程序材料按**前后各 30 页**交存（共 60 页），中间页不交；手册全文正好 60 页，
  按「前 30 + 后 30」交存即为全量，两口径一致。
- 手册中的门户界面图采用**右浮动 + 正文环绕**排版：这是在保证截图清晰度（宽度 54%，
  较原先满幅更宽）的同时满足「每页 ≥ 30 行」要求的关键排版手段；若改为居中满幅，
  图页的文字行数会回落至 30 行以下。
- PDF 由 Chromium 打印生成（中文与版式保真），未使用 reportlab 排正文（其内置字体无中文字形）；
  reportlab 仅用于生成页眉页码叠加层。
- 生成脚本采绝对路径与显式排除规则，不依赖当前工作目录之外的假设。
