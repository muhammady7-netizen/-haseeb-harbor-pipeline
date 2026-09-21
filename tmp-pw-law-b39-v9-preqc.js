/**
 * Start Optional deep-dive (PreQC) + note QC check on latest law-b39 task.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const URL =
  process.env.B39_URL ||
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
  const result = { ok: false, url: URL, clicks: [] };
  try {
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    const body = async () => page.locator('body').innerText().catch(() => '');
    fs.writeFileSync(path.join(OUT, 'law-b39-v9-preqc-before.txt'), (await body()).slice(0, 10000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v9-preqc-before.png'), fullPage: true });

    const names = await page.getByRole('button').allTextContents();
    fs.writeFileSync(path.join(OUT, 'law-b39-v9-buttons.txt'), names.join('\n'));

    for (const label of [
      'Re-run',
      'Run',
      'Optional deep-dive checks',
      'Run client preQC',
      'Run PreQC',
    ]) {
      const btn = page.getByRole('button', { name: new RegExp(`^${label}$`, 'i') }).first();
      if (await btn.count()) {
        const disabled =
          (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
          (await btn.isDisabled().catch(() => false));
        if (!disabled) {
          await btn.click().catch(() => {});
          result.clicks.push(label);
          await sleep(2000);
        }
      }
    }
    // Prefer explicit Re-run on deep-dive if present
    const rerun = page.getByRole('button', { name: /^Re-run$/i }).first();
    if (await rerun.count()) {
      await rerun.click().catch(() => {});
      result.clicks.push('Re-run-deepdive');
      await sleep(3000);
    }

    await sleep(5000);
    const t = await body();
    fs.writeFileSync(path.join(OUT, 'law-b39-v9-preqc-after.txt'), t.slice(0, 12000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v9-preqc-after.png'), fullPage: true });
    result.snippet = t.slice(0, 2000);
    result.ok = true;
    fs.writeFileSync(path.join(OUT, 'law-b39-v9-preqc-result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(0);
  } catch (e) {
    result.error = String(e);
    fs.writeFileSync(path.join(OUT, 'law-b39-v9-preqc-result.json'), JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
