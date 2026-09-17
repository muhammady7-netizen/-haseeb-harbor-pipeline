/**
 * On open task page: Run client preQC + Run QC-Oracle-GLM.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-cc9eb99d91a211eeeb149d3b50cb0ddf-v1';
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
  clearLocks();
  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    viewport: { width: 1440, height: 960 },
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = context.pages()[0] || (await context.newPage());
  const result = { ok: false, clicks: [], url: URL };
  try {
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(5000);
    // Ensure on task detail
    let t = await page.locator('body').innerText();
    if (!/Run client preQC|Run QC-Oracle-GLM|Harbor package/i.test(t)) {
      await page.getByRole('button', { name: /Open task/i }).first().click();
      await sleep(8000);
      t = await page.locator('body').innerText();
    }
    fs.writeFileSync(path.join(OUT, 'law-b39-v10d-before.txt'), t.slice(0, 12000));

    for (const label of ['Run client preQC', 'Run QC-Oracle-GLM']) {
      const btn = page.getByRole('button', { name: new RegExp(label, 'i') }).first();
      if (!(await btn.count())) {
        result.clicks.push('missing:' + label);
        continue;
      }
      const disabled =
        (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
        (await btn.isDisabled().catch(() => false));
      if (disabled) {
        result.clicks.push('disabled:' + label);
        continue;
      }
      await btn.scrollIntoViewIfNeeded().catch(() => {});
      await btn.click({ timeout: 10000 });
      result.clicks.push(label);
      await sleep(4000);
      const conf = page.getByRole('button', { name: /^Confirm$/i }).first();
      if (await conf.count()) {
        await conf.click().catch(() => {});
        result.clicks.push('confirm:' + label);
        await sleep(2000);
      }
    }

    await sleep(15000);
    t = await page.locator('body').innerText();
    fs.writeFileSync(path.join(OUT, 'law-b39-v10d-after.txt'), t.slice(0, 16000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10d-after.png'), fullPage: true });
    result.url = page.url();
    result.snippet = t.slice(0, 5000);
    result.ok = /Running|in progress|queued|Client PreQC|QC-Oracle-GLM|passed|Review required/i.test(t);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10d-result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(0);
  } catch (e) {
    result.error = String(e && e.stack ? e.stack : e);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10d-result.json'), JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
