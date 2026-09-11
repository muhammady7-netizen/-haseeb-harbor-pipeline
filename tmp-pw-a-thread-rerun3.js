/** Click Re-run on the-thread using known #task URL (qc_queue openLatest is broken). */
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
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 120000 }).catch(() => null);
  await sleep(12000);
  // Prefer exact button locator
  let clicked = false;
  const candidates = [
    page.locator('button:has-text("Re-run QC-Oracle-GLM")').first(),
    page.locator('button:has-text("Run QC-Oracle-GLM")').first(),
    page.getByRole('button', { name: /Re-run QC-Oracle-GLM/i }).first(),
    page.getByRole('button', { name: /Run QC-Oracle-GLM/i }).first(),
  ];
  for (const loc of candidates) {
    const n = await loc.count();
    if (!n) continue;
    const disabled = (await loc.getAttribute('aria-disabled').catch(() => null)) === 'true';
    const title = await loc.getAttribute('title').catch(() => '');
    console.log(JSON.stringify({ event: 'found', text: await loc.innerText().catch(() => ''), disabled, title }));
    if (disabled || /slots are currently in use/i.test(title || '')) continue;
    await loc.scrollIntoViewIfNeeded().catch(() => {});
    await loc.click({ force: true, timeout: 15000 });
    clicked = true;
    console.log(JSON.stringify({ event: 'clicked' }));
    break;
  }
  await sleep(15000);
  const t = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/a-thread-rerun3.txt', t);
  console.log(
    JSON.stringify({
      clicked,
      url: page.url(),
      lastRun: (t.match(/Last run:[^\n]+/i) || [])[0],
      oracleLine: (t.match(/Oracle[^\n]{0,80}/) || [])[0],
      glmLine: (t.match(/GLM-5\.2[^\n]{0,80}/) || [])[0],
      runHistory: (t.match(/\d+ runs?[^\n]{0,40}/) || [])[0],
    })
  );
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
