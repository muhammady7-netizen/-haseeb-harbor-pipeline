/**
 * law-b39 headless: upload rebuilt zip + review.csv to Drive task folder,
 * then upload zip to Shannon QC V1/V2 trainer.
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
  for (let i = 0; i < 40; i++) {
    await sleep(2000);
    const t = await body(page);
    if (/upload complete/i.test(t)) break;
  }
  await sleep(1500);
}

(async () => {
  const result = { ok: false, errors: [], folderUrl: FOLDER_URL };
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
    // Drive
    await page.goto(FOLDER_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(5000);
    if (page.url().includes('accounts.google.com')) throw new Error('Drive not logged in');
    await uploadFile(page, ZIP);
    console.log(JSON.stringify({ event: 'zip_uploaded' }));
    if (fs.existsSync(CSV)) {
      await uploadFile(page, CSV);
      console.log(JSON.stringify({ event: 'csv_uploaded' }));
    }
    await page.screenshot({ path: path.join(OUT, 'law-b39-v8-drive.png'), fullPage: true });
    fs.writeFileSync(path.join(OUT, 'law-b39-v8-drive.txt'), (await body(page)).slice(0, 8000));

    // QC upload
    await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(7000);
    const input = page.locator('input[type="file"]').first();
    if (!(await input.count())) throw new Error('no trainer file input');
    await input.setInputFiles(ZIP);
    console.log(JSON.stringify({ event: 'qc_file_set' }));
    for (let i = 0; i < 36; i++) {
      await sleep(5000);
      const t = await body(page);
      const url = page.url();
      console.log(JSON.stringify({ event: 'poll', i, url, reading: /reading the bundle/i.test(t) }));
      fs.writeFileSync(path.join(OUT, 'law-b39-v8-poll.txt'), `i=${i}\n${url}\n` + t.slice(0, 4000));
      if (url.includes('task=content-')) break;
      if (!/reading the bundle/i.test(t) && i > 3) break;
    }
    result.trainerUrl = page.url();
    await page.screenshot({ path: path.join(OUT, 'law-b39-v8-qc.png'), fullPage: true });
    fs.writeFileSync(path.join(OUT, 'law-b39-v8-qc.txt'), (await body(page)).slice(0, 10000));
    result.ok = true;
    fs.writeFileSync(path.join(OUT, 'law-b39-v8-result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(0);
  } catch (e) {
    result.errors.push(String(e && e.stack ? e.stack : e));
    fs.writeFileSync(path.join(OUT, 'law-b39-v8-result.json'), JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
