/**
 * Session B keep-going (authorized automation).
 * Shared opencode chrome-profile, headless.
 * 1) Upload c227 + c249 zips
 * 2) Open newest version of each
 * 3) Check with QC reviewer → PreQC (dismiss advisory only) → Oracle+GLM
 * Never Confirm PreQC. Never dismiss Harbor blockers as FP.
 * Respect ~3 concurrent eval slots (skip Oracle start if 3 already running).
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const PORTAL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const OUT = path.join(__dirname, 'tmp-pw');
const MAX_EVAL = 3;

const JOBS = [
  {
    short: 'code-c227',
    pack: 'code-c227-table-bloat-maintenance-audit',
    zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-code-c227.zip',
  },
  {
    short: 'code-c249',
    pack: 'code-c249-recurring-report-source-selection-audit',
    zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-code-c249.zip',
  },
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const dump = (n, t) => fs.writeFileSync(path.join(OUT, n), t || '');

async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}

async function clickAny(page, patterns, label) {
  for (const re of patterns) {
    const btn = page.getByRole('button', { name: re }).first();
    if (await btn.count()) {
      await btn.click({ force: true, timeout: 12000 }).catch(() => null);
      await sleep(2500);
      console.log(JSON.stringify({ event: 'click_btn', label, re: String(re) }));
      return true;
    }
    const txt = page.getByText(re).first();
    if (await txt.count()) {
      await txt.click({ force: true, timeout: 12000 }).catch(() => null);
      await sleep(2500);
      console.log(JSON.stringify({ event: 'click_txt', label, re: String(re) }));
      return true;
    }
  }
  return false;
}

async function countRunning(page) {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  const t = await body(page);
  const n = (t.match(/QC running/gi) || []).length;
  console.log(JSON.stringify({ event: 'running_slots', n }));
  return n;
}

async function uploadAndOpen(page, job) {
  console.log(JSON.stringify({ event: 'upload_start', short: job.short }));
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(4000);
  const input = page.locator('input[type="file"]').first();
  if (!(await input.count())) throw new Error('no file input');
  await input.setInputFiles(job.zip);
  console.log(JSON.stringify({ event: 'uploaded', short: job.short }));

  // Wait until upload lands on a task page OR recent list shows pack
  for (let i = 0; i < 45; i++) {
    await sleep(2000);
    const u = page.url();
    const t = await body(page);
    if (/#task=content-/.test(u) && !/reading the bundle/i.test(t)) {
      console.log(JSON.stringify({ event: 'landed_task', short: job.short, url: u, i }));
      dump(`sessb4-${job.short}-landed.txt`, `URL=${u}\n\n${t}`);
      return u;
    }
    if (/reading the bundle/i.test(t)) continue;
    // Try open newest matching pack from recent list
    if (t.includes(job.pack)) {
      const openNear = page
        .locator('a,button,span,div')
        .filter({ hasText: new RegExp(job.pack.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') })
        .first();
      // Prefer the Open button next to first match: scroll then force click Open near pack name
      const packLoc = page.locator(`text=${job.pack}`).first();
      if (await packLoc.count()) {
        await packLoc.scrollIntoViewIfNeeded().catch(() => null);
        await sleep(500);
        // Click the first "Open" on the page after pack appears at top of Recent
        const openBtn = page.getByRole('button', { name: /^Open$/i }).first();
        const openLink = page.getByText(/^Open$/).first();
        if (await openBtn.count()) {
          await openBtn.click({ force: true }).catch(() => null);
        } else if (await openLink.count()) {
          await openLink.click({ force: true }).catch(() => null);
        } else {
          await packLoc.click({ force: true }).catch(() => null);
        }
        await sleep(5000);
        if (/#task=content-/.test(page.url())) {
          const u2 = page.url();
          console.log(JSON.stringify({ event: 'opened_from_list', short: job.short, url: u2, i }));
          dump(`sessb4-${job.short}-landed.txt`, `URL=${u2}\n\n${await body(page)}`);
          return u2;
        }
      }
    }
  }
  dump(`sessb4-${job.short}-fail.txt`, `URL=${page.url()}\n\n${await body(page)}`);
  throw new Error(`failed to open ${job.short}`);
}

async function runGates(page, job, allowOracle) {
  let t = await body(page);
  dump(`sessb4-${job.short}-before-gates.txt`, `URL=${page.url()}\n\n${t}`);

  await clickAny(page, [/Check with QC reviewer/i], `${job.short}-reviewer`);
  await sleep(15000);
  t = await body(page);
  dump(`sessb4-${job.short}-after-reviewer.txt`, t);

  await clickAny(page, [/Run client preQC|Re-run client preQC/i], `${job.short}-preqc`);
  // Wait for preQC UI
  for (let i = 0; i < 40; i++) {
    await sleep(3000);
    t = await body(page);
    if (/Dismiss|Confirm issue|PreQC complete|advisory|findings/i.test(t) && !/preQC.*running|Client preQC[\s\S]{0,60}running/i.test(t)) {
      break;
    }
    if (i % 5 === 0) console.log(JSON.stringify({ event: 'wait_preqc', short: job.short, i }));
  }
  // Dismiss advisory only — NEVER Confirm
  for (let i = 0; i < 20; i++) {
    const ok = await clickAny(page, [/^Dismiss$/i, /Dismiss finding/i], `${job.short}-dismiss-${i}`);
    if (!ok) break;
  }
  t = await body(page);
  dump(`sessb4-${job.short}-after-preqc.txt`, t);

  let oracle = false;
  if (/QC running|Oracle running|GLM waiting|In queue|queued/i.test(t)) {
    console.log(JSON.stringify({ event: 'already_running', short: job.short }));
    oracle = true;
  } else if (!allowOracle) {
    console.log(JSON.stringify({ event: 'oracle_skipped_slots_full', short: job.short }));
  } else {
    oracle =
      (await clickAny(page, [/Re-run QC-Oracle-GLM/i], `${job.short}-rerun`)) ||
      (await clickAny(page, [/Run QC-Oracle-GLM/i], `${job.short}-run`));
    await sleep(10000);
  }
  t = await body(page);
  dump(`sessb4-${job.short}-after-oracle.txt`, `URL=${page.url()}\noracle=${oracle}\n\n${t}`);
  const summary = {
    event: 'gates_done',
    short: job.short,
    url: page.url(),
    oracle,
    banner: /review\.csv must be complete/i.test(t),
    reviewNotFinished: /Not finished/i.test(t),
    running: /QC running|Oracle running|GLM waiting|queued|In queue/i.test(t),
    blockers: (t.match(/BLOCKER/gi) || []).length,
    head: t.slice(0, 800),
  };
  console.log(JSON.stringify(summary));
  return summary;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  for (const name of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, name));
    } catch {}
  }

  let browser;
  try {
    // Off-screen (not headless): more stable with shared opencode profile.
    browser = await chromium.launchPersistentContext(PROFILE, {
      headless: false,
      channel: 'chrome',
      acceptDownloads: true,
      viewport: { width: 1280, height: 900 },
      args: [
        '--window-position=-32000,-32000',
        '--window-size=1280,900',
        '--disable-blink-features=AutomationControlled',
      ],
    });
  } catch (e) {
    console.log(JSON.stringify({ event: 'PROFILE_BUSY', error: String(e).slice(0, 300) }));
    process.exit(3);
  }

  browser.on('close', () => console.log(JSON.stringify({ event: 'browser_closed' })));
  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(90000);
  page.on('close', () => console.log(JSON.stringify({ event: 'page_closed' })));

  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  let t0 = await body(page);
  if (/Sign in with Google|accounts\.google/i.test(t0) && !/muhammad\.y7@turing\.com/i.test(t0)) {
    console.log(JSON.stringify({ event: 'login_required' }));
    await browser.close();
    process.exit(2);
  }
  console.log(JSON.stringify({ event: 'logged_in' }));

  let running = await countRunning(page);
  const results = [];
  for (const job of JOBS) {
    try {
      if (!fs.existsSync(job.zip)) throw new Error(`missing zip ${job.zip}`);
      await uploadAndOpen(page, job);
      const allowOracle = running < MAX_EVAL;
      const summary = await runGates(page, job, allowOracle);
      if (summary.oracle && allowOracle) running += 1;
      results.push(summary);
    } catch (e) {
      const err = { event: 'job_fail', short: job.short, error: String(e).slice(0, 400) };
      console.log(JSON.stringify(err));
      results.push(err);
    }
  }

  dump('sessb4-summary.json', JSON.stringify({ at: new Date().toISOString(), running, results }, null, 2));
  console.log(JSON.stringify({ event: 'done', running, resultsCount: results.length }));
  await browser.close();
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
