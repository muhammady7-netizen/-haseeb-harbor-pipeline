/**
 * fin-f53 ONLY — OpenCode-style headless portal upload + FINAL QC.
 * Per STRICT-RULES.md / tmp-pw-qc-queue-B.js / tmp-pw-g806-finalqc.js:
 *   PreQC is optional/advisory — NEVER click Client PreQC / dismiss findings.
 *   Final gate only: Run / Re-run QC-Oracle-GLM.
 * - Shared profile: ~/.config/opencode/chrome-profile
 * - headless: true (no visible Chrome thrash)
 * - NEVER kill chrome.exe; wait if profile busy
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const ZIP = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-fin-f53.zip';
const STEM = 'fin-f53-deposit-account-fee-assessment-audit';
const OUT = path.join(__dirname, 'tmp-pw');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const dump = (n, t) => fs.writeFileSync(path.join(OUT, n), t || '');

async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}

async function clickFinalQcOnly(page) {
  // NEVER click Client PreQC / Run client preQC
  for (const re of [/Re-run QC-Oracle-GLM/i, /Run QC-Oracle-GLM/i]) {
    const btn = page.getByRole('button', { name: re }).first();
    if (!(await btn.count())) continue;
    const disabled =
      (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
      (await btn.isDisabled().catch(() => false));
    if (disabled) {
      console.log(JSON.stringify({ event: 'oracle_btn_disabled', re: String(re) }));
      continue;
    }
    await btn.click({ timeout: 15000 });
    console.log(JSON.stringify({ event: 'clicked_final_qc', re: String(re) }));
    await sleep(6000);
    return true;
  }
  for (const re of [/Re-run QC-Oracle-GLM/i, /Run QC-Oracle-GLM/i]) {
    const loc = page.getByText(re).first();
    if ((await loc.count()) && (await loc.isVisible().catch(() => false))) {
      await loc.click({ timeout: 10000 }).catch(() => null);
      console.log(JSON.stringify({ event: 'clicked_final_qc_text', re: String(re) }));
      await sleep(6000);
      return true;
    }
  }
  return false;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  if (!fs.existsSync(ZIP)) {
    console.log(JSON.stringify({ event: 'zip_missing', ZIP }));
    process.exit(4);
  }

  let browser;
  for (let i = 1; i <= 90; i++) {
    try {
      browser = await chromium.launchPersistentContext(PROFILE, {
        headless: true,
        channel: 'chrome',
        acceptDownloads: true,
        args: ['--disable-blink-features=AutomationControlled'],
      });
      console.log(JSON.stringify({ event: 'LAUNCHED', attempt: i }));
      break;
    } catch (e) {
      console.log(
        JSON.stringify({
          event: 'PROFILE_BUSY_WAIT',
          attempt: i,
          error: String(e).slice(0, 160),
        }),
      );
      await sleep(45 * 1000);
    }
  }
  if (!browser) {
    console.log(JSON.stringify({ event: 'PROFILE_BUSY_TIMEOUT' }));
    process.exit(3);
  }

  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(60000);

  try {
    await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(5000);
    let t = await body(page);
    dump('f53-headless-root.txt', t);
    if (
      (/Sign in with Google|accounts\.google/i.test(t) || /accounts\.google\.com/i.test(page.url())) &&
      !/muhammad\.y7@turing\.com/i.test(t)
    ) {
      console.log(JSON.stringify({ event: 'login_required' }));
      process.exit(2);
    }
    console.log(JSON.stringify({ event: 'logged_in' }));

    const before = page.url();
    await page.locator('input[type="file"]').first().setInputFiles(ZIP);
    console.log(JSON.stringify({ event: 'uploaded', zip: ZIP }));

    for (let i = 0; i < 45; i++) {
      await sleep(1000);
      const url = page.url();
      t = await body(page);
      if (url !== before && /#task=/.test(url)) break;
      if (/Upload new version|Run QC-Oracle-GLM/i.test(t) && /fin-f53|latest|v\d+/i.test(t)) break;
    }
    dump('f53-headless-after-upload.txt', await body(page));
    console.log(JSON.stringify({ event: 'after_upload', url: page.url() }));

    if (!/#task=/.test(page.url())) {
      const openInRow = page
        .locator('div')
        .filter({ hasText: new RegExp(STEM.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) })
        .getByText(/^Open$/i)
        .first();
      if (await openInRow.count()) {
        await openInRow.scrollIntoViewIfNeeded().catch(() => {});
        await openInRow.click({ timeout: 20000 });
        await sleep(9000);
      } else {
        const link = page.getByText(STEM, { exact: false }).first();
        if (await link.count()) {
          await link.scrollIntoViewIfNeeded().catch(() => {});
          await link.click({ timeout: 15000 });
          await sleep(7000);
        }
      }
    }
    console.log(JSON.stringify({ event: 'on_task', url: page.url(), skipped_preqc: true }));

    // Portal allows up to 4 concurrent Oracle+GLM sessions — always try Final QC.
    // Only treat as full if the button is disabled / click fails (not the old "3 slots" copy).
    t = await body(page);
    if (/Running now|In queue|queued|QC running|Oracle Waiting|GLM[^\n]{0,40}Waiting/i.test(t)) {
      console.log(JSON.stringify({ event: 'already_queued', skipped_preqc: true }));
    } else {
      const started = await clickFinalQcOnly(page);
      const slotsHint = /(?:3|4) run slots are currently in use|Your (?:3|4) run slots|4-task limit|3-task limit/i.test(t);
      console.log(
        JSON.stringify({
          event: 'final_qc',
          started,
          skipped_preqc: true,
          max_sessions: 4,
          slots_hint: slotsHint,
        }),
      );
      if (!started && slotsHint) {
        console.log(JSON.stringify({ event: 'slots_full_wait', max_sessions: 4 }));
      }
      await sleep(8000);
    }

    t = await body(page);
    dump('f53-headless-final.txt', `URL=${page.url()}\n\n${t}`);
    const lines = t
      .split(/\n/)
      .filter((l) => /Oracle|GLM|Running|Passed|Failed|queue|slots|Submit|TOO_EASY|Waiting/i.test(l))
      .slice(0, 40);
    console.log(JSON.stringify({ event: 'final', url: page.url(), skipped_preqc: true, lines }));
  } finally {
    await browser.close().catch(() => {});
  }
})().catch((e) => {
  console.log(JSON.stringify({ event: 'FAIL', error: String(e) }));
  process.exit(1);
});
