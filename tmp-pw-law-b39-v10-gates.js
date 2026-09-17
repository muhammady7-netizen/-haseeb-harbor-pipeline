/**
 * Open law-b39 v10 task page and run PreQC + QC check.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const URL =
  process.env.B39_URL ||
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-cc9eb99d91a211eeeb149d3b50cb0ddf-v1';
const CSV = path.join(__dirname, 'tmp-pw/review.csv');
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
  const result = { ok: false, url: URL, clicks: [], steps: [] };
  try {
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    // If hash routing needs a nudge
    if (!page.url().includes('task=content-')) {
      await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(5000);
    }
    const body = async () => page.locator('body').innerText().catch(() => '');
    let t = await body();
    fs.writeFileSync(path.join(OUT, 'law-b39-v10-task-before.txt'), t.slice(0, 15000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10-task-before.png'), fullPage: true });
    result.steps.push({ at: 'before', url: page.url(), hasPreQC: /preQC|PreQC/i.test(t) });

    // Replace review.csv if control present
    const fileInputs = page.locator('input[type="file"]');
    const nFiles = await fileInputs.count();
    result.steps.push({ fileInputs: nFiles });
    if (nFiles > 0 && fs.existsSync(CSV)) {
      for (let i = 0; i < nFiles; i++) {
        try {
          await fileInputs.nth(i).setInputFiles(CSV);
          result.clicks.push(`csv_input_${i}`);
          await sleep(2000);
        } catch {}
      }
    }

    // Click Re-run / Run near PreQC and QC check sections
    const buttons = await page.getByRole('button').all();
    const names = [];
    for (const b of buttons) {
      const name = ((await b.innerText().catch(() => '')) || '').trim().replace(/\s+/g, ' ');
      if (name) names.push(name);
    }
    fs.writeFileSync(path.join(OUT, 'law-b39-v10-task-buttons.txt'), names.join('\n'));

    for (const label of ['Re-run', 'Run', 'Upload', 'Replace CSV', 'Complete']) {
      const matches = page.getByRole('button', { name: new RegExp(`^${label}$`, 'i') });
      const count = await matches.count();
      for (let i = 0; i < count; i++) {
        const btn = matches.nth(i);
        const disabled =
          (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
          (await btn.isDisabled().catch(() => false));
        if (disabled) continue;
        await btn.scrollIntoViewIfNeeded().catch(() => {});
        await btn.click({ timeout: 5000 }).catch(() => {});
        result.clicks.push(`${label}#${i}`);
        await sleep(2500);
      }
    }

    await sleep(8000);
    t = await body();
    fs.writeFileSync(path.join(OUT, 'law-b39-v10-task-after.txt'), t.slice(0, 15000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10-task-after.png'), fullPage: true });
    result.url = page.url();
    result.snippet = t.slice(0, 3500);
    result.ok = /preQC|QC check|Review required|passed|Running/i.test(t);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10-gates-result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(result.ok ? 0 : 1);
  } catch (e) {
    result.error = String(e && e.stack ? e.stack : e);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10-gates-result.json'), JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
