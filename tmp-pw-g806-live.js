/**
 * Session C g806 — robust open + status (+ Accept only if truly ready, no Harbor blockers).
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
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}
function onTask(t) {
  return (
    !/Drop a task here/i.test(t.slice(0, 1000)) &&
    /gen-g806-leadership-brief-rhetorical-style-audit/i.test(t.slice(0, 3500)) &&
    /QC check|QC-Oracle-GLM|Upload new version|Client [Pp]reQC/i.test(t)
  );
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  let browser;
  for (let i = 1; ; i++) {
    try {
      browser = await chromium.launchPersistentContext(PROFILE, {
        headless: true,
        channel: 'chrome',
        acceptDownloads: true,
        args: ['--disable-blink-features=AutomationControlled'],
      });
      console.log(JSON.stringify({ event: 'LAUNCHED', i }));
      break;
    } catch {
      console.log(JSON.stringify({ event: 'BUSY', i }));
      await sleep(25000);
    }
  }
  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(90000);

  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(8000);
  // scroll to load recent list
  for (let s = 0; s < 12; s++) {
    await page.mouse.wheel(0, 1400);
    await sleep(300);
  }
  await sleep(2000);
  let t = await body(page);
  fs.writeFileSync(path.join(OUT, 'g806-live-home.txt'), t);

  // Click first matching title in recent tasks
  const titles = page.getByText(STEM, { exact: false });
  const tn = await titles.count();
  console.log(JSON.stringify({ event: 'stem_count', tn }));
  if (tn > 0) {
    await titles.first().click({ timeout: 20000 });
    await sleep(9000);
  } else {
    // fallback Open buttons from top
    const opens = page.getByText(/^Open$/i);
    const n = await opens.count();
    console.log(JSON.stringify({ event: 'open_count', n }));
    for (let i = 0; i < Math.min(n, 20); i++) {
      await opens.nth(i).click({ timeout: 8000 }).catch(() => null);
      await sleep(6000);
      t = await body(page);
      if (onTask(t)) break;
      await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(4000);
      for (let s = 0; s < 8; s++) {
        await page.mouse.wheel(0, 1200);
        await sleep(200);
      }
    }
  }

  t = await body(page);
  if (!onTask(t)) {
    await page.goto(DIRECT, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    await page.evaluate((u) => {
      location.href = u;
    }, DIRECT);
    await sleep(8000);
    t = await body(page);
  }

  fs.writeFileSync(path.join(OUT, 'g806-live-task.txt'), t);
  const blockers = (t.match(/(\d+)\s+blocking issues/i) ||
    t.match(/(\d+)\s+issues to review/i) ||
    [])[1];
  const glmM = t.match(/GLM-5\.2[^\n]{0,80}?(\d)\s*\/\s*4/i);
  const summary = {
    url: page.url(),
    onTask: onTask(t),
    version: (t.match(/v(\d+)\s*·\s*latest/i) || [null])[0],
    oraclePass: /Oracle Passed/i.test(t),
    oracleFail: /Oracle Failed/i.test(t),
    glm: glmM ? glmM[1] + '/4' : null,
    running: /Running now|Oracle Waiting|GLM[^\n]{0,40}Waiting|running ·/i.test(t),
    blockers: blockers || null,
    toDecide: (t.match(/(\d+)\s+to decide/i) || [])[1] || null,
    readySubmit: /Ready to submit|Submit to pipeline|READY_FOR_FINALIZATION/i.test(t),
    needsAttention: /NEEDS ATTENTION|Needs attention|Review required/i.test(t),
    head: t.slice(0, 1500).replace(/\s+/g, ' '),
  };
  fs.writeFileSync(path.join(OUT, 'g806-live-status.json'), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify({ event: 'STATUS', ...summary }));

  const canAccept =
    summary.onTask &&
    summary.oraclePass &&
    !summary.running &&
    !summary.blockers &&
    summary.readySubmit;

  if (canAccept) {
    for (const re of [/Submit to pipeline/i, /Ready to submit/i, /^Submit$/i]) {
      const btn = page.getByRole('button', { name: re }).first();
      if (!(await btn.count())) continue;
      const dis =
        (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
        (await btn.isDisabled().catch(() => false));
      if (dis) {
        console.log(JSON.stringify({ event: 'SUBMIT_DISABLED', re: String(re) }));
        continue;
      }
      await btn.click({ timeout: 15000 });
      console.log(JSON.stringify({ event: 'CLICKED_SUBMIT', re: String(re) }));
      await sleep(10000);
      break;
    }
    t = await body(page);
    fs.writeFileSync(path.join(OUT, 'g806-live-after-submit.txt'), t);
    console.log(
      JSON.stringify({
        event: 'AFTER_SUBMIT',
        accepted: /Accepted|Submitted to the pipeline/i.test(t),
        head: t.slice(0, 700).replace(/\s+/g, ' '),
      })
    );
  } else {
    console.log(JSON.stringify({ event: 'NO_ACCEPT', reason: summary }));
  }

  await browser.close().catch(() => {});
})().catch((e) => {
  console.log(JSON.stringify({ event: 'FATAL', error: String(e).slice(0, 400) }));
  process.exit(1);
});
