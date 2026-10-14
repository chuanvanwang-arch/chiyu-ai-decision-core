# foundation 回函 · 致三仓（Batch-5 落地：调度复盘判据核上收）

> 日期：2026-10-14 ｜ 提交：`3006c00`（T109）｜ 能力面 43 → **45 capabilities**
> 全量回归：**1200 passed / 0 failed**（基线 1188 → 1200；首跑 1 红为 harness 时序敏感用例
> `test_independent_steps_run_in_parallel_not_serial`，隔离+全量复跑翻转甄别为偶发，与 T99 同型）
> 变异自证：**10/10**（M1-M10；M9 判别力返工一次——补 0.7~0.79 区间边界用例后抓红）

---

## 一、交付总账（对应两页分析 §三 候选 #9/#11）

### scheduler_core —— 新子包 `chiyu_kernel.scheduler_core` + 契约 `contract/scheduler.py`

| 判据 | 语义锚点（CRM timers.js） | 不变量 |
|---|---|---|
| `next_run_at` 每日时点顺延 | :185-190 nextRetroAt | 时点参数化（缺省 2 点=**运维调度配置非业务阈值**）；恰等于时点也顺延（`next <= t0` 语义，变异钉住）；非法时点 fail-closed |
| `catchup_verdict` 三态判决 | :199-207 | **S4** stale(>24h) 补跑 / fresh(<24h) 天然限流重启不重跑 / **S5** near_schedule(<30min) 交给定时防补跑与定时双跑；首启无记录视为 stale；IO（查最新 run_at）留消费方 |
| `run_segments` 段隔离编排 | :141-182 runRetroOnce 范式 | **S1** 每段独立 catch 互不传染（复盘 LLM 失败不拖垮收口/体检）/ **S2** 失败必留痕禁裸 catch（「没跑」≠「跑了失败」）/ **S3** 收尾段独立兜底 catch（前置全败仍执行报告落库） |

### nightly_report —— 新子包 `chiyu_kernel.nightly_report` + 契约 `contract/nightly_report.py`

| 判据 | 语义锚点（nightlyReport.js） | 不变量 |
|---|---|---|
| `collect_segments` 三段归一化 | :27-41 | **R2** 任一段 null → 空结构防渲染崩；param.items 贯穿（九尺子明细不丢） |
| `extract_retro_metrics` 双形态统一 | :57-77 | **R3** 实时/落库回读双形态兼容，summary.* 权威、clusters 明细、缺失回退顶层——防回读计数恒 0；**R5** 失败原因过滤阈值独立注入，**缺省 0.7 与 D3 裁定同源，禁与基座 0.79 自主放行阈值静默互替**（0.7~0.79 区间边界用例钉住） |
| `render_nightly_markdown` 纯模板 | :80-147 | **R1** 零额外 LLM（复盘归因由消费方 LLM 产出属既有行为，本核只汇总）；**R4** 漂移口径诚实——drift>0 且无自动建议值必须显示「需人工研判」，禁误显示「全部健康」（:122-128 修复语义随上收） |
| `aggregate_report_metrics` | :161-170 | insufficient 计入 total 与失败行、**不计入 drift**（CRM 口径）；patches 三段累加 |

**IO 边界**：定时器注册、DB 查最新 run_at、报告落盘/落库 upsert——留消费方。任务名/时区/报告标题/日期口径由消费方注入。

## 二、致 CRM：parity 扩展锚点

- 调度侧优先对拍：catchup 三态判决（`CATCHUP_MAX_AGE_HOURS=24` / `CATCHUP_NEAR_SCHEDULE_MS=30min` 已入契约常量）与 `next <= t0` 顺延语义；
- 夜报侧优先对拍：R3 双形态（贵仓 :53-56 注释记载的「落库回读计数恒 0」缺陷的守护判据）与 R4 漂移诚实（:122-128 修复）；
- R5：`FAIL_CONFIDENCE_THRESHOLD_DEFAULT=0.7` 契约常量已登记 D3 同源——CRM 侧如注入自定义阈值请与 0.79 保持「两默认值各归其位」纪律。

## 三、致 APS / enterprise

- 本批零删除项、零既有 API 变更（纯加法两子包）；无强制动作。
- `run_segments` 段隔离范式可复用于贵仓夜批/批处理结构（callable 全注入，S1-S3 结构保证由基座承载）。

## 四、进度与下一步

- 收敛计划：Batch-1a/1b/2a/2b/3/4/5 ✅ 全部落地；下一批 **Batch-6 横切**（范围待盘点：错误分类横切/配置注入横切/租户隔离横切等，启动前先出盘点稿）→ Batch-7 P2/P3。
- 待三仓：CRM 四能力+两能力 parity 扩展可即启；enterprise 观测索引收口回函（T108 已开窗口）；APS 择机补全量。
