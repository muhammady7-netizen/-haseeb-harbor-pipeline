const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const URL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-84eb7a39a92e9cea6ddd6dd2f0ae7a8d-v1';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function clearLocks() {
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try { fs.unlinkSync(path.join(PROFILE, n)); } catch {}
  }
}
(async () => {
  clearLocks();
  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: true, channel: 'chrome', viewport: { width: 1440, height: 960 },
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = context.pages()[0] || await context.newPage();
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  // Ensure on task page
  if (!(await page.getByRole('button', { name: /Run client preQC/i }).count())) {
    await page.getByRole('button', { name: /Open task/i }).first().click().catch(() => {});
    await sleep(6000);
  }
  const btn = page.getByRole('button', { name: /Run client preQC/i }).first();
  console.log(JSON.stringify({ has: await btn.count(), disabled: await btn.isDisabled().catch(() => null) }));
  await btn.click({ force: true });
  await sleep(2000);
  const conf = page.getByRole('button', { name: /^Confirm$/i });
  if (await conf.count()) await conf.first().click().catch(() => {});
  for (let i = 0; i < 24; i++) {
    await sleep(10000);
    const t = await page.locator('body').innerText();
    const status = {
      i,
      running: /Client preQC.*(running|in progress|queued)|PreQC.*(running|in progress)/i.test(t),
      done: /Client preQC.*(pass|fail|complete|PASS|FAIL)|preQC.*just now/i.test(t),
      notYet: /Client preQC[\s\S]{0,80}Not run yet/i.test(t),
      slots: /slots? are currently in use/i.test(t),
    };
    console.log(JSON.stringify(status));
    fs.writeFileSync(path.join(OUT, 'law-b39-v9c-poll.txt'), t.slice(0, 8000));
    if (status.running || status.done || (!status.notYet && i > 1)) break;
    if (status.notYet && i % 3 === 2) {
      await btn.click({ force: true }).catch(() => {});
    }
  }
  await page.screenshot({ path: path.join(OUT, 'law-b39-v9c-final.png'), fullPage: true });
  const final = await page.locator('body').innerText();
  fs.writeFileSync(path.join(OUT, 'law-b39-v9c-final.txt'), final.slice(0, 10000));
  console.log(JSON.stringify({ url: page.url(), head: final.slice(0, 1200) }));
  await context.close().catch(() => {});
})();
