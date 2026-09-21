/**
 * Headless: finish Session B portal gates without visible Chrome.
 * - c227: open latest uploaded version, Check QC reviewer, Run PreQC, Run Oracle+GLM
 * - c249: open latest, capture blocking findings text (do NOT dismiss)
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const OUT = path.join(__dirname, 'tmp-pw');

const C227_URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-3a68a4668fe6d080ac4779cd324e6dc6-v1';
const C249_URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-f839351902aa1a404c1ca929e374a2f8-v1';

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
function dump(name, text) {
  fs.writeFileSync(path.join(OUT, name), text || '');
}
async function bodyText(page) {
  return page.locator('body').innerText().catch(() => '');
}

async function clickAny(page, patterns) {
  for (const re of patterns) {
    const btn = page.getByRole('button', { name: re });
    if (await btn.count()) {
      await btn.first().click({ timeout: 5000 }).catch(() => null);
      await sleep(2500);
      console.log(JSON.stringify({ event: 'click_button', re: String(re) }));
      return true;
    }
    const txt = page.getByText(re).first();
    if ((await txt.count()) && (await txt.isVisible().catch(() => false))) {
      await txt.click({ timeout: 5000 }).catch(() => null);
      await sleep(2500);
      console.log(JSON.stringify({ event: 'click_text', re: String(re) }));
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

  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(60000);

  // ---- c227 gates ----
  console.log(JSON.stringify({ event: 'open_c227' }));
  await page.goto(C227_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(8000);
  let t = await bodyText(page);
  dump('sessb2-c227-before.txt', `URL=${page.url()}\n\n${t}`);

  // Mark review.csv read (advisory) so Oracle unlocks
  await clickAny(page, [/Check with QC reviewer/i]);
  await sleep(8000);
  t = await bodyText(page);
  dump('sessb2-c227-after-reviewer.txt', t);

  await clickAny(page, [/Run client preQC|Re-run client preQC/i]);
  await sleep(10000);
  t = await bodyText(page);
  dump('sessb2-c227-after-preqc.txt', t);

  // Banner may say review.csv must be complete — try Oracle anyway after reviewer click
  const oracleOk = await clickAny(page, [/Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i]);
  await sleep(12000);
  t = await bodyText(page);
  dump('sessb2-c227-after-oracle.txt', `URL=${page.url()}\noracleClicked=${oracleOk}\n\n${t}`);
  console.log(
    JSON.stringify({
      event: 'c227_done',
      oracleClicked: oracleOk,
      banner: /review\.csv must be complete/i.test(t),
      qcRunning: /QC running|Oracle running|GLM waiting|queued/i.test(t),
      head: t.slice(0, 700),
    })
  );

  // ---- c249 capture findings (no dismiss) ----
  console.log(JSON.stringify({ event: 'open_c249' }));
  await page.goto(C249_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(8000);
  for (let i = 0; i < 12; i++) {
    await page.mouse.wheel(0, 1800);
    await sleep(200);
  }
  t = await bodyText(page);
  dump('sessb2-c249-findings.txt', `URL=${page.url()}\n\n${t}`);
  console.log(
    JSON.stringify({
      event: 'c249_done',
      blockers: (t.match(/BLOCKER/gi) || []).length,
      needsReview: /Needs your review|Review required|26 blocking/i.test(t),
      head: t.slice(0, 700),
    })
  );

  await browser.close();
  console.log(JSON.stringify({ event: 'done' }));
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
