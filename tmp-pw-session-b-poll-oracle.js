/**
 * Session B: poll until an eval slot frees, then finish gates on c227 + c249.
 * Never Confirm PreQC. Never dismiss Harbor blockers as FP.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const PORTAL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const OUT = path.join(__dirname, 'tmp-pw');
const MAX_EVAL = 3;

// Prefer newest known URLs from last keepgoing run
const JOBS = [
  {
    short: 'code-c249',
    url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-10994eb6b7816775f36ff3ccca5c9268-v1',
  },
  {
    short: 'code-c227',
    url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-3a68a4668fe6d080ac4779cd324e6dc6-v1',
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
      await sleep(2000);
      console.log(JSON.stringify({ event: 'click_btn', label, re: String(re) }));
      return true;
    }
    const txt = page.getByText(re).first();
    if (await txt.count()) {
      await txt.click({ force: true, timeout: 12000 }).catch(() => null);
      await sleep(2000);
      console.log(JSON.stringify({ event: 'click_txt', label, re: String(re) }));
      return true;
    }
  }
  return false;
}

async function slotsInUse(page) {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(4000);
  const t = await body(page);
  const n = (t.match(/QC running/gi) || []).length;
  const full = /3 runs in flight|3 run slots are currently in use/i.test(t);
  return { n, full, head: t.slice(0, 400) };
}

async function finishGates(page, job) {
  console.log(JSON.stringify({ event: 'open', short: job.short, url: job.url }));
  await page.goto(job.url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(7000);
  let t = await body(page);
  dump(`sessb5-${job.short}-before.txt`, `URL=${page.url()}\n\n${t}`);

  // Reviewer (unlocks review record)
  if (/Not finished|Check with QC reviewer/i.test(t)) {
    await clickAny(page, [/Check with QC reviewer/i], `${job.short}-reviewer`);
    for (let i = 0; i < 24; i++) {
      await sleep(5000);
      t = await body(page);
      if (!/Not finished/i.test(t) || /Review record[\s\S]{0,40}✓|Complete/i.test(t)) break;
      if (i % 3 === 0) console.log(JSON.stringify({ event: 'wait_reviewer', short: job.short, i }));
    }
    dump(`sessb5-${job.short}-after-reviewer.txt`, t);
  }

  // PreQC
  if (/not run yet|did not finish|errored|Re-run client preQC|Run client preQC/i.test(t)) {
    await clickAny(page, [/Re-run client preQC|Run client preQC/i], `${job.short}-preqc`);
    for (let i = 0; i < 50; i++) {
      await sleep(4000);
      t = await body(page);
      if (/Dismiss|Confirm issue/i.test(t)) break;
      if (/Client preQC[\s\S]{0,120}(complete|PASS|findings|advisory)/i.test(t) && !/running/i.test(t.slice(0, 2000))) break;
      if (/did not finish|errored/i.test(t) && i > 5) break;
      if (i % 5 === 0) console.log(JSON.stringify({ event: 'wait_preqc', short: job.short, i }));
    }
    for (let i = 0; i < 20; i++) {
      if (!(await clickAny(page, [/^Dismiss$/i], `${job.short}-dismiss-${i}`))) break;
    }
    dump(`sessb5-${job.short}-after-preqc.txt`, await body(page));
  }

  t = await body(page);
  if (/QC running|Oracle running|GLM waiting|In queue|queued/i.test(t)) {
    console.log(JSON.stringify({ event: 'already_running', short: job.short }));
    dump(`sessb5-${job.short}-final.txt`, `URL=${page.url()}\n\n${t}`);
    return { short: job.short, oracle: true, already: true, url: page.url(), head: t.slice(0, 700) };
  }
  if (/3 runs in flight|3 run slots are currently in use/i.test(t)) {
    console.log(JSON.stringify({ event: 'slots_full_on_task', short: job.short }));
    dump(`sessb5-${job.short}-final.txt`, `URL=${page.url()}\n\n${t}`);
    return { short: job.short, oracle: false, slotsFull: true, url: page.url(), head: t.slice(0, 700) };
  }

  const oracle =
    (await clickAny(page, [/Re-run QC-Oracle-GLM/i], `${job.short}-rerun`)) ||
    (await clickAny(page, [/Run QC-Oracle-GLM/i], `${job.short}-run`));
  await sleep(12000);
  t = await body(page);
  dump(`sessb5-${job.short}-final.txt`, `URL=${page.url()}\noracle=${oracle}\n\n${t}`);
  const summary = {
    short: job.short,
    oracle,
    url: page.url(),
    running: /QC running|Oracle running|GLM waiting|queued|In queue/i.test(t),
    reviewNotFinished: /Not finished/i.test(t),
    banner: /review\.csv must be complete/i.test(t),
    blockers: (t.match(/BLOCKER/gi) || []).length,
    head: t.slice(0, 800),
  };
  console.log(JSON.stringify({ event: 'gates_done', ...summary }));
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

  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(90000);
  browser.on('close', () => console.log(JSON.stringify({ event: 'browser_closed' })));

  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(4000);
  const t0 = await body(page);
  if (/Sign in with Google|accounts\.google/i.test(t0) && !/muhammad\.y7@turing\.com/i.test(t0)) {
    console.log(JSON.stringify({ event: 'login_required' }));
    await browser.close();
    process.exit(2);
  }
  console.log(JSON.stringify({ event: 'logged_in' }));

  // Poll up to ~25 min for a free slot
  let free = false;
  for (let i = 0; i < 50; i++) {
    const s = await slotsInUse(page);
    console.log(JSON.stringify({ event: 'slot_poll', i, n: s.n, full: s.full }));
    if (!s.full && s.n < MAX_EVAL) {
      free = true;
      break;
    }
    await sleep(30000);
  }
  if (!free) {
    console.log(JSON.stringify({ event: 'no_slot_timeout' }));
    dump('sessb5-summary.json', JSON.stringify({ at: new Date().toISOString(), free: false }, null, 2));
    await browser.close();
    process.exit(5);
  }

  const results = [];
  for (const job of JOBS) {
    try {
      results.push(await finishGates(page, job));
      // refresh slot awareness between jobs
      const s = await slotsInUse(page);
      if (s.full) {
        console.log(JSON.stringify({ event: 'slots_full_mid', after: job.short }));
        // still try next; finishGates will report slotsFull
      }
    } catch (e) {
      results.push({ short: job.short, error: String(e).slice(0, 400) });
      console.log(JSON.stringify({ event: 'job_fail', short: job.short, error: String(e).slice(0, 400) }));
    }
  }

  dump('sessb5-summary.json', JSON.stringify({ at: new Date().toISOString(), free, results }, null, 2));
  console.log(JSON.stringify({ event: 'done', resultsCount: results.length }));
  await browser.close();
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
