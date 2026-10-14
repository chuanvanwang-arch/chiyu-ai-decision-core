/**
 * 终端运行截图捕获器（软著文档鉴别材料用）。
 *
 * ⛔ 真实性约束：所有截图内容均来自**真实执行**命令/演示脚本产生的标准输出，
 *    不做任何手工编排或伪造。原始输出同时落盘到 terminal-output/*.txt 留证。
 *
 * 用法：
 *   node docs/copyright/capture-terminal.mjs            # 全部
 *   node docs/copyright/capture-terminal.mjs B01 C01    # 只跑指定编号
 */
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
// ESM 不读 NODE_PATH，这里用 CJS require 从共享 workspace 解析 playwright
const PW = process.env.PLAYWRIGHT_PATH
  || 'C:/Users/wangchuan08/.workbuddy/binaries/node/workspace/node_modules/playwright';
const { chromium } = require(PW);

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');
const OUT_DIR = join(__dirname, 'screenshots');
// 渲染用的临时 HTML 写到系统临时目录，避免污染截图目录（截图目录只放正式 PNG）
const TMP_DIR = join(tmpdir(), 'chiyu-terminal-capture');
const TXT_DIR = join(__dirname, 'terminal-output');
const PY = 'C:/Users/wangchuan08/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe';

const PYTHONPATH = [
  join(ROOT, 'packages', 'chiyu-kernel', 'src'),
  join(ROOT, 'packages', 'chiyu-decision', 'src'),
  join(ROOT, 'packages', 'chiyu-portal', 'src'),
  join(ROOT, 'packages', 'chiyu-cli', 'src'),
].join(';');

