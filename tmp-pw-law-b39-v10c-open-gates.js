/**
 * Open latest law-b39 upload (link or button) and run PreQC + QC Re-run.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const HOME = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const DIRECT =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-cc9eb99d91a211eeeb149d3b50cb0ddf-v1';
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

async function bodyText(page) {
  return page.locator('body').innerText().catch(() => '');
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
    await page.goto(DIRECT, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    let t = await bodyText(page);
    // If still on list, click first Open task (button OR link OR text)
    if (!/Harbor package|Upload new version|preQC \(deterministic/i.test(t)) {
      await page.goto(HOME, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(6000);
      t = await bodyText(page);
      fs.writeFileSync(path.join(OUT, 'law-b39-v10c-list.txt'), t.slice(0, 8000));

      const candidates = [
        page.getByRole('link', { name: /Open task/i }).first(),
        page.getByRole('button', { name: /Open task/i }).first(),
        page.locator('a', { hasText: /Open task/i }).first(),
        page.locator('text=Open task').first(),
        page.locator('text=→').first(),
      ];
      let clicked = false;
      for (const c of candidates) {
        if (await c.count()) {
          await c.click({ timeout: 8000 }).catch(() => {});
          result.steps.push('clicked_open');
          clicked = true;
          await sleep(9000);
          break;
        }
      }
      if (!clicked) {
        // click the first task title
        const title = page.getByText(/L16 custody letter instruction audit/i).first();
        if (await title.count()) {
          await title.click();
          result.steps.push('clicked_title');
          await sleep(9000);
        }
      }
    }

    result.url = page.url();
    t = await bodyText(page);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10c-task.txt'), t.slice(0, 18000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10c-task.png'), fullPage: true });
    const btns = await page.getByRole('button').allTextContents();
    const links = await page.getByRole('link').allTextContents();
    fs.writeFileSync(
      path.join(OUT, 'law-b39-v10c-controls.txt'),
      'BUTTONS\n' + btns.join('\n') + '\n\nLINKS\n' + links.join('\n')
    );
    console.log(
      JSON.stringify({
        event: 'on_page',
        url: result.url,
        btnSample: btns.slice(0, 80),
        hasHarbor: /Harbor package/i.test(t),
      })
    );

    // Replace CSV
    const replace = page.getByRole('button', { name: /Replace CSV/i }).first();
    if ((await replace.count()) && fs.existsSync(CSV)) {
      const chooserPromise = page.waitForEvent('filechooser', { timeout: 10000 }).catch(() => null);
      await replace.click().catch(() => {});
      const chooser = await chooserPromise;
      if (chooser) {
        await chooser.setFiles(CSV);
        result.clicks.push('replace_csv');
        await sleep(2500);
      }
    }

    // Click all Re-run
    const reruns = page.getByRole('button', { name: /^Re-run$/i });
    const n = await reruns.count();
    result.steps.push({ rerunCount: n });
    for (let i = 0; i < n; i++) {
      const btn = reruns.nth(i);
      const disabled =
        (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
        (await btn.isDisabled().catch(() => false));
      if (disabled) continue;
      await btn.scrollIntoViewIfNeeded().catch(() => {});
      await btn.click({ timeout: 8000 }).catch(() => {});
      result.clicks.push(`Re-run#${i}`);
      await sleep(2500);
      const conf = page.getByRole('button', { name: /^Confirm$/i }).first();
      if (await conf.count()) {
        await conf.click().catch(() => {});
        result.clicks.push('confirm');
        await sleep(1000);
      }
    }

    // Run buttons if needed
    if (!result.clicks.some((c) => String(c).startsWith('Re-run'))) {
      const runs = page.getByRole('button', { name: /^Run$/i });
      for (let i = 0; i < (await runs.count()); i++) {
        const btn = runs.nth(i);
        const disabled =
          (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
          (await btn.isDisabled().catch(() => false));
        if (disabled) continue;
        await btn.click({ timeout: 8000 }).catch(() => {});
        result.clicks.push(`Run#${i}`);
        await sleep(2500);
      }
    }

    await sleep(12000);
    t = await bodyText(page);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10c-after.txt'), t.slice(0, 18000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10c-after.png'), fullPage: true });
    result.url = page.url();
    result.snippet = t.slice(0, 4500);
    result.ok = /preQC|QC check|Running|passed|Review required|no blocking|Harbor package/i.test(t);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10c-result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(0);
  } catch (e) {
    result.error = String(e && e.stack ? e.stack : e);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10c-result.json'), JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
