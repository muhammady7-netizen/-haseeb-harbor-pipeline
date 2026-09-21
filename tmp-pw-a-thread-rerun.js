/**
 * Re-run QC-Oracle-GLM on the-thread (oracle crash recovery).
 * Also dump status; do not re-upload.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-5cc146d448ffc4f0a07bba4ad679dd1f-v1';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(7000);
  let t = await page.locator('body').innerText().catch(() => '');
  fs.writeFileSync('tmp-pw/a-thread-before-rerun.txt', t);
  const slotsFull = /run slots? are currently in use|\d+\s+runs?\s+in flight/i.test(t);
  console.log(JSON.stringify({ event: 'before', url: page.url(), slotsFull, oracleFail: /Oracle Failed|crashed/i.test(t), head: t.slice(0, 800) }));

  if (slotsFull) {
    console.log(JSON.stringify({ event: 'defer', reason: 'slots_full' }));
    process.exit(0);
  }

  const btn =
    page.getByRole('button', { name: /Re-run QC-Oracle-GLM/i }).first() ||
    page.getByRole('button', { name: /Run QC-Oracle-GLM/i }).first();
  let clicked = false;
  for (const re of [/Re-run QC-Oracle-GLM/i, /Run QC-Oracle-GLM/i]) {
    const b = page.getByRole('button', { name: re }).first();
    if (!(await b.count())) continue;
    const disabled = (await b.getAttribute('aria-disabled').catch(() => null)) === 'true';
    if (disabled) {
      console.log(JSON.stringify({ event: 'btn_disabled', re: String(re) }));
      continue;
    }
    await b.click({ timeout: 10000 });
    clicked = true;
    console.log(JSON.stringify({ event: 'clicked', re: String(re) }));
    break;
  }
  await sleep(10000);
  t = await page.locator('body').innerText().catch(() => '');
  fs.writeFileSync('tmp-pw/a-thread-after-rerun.txt', t);
  console.log(
    JSON.stringify({
      event: 'after',
      clicked,
      url: page.url(),
      running: /running|queued|Waiting/i.test(t),
      head: t.slice(0, 1000),
    })
  );
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
