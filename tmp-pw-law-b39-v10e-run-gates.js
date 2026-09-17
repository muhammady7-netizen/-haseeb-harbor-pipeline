/**
 * Click PreQC / QC-Oracle-GLM via getByText (may not be role=button).
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
    headless: false, // briefly headed can help with SPA; still automated
    channel: 'chrome',
    viewport: { width: 1440, height: 960 },
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = context.pages()[0] || (await context.newPage());
  const result = { ok: false, clicks: [] };
  try {
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    // Force hash navigation again
    await page.evaluate((u) => {
      window.location.hash = u.split('#')[1] || '';
    }, URL);
    await sleep(3000);

    let t = await page.locator('body').innerText();
    if (!/Run client preQC/i.test(t)) {
      const open = page.getByText('Open task', { exact: false }).first();
      await open.click();
      await sleep(8000);
      t = await page.locator('body').innerText();
    }
    fs.writeFileSync(path.join(OUT, 'law-b39-v10e-before.txt'), t.slice(0, 12000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10e-before.png'), fullPage: true });

    for (const label of ['Run client preQC', 'Run QC-Oracle-GLM']) {
      const locators = [
        page.getByRole('button', { name: label }),
        page.getByText(label, { exact: true }),
        page.locator(`text=${label}`),
        page.locator(`button:has-text("${label}")`),
        page.locator(`a:has-text("${label}")`),
        page.locator(`[role="button"]:has-text("${label}")`),
      ];
      let done = false;
      for (const loc of locators) {
        if (!(await loc.count())) continue;
        const el = loc.first();
        await el.scrollIntoViewIfNeeded().catch(() => {});
        try {
          await el.click({ timeout: 8000 });
          result.clicks.push(label + ':' + (await el.evaluate((e) => e.tagName + '.' + (e.className || '')).catch(() => '?')));
          done = true;
          await sleep(5000);
          break;
        } catch (err) {
          result.clicks.push('fail:' + label + ':' + String(err).slice(0, 80));
        }
      }
      if (!done) result.clicks.push('notfound:' + label);
      // confirm dialogs
      const conf = page.getByText('Confirm', { exact: true }).first();
      if (await conf.count()) {
        await conf.click().catch(() => {});
        result.clicks.push('confirm');
        await sleep(2000);
      }
    }

    await sleep(20000);
    t = await page.locator('body').innerText();
    fs.writeFileSync(path.join(OUT, 'law-b39-v10e-after.txt'), t.slice(0, 16000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10e-after.png'), fullPage: true });
    result.snippet = t.slice(0, 4500);
    result.url = page.url();
    result.ok = /Running|in progress|queued|passed|Review required|Last run/i.test(t);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10e-result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(0);
  } catch (e) {
    result.error = String(e && e.stack ? e.stack : e);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10e-result.json'), JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
