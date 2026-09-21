/**
 * Session B headless QC queue — uses shared opencode chrome-profile.
 * headless:true = no visible Chrome window.
 * Respects portal max ~3 concurrent Oracle+GLM evals.
 *
 * Session B only: code-c227 (upload+start), code-c249 (open+act).
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const OUT = path.join(__dirname, 'tmp-pw');
const MAX_EVAL = 3;

const JOBS = [
  {
    short: 'code-c227',
    stem: 'code-c227-table-bloat-maintenance-audit',
    zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-code-c227.zip',
    upload: true, // fresh v14
  },
  {
    short: 'code-c249',
    stem: 'code-c249-recurring-report-source-selection-audit',
    zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-code-c249.zip',
    upload: false, // already on portal; open + review/start if needed
  },
];

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
function dump(name, text) {
  fs.writeFileSync(path.join(OUT, name), text || '');
}
async function bodyText(page) {
  return page.locator('body').innerText().catch(() => '');
}
async function clickText(page, re) {
  const loc = page.getByText(re).first();
  if ((await loc.count()) && (await loc.isVisible().catch(() => false))) {
    await loc.click();
    await sleep(3000);
    return true;
  }
  return false;
}
async function clickButton(page, re) {
  const btn = page.getByRole('button', { name: re });
  if (await btn.count()) {
    await btn.first().click();
    await sleep(3000);
    return true;
  }
  return clickText(page, re);
}

async function goRoot(page) {
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  return bodyText(page);
}

async function countActiveEvals(text) {
  // "QC running" on recent-task cards is the best signal
  const running = (text.match(/\bQC running\b/gi) || []).length;
  return running;
}

async function openLatestStem(page, stem) {
  await goRoot(page);
  for (let i = 0; i < 10; i++) {
    await page.mouse.wheel(0, 1600);
    await sleep(250);
  }
  // Prefer first matching card link containing stem
  const link = page.locator(`text=${stem}`).first();
  if (!(await link.count())) {
    console.log(JSON.stringify({ event: 'open_miss', stem }));
    return '';
  }
  await link.click();
  await sleep(8000);
  const t = await bodyText(page);
  dump(`sessb-${stem}-opened.txt`, `URL=${page.url()}\n\n${t}`);
  console.log(JSON.stringify({ event: 'opened', stem, url: page.url() }));
  return t;
}

async function uploadZip(page, zip, short) {
  await goRoot(page);
  const input = page.locator('input[type="file"]').first();
  await input.setInputFiles(zip);
  console.log(JSON.stringify({ event: 'uploaded', short, zip }));
  await sleep(15000);
  const t = await bodyText(page);
  dump(`sessb-${short}-after-upload.txt`, t);
  return t;
}

async function startGates(page, short, { allowEval }) {
  // Never Confirm PreQC. Optional advisory PreQC is fine.
  const pre = await clickButton(page, /Run client preQC|Re-run client preQC/i);
  let ev = false;
  if (allowEval) {
    ev = await clickButton(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i);
  } else {
    console.log(JSON.stringify({ event: 'defer_eval', short, reason: 'max_eval' }));
  }
  const t = await bodyText(page);
  dump(`sessb-${short}-after-gates.txt`, t);
  console.log(
    JSON.stringify({
      event: 'gates',
      short,
      preqc: pre,
      oracle: ev,
      head: t.slice(0, 900),
    })
  );
  return { pre, ev, t };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  for (const name of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, name));
    } catch {}
  }

  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true, // no on-screen Chrome
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(60000);

  let root = await goRoot(page);
  dump('sessb-root.txt', root);
  if (/accounts\.google\.com|Sign in with Google/i.test(root) && !/muhammad\.y7@turing\.com/i.test(root)) {
    console.log(JSON.stringify({ event: 'login_required' }));
    dump('sessb-login-required.txt', root);
    await browser.close();
    process.exit(2);
  }
  console.log(JSON.stringify({ event: 'logged_in', head: root.slice(0, 350) }));

  let active = await countActiveEvals(root);
  console.log(JSON.stringify({ event: 'slots_start', active, max: MAX_EVAL }));

  const results = [];
  for (const job of JOBS) {
    try {
      if (job.upload) {
        await uploadZip(page, job.zip, job.short);
      }
      let opened = await openLatestStem(page, job.stem);
      if (!opened) opened = await openLatestStem(page, job.short);

      // Refresh slot count from root
      root = await goRoot(page);
      active = await countActiveEvals(root);
      console.log(JSON.stringify({ event: 'slots', short: job.short, active }));

      // Re-open task
      opened = (await openLatestStem(page, job.stem)) || opened;
      const allowEval = active < MAX_EVAL;
      const g = await startGates(page, job.short, { allowEval });
      if (g.ev) active += 1;
      results.push({
        short: job.short,
        uploaded: !!job.upload,
        preqc: g.pre,
        oracle: g.ev,
        deferred: !allowEval,
      });
    } catch (e) {
      console.log(JSON.stringify({ event: 'error', short: job.short, error: String(e) }));
      results.push({ short: job.short, error: String(e) });
    }
  }

  dump('sessb-queue-results.json', JSON.stringify(results, null, 2));
  console.log(JSON.stringify({ event: 'done', results, active }));
  await browser.close();
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
