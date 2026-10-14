/**
 * HTML → PDF（Playwright/Chromium，中文保真，遵循 HTML 内 @page 分页规则）。
 *
 * 用法：node docs/copyright/html2pdf.mjs <html> <out.pdf>
 */
import { createRequire } from 'node:module';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

const require = createRequire(import.meta.url);
const PW = process.env.PLAYWRIGHT_PATH
  || 'C:/Users/wangchuan08/.workbuddy/binaries/node/workspace/node_modules/playwright';
const { chromium } = require(PW);

const [src, out] = process.argv.slice(2);
if (!src || !out) {
  console.error('用法：node html2pdf.mjs <html> <out.pdf>');
  process.exit(2);
}

const srcAbs = resolve(src);
const outAbs = resolve(out);
if (!existsSync(srcAbs)) {
  console.error('源文件不存在：', srcAbs);
  process.exit(2);
}

const browser = await chromium.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
});
try {
  const page = await browser.newPage();
  await page.goto(`file:///${srcAbs.replace(/\\/g, '/')}`, {
    waitUntil: 'networkidle', timeout: 120000,
  });
  // 等所有图片解码完成，避免打印出空白图位
  await page.evaluate(async () => {
    const imgs = Array.from(document.images);
    await Promise.all(imgs.map((im) => (im.complete
      ? Promise.resolve()
      : new Promise((r) => { im.onload = im.onerror = r; }))));
  });
  await page.waitForTimeout(800);
  await page.pdf({
    path: outAbs,
    printBackground: true,
    preferCSSPageSize: true,     // 采用 HTML 内 @page { size/margin }
  });
} finally {
  await browser.close();
}
console.log(`已生成：${outAbs}`);
