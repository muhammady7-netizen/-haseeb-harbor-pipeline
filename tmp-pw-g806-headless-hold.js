/**
 * Session C — gen-g806 only.
 * OpenCode / pipeline.qc_queue method:
 * - shared chrome-profile, headless, wait if busy (no taskkill)
 * - open task via Recent list click (hash alone often stays on home SPA)
 * - keep ONE browser open while polling
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const STEM = 'gen-g806-leadership-brief-rhetorical-style-audit';
const OUT = path.join(__dirname, 'tmp-pw');
const POLL_MS = 8 * 60 * 1000;
const MAX_ROUNDS = 18;
const LAUNCH_RETRY_MS = 30 * 1000;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
function dump(n, t) {
  fs.writeFileSync(path.join(OUT, n), t || '');
}
async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}

function onTaskPage(t) {
  const home = /Drop a task here/i.test(t.slice(0, 1200));
  const hasStem = new RegExp(STEM.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i').test(t.slice(0, 2500));
  const hasGates = /Client [Pp]reQC|QC-Oracle-GLM|ORACLE GOLDEN|Upload new version/i.test(t);
  return !home && hasStem && hasGates;
}

function parse(t) {
  // Prefer evaluation block if present
  const idx = t.search(/QC-Oracle-GLM|ORACLE GOLDEN REPLAY|Execution status/i);
  const section = (idx >= 0 ? t.slice(idx, idx + 4500) : t.slice(0, 4500));
  const oracleFail = /Oracle\s*(Failed|Fail)|below_1\.0/i.test(section);
  const oraclePass =
    /Oracle\s*(Passed|PASS|Success)|best reward 1(?:\.0)?|pass:\s*1(?:\.0)?/i.test(section) &&
    !oracleFail;
  const glmM =
    section.match(/GLM-5\.2[^\n]{0,60}?(\d)\s*\/\s*4/i) ||
    section.match(/(\d)\s*\/\s*4\s*(?:passed|graded|difficulty)/i);
  const glm = glmM ? glmM[1] : null;
  const running = /Running now|Oracle Waiting|Waiting for Oracle|GLM[^\n]{0,40}Waiting|running ·\s*\d/i.test(
    section
  );
  const doneUi =
    !running &&
    (/Needs your review|Changes needed|Submit for review|Accepted|Harbor Check|Oracle (Passed|Failed)/i.test(
      section
    ) ||
      (oraclePass && glm != null));
  return { oracleFail, oraclePass, glm, running, doneUi };
}

async function launchWhenFree() {
  for (let i = 1; i <= 80; i++) {
    try {
      const browser = await chromium.launchPersistentContext(PROFILE, {
        headless: true,
        channel: 'chrome',
        acceptDownloads: true,
        args: ['--disable-blink-features=AutomationControlled'],
      });
      console.log(JSON.stringify({ event: 'LAUNCHED', attempt: i }));
      return browser;
    } catch (e) {
      console.log(
        JSON.stringify({
          event: 'PROFILE_BUSY',
          attempt: i,
          error: String(e).split('\n')[0].slice(0, 140),
        })
      );
      await sleep(LAUNCH_RETRY_MS);
    }
  }
  throw new Error('profile never free');
}

async function openG806(page) {
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  let t = await body(page);
  dump('g806-hold-home.txt', t);

  // Recent-tasks: open the row that contains STEM (not first Open on page)
  const openInRow = page
    .locator('div')
    .filter({ hasText: new RegExp(STEM.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) })
    .getByText(/^Open$/i)
    .first();
  if (await openInRow.count()) {
    await openInRow.scrollIntoViewIfNeeded().catch(() => {});
    await openInRow.click({ timeout: 20000 });
    console.log(JSON.stringify({ event: 'clicked_open_in_row' }));
    await sleep(9000);
  } else {
    const title = page.getByText(STEM, { exact: false }).first();
    if (await title.count()) {
      await title.scrollIntoViewIfNeeded().catch(() => {});
      await title.click({ timeout: 20000 });
      console.log(JSON.stringify({ event: 'clicked_title' }));
      await sleep(9000);
    }
  }

  t = await body(page);
  if (!onTaskPage(t)) {
    // last resort: force hash + reload
    await page.goto(
      'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-58a3a86e0067ef5b91601705a8772487-v1',
      { waitUntil: 'domcontentloaded', timeout: 120000 }
    );
    await sleep(8000);
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 120000 }).catch(() => {});
    await sleep(6000);
    t = await body(page);
  }

  console.log(
    JSON.stringify({
      event: 'opened',
      url: page.url(),
      onTask: onTaskPage(t),
      head: t.slice(0, 200).replace(/\s+/g, ' '),
    })
  );
  return t;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await launchWhenFree();
  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(90000);

  let t = await openG806(page);
  if (/accounts\.google|Sign in with Google/i.test(page.url() + t) && !/muhammad\.y7@turing\.com/i.test(t)) {
    console.log(JSON.stringify({ event: 'login_required' }));
    dump('g806-hold-login.txt', t);
    await browser.close().catch(() => {});
    process.exit(2);
  }

  for (let round = 1; round <= MAX_ROUNDS; round++) {
    if (round > 1) {
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 120000 }).catch(() => {});
      await sleep(5000);
      t = await body(page);
      if (!onTaskPage(t)) t = await openG806(page);
    }

    dump(`g806-hold-${round}.txt`, t);
    const p = parse(t);
    const status = {
      event: 'POLL',
      round,
      at: new Date().toISOString(),
      url: page.url(),
      onTask: onTaskPage(t),
      ...p,
      head: t.slice(0, 600).replace(/\s+/g, ' '),
    };
    fs.writeFileSync(path.join(OUT, 'g806-hold-status.json'), JSON.stringify(status, null, 2));
    console.log(JSON.stringify(status));

    if (!status.onTask) {
      console.log(JSON.stringify({ event: 'NOT_ON_TASK', round }));
      await sleep(90000);
      t = await openG806(page);
      continue;
    }

    if (p.oracleFail) {
      console.log(JSON.stringify({ event: 'ORACLE_FAIL', round }));
      break;
    }
    if (p.doneUi) {
      console.log(JSON.stringify({ event: 'DONE', round, glm: p.glm, oraclePass: p.oraclePass }));
      break;
    }

    console.log(JSON.stringify({ event: 'SLEEP', ms: POLL_MS, keep_browser: true }));
    await sleep(POLL_MS);
    t = await body(page);
  }

  await sleep(1000);
  await browser.close().catch(() => {});
  console.log(JSON.stringify({ event: 'CLOSED_ONCE' }));
})().catch((e) => {
  console.log(JSON.stringify({ event: 'FATAL', error: String(e).slice(0, 400) }));
  process.exit(1);
});
