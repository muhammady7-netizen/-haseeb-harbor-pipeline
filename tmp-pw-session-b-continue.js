/**
 * Session B headless keep-going queue.
 * Uses shared opencode chrome-profile, headless, never kill other Chrome.
 * 1) Re-upload c227 v14b
 * 2) Check with QC reviewer + PreQC + Oracle
 * 3) Open c249 and dump findings / try download package if available
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const ZIP227 = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-code-c227.zip';
const C249 =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-f839351902aa1a404c1ca929e374a2f8-v1';
const OUT = path.join(__dirname, 'tmp-pw');

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
function dump(n, t) {
  fs.writeFileSync(path.join(OUT, n), t || '');
}
async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}
async function clickAny(page, patterns) {
  for (const re of patterns) {
    const btn = page.getByRole('button', { name: re });
    if (await btn.count()) {
      await btn.first().click({ timeout: 8000 }).catch(() => null);
      await sleep(3000);
      console.log(JSON.stringify({ event: 'click_btn', re: String(re) }));
      return true;
    }
    const txt = page.getByText(re).first();
    if ((await txt.count()) && (await txt.isVisible().catch(() => false))) {
      await txt.click({ timeout: 8000 }).catch(() => null);
      await sleep(3000);
      console.log(JSON.stringify({ event: 'click_txt', re: String(re) }));
      return true;
    }
  }
  return false;
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
      headless: true,
      channel: 'chrome',
      acceptDownloads: true,
      args: ['--disable-blink-features=AutomationControlled'],
    });
  } catch (e) {
    console.log(JSON.stringify({ event: 'PROFILE_BUSY', error: String(e).slice(0, 250) }));
    process.exit(3);
  }

  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(60000);

  // login check
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  let t = await body(page);
  dump('sessb3-root.txt', t);
  if (/Sign in with Google|accounts\.google/i.test(t) && !/muhammad\.y7@turing\.com/i.test(t)) {
    console.log(JSON.stringify({ event: 'login_required' }));
    await browser.close();
    process.exit(2);
  }
  console.log(JSON.stringify({ event: 'logged_in' }));

  // upload c227
  const input = page.locator('input[type="file"]').first();
  await input.setInputFiles(ZIP227);
  console.log(JSON.stringify({ event: 'uploaded_c227' }));
  await sleep(15000);
  t = await body(page);
  dump('sessb3-c227-after-upload.txt', t);

  // open latest c227
  for (let i = 0; i < 8; i++) {
    await page.mouse.wheel(0, 1600);
    await sleep(200);
  }
  const link = page.locator('text=code-c227-table-bloat-maintenance-audit').first();
  if (await link.count()) {
    await link.click();
    await sleep(8000);
  }
  t = await body(page);
  dump('sessb3-c227-opened.txt', `URL=${page.url()}\n\n${t}`);
  console.log(JSON.stringify({ event: 'c227_opened', url: page.url() }));

  await clickAny(page, [/Check with QC reviewer/i]);
  await sleep(12000); // cloud GLM review
  t = await body(page);
  dump('sessb3-c227-after-reviewer.txt', t);

  await clickAny(page, [/Run client preQC|Re-run client preQC/i]);
  await sleep(15000);
  t = await body(page);
  dump('sessb3-c227-after-preqc.txt', t);

  const oracle = await clickAny(page, [/Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i]);
  await sleep(12000);
  t = await body(page);
  dump('sessb3-c227-after-oracle.txt', `URL=${page.url()}\noracle=${oracle}\n\n${t}`);
  console.log(
    JSON.stringify({
      event: 'c227_gates',
      oracle,
      reviewComplete: /Complete/i.test(t) && !/Not finished/i.test(t),
      banner: /review\.csv must be complete/i.test(t),
      running: /QC running|Oracle running|GLM waiting|queued/i.test(t),
      head: t.slice(0, 600),
    })
  );

  // c249 dump + try download zip from run history
  await page.goto(C249, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(8000);
  for (let i = 0; i < 15; i++) {
    await page.mouse.wheel(0, 1800);
    await sleep(200);
  }
  t = await body(page);
  dump('sessb3-c249.txt', `URL=${page.url()}\n\n${t}`);

  // Try click download zip if present
  const dl = page.getByText(/download|zip|Harbor package/i).first();
  console.log(JSON.stringify({ event: 'c249_dump', blockers: (t.match(/BLOCKER/gi) || []).length, url: page.url() }));

  await browser.close();
  console.log(JSON.stringify({ event: 'done' }));
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