// ── 命令清单：编号 = 截图编号，cmd = 真实执行的命令 ─────────────────────
const JOBS = [
  // B 系列：命令行与运维工具（功能 12）
  { id: 'B01', title: '命令行入口总览', desc: 'chiyu --help：七类子命令',
    argv: [PY, '-m', 'chiyu_cli', '--help'], max: 24 },
  { id: 'B02', title: '版本查询', desc: 'chiyu --version：分发版本出口',
    argv: [PY, '-m', 'chiyu_cli', '--version'], max: 6 },
  { id: 'B03', title: '工作模式查询', desc: 'chiyu modes：四种模式与启用插件',
    argv: [PY, '-m', 'chiyu_cli', 'modes'], max: 26 },
  { id: 'B04', title: '单模式详情', desc: 'chiyu modes --mode ptc',
    argv: [PY, '-m', 'chiyu_cli', 'modes', '--mode', 'ptc'], max: 12 },
  { id: 'B05', title: '决策脊柱执行', desc: 'chiyu decide：确定性分支运行',
    argv: [PY, '-m', 'chiyu_cli', 'decide', '--topic', '是否批准该客户的预算追加请求'], max: 14 },
  { id: 'B06', title: '决策结果结构化输出', desc: 'chiyu decide --scores --json',
    argv: [PY, '-m', 'chiyu_cli', 'decide', '--topic', '是否批准该客户的预算追加请求',
           '--scores', 'clarity=4,logic=4', '--json'], max: 24 },
  { id: 'B07', title: '门户页面渲染', desc: 'chiyu portal render：自然语言→HTML',
    argv: [PY, '-m', 'chiyu_cli', 'portal', 'render', '--nl',
           '显示本季度全部订单的列表，按金额排序', '--title', '季度订单',
           '--particle-types', 'order', '--entity-map', '订单=order'], max: 26 },
  { id: 'B08', title: '引导页生成', desc: 'chiyu portal onboarding',
    argv: [PY, '-m', 'chiyu_cli', 'portal', 'onboarding'], max: 22 },
  { id: 'B09', title: '自进化开闸认证', desc: 'chiyu evolution readiness',
    argv: [PY, '-m', 'chiyu_cli', 'evolution', 'readiness'], max: 30 },
  { id: 'B10', title: '包内自测', desc: 'chiyu selftest：运行包内全部测试',
    argv: [PY, '-m', 'chiyu_cli', 'selftest'], max: 20, timeout: 300000 },

  // C 系列：门面能力演示（功能 1-11、14）
  { id: 'C01', title: '版本化与兼容承诺', desc: '能力清单、档位与弃用别名查询',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'version'], max: 46 },
  { id: 'C02', title: '契约与配置载体', desc: '租户画像与红线规格构造及构造期校验',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'contract'], max: 40 },
  { id: 'C03', title: '粒子与本体管理', desc: '统一实体模型与受控谓词本体图',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'particle'], max: 34 },
  { id: 'C04', title: '向量与语义检索', desc: '本地离线推理、降级语义与相似度排序',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'vector'], max: 42 },
  { id: 'C05', title: '情境装配与降级召回', desc: '三级降级召回与供需缺口检查',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'context'], max: 44 },
  { id: 'C06', title: '图存储与关系视图', desc: '多跳遍历、时间线视图与决策回链',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'graph'], max: 48 },
  { id: 'C07', title: '决策脊柱', desc: '六阶段顺序契约、九尺子与红线判定',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'spine'], max: 52 },
  { id: 'C08', title: '审批治理与续跑', desc: '三态模型、冻结裁定与幂等续跑',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'approval'], max: 36 },
  { id: 'C09', title: '事件与审计', desc: '事件总线分发、留痕与失败计数',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'events'], max: 36 },
  { id: 'C10', title: '金丝雀探针', desc: '接入期三判据连通性与落库自检',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'canary'], max: 40 },
  { id: 'C11', title: '插件与工作模式', desc: '六类内置插件与四种工作模式解析',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'plugins'], max: 50 },
  { id: 'C12', title: '模型接入与协议适配', desc: 'MCP 传输层、工具注册与命名规范化',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'mcp'], max: 34 },
  { id: 'C13', title: '门户运行时', desc: '输入守卫、Schema 解析与页面渲染',
    argv: [PY, join(__dirname, 'demo-runner.py'), 'portal'], max: 38 },

  // D 系列：质量保证与守卫工具链（功能 13）
  { id: 'D01', title: '导入方向守卫', desc: 'check_import_surface.py：跨分发 import 面检查',
    argv: [PY, join(ROOT, 'tools', 'check_import_surface.py')], max: 14 },
  { id: 'D02', title: '门面覆盖守卫', desc: 'check_facade_coverage.py：门面符号覆盖检查',
    argv: [PY, join(ROOT, 'tools', 'check_facade_coverage.py')], max: 14 },
  { id: 'D03', title: '零残留守卫', desc: 'check_zero_residue.py：披露口径零残留检查',
    argv: [PY, join(ROOT, 'tools', 'check_zero_residue.py')], max: 14 },
  { id: 'D04', title: '分发物同步守卫', desc: 'check_dist_sync.py：分发物与源码同步检查',
    argv: [PY, join(ROOT, 'tools', 'check_dist_sync.py')], max: 14 },
  { id: 'D05', title: '能力清单生成', desc: 'gen_capability_manifest.py：机器可读能力清单',
    argv: [PY, join(ROOT, 'tools', 'gen_capability_manifest.py')], max: 26 },
];

/** 读取由 gen-terminal-output.sh 真实执行并落盘的输出。 */
function readOutput(job) {
  const p = join(TXT_DIR, `${job.id}-${job.title}.txt`);
  if (!existsSync(p)) {
    throw new Error(`缺少输出文件：${p}（请先运行 gen-terminal-output.sh）`);
  }
  return readFileSync(p, 'utf-8');
}

