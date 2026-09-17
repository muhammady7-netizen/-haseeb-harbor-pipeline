/**
 * Open latest law-b39 upload and run PreQC + QC check Re-run buttons.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const HOME = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const OUT = path.join(__dirname, 'tmp-pw');
const CSV = path.join(__dirname, 'tmp-pw/review.csv');
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
  const result = { ok: false, steps: [], clicks: [] };
  try {
    await page.goto(HOME, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(7000);

    // Dismiss banner if any
    const dismiss = page.getByRole('button', { name: /dismiss/i }).first();
    if (await dismiss.count()) {
      await dismiss.click().catch(() => {});
      result.steps.push('dismiss');
      await sleep(1000);
    }

    const open = page.getByRole('button', { name: /Open task/i }).first();
    if (!(await open.count())) throw new Error('no Open task button');
    await open.click();
    result.steps.push('open_task');
    await sleep(9000);
    result.url = page.url();

    let t = await page.locator('body').innerText();
    fs.writeFileSync(path.join(OUT, 'law-b39-v10b-task.txt'), t.slice(0, 16000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10b-task.png'), fullPage: true });
    const btns = await page.getByRole('button').allTextContents();
    fs.writeFileSync(path.join(OUT, 'law-b39-v10b-buttons.txt'), btns.join('\n'));
    console.log(JSON.stringify({ event: 'on_page', url: result.url, btnSample: btns.slice(0, 60) }));

    // Replace CSV if present on task page
    const replace = page.getByRole('button', { name: /Replace CSV/i }).first();
    if ((await replace.count()) && fs.existsSync(CSV)) {
      const [chooser] = await Promise.all([
        page.waitForEvent('filechooser', { timeout: 10000 }).catch(() => null),
        replace.click().catch(() => {}),
      ]);
      if (chooser) {
        await chooser.setFiles(CSV);
        result.clicks.push('replace_csv');
        await sleep(3000);
      }
    }

    // Prefer Re-run / Run for preQC then QC check — click all enabled Re-run
    const reruns = page.getByRole('button', { name: /^Re-run$/i });
    const n = await reruns.count();
    for (let i = 0; i < n; i++) {
      const btn = reruns.nth(i);
      const disabled =
        (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
        (await btn.isDisabled().catch(() => false));
      if (disabled) continue;
      await btn.scrollIntoViewIfNeeded().catch(() => {});
      await btn.click({ timeout: 8000 }).catch(() => {});
      result.clicks.push(`Re-run#${i}`);
      await sleep(3000);
      const conf = page.getByRole('button', { name: /^Confirm$/i }).first();
      if (await conf.count()) {
        await conf.click().catch(() => {});
        result.clicks.push('confirm');
        await sleep(1500);
      }
    }

    // Also try Run if no Re-run clicked
    if (!result.clicks.some((c) => c.startsWith('Re-run'))) {
      const runs = page.getByRole('button', { name: /^Run$/i });
      const rn = await runs.count();
      for (let i = 0; i < rn; i++) {
        const btn = runs.nth(i);
        const disabled =
          (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
          (await btn.isDisabled().catch(() => false));
        if (disabled) continue;
        await btn.click({ timeout: 8000 }).catch(() => {});
        result.clicks.push(`Run#${i}`);
        await sleep(3000);
      }
    }

    await sleep(10000);
    t = await page.locator('body').innerText();
    fs.writeFileSync(path.join(OUT, 'law-b39-v10b-after.txt'), t.slice(0, 16000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10b-after.png'), fullPage: true });
    result.url = page.url();
    result.snippet = t.slice(0, 4000);
    result.ok =
      /preQC|QC check|Running|in progress|passed|Review required|no blocking/i.test(t) &&
      /custody-letter|Harbor package|Upload new version/i.test(t);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10b-result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(result.ok ? 0 : 2);
  } catch (e) {
    result.error = String(e && e.stack ? e.stack : e);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10b-result.json'), JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
