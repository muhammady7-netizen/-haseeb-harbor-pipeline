/**
 * Session C gen-g806 — FINAL QC only (STRICT-RULES). Never stop.
 * Shared chrome-profile, headless, wait if busy, relaunch on steal.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const DIRECT =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-58a3a86e0067ef5b91601705a8772487-v1';
const STEM = 'gen-g806-leadership-brief-rhetorical-style-audit';
const OUT = path.join(__dirname, 'tmp-pw');
const POLL_MS = 5 * 60 * 1000;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
function dump(n, t) {
  fs.writeFileSync(path.join(OUT, n), t || '');
}
async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}
function onTask(t) {
  return (
    !/Drop a task here/i.test(t.slice(0, 1000)) &&
    /gen-g806-leadership-brief-rhetorical-style-audit/i.test(t.slice(0, 3000)) &&
    /QC-Oracle-GLM|ORACLE GOLDEN|Upload new version|Client [Pp]reQC/i.test(t)
  );
}
function parse(t) {
  const idx = t.search(/QC-Oracle-GLM|ORACLE GOLDEN|Execution status/i);
  const s = idx >= 0 ? t.slice(idx, idx + 5000) : t.slice(0, 4000);
  const oracleFail = /Oracle\s*(Failed|Fail)|below_1\.0/i.test(s);
  const oraclePass =
    /Oracle\s*(Passed|PASS)|best reward 1(?:\.0)?|pass:\s*1(?:\.0)?/i.test(s) && !oracleFail;
  const glmM =
    s.match(/GLM-5\.2[^\n]{0,80}?(\d)\s*\/\s*4/i) || s.match(/(\d)\s*\/\s*4\s*(?:passed|graded)/i);
  const glm = glmM ? glmM[1] : null;
  const running = /Running now|Oracle Waiting|Waiting for Oracle|GLM[^\n]{0,40}Waiting|running ·\s*\d/i.test(
    s
  );
  const slotsFull = /3 run slots are currently in use|Your 3 run slots/i.test(t);
  const readySubmit = /Submit to pipeline|READY_FOR_FINALIZATION|Ready to submit/i.test(t);
  const homeStatus = (() => {
    const m = t.match(
      /gen-g806-leadership-brief-rhetorical-style-audit#[a-f0-9]+\s*\n[^\n]*\n([^\n]+)/i
    );
    return m ? m[1].trim() : null;
  })();
  return { oracleFail, oraclePass, glm, running, slotsFull, readySubmit, homeStatus };
}

async function launchWhenFree() {
  for (let i = 1; ; i++) {
    try {
      const b = await chromium.launchPersistentContext(PROFILE, {
        headless: true,
        channel: 'chrome',
        acceptDownloads: true,
        args: ['--disable-blink-features=AutomationControlled'],
      });
      console.log(JSON.stringify({ event: 'LAUNCHED', attempt: i }));
      return b;
    } catch {
      console.log(JSON.stringify({ event: 'PROFILE_BUSY', attempt: i }));
      await sleep(30000);
    }
  }
}

async function openG806(page) {
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  let t = await body(page);
  dump('g806-finalqc-home.txt', t);

  // Click Open on the first Recent-tasks g806 row (newest first)
  const opens = page.getByText(/^Open$/i);
  const n = await opens.count();
  console.log(JSON.stringify({ event: 'open_count', n }));
  // Scan titles near each Open by clicking candidates that sit after STEM text
  const stemLoc = page.getByText(STEM, { exact: false });
  const stemN = await stemLoc.count();
  console.log(JSON.stringify({ event: 'stem_count', stemN }));
  if (stemN > 0) {
    // Prefer first occurrence in Recent tasks (usually top)
    await stemLoc.first().scrollIntoViewIfNeeded().catch(() => {});
    await stemLoc.first().click({ timeout: 15000 }).catch(() => null);
    await sleep(2000);
    // Try Open in the same viewport: find Open after scrolling to stem
    for (let i = 0; i < Math.min(n, 12); i++) {
      const before = page.url();
      await opens.nth(i).click({ timeout: 8000 }).catch(() => null);
      await sleep(5000);
      t = await body(page);
      if (onTask(t)) {
        console.log(JSON.stringify({ event: 'opened_via_open_idx', i, url: page.url() }));
        return t;
      }
      if (page.url() !== before && /#task=/.test(page.url())) {
        // wrong task — go home and continue
        await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
        await sleep(4000);
      }
    }
  }

  await page.goto(DIRECT, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(8000);
  await page.evaluate((u) => {
    if (location.href !== u) location.href = u;
  }, DIRECT);
  await sleep(6000);
  t = await body(page);
  console.log(JSON.stringify({ event: 'opened', onTask: onTask(t), url: page.url() }));
  return t;
}

async function clickFinalQcOnly(page) {
  for (const re of [/Re-run QC-Oracle-GLM/i, /Run QC-Oracle-GLM/i]) {
    const btn = page.getByRole('button', { name: re }).first();
    if (!(await btn.count())) continue;
    const disabled =
      (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
      (await btn.isDisabled().catch(() => false));
    if (disabled) {
      console.log(JSON.stringify({ event: 'oracle_btn_disabled' }));
      continue;
    }
    await btn.click({ timeout: 15000 });
    console.log(JSON.stringify({ event: 'clicked_final_qc', re: String(re) }));
    await sleep(6000);
    return true;
  }
  return false;
}

async function trackOnce() {
  const browser = await launchWhenFree();
  try {
    const page = browser.pages()[0] || (await browser.newPage());
    page.setDefaultTimeout(90000);
    let t = await openG806(page);

    if (onTask(t)) {
      const p0 = parse(t);
      if (!p0.running) await clickFinalQcOnly(page);
      else console.log(JSON.stringify({ event: 'already_running', ...p0 }));
    }

    for (let round = 1; round <= 24; round++) {
      if (round > 1) {
        await page.reload({ waitUntil: 'domcontentloaded', timeout: 120000 }).catch(() => {});
        await sleep(4000);
        t = await body(page);
        if (!onTask(t)) t = await openG806(page);
      } else {
        t = await body(page);
      }
      dump(`g806-finalqc-${round}.txt`, t);
      const p = parse(t);
      const status = {
        event: 'POLL',
        round,
        at: new Date().toISOString(),
        onTask: onTask(t),
        skipped_preqc: true,
        ...p,
        head: t.slice(0, 450).replace(/\s+/g, ' '),
      };
      fs.writeFileSync(path.join(OUT, 'g806-finalqc-status.json'), JSON.stringify(status, null, 2));
      console.log(JSON.stringify(status));

      if (status.onTask) {
        if (p.oracleFail) return 'ORACLE_FAIL';
        if (p.readySubmit || (p.oraclePass && p.glm != null && !p.running)) return 'DONE';
        if (!p.running && !p.slotsFull) await clickFinalQcOnly(page);
      } else if (p.homeStatus) {
        console.log(JSON.stringify({ event: 'HOME_STATUS', homeStatus: p.homeStatus }));
        if (/Needs your review|Changes needed|Accepted/i.test(p.homeStatus)) return 'HOME_DONE';
      }

      console.log(JSON.stringify({ event: 'SLEEP', ms: POLL_MS }));
      await sleep(POLL_MS);
    }
    return 'TIMEOUT_ROUND';
  } finally {
    await browser.close().catch(() => {});
    console.log(JSON.stringify({ event: 'CLOSED_ONCE' }));
  }
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  for (let life = 1; ; life++) {
    console.log(JSON.stringify({ event: 'LIFE', life }));
    try {
      const r = await trackOnce();
      console.log(JSON.stringify({ event: 'TRACK_RESULT', r, life }));
      if (r === 'DONE' || r === 'ORACLE_FAIL' || r === 'HOME_DONE') {
        // keep process alive briefly then continue polling forever until accepted path handled outside
        await sleep(120000);
      }
    } catch (e) {
      console.log(JSON.stringify({ event: 'LIFE_ERR', error: String(e).slice(0, 300) }));
      await sleep(20000);
    }
  }
})();
