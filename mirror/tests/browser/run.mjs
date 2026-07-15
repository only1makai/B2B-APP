// Headless-Chromium harness for the client-only logic that has no backend
// dependency: the lighting-drift warning (PRD §1) and the Compare export ->
// download pipeline (PRD §2). Uses the function bodies copied VERBATIM from
// src/ (see harness.html).
//
// Run:
//   npm i -D playwright-core
//   CHROME=/path/to/chrome node tests/browser/run.mjs
// In this repo's cloud environment the prebuilt Chromium lives at
//   /opt/pw-browsers/chromium-1194/chrome-linux/chrome
import { chromium } from 'playwright-core';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { statSync } from 'node:fs';
import { tmpdir } from 'node:os';

const here = path.dirname(fileURLToPath(import.meta.url));
const EXE = process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const PAGE = 'file://' + path.join(here, 'harness.html');

const browser = await chromium.launch({ executablePath: EXE, args: ['--no-sandbox'] });
const ctx = await browser.newContext({ acceptDownloads: true });
const page = await ctx.newPage();

let download = null;
page.on('download', (d) => { download = d; });
const errs = [];
page.on('pageerror', (e) => errs.push(String(e)));

await page.goto(PAGE);
await page.waitForFunction('window.__ready === true', { timeout: 15000 });
const results = await page.evaluate('window.__results');

await page.waitForTimeout(500);
let downloadInfo = null;
if (download) {
  const fname = download.suggestedFilename();
  const savePath = path.join(tmpdir(), fname);
  await download.saveAs(savePath);
  downloadInfo = { suggestedFilename: fname, savedBytes: statSync(savePath).size };
}

console.log(JSON.stringify({ results, downloadTriggered: !!download, downloadInfo, pageErrors: errs }, null, 2));
await browser.close();
