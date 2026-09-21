/**
 * Headless h40 follow-up: finish upload if needed, open LATEST version,
 * start gates only when buttons are enabled (respect 3-slot portal cap).
 * Uses shared opencode chrome-profile; headless; no taskkill.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const ZIP = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-health-h40.zip';
const STEM = 'health-h40-critical-result-acknowledgement';
const OUT = path.join(__dirname, 'tmp-pw');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const dump = (name, t) => fs.writeFileSync(path.join(OUT, name), t || '');

async function bodyText(page) {
  return page.locator('body').innerText().catch(() => '');
}

async function clickEnabled(page, re) {
  const loc = page.getByRole('button', { name: re }).first();
  if (!(await loc.count())) return false;
  const disabled =
    (await loc.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
    (await loc.isDisabled().catch(() => true));
  if (disabled) {
    const title = await loc.getAttribute('title').catch(() => '');
    console.log(JSON.stringify({ event: 'btn_disabled', name: String(re), title }));
    return false;
  }
  await loc.click({ timeout: 10000 });
  await sleep(4000);
  return true;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
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

  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  let t = await bodyText(page);
  dump('h40-v10-root.txt', t);
  console.log(JSON.stringify({ event: 'logged_in', head: t.slice(0, 300) }));

  // Upload (idempotent new version)
  const input = page.locator('input[type="file"]').first();
  await input.setInputFiles(ZIP);
  console.log(JSON.stringify({ event: 'upload_started', zip: ZIP }));

  let url = page.url();
  for (let i = 0; i < 90; i++) {
    await sleep(2000);
    t = await bodyText(page);
    url = page.url();
    if (/preparing upload/i.test(t)) {
      if (i % 5 === 0) console.log(JSON.stringify({ event: 'upload_wait', i }));
      continue;
    }
    if (/#task=/.test(url)) {
      console.log(JSON.stringify({ event: 'landed_task', url, i }));
      break;
    }
    // new card on recent list
    if (/health-h40-critical-result-acknowledgement#[0-9a-f]{6}/i.test(t) && !/preparing upload/i.test(t)) {
      console.log(JSON.stringify({ event: 'upload_settled_root', i }));
      break;
    }
  }
  dump('h40-v10-after-upload.txt', `URL=${url}\n\n${t}`);

  // Open latest stem from root if not on task
  if (!/#task=/.test(page.url())) {
    await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(4000);
    const link = page.getByText(STEM, { exact: false }).first();
    await link.click({ timeout: 20000 });
    await sleep(8000);
  }
  t = await bodyText(page);
  url = page.url();
  dump('h40-v10-opened.txt', `URL=${url}\n\n${t}`);
  console.log(JSON.stringify({ event: 'opened', url, head: t.slice(0, 500) }));

  // Extract version hash from page
  const m = t.match(/health-h40-critical-result-acknowledgement#([0-9a-f]{6})/i);
  console.log(JSON.stringify({ event: 'version', hash: m && m[1], url }));

  // Poll until a gate button is enabled (slots free), then start Oracle+GLM
  let pre = false;
  let ev = false;
  for (let i = 0; i < 60; i++) {
    t = await bodyText(page);
    const slotsBusy = /3 run slots are currently in use|run slots are currently in use/i.test(t);
    console.log(JSON.stringify({ event: 'slot_poll', i, slotsBusy, url: page.url() }));

    pre = (await clickEnabled(page, /Run client preQC|Re-run client preQC/i)) || pre;
    ev = (await clickEnabled(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i)) || ev;
    if (ev) break;

    // refresh task page
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 90000 }).catch(() => {});
    await sleep(15000);
  }

  t = await bodyText(page);
  dump('h40-v10-after-gates.txt', `URL=${page.url()}\n\n${t}`);
  console.log(
    JSON.stringify({
      event: 'done',
      url: page.url(),
      preqc: pre,
      oracle: ev,
      head: t.slice(0, 900),
    })
  );
  await browser.close().catch(() => {});
})().catch(async (e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
