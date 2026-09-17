/**
 * law-b39 v10: upload zip+review.csv to Drive, upload zip to Shannon QC trainer,
 * then trigger PreQC + QC check on the new task page.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const FOLDER_URL =
  'https://drive.google.com/drive/folders/1nXcKPyHmrJxPuig-ptnrwfnt_Mi57U9Y';
const ZIP =
  'C:/Users/Haseeb Mirza/Downloads/law-b39-l16-custody-letter-instruction-audit.zip';
const CSV = path.join(__dirname, 'tmp-pw/review.csv');
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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
async function uploadDriveFile(page, filePath) {
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
  for (let i = 0; i < 60; i++) {
    await sleep(2000);
    const t = await body(page);
    if (/upload complete|1 upload complete/i.test(t)) break;
  }
  await sleep(1500);
}

async function clickFirstEnabled(page, labels, result) {
  for (const label of labels) {
    const btn = page.getByRole('button', { name: new RegExp(label, 'i') }).first();
    if (!(await btn.count())) continue;
    const disabled =
      (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
      (await btn.isDisabled().catch(() => false));
    if (disabled) continue;
    await btn.click().catch(() => {});
    result.clicks.push(label);
    await sleep(2500);
  }
}

(async () => {
  const result = { ok: false, errors: [], clicks: [], folderUrl: FOLDER_URL };
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
    if (!fs.existsSync(ZIP)) throw new Error('missing zip: ' + ZIP);

    // Drive
    await page.goto(FOLDER_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(5000);
    if (page.url().includes('accounts.google.com')) throw new Error('Drive not logged in');
    await uploadDriveFile(page, ZIP);
    console.log(JSON.stringify({ event: 'zip_uploaded' }));
    if (fs.existsSync(CSV)) {
      await uploadDriveFile(page, CSV);
      console.log(JSON.stringify({ event: 'csv_uploaded' }));
    }
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10-drive.png'), fullPage: true });

    // QC upload (new version)
    await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(7000);
    const input = page.locator('input[type="file"]').first();
    if (!(await input.count())) throw new Error('no trainer file input');
    await input.setInputFiles(ZIP);
    console.log(JSON.stringify({ event: 'qc_file_set' }));
    let taskUrl = '';
    for (let i = 0; i < 48; i++) {
      await sleep(5000);
      const t = await body(page);
      const url = page.url();
      console.log(JSON.stringify({ event: 'poll', i, url: url.slice(0, 120) }));
      fs.writeFileSync(path.join(OUT, 'law-b39-v10-poll.txt'), `i=${i}\n${url}\n` + t.slice(0, 5000));
      if (url.includes('task=content-')) {
        taskUrl = url;
        break;
      }
      if (!/reading the bundle/i.test(t) && i > 5 && url.includes('task=')) {
        taskUrl = url;
        break;
      }
    }
    result.trainerUrl = taskUrl || page.url();
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10-qc.png'), fullPage: true });
    fs.writeFileSync(path.join(OUT, 'law-b39-v10-qc.txt'), (await body(page)).slice(0, 12000));

    // Prefer open latest task if still on list
    if (!String(result.trainerUrl).includes('task=content-')) {
      const link = page.locator('a[href*="task=content-"]').first();
      if (await link.count()) {
        await link.click();
        await sleep(5000);
        result.trainerUrl = page.url();
      }
    }

    // Trigger PreQC + QC check
    await clickFirstEnabled(
      page,
      [
        '^Re-run$',
        '^Run$',
        'Run client preQC',
        'Run PreQC',
        'Optional deep-dive',
        'QC check',
        'Upload new version',
      ],
      result
    );

    // Also try review.csv replace if prompted
    const csvInput = page.locator('input[type="file"]').nth(1);
    if ((await page.locator('input[type="file"]').count()) > 1 && fs.existsSync(CSV)) {
      try {
        await csvInput.setInputFiles(CSV);
        result.clicks.push('review_csv_set');
      } catch {}
    }

    await sleep(4000);
    const after = await body(page);
    fs.writeFileSync(path.join(OUT, 'law-b39-v10-after-gates.txt'), after.slice(0, 12000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v10-after-gates.png'), fullPage: true });
    result.snippet = after.slice(0, 2500);
    result.ok = true;
    fs.writeFileSync(path.join(OUT, 'law-b39-v10-result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(0);
  } catch (e) {
    result.errors.push(String(e && e.stack ? e.stack : e));
    fs.writeFileSync(path.join(OUT, 'law-b39-v10-result.json'), JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
