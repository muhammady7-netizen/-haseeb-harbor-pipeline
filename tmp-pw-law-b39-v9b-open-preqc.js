/**
 * Open latest law-b39 task from list, start Client PreQC / deep-dive Run.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const HOME = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const DIRECT =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-84eb7a39a92e9cea6ddd6dd2f0ae7a8d-v1';
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
  const result = { ok: false, steps: [] };
  try {
    await page.goto(HOME, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(6000);
    // Click first Open task (latest upload)
    const open = page.getByRole('button', { name: /Open task/i }).first();
    if (await open.count()) {
      await open.click();
      result.steps.push('open_task');
      await sleep(8000);
    } else {
      await page.goto(DIRECT, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(8000);
      // if still list, click open again
      const open2 = page.getByRole('button', { name: /Open task/i }).first();
      if (await open2.count()) {
        await open2.click();
        result.steps.push('open_task_retry');
        await sleep(8000);
      }
    }
    result.url = page.url();
    let t = await page.locator('body').innerText();
    fs.writeFileSync(path.join(OUT, 'law-b39-v9b-task.txt'), t.slice(0, 12000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v9b-task.png'), fullPage: true });
    const btns = await page.getByRole('button').allTextContents();
    fs.writeFileSync(path.join(OUT, 'law-b39-v9b-buttons.txt'), btns.join('\n'));
    console.log(JSON.stringify({ event: 'on_page', url: result.url, btns: btns.slice(0, 40) }));

    // Click PreQC / Run / Re-run for deep-dive
    for (const re of [
      /Run client preQC/i,
      /Run PreQC/i,
      /Client PreQC/i,
      /^Re-run$/i,
      /^Run$/i,
    ]) {
      const b = page.getByRole('button', { name: re }).first();
      if (!(await b.count())) continue;
      const disabled =
        (await b.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
        (await b.isDisabled().catch(() => false));
      if (disabled) {
        result.steps.push('disabled:' + String(re));
        continue;
      }
      await b.click();
      result.steps.push('click:' + String(re));
      await sleep(4000);
      // confirm if needed
      const conf = page.getByRole('button', { name: /^Confirm$/i }).first();
      if (await conf.count()) {
        await conf.click().catch(() => {});
        result.steps.push('confirm');
        await sleep(2000);
      }
      break;
    }

    await sleep(6000);
    t = await page.locator('body').innerText();
    fs.writeFileSync(path.join(OUT, 'law-b39-v9b-after.txt'), t.slice(0, 12000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v9b-after.png'), fullPage: true });
    result.url = page.url();
    result.snippet = t.slice(0, 2500);
    result.ok = /preqc|deep-dive|running|in progress|not run|FAIL|PASS|QC check/i.test(t);
    fs.writeFileSync(path.join(OUT, 'law-b39-v9b-result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(result.ok ? 0 : 2);
  } catch (e) {
    result.error = String(e && e.stack ? e.stack : e);
    fs.writeFileSync(path.join(OUT, 'law-b39-v9b-result.json'), JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