function clip(text, max) {
  const lines = String(text).replace(/\r\n/g, '\n').split('\n');
  if (lines.length <= max) return lines.join('\n');
  const head = lines.slice(0, max - 1);
  head.push(`… （输出已截断，共 ${lines.length} 行）`);
  return head.join('\n');
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderHTML(job, output, cmdline) {
  return `<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><style>
    * { box-sizing: border-box; }
    body { margin:0; background:#f5f6f8; font-family: "Cascadia Mono", "Consolas",
           "Microsoft YaHei Mono", "Courier New", monospace; }
    .win { width:1180px; background:#ffffff; border:1px solid #c9ced6;
           border-radius:6px; overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,.08); }
    .bar { background:#e9edf3; border-bottom:1px solid #c9ced6; padding:8px 14px;
           display:flex; align-items:center; gap:10px; }
    .dot { width:11px; height:11px; border-radius:50%; display:inline-block; }
    .d1{background:#e06c75}.d2{background:#e5c07b}.d3{background:#98c379}
    .ttl { font-size:13px; color:#3c4250; font-weight:600; font-family:"Microsoft YaHei",sans-serif; }
    .sub { font-size:12px; color:#6b7280; margin-left:auto; font-family:"Microsoft YaHei",sans-serif; }
    .body { padding:10px 16px 16px; }
    .cmd { font-size:13.5px; color:#1f2430; margin-bottom:8px; word-break:break-all; }
    .cmd .prompt { color:#2a7fbf; font-weight:700; }
    pre { margin:0; font-size:13px; line-height:1.55; color:#20242c; white-space:pre-wrap;
          word-break:break-word; }
  </style></head><body>
    <div class="win">
      <div class="bar">
        <span class="dot d1"></span><span class="dot d2"></span><span class="dot d3"></span>
        <span class="ttl">${esc(job.id)}　${esc(job.title)}</span>
        <span class="sub">青羽 AI 原生底座软件（ChiYu-Foundation）V1.0</span>
      </div>
      <div class="body">
        <div class="cmd"><span class="prompt">$</span> ${esc(cmdline)}</div>
        <pre>${esc(output)}</pre>
      </div>
    </div>
  </body></html>`;
}

function displayCmd(argv) {
  return argv.map((a) => {
    if (a === PY) return 'python';
    if (a.startsWith('C:') || a.includes('\\')) {
      const rel = a.replace(ROOT.replace(/\//g, '\\') + '\\', '');
      return rel.split('\\').join('/');
    }
    return /\s/.test(a) ? `"${a}"` : a;
  }).join(' ').replace('python -m chiyu_cli', 'chiyu');
}

async function main() {
  const only = process.argv.slice(2);
  const jobs = only.length ? JOBS.filter((j) => only.includes(j.id)) : JOBS;
  mkdirSync(OUT_DIR, { recursive: true });
  mkdirSync(TMP_DIR, { recursive: true });
  mkdirSync(TXT_DIR, { recursive: true });

  const browser = await chromium.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  });
  const page = await browser.newPage({ viewport: { width: 1220, height: 900 } });

  for (const job of jobs) {
    let out;
    try {
      out = readOutput(job);
    } catch (e) {
      console.log(`  ✗ ${job.id} ${e.message}`);
      continue;
    }
    if (out.includes('执行失败')) {
      console.log(`  ✗ ${job.id} 输出含失败标记，请重跑 gen-terminal-output.sh`);
      continue;
    }
    const shown = clip(out, job.max);
    const html = renderHTML(job, shown, displayCmd(job.argv));
    const htmlPath = join(TMP_DIR, `_tmp-${job.id}.html`);
    writeFileSync(htmlPath, html, 'utf-8');
    await page.goto(`file:///${htmlPath.replace(/\\/g, '/')}`);
    await page.waitForTimeout(120);
    const el = await page.$('.win');
    await el.screenshot({ path: join(OUT_DIR, `${job.id}-${job.title}.png`) });
    console.log(`  ✓ ${job.id} ${job.title}`);
  }

  await browser.close();
  rmSync(TMP_DIR, { recursive: true, force: true });
  console.log(`\n完成：${jobs.length} 张终端截图 -> ${OUT_DIR}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
