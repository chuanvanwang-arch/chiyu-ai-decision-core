// 补充门户界面截图（软著「文档鉴别材料」配图第二批，编号 A08 起）。
//
// 前置（与 capture-screens.mjs 相同）：
//   1) 门户后端  uvicorn app:app --host 127.0.0.1 --port 8015（PYTHONPATH 指向 packages/*/src）
//   2) 门户前端  vite --port 5178（vite.config.ts 将 /api 代理到 8015）
// 运行：
//   node docs/copyright/capture-screens-2.mjs

import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';

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
  await page.screenshot({ path: `${OUT}/${name}.png` });
  shots.push(name);
  console.log(`  ✓ ${name}.png  ${desc}`);
}

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
    try {
      await els[index].evaluate((el) => el.click());
      return true;
    } catch {
      console.log(`  ! 点击失败（被遮挡） ${selector}[${index}]`);
      return false;
    }
  }
}

/** 走完引导式导航，进入工作台。 */
async function enterWorkbench(page) {
  for (let step = 0; step < 4; step++) {
    await clickIf(page, '.ob-choice', 0);
    await page.waitForTimeout(350);
    await clickIf(page, '.btn.primary', 0);
    await page.waitForTimeout(800);
  }
  await page.waitForTimeout(1600);
}

const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

try {
  console.log(`打开 ${BASE}`);
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(1200);
  await enterWorkbench(page);

  // A08 新建会话：侧栏会话管理
  if (await clickIf(page, '.sb-new', 0)) {
    await page.waitForTimeout(1200);
    await shot(page, 'A08-会话管理与新建会话', '侧栏会话列表与「新建会话」入口');
  }

  // A09 插件注册表 / 原生工具 / 决策脊柱（能力面板主体）
  if (await clickIf(page, '.sb-nav', 0)) {
    await page.waitForTimeout(1200);
    await shot(page, 'A09-能力面板-工作模式与插件注册表', '能力面板：工作模式、插件注册表、原生工具');
    // 向下滚动展示原生工具与决策脊柱评分细则区块
    await page.mouse.move(1200, 500);
    await page.mouse.wheel(0, 900);
    await page.waitForTimeout(800);
    // 取景：仅隐藏「企业控制面」卡片（属可选上层组件，其连接状态不属于本软件运行界面）
    await page.evaluate(() => {
      const cards = Array.from(document.querySelectorAll('.panel-card'));
      for (const c of cards) {
        const h = c.querySelector('h4');
        if (h && h.innerText.includes('企业控制面')) c.style.display = 'none';
      }
    });
    await page.waitForTimeout(300);
    await shot(page, 'A10-能力面板-原生工具与决策脊柱', '能力面板下半部：原生工具与决策脊柱评分细则');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(600);
    if (await page.$('button[title="关闭"]')) await clickIf(page, 'button[title="关闭"]', 0);
    await page.waitForTimeout(700);
  }

  // A11 LLM 设置：模型接入配置界面
  if (await clickIf(page, 'button[title="LLM 设置"]', 0)) {
    await page.waitForTimeout(1000);
    // 切到「模型」标签，展示分层模型接入配置
    const tabs = await page.$$('.settings-nav-item');
    for (const t of tabs) {
      const txt = (await t.innerText().catch(() => '')) || '';
      if (txt.includes('模型')) { await t.click().catch(() => {}); break; }
    }
    await page.waitForTimeout(900);
    await shot(page, 'A11-模型接入设置', 'LLM 设置：分层的模型接入层配置（本地与云端端点）');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    if (await page.$('button[title="关闭"]')) await clickIf(page, 'button[title="关闭"]', 0);
    await page.waitForTimeout(600);
  }

  // A12 对话执行：驱动内核做一次完整决策
  const ta = await page.$('textarea');
  if (ta) {
    await ta.click();
    await ta.fill('请对「是否批准该客户的预算追加请求」执行一次决策并给出结论');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(7000);
    await shot(page, 'A12-决策执行与阶段轨迹', '对话执行：内核返回的决策阶段轨迹与结论');

    // A13 导出对话为 HTML（门户真实渲染能力）
    if (await clickIf(page, 'button[title^="导出当前对话"]', 0)) {
      await page.waitForTimeout(1500);
      await shot(page, 'A13-对话导出为页面', '导出当前对话：由门户渲染为可交付 HTML 页面');
    }
  } else {
    console.log('  ! 未找到对话输入框');
  }
} finally {
  await browser.close();
}

console.log(`\n共新增 ${shots.length} 张 -> ${OUT}`);
