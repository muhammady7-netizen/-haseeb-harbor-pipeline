/**
 * Headless Final-QC poller for h40 v10. Never clicks PreQC.
 * Opens task from root by stem, waits for Oracle/GLM/Harbor outcome.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const STEM = 'health-h40-critical-result-acknowledgement';
const DIRECT =
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

function parse(t) {
  const oracle =
    /Oracle\s+Passed[^\d]*([\d.]+)/i.exec(t)?.[1] ||
    (/Oracle\s+Failed/i.test(t) ? 'FAIL' : null);
  const glmPass = /(?:GLM[^\n]{0,40}?|eligible[^\n]{0,40}?)(\d)\s*\/\s*4/i.exec(t)?.[1];
  const rewards = [...t.matchAll(/reward[^\d]*([\d.]+)/gi)].map((m) => m[1]).slice(0, 8);
  return {
    oracle,
    glm: glmPass ? `${glmPass}/4` : null,
    rewards,
    qc_running: /QC running|Starting…|starting now|Harbor Check.*running/i.test(t),
    harbor_fail: /Harbor Check[\s\S]{0,80}FAIL|blocking finding/i.test(t),
    harbor_pass: /Harbor Check[\s\S]{0,80}PASS|no blocking/i.test(t),
    ready: /READY_FOR_FINALIZATION/i.test(t),
    changes: /changes needed/i.test(t),
  };
}

(async () => {
  for (let i = 0; i < 48; i++) {
    clearLocks();
    const browser = await chromium.launchPersistentContext(PROFILE, {
      headless: true,
      channel: 'chrome',
      acceptDownloads: true,
      args: ['--disable-blink-features=AutomationControlled'],
    });
    try {
      const page = browser.pages()[0] || (await browser.newPage());
      await page.goto(DIRECT, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(5000);
      let t = await page.locator('body').innerText().catch(() => '');
      // if stuck on root list, open stem
      if (!/Upload new version|QC-Oracle-GLM|Evaluation/i.test(t)) {
        await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
        await sleep(4000);
        const link = page.getByText(STEM, { exact: false }).first();
        if (await link.count()) {
          await link.click({ timeout: 15000 });
          await sleep(7000);
        }
        t = await page.locator('body').innerText().catch(() => '');
      }
      fs.writeFileSync(path.join(OUT, `h40-v10-final-poll-${i}.txt`), `URL=${page.url()}\n\n${t}`);
      const s = parse(t);
      console.log(JSON.stringify({ event: 'poll', i, url: page.url(), ...s, head: t.replace(/\s+/g, ' ').slice(0, 280) }));

      // Never touch PreQC. If Final QC idle and button enabled, start it.
      const btn = page.getByRole('button', { name: /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i }).first();
      if (await btn.count()) {
        const disabled =
          (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
          (await btn.isDisabled().catch(() => false));
        if (!disabled && !s.qc_running && !s.oracle) {
          await btn.click();
          console.log(JSON.stringify({ event: 'clicked_final_qc_only' }));
          await sleep(5000);
        }
      }

      if (s.oracle || s.ready || s.harbor_fail || s.changes) {
        console.log(JSON.stringify({ event: 'terminal', ...s, url: page.url() }));
        fs.writeFileSync(path.join(OUT, 'h40-v10-final-done.txt'), `URL=${page.url()}\n\n${t}`);
        await browser.close().catch(() => {});
        process.exit(0);
      }
    } catch (e) {
      console.log(JSON.stringify({ event: 'poll_error', i, error: String(e).slice(0, 200) }));
    } finally {
      // closed in try on terminal; otherwise here
    }
    try {
      /* browser may already be closed */
    } catch {}
    await sleep(30000);
  }
  console.log(JSON.stringify({ event: 'timeout' }));
  process.exit(2);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
