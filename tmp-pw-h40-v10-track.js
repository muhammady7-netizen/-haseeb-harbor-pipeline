/**
 * Keep tracking h40 v10 Final QC until GLM+Harbor settle.
 * Never clicks PreQC. Exits only on terminal outcome (not Oracle alone).
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
  const oraclePass = /Oracle\s+Passed/i.test(t);
  const oracleScore = /Passed\s+([\d.]+)\s+on/i.exec(t)?.[1] || (/Oracle\s+Passed\s+([\d.]+)/i.exec(t)?.[1] ?? null);
  const oracleFail = /Oracle\s+Failed/i.test(t);
  const glmRunning = /GLM-5\.2\s*[×x]4\s+difficulty\s+Running/i.test(t);
  const glmWaiting = /GLM-5\.2\s*[×x]4\s+difficulty\s+Waiting/i.test(t);
  // count reward 1.0 / scored passes in difficulty section
  const diff = /GLM-5\.2\s*[×x]4\s+DIFFICULTY([\s\S]{0,1200})/i.exec(t)?.[1] || '';
  const ones = (diff.match(/\b1(?:\.0+)?\b/g) || []).length;
  const glmFrac =
    /(\d)\s*\/\s*4/.exec(t)?.[0] ||
    (/(\d)\s+of\s+4/.exec(diff) || [])[0] ||
    null;
  const running =
    /Running now|Oracle Running|running ·|4 scored GLM runs are in progress|Harbor Check[\s\S]{0,40}running/i.test(
      t
    );
  const harborFail = /Harbor Check[\s\S]{0,120}FAIL|blocking finding/i.test(t);
  const harborPass = /Harbor Check[\s\S]{0,120}PASS/i.test(t);
  const ready = /READY_FOR_FINALIZATION/i.test(t);
  const changes = /changes needed/i.test(t);
  const glmDone = /GLM-5\.2\s*[×x]4\s+difficulty\s+(Passed|Failed|Complete|Done)/i.test(t) ||
    (!glmRunning && !glmWaiting && /oracle — Oracle completed/i.test(t) && /glm —/i.test(t) && !running);
  return {
    oracle: oracleFail ? 'FAIL' : oraclePass ? oracleScore || '1.0' : null,
    glmRunning,
    glmWaiting,
    glmFrac,
    ones,
    running,
    harborFail,
    harborPass,
    ready,
    changes,
    glmDone,
  };
}

function terminal(s) {
  if (s.ready || s.harborFail || s.changes) return true;
  // finished eval: not running and we have oracle + harbor section resolved
  if (s.oracle && !s.running && (s.harborPass || s.harborFail || s.ready || s.changes)) return true;
  return false;
}

(async () => {
  for (let i = 0; i < 120; i++) {
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
      const idx = Math.max(t.indexOf('QC-Oracle-GLM'), t.indexOf('Oracle Passed'), 0);
      const snip = t.slice(idx, idx + 320).replace(/\s+/g, ' ');
      console.log(JSON.stringify({ event: 'poll', i, url: page.url(), ...s, snip }));
      fs.writeFileSync(
        path.join(OUT, 'h40-v10-track-status.json'),
        JSON.stringify({ at: new Date().toISOString(), ...s, url: page.url() }, null, 2)
      );

      if (terminal(s)) {
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
    await sleep(45000);
  }
  console.log(JSON.stringify({ event: 'timeout' }));
  process.exit(2);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
