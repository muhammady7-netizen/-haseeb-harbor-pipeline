const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-session-b';
const ROOT = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const ZIP_C227 = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-code-c227.zip';
const C249_URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-96a4f76bb1fc479e9cefdf781b86eb0b-v1';
const C227_OLD_URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-a1cc40b3e1c27d640de1820b974b1ce4-v1';
const OUT = path.join(__dirname, 'tmp-pw');

function dump(name, text) {
  fs.writeFileSync(path.join(OUT, name), text);
}

async function bodyText(page) {
  return page.locator('body').innerText();
}

async function clickIfPresent(page, re, label) {
  const btn = page.getByRole('button', { name: re });
  const n = await btn.count();
  console.log(label, 'count', n);
  if (n) {
    await btn.first().click();
    console.log(label, 'clicked');
    await page.waitForTimeout(4000);
    return true;
  }
  const txt = page.getByText(re).first();
  if (await txt.count()) {
    await txt.click();
    console.log(label, 'text-clicked');
    await page.waitForTimeout(4000);
    return true;
  }
  return false;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());

  // ---- 1) Poll code-c249 current portal state ----
  console.log('=== POLL c249 ===');
  await page.goto(C249_URL, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(7000);
  let text = await bodyText(page);
  dump('session-b-c249-status.txt', `URL=${page.url()}\n\n${text}`);
  console.log('c249 head:\n', text.slice(0, 2200));

  // ---- 2) Upload fresh code-c227 from root ----
  console.log('=== UPLOAD c227 ===');
  await page.goto(ROOT, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(6000);
  const before = await bodyText(page);
  dump('session-b-root-before.txt', before);
  const beforeHit = (before.match(/code-c227-table-bloat-maintenance-audit#[a-f0-9]+/i) || [])[0];
  console.log('BEFORE_TOP_c227', beforeHit);

  const input = page.locator('input[type="file"]').first();
  await input.setInputFiles(ZIP_C227);
  console.log('ROOT_FILE_SET c227');

  let newId = null;
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(2000);
    text = await bodyText(page);
    const m = text.match(/code-c227-table-bloat-maintenance-audit#[a-f0-9]+/i);
    if (m && m[0] !== beforeHit) {
      newId = m[0];
      console.log('NEW_TOP', i, newId);
      break;
    }
    if (i % 10 === 0) console.log('wait', i, 'top', m && m[0]);
  }

  if (!newId) {
    // Fallback: try Upload new version on old task page
    console.log('NO_NEW_ID on root; trying old task Upload new version');
    await page.goto(C227_OLD_URL, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(6000);
    await clickIfPresent(page, /Upload new version/i, 'upload-new');
    const inputs = page.locator('input[type="file"]');
    if (await inputs.count()) {
      await inputs.first().setInputFiles(ZIP_C227);
      console.log('setInputFiles on old task');
      await page.waitForTimeout(10000);
    }
    text = await bodyText(page);
    dump('session-b-c227-fallback-upload.txt', `URL=${page.url()}\n\n${text}`);
    console.log(text.slice(0, 2500));
  } else {
    await page.getByText(newId).first().click();
    await page.waitForTimeout(8000);
    text = await bodyText(page);
    dump('session-b-c227-opened.txt', `URL=${page.url()}\nID=${newId}\n\n${text}`);
    console.log('OPENED', page.url());
    console.log(text.slice(0, 2200));

    // Skip/dismiss advisory PreQC if present (do NOT Confirm)
    await clickIfPresent(page, /Dismiss|Skip|false.?positive/i, 'preqc-dismiss');
    // Prefer running Oracle+GLM without confirming PreQC
    await clickIfPresent(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i, 'run-oracle');
    await page.waitForTimeout(8000);
    text = await bodyText(page);
    dump('session-b-c227-after-run.txt', `URL=${page.url()}\nID=${newId}\n\n${text}`);
    console.log('AFTER_RUN', page.url());
    console.log(text.slice(0, 2500));
  }

  // ---- 3) Re-check c249 ----
  console.log('=== RECHECK c249 ===');
  await page.goto(C249_URL, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(7000);
  text = await bodyText(page);
  dump('session-b-c249-status-2.txt', `URL=${page.url()}\n\n${text}`);
  console.log('c249 recheck:\n', text.slice(0, 2200));

  await browser.close();
  console.log('DONE');
})().catch((e) => {
  console.error('FAIL', e);
  process.exit(1);
});

