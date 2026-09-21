/**
 * One-shot headless Final-QC status for h40 v10 — open from Recent tasks card.
 * Never clicks PreQC.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const STEM = 'health-h40-critical-result-acknowledgement';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
    } catch {}
  }
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  // Prefer the #f077d3 card (v10)
  let clicked = false;
  const exact = page.getByText(/health-h40-critical-result-acknowledgement#f077d3/i).first();
  if (await exact.count()) {
    await exact.click({ timeout: 15000 });
    clicked = true;
  } else {
    const link = page.getByText(STEM, { exact: false }).first();
    await link.click({ timeout: 15000 });
    clicked = true;
  }
  await sleep(8000);
  const t = await page.locator('body').innerText();
  fs.writeFileSync(path.join(OUT, 'h40-v10-status-now.txt'), `URL=${page.url()}\nclicked=${clicked}\n\n${t}`);

  const oraclePass = /Oracle\s+Passed\s*([\d.]+)/i.exec(t);
  const oracleFail = /Oracle\s+Failed/i.test(t);
  const glm = /(?:pass rate|GLM[^\n]{0,60}?)(\d)\s*\/\s*4/i.exec(t);
  const qcRunning = /QC running|Starting…|starting now/i.test(t);
  const harbor =
    /Harbor Check[\s\S]{0,120}?(PASS|FAIL|running|queued)/i.exec(t)?.[1] || null;
  const ready = /READY_FOR_FINALIZATION/i.test(t);
  const changes = /changes needed/i.test(t);

  // Start Final QC only if idle and button enabled
  let started = false;
  const btn = page.getByRole('button', { name: /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i }).first();
  if (await btn.count()) {
    const disabled =
      (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
      (await btn.isDisabled().catch(() => false));
    if (!disabled && !qcRunning && !oraclePass && !oracleFail) {
      await btn.click();
      started = true;
      await sleep(5000);
    }
  }
  const after = started ? await page.locator('body').innerText() : t;
  if (started) fs.writeFileSync(path.join(OUT, 'h40-v10-status-after-start.txt'), after);

  console.log(
    JSON.stringify({
      event: 'h40_status',
      url: page.url(),
      oracle: oraclePass ? oraclePass[1] : oracleFail ? 'FAIL' : null,
      glm: glm ? `${glm[1]}/4` : null,
      qcRunning,
      harbor,
      ready,
      changes,
      started_final_qc: started,
      head: after.replace(/\s+/g, ' ').slice(0, 900),
    })
  );
  await browser.close().catch(() => {});
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
