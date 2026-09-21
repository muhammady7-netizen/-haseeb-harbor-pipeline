/**
 * Headless poll Final QC only (skip PreQC) for h40 v10 #6183c5.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-6183c5072ed5fbd2ff923a821ff077d3-v1';
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
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(6000);
  await page.evaluate((u) => {
    if (location.href !== u) location.href = u;
  }, URL);
  await sleep(5000);
  const t = await page.locator('body').innerText().catch(() => '');
  fs.writeFileSync(path.join(OUT, 'h40-v10-finalqc-now.txt'), `URL=${page.url()}\n\n${t}`);

  // If Final QC not running and button enabled, click ONLY Oracle+GLM (never PreQC)
  const oracleBtn = page.getByRole('button', { name: /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i }).first();
  let clicked = false;
  if (await oracleBtn.count()) {
    const disabled =
      (await oracleBtn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
      (await oracleBtn.isDisabled().catch(() => false));
    const running = /QC running|Oracle Passed|Oracle Failed|Starting|Harbor Check/i.test(t);
    if (!disabled && !running) {
      await oracleBtn.click();
      clicked = true;
      await sleep(5000);
    }
  }
  const after = await page.locator('body').innerText().catch(() => '');
  fs.writeFileSync(path.join(OUT, 'h40-v10-finalqc-after.txt'), `URL=${page.url()}\n\n${after}`);
  console.log(
    JSON.stringify({
      event: 'status',
      clicked_oracle: clicked,
      skipped_preqc: true,
      url: page.url(),
      signals: {
        starting: /Starting|starting now/i.test(after),
        qc_running: /QC running/i.test(after),
        oracle_pass: /Oracle Passed/i.test(after),
        oracle_fail: /Oracle Failed/i.test(after),
        harbor: /Harbor Check/i.test(after),
        ready: /READY_FOR_FINALIZATION|ready for finalization/i.test(after),
        glm: (after.match(/GLM[^\n]{0,80}/i) || [null])[0],
      },
      head: after.replace(/\s+/g, ' ').slice(0, 700),
    })
  );
  await browser.close().catch(() => {});
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
