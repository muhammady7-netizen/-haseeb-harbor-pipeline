/**
 * law-b39 headless:
 * A) upload review.csv (correct name) into Drive task folder
 * B) upload zip to Shannon QC V2 + start PreQC then QC-Oracle-GLM when possible
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const FOLDER_URL =
  'https://drive.google.com/drive/folders/1nXcKPyHmrJxPuig-ptnrwfnt_Mi57U9Y';
const CSV = path.join(__dirname, 'tmp-pw/review.csv');
const ZIP =
  'C:/Users/Haseeb Mirza/Downloads/law-b39-l16-custody-letter-instruction-audit.zip';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function dump(name, text) {
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(
    path.join(OUT, name),
    typeof text === 'string' ? text : JSON.stringify(text, null, 2)
  );
}

function clearLocks() {
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
    } catch {}
  }
}

async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}

async function uploadFile(page, filePath) {
  await page.keyboard.press('Escape').catch(() => {});
  await sleep(400);
  await page.getByRole('button', { name: /^New$/i }).first().click({ timeout: 15000 });
  await sleep(800);
  const item = page.getByRole('menuitem', { name: /File upload/i }).first();
  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser', { timeout: 20000 }),
    item.click({ timeout: 15000 }),
  ]);
  await chooser.setFiles(filePath);
  for (let i = 0; i < 30; i++) {
    await sleep(2000);
    const t = await body(page);
    if (/upload complete/i.test(t)) break;
  }
  await sleep(1500);
}

async function clickEnabled(page, re) {
  const loc = page.getByRole('button', { name: re }).first();
  if (!(await loc.count())) return false;
  const disabled =
    (await loc.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
    (await loc.isDisabled().catch(() => false));
  if (disabled) {
    console.log(JSON.stringify({ event: 'btn_disabled', name: String(re) }));
    return false;
  }
  await loc.click({ timeout: 10000 });
  return true;
}

(async () => {
  const result = {
    ok: false,
    step: 'start',
    folderUrl: FOLDER_URL,
    trainerUrl: null,
    errors: [],
  };
  clearLocks();
  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    viewport: { width: 1440, height: 960 },
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = context.pages()[0] || (await context.newPage());

  try {
    // ---- A: Drive review.csv ----
    result.step = 'drive_review_csv';
    await page.goto(FOLDER_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(5000);
    if (page.url().includes('accounts.google.com')) throw new Error('Drive not logged in');
    await uploadFile(page, CSV);
    await page.screenshot({ path: path.join(OUT, 'law-b39-v5-drive.png'), fullPage: true });
    dump('law-b39-v5-drive-body.txt', (await body(page)).slice(0, 8000));
    console.log(JSON.stringify({ event: 'review_csv_uploaded' }));

    // ---- B: Shannon QC upload ----
    result.step = 'qc_upload';
    await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    await page.screenshot({ path: path.join(OUT, 'law-b39-v5-trainer.png'), fullPage: true });
    dump('law-b39-v5-trainer1.txt', (await body(page)).slice(0, 6000));

    if (page.url().includes('accounts.google.com')) throw new Error('Trainer not logged in');

    let input = page.locator('input[type="file"]').first();
    if (!(await input.count())) {
      // try New Task / Upload
      const up = page.getByRole('button', { name: /Upload|New task|Submit/i }).first();
      if (await up.count()) await up.click().catch(() => {});
      await sleep(2000);
      input = page.locator('input[type="file"]').first();
    }
    if (!(await input.count())) throw new Error('No file input on trainer');
    await input.setInputFiles(ZIP);
    console.log(JSON.stringify({ event: 'qc_file_set' }));
    await sleep(20000);

    let t = await body(page);
    dump('law-b39-v5-after-upload.txt', t.slice(0, 10000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v5-after-upload.png'), fullPage: true });
    result.trainerUrl = page.url();
    console.log(JSON.stringify({ event: 'after_upload', url: page.url() }));

    // Start PreQC if available
    result.step = 'preqc';
    const preqc =
      (await clickEnabled(page, /Run PreQC|Start PreQC|Client PreQC|Pre-?QC/i)) ||
      (await clickEnabled(page, /PreQC/i));
    console.log(JSON.stringify({ event: 'preqc_click', preqc }));
    await sleep(8000);

    // Confirm / dismiss dialogs carefully — never Confirm Harbor findings as FP
    // But do confirm starting PreQC if asked
    const confirm = page.getByRole('button', { name: /^Confirm$/i }).first();
    if (await confirm.count()) {
      const title = await body(page);
      if (/PreQC|start|run/i.test(title) && !/false positive|dismiss finding/i.test(title)) {
        await confirm.click().catch(() => {});
        await sleep(3000);
      }
    }

    t = await body(page);
    dump('law-b39-v5-after-preqc.txt', t.slice(0, 10000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v5-preqc.png'), fullPage: true });

    // QC-Oracle-GLM when enabled
    result.step = 'oracle_glm';
    const glm =
      (await clickEnabled(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM|QC-Oracle-GLM/i)) ||
      (await clickEnabled(page, /Oracle.?GLM/i));
    console.log(JSON.stringify({ event: 'glm_click', glm }));
    await sleep(10000);

    t = await body(page);
    dump('law-b39-v5-final.txt', t.slice(0, 12000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v5-final.png'), fullPage: true });
    result.trainerUrl = page.url();
    result.finalSnippet = t.slice(0, 2000);
    result.ok = true;
    result.step = 'done';
    dump('law-b39-v5-result.json', result);
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(0);
  } catch (e) {
    result.errors.push(String(e && e.stack ? e.stack : e));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v5-error.png'), fullPage: true }).catch(() => {});
    dump('law-b39-v5-result.json', result);
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
