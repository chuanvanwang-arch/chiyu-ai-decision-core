// 捕获门户界面截图，供软著「文档鉴别材料」（用户手册）配图使用。
//
// 前置：
//   1) 门户后端  python -m uvicorn app:app --host 127.0.0.1 --port 8015
//      （PYTHONPATH 指向 packages/{chiyu-kernel,chiyu-decision,chiyu-portal}/src）
//   2) 门户前端  vite --port 5178（vite.config.ts 默认把 /api 代理到 8015）
// 运行：
//   NODE_PATH=<node workspace>/node_modules node docs/copyright/capture-screens.mjs

import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';

// ESM 不读 NODE_PATH，这里用 CJS require 从共享 workspace 解析 playwright
const require = createRequire(import.meta.url);
const PW = process.env.PLAYWRIGHT_PATH
  || 'C:/Users/wangchuan08/.workbuddy/binaries/node/workspace/node_modules/playwright';
const { chromium } = require(PW);

const BASE = process.env.PORTAL_URL || 'http://127.0.0.1:5178/';
const OUT = new URL('./screenshots/', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';

mkdirSync(OUT, { recursive: true });

const shots = [];
async function shot(page, name, desc) {
  const file = `${OUT}/${name}.png`;
  await page.screenshot({ path: file });
  shots.push({ file: `${name}.png`, desc });
  console.log(`  ✓ ${name}.png  ${desc}`);
}

// 容错点击：找不到就直接跳过，不中断整轮
async function clickIf(page, selector, index = 0, timeout = 5000) {
  const els = await page.$$(selector);
  if (els.length <= index) {
    console.log(`  ! 未命中选择器 ${selector}[${index}]`);
    return false;
  }
  try {
    await els[index].click({ timeout });
    return true;
  } catch {
    // 被浮层遮挡时退回直接派发点击，不中断整轮截图
    try {
      await els[index].evaluate((el) => el.click());
      return true;
    } catch {
      console.log(`  ! 点击失败（被遮挡） ${selector}[${index}]`);
      return false;
    }
  }
}

const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

try {
  console.log(`打开 ${BASE}`);
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(1200);

  // A01 引导式导航 · 第一步（选择业务方向）
  await shot(page, 'A01-引导式导航-选择方向', '启动引导：业务方向选择');

  // 选第一个方向 → 下一步
  await clickIf(page, '.ob-choice', 0);
  await page.waitForTimeout(400);
  await clickIf(page, '.btn.primary', 0);
  await page.waitForTimeout(900);
  await shot(page, 'A02-引导式导航-选择工作流', '引导第二步：工作流与难度分级');

  // 选第一个工作流 → 下一步
  await clickIf(page, '.ob-choice', 0);
  await page.waitForTimeout(400);
  await clickIf(page, '.btn.primary', 0);
  await page.waitForTimeout(900);
  await shot(page, 'A03-引导式导航-选择工作模式', '引导第三步：四种工作模式与启用插件');

  // 选模式 → 下一步（第 4 步为进入工作台确认页）
  await clickIf(page, '.ob-choice', 0);
  await page.waitForTimeout(400);
  await clickIf(page, '.btn.primary', 0);
  await page.waitForTimeout(900);
  await shot(page, 'A04-引导式导航-进入工作台确认', '引导第四步：确认所选方向、工作流与工作模式');

  // 进入工作台
  const entered = await clickIf(page, '.btn.primary', 0);
  await page.waitForTimeout(1800);
  if (entered) await shot(page, 'A05-对话工作台', '对话工作台（已按所选模式与方向初始化）');

  // A06 能力面板（工作模式 / 插件注册表 / 原生工具 / 决策脊柱）
  if (await clickIf(page, 'button[title="插件 / 能力面板"]', 0)) {
    await page.waitForTimeout(900);
    await shot(page, 'A06-能力面板', '能力面板：工作模式、插件注册表、原生工具、决策脊柱');
    // 关闭面板：Esc 优先，失败再点关闭按钮（浮层可能遮挡）
    await page.keyboard.press('Escape');
    await page.waitForTimeout(600);
    if (await page.$('button[title="关闭"]')) await clickIf(page, 'button[title="关闭"]', 0);
    await page.waitForTimeout(700);
  }

  // A07 对话执行：向真实内核发一条指令，展示工具调用回执
  const ta = await page.$('textarea');
  if (ta) {
    await ta.click();
    await ta.fill('用内核能力检查当前工作模式与可用插件');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(6000);
    await shot(page, 'A07-对话执行与工具调用回执', '对话执行：内核真实返回与工具调用轨迹');
  } else {
    console.log('  ! 未找到对话输入框 textarea');
  }
} finally {
  await browser.close();
}

console.log(`\n共 ${shots.length} 张，输出目录：${OUT}`);
