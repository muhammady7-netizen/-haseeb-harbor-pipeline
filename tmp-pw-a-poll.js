/**
 * Session A — open latest known list entries and dump eval status.
 * Prefer short-hash Open buttons from Recent tasks.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const JOBS = [
  {
    short: 'fin-f39',
    markers: ['fin-f39-distributable-profits#683901', 'fin-f39-distributable-profits'],
    fallbackUrl:
      'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-6513101fd1bccf3a2b340d4a87b24e5f-v1',
  },
  {
    short: 'gen-g1205',
    markers: [
      'gen-g1205-meal-prep-cost-claim-recompute-audit#70f11b',
      'gen-g1205-meal-prep-cost-claim-recompute-audit',
    ],
  },
  {
    short: 'the-thread',
    markers: [
      'the-thread-hands-back-its-own-opener#79dd1f',
      'the-thread-hands-back-its-own-opener',
    ],
  },
];

function summarize(t) {
  const pick = (re, n = 10) => [...t.matchAll(re)].map((m) => m[0]).slice(0, n);
  return {
    slotsFull: /\d+\s+runs?\s+in flight|run slots? are currently in use/i.test(t),
    changesNeeded: /Changes needed|Changes required/i.test(t),
    needsReview: /Needs your review/i.test(t),
    oraclePass: /Oracle\s*(Passed|Pass)|Oracle Passed/i.test(t),
    oracleFail: /Oracle Failed|Oracle\s*Failed|below_1\.0/i.test(t),
    oracleWaiting: /Oracle Waiting|Waiting for Oracle/i.test(t),
    oracleRunning: /QC-Oracle-GLM[\s\S]{0,220}(running|Running now|queued|in progress)/i.test(t),
    glmHints: pick(/GLM[^\n]{0,100}/gi, 12),
    rewardHints: pick(/reward[^\n]{0,60}|[0-4]\s*\/\s*4|pass rate[^\n]{0,40}|TOO_EASY|too hard/gi, 15),
    harborHints: pick(/Harbor[^\n]{0,120}|finding[^\n]{0,80}/gi, 12),
    accepted: /Ready to submit|Accepted/i.test(t),
    version: (t.match(/\bv(\d+)\s*[·•]\s*latest/i) || [])[1] || null,
    runningSec: (t.match(/running · (\d+)s/) || [])[1] || null,
  };
}

async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}

async function openMarker(page, marker) {
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  // Prefer exact list label with hash when provided
  const label = page.getByText(marker, { exact: false }).first();
  if (!(await label.count())) return { ok: false, reason: 'marker_missing' };
  await label.scrollIntoViewIfNeeded().catch(() => {});
  // Click nearby Open: go up to a row-ish ancestor
  const row = label.locator('xpath=ancestor::*[self::div or self::li or self::article][1]');
  const openInRow = row.getByRole('button', { name: /^Open$/i }).first();
  if (await openInRow.count()) {
    await openInRow.click({ force: true, timeout: 10000 });
  } else {
    // fallback: next Open after the label
    await label.click({ force: true, timeout: 10000 }).catch(() => null);
    const open = page.getByRole('button', { name: /^Open$/i }).first();
    if (await open.count()) await open.click({ force: true, timeout: 8000 }).catch(() => null);
  }
  await sleep(8000);
  // If still on list, try clicking the label itself harder
  if (!/#task=/.test(page.url())) {
    await label.click({ force: true, timeout: 8000 }).catch(() => null);
    await sleep(6000);
  }
  return { ok: /#task=/.test(page.url()), url: page.url() };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(90000);

  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  const root = await body(page);
  fs.writeFileSync(path.join(OUT, 'a-poll-root.txt'), root);
  if (/accounts\.google/i.test(page.url()) || (/Sign in/i.test(root) && !/muhammad\.y7@turing\.com/i.test(root))) {
    console.log(JSON.stringify({ event: 'need_login' }));
    process.exit(2);
  }

  const results = [];
  for (const job of JOBS) {
    let opened = { ok: false };
    for (const marker of job.markers) {
      opened = await openMarker(page, marker);
      console.log(JSON.stringify({ event: 'try_open', short: job.short, marker, ...opened }));
      if (opened.ok) break;
    }
    if (!opened.ok && job.fallbackUrl) {
      await page.goto(job.fallbackUrl, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(7000);
      opened = { ok: /#task=/.test(page.url()), url: page.url(), via: 'fallback' };
      console.log(JSON.stringify({ event: 'fallback', short: job.short, ...opened }));
    }
    let t = await body(page);
    // If still list page, dump and continue
    fs.writeFileSync(path.join(OUT, `a-poll-${job.short}.txt`), t);
    const sum = summarize(t);
    const row = {
      short: job.short,
      url: page.url(),
      opened: !!opened.ok,
      ...sum,
      head: t.slice(0, 2500),
    };
    results.push(row);
    console.log(
      JSON.stringify({
        event: 'polled',
        short: job.short,
        url: page.url(),
        changesNeeded: sum.changesNeeded,
        needsReview: sum.needsReview,
        oraclePass: sum.oraclePass,
        oracleFail: sum.oracleFail,
        oracleRunning: sum.oracleRunning,
        version: sum.version,
        glmHints: sum.glmHints,
        rewardHints: sum.rewardHints,
      })
    );
  }

  fs.writeFileSync(path.join(OUT, 'a-poll-status.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify({ event: 'done', count: results.length }));
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
