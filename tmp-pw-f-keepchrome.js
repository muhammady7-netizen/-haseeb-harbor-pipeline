/**
 * Session F — keepchrome queue (OpenCode style).
 * - ONE shared ~/.config/opencode/chrome-profile
 * - headless:true (no visible Chrome / no tab spam)
 * - Launch once; NEVER browser.close(); poll in-process
 * - Portal eval cap ~3 (configurable MAX_EVAL)
 * - Upload via setInputFiles (same as portal UI; invisible when headless)
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const G857 =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-2a489be4b73a943d11d2c52efefae8c6-v2';
const C251 =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-db0490a135ad1cc1e0d71549021ddef3-v1';
const ZIP_G857 = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g857.zip';
const OUT = path.join(__dirname, 'tmp-pw');
const MAX_EVAL = 3;
const POLL_MS = 90000;
const MAX_ROUNDS = 40;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
function log(o) {
  const line = typeof o === 'string' ? o : JSON.stringify(o);
  console.log(line);
  fs.appendFileSync(path.join(OUT, 'f-keepchrome.log'), line + '\n');
}
function dump(name, text) {
  fs.writeFileSync(path.join(OUT, name), text || '');
}
async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}

async function softClick(page, re, label) {
  const btn = page.getByRole('button', { name: re }).first();
  const loc = (await btn.count()) ? btn : page.getByText(re).first();
  if (!(await loc.count())) {
    log({ event: 'missing', label });
    return false;
  }
  const disabled = await loc.getAttribute('aria-disabled').catch(() => null);
  const title = await loc.getAttribute('title').catch(() => '');
  if (disabled === 'true' || /slots are currently in use/i.test(title || '')) {
    log({ event: 'disabled', label, title });
    return false;
  }
  try {
    await loc.click({ timeout: 8000 });
    await sleep(4000);
    log({ event: 'clicked', label });
    return true;
  } catch (e) {
    log({ event: 'click_fail', label, error: String(e).slice(0, 120) });
    return false;
  }
}

function summarize(t) {
  return {
    slotsFull: /3 run slots are currently in use/i.test(t),
    preqcReview: /Review required|trainer finding/i.test(t),
    preqcNotRun: /Client [Pp]reQC[\s\S]{0,80}[Nn]ot run yet/i.test(t),
    oracleRunning: /QC-Oracle-GLM[\s\S]{0,200}(running|Running now|queued)/i.test(t),
    oracleWaiting: /Oracle Waiting|Waiting for Oracle/i.test(t),
    oraclePass: /Oracle\s*(Passed|Pass|1\.0)/i.test(t) || /Oracle Passed/i.test(t),
    changesNeeded: /Changes needed|Changes required|Oracle Failed|below_1\.0/i.test(t),
    accepted: /Accepted|ready to submit/i.test(t),
    runningSec: (t.match(/running · (\d+)s/) || [])[1] || null,
  };
}

async function drive(page, name, url, { mayUpload, zip, allowOracle }) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(6000);
  let t = await body(page);
  dump(`f-kc-${name}.txt`, t);
  if (/accounts\.google|Enter your email/i.test(page.url() + t)) {
    return { status: 'need_login' };
  }
  const sum = summarize(t);
  log({ event: 'state', name, url: page.url(), ...sum, head: t.slice(0, 350) });

  if (mayUpload && zip && fs.existsSync(zip) && /Upload new version/i.test(t) && sum.changesNeeded) {
    await softClick(page, /Upload new version/i, name + '-upload-btn');
    const inputs = page.locator('input[type="file"]');
    if (await inputs.count()) {
      await inputs.first().setInputFiles(zip);
      log({ event: 'uploaded', name, zip });
      await sleep(12000);
      t = await body(page);
      dump(`f-kc-${name}-after-upload.txt`, t);
    }
  }

  if (sum.oracleRunning || sum.oraclePass) {
    return { status: sum.oraclePass ? 'doneish' : 'inflight', ...sum, url: page.url() };
  }

  // STRICT-RULES: PreQC is optional — skip Client PreQC; go straight to final QC (QC-Oracle-GLM).
  let ev = false;
  if (allowOracle && !sum.slotsFull) {
    ev =
      (await softClick(page, /Re-run QC-Oracle-GLM/i, name + '-oracle-rerun')) ||
      (await softClick(page, /Run QC-Oracle-GLM/i, name + '-oracle'));
  } else if (sum.slotsFull) {
    log({ event: 'defer_oracle', name, reason: 'slots_full' });
  } else if (!allowOracle) {
    log({ event: 'defer_oracle', name, reason: 'max_eval' });
  }
  await sleep(5000);
  t = await body(page);
  dump(`f-kc-${name}-after.txt`, t);
  const after = summarize(t);
  return {
    status: ev || after.oracleRunning ? 'started' : after.slotsFull ? 'slots_full' : 'idle',
    pre: false,
    skipped_preqc: true,
    ev,
    ...after,
    url: page.url(),
  };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'f-keepchrome.log'), '');

  let browser;
  try {
    browser = await chromium.launchPersistentContext(PROFILE, {
      headless: true,
      channel: 'chrome',
      acceptDownloads: true,
      args: ['--disable-blink-features=AutomationControlled'],
    });
  } catch (e) {
    log({ event: 'PROFILE_BUSY', error: String(e).slice(0, 250) });
    process.exit(3);
  }

  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(90000);

  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  let root = await body(page);
  dump('f-kc-root.txt', root);
  if (/accounts\.google/i.test(page.url()) || (/Sign in/i.test(root) && !/muhammad\.y7@turing\.com/i.test(root))) {
    log({ event: 'need_login' });
    // keep chrome warm — do not close
    await new Promise(() => {});
  }
  log({ event: 'logged_in', head: root.slice(0, 300) });

  let evalsStarted = 0;
  for (let round = 1; round <= MAX_ROUNDS; round++) {
    log(`\n==== F KEEPCHROME ${round}/${MAX_ROUNDS} ====`);
    try {
      // refresh root running count
      await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(4000);
      root = await body(page);
      dump('f-kc-root.txt', root);
      const runningCards = (root.match(/\bQC running\b/gi) || []).length;
      log({ event: 'root_running_cards', runningCards });

      const allowG = evalsStarted < MAX_EVAL;
      const g857 = await drive(page, 'g857', G857, {
        mayUpload: false,
        zip: ZIP_G857,
        allowOracle: allowG,
      });
      if (g857.ev) evalsStarted += 1;

      const allowC = evalsStarted < MAX_EVAL && !(g857.slotsFull);
      const c251 = await drive(page, 'c251', C251, {
        mayUpload: false,
        zip: null,
        allowOracle: allowC,
      });
      if (c251.ev) evalsStarted += 1;

      const status = { round, at: new Date().toISOString(), evalsStarted, g857, c251 };
      dump('f-keepchrome-status.json', JSON.stringify(status, null, 2));
      log({ event: 'round_done', round, g857: g857.status, c251: c251.status, evalsStarted });

      if (
        (g857.status === 'doneish' || g857.oraclePass) &&
        (c251.status === 'doneish' || c251.oraclePass || c251.status === 'started' || c251.oracleRunning)
      ) {
        // keep polling until both finished-ish
      }
    } catch (e) {
      log({ event: 'round_error', error: String(e).slice(0, 300) });
      // NEVER close — wait and retry same browser
    }
    log({ event: 'sleep', seconds: POLL_MS / 1000 });
    await sleep(POLL_MS);
  }

  log({ event: 'DONE_MAX_ROUNDS_KEEP_CHROME' });
  // Keep Chrome alive forever for shared queue (OpenCode style)
  await new Promise(() => {});
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
