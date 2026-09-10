/**
 * Reliable headless Final-QC poll for h40 v10 (#f077d3).
 * Relaunches each cycle; never clicks PreQC.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const STEM = 'health-h40-critical-result-acknowledgement';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function clearLocks() {
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
    } catch {}
  }
}

function summarize(t) {
  const oraclePass = /Oracle\s+Passed\s*([\d.]+)/i.exec(t);
  const oracleFail = /Oracle\s+Failed/i.test(t);
  const glmBlock = /GLM-5\.2\s*[×x]4[\s\S]{0,400}/i.exec(t)?.[0] || '';
  const glmPass = /(\d)\s*\/\s*4/.exec(glmBlock);
  const running =
    /Oracle Running|Running now|running ·|Waiting for Oracle|GLM-5\.2[^\n]*Running/i.test(t);
  const harborFail = /Harbor Check[\s\S]{0,120}FAIL|blocking finding/i.test(t);
  const ready = /READY_FOR_FINALIZATION/i.test(t);
  const changes = /changes needed/i.test(t);
  return {
    oracle: oraclePass ? oraclePass[1] : oracleFail ? 'FAIL' : null,
    glm: glmPass ? `${glmPass[1]}/4` : null,
    running,
    harborFail,
    ready,
    changes,
  };
}

(async () => {
  for (let i = 0; i < 80; i++) {
    clearLocks();
    let browser;
    try {
      browser = await chromium.launchPersistentContext(PROFILE, {
        headless: true,
        channel: 'chrome',
        acceptDownloads: true,
        args: ['--disable-blink-features=AutomationControlled'],
      });
      const page = browser.pages()[0] || (await browser.newPage());
      await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(4500);
      const card = page.getByText(/health-h40-critical-result-acknowledgement#f077d3/i).first();
      if (await card.count()) await card.click({ timeout: 20000 });
      else await page.getByText(STEM, { exact: false }).first().click({ timeout: 20000 });
      await sleep(8000);
      const t = await page.locator('body').innerText();
      fs.writeFileSync(path.join(OUT, 'h40-v10-live.txt'), `URL=${page.url()}\n\n${t}`);
      const s = summarize(t);
      const idx = t.indexOf('QC-Oracle-GLM');
      const snip = t
        .slice(idx >= 0 ? idx : 0, (idx >= 0 ? idx : 0) + 280)
        .replace(/\s+/g, ' ');
      console.log(JSON.stringify({ event: 'poll', i, url: page.url(), ...s, snip }));

      if (s.oracle || s.ready || s.harborFail || s.changes) {
        console.log(JSON.stringify({ event: 'done', ...s, url: page.url() }));
        fs.writeFileSync(path.join(OUT, 'h40-v10-final-done.txt'), `URL=${page.url()}\n\n${t}`);
        await browser.close().catch(() => {});
        process.exit(0);
      }
    } catch (e) {
      console.log(JSON.stringify({ event: 'poll_error', i, error: String(e).slice(0, 220) }));
    } finally {
      if (browser) await browser.close().catch(() => {});
    }
    await sleep(40000);
  }
  console.log(JSON.stringify({ event: 'timeout' }));
  process.exit(2);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
