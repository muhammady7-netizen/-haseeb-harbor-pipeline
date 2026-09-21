/**
 * law-b39 headless: upload local review.csv into the task Drive folder.
 * (Review tool Submit fails: UrlFetchApp.external_request auth)
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const FOLDER_URL =
  'https://drive.google.com/drive/folders/1nXcKPyHmrJxPuig-ptnrwfnt_Mi57U9Y';
const CSV = path.join(__dirname, 'tmp-pw/law-b39-generated-review.csv');
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function clearLocks() {
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
    } catch {}
  }
}

(async () => {
  if (!fs.existsSync(CSV)) throw new Error('missing ' + CSV);
  clearLocks();
  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    viewport: { width: 1440, height: 960 },
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = context.pages()[0] || (await context.newPage());
  const result = { ok: false, errors: [] };

  try {
    await page.goto(FOLDER_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(5000);
    if (page.url().includes('accounts.google.com')) throw new Error('not logged in');
    await page.keyboard.press('Escape').catch(() => {});
    await page.screenshot({ path: path.join(OUT, 'law-b39-v4-folder.png'), fullPage: true });

    const newBtn = page.getByRole('button', { name: /^New$/i }).first();
    await newBtn.click({ timeout: 15000 });
    await sleep(800);
    const fileUpload = page.getByRole('menuitem', { name: /File upload/i }).first();
    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser', { timeout: 20000 }),
      fileUpload.click({ timeout: 15000 }),
    ]);
    await chooser.setFiles(CSV);

    for (let i = 0; i < 30; i++) {
      await sleep(2000);
      const t = await page.locator('body').innerText().catch(() => '');
      if (/upload complete/i.test(t)) break;
      if (t.includes('review.csv') && !/uploading/i.test(t) && i > 2) break;
    }
    await sleep(2000);
    await page.screenshot({ path: path.join(OUT, 'law-b39-v4-csv-uploaded.png'), fullPage: true });
    const body = await page.locator('body').innerText().catch(() => '');
    fs.writeFileSync(path.join(OUT, 'law-b39-v4-body.txt'), body.slice(0, 8000));
    result.ok = /review\.csv/i.test(body);
    result.bodySnippet = body.slice(0, 1500);
    fs.writeFileSync(path.join(OUT, 'law-b39-v4-result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(result.ok ? 0 : 2);
  } catch (e) {
    result.errors.push(String(e && e.stack ? e.stack : e));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v4-error.png'), fullPage: true }).catch(() => {});
    fs.writeFileSync(path.join(OUT, 'law-b39-v4-result.json'), JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
