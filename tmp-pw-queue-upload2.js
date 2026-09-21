/**
 * Finish gates on recently uploaded tasks + retry remaining uploads.
 * Uses OpenCode chrome-profile off-screen. Never Confirm PreQC.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const PORTAL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';

const OPEN_AND_RUN = [
  {
    short: 'health-h40',
    url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-0f5e7ea213cebcd75662f8b0281f1da7-v1',
  },
  {
    short: 'code-c227',
    url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-3a68a4668fe6d080ac4779cd324e6dc6-v1',
  },
];

const REUPLOAD = [
  { short: 'gen-g734', zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g734.zip' },
  { short: 'gen-g806', zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g806.zip' },
  { short: 'gen-g857', zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g857.zip' },
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function clickText(page, re, label) {
  const loc = page.getByText(re).first();
  const n = await loc.count();
  const vis = n ? await loc.isVisible().catch(() => false) : false;
  console.log(`[${label}] n=${n} vis=${vis}`);
  if (n && vis) {
    await loc.click({ force: true }).catch(() => {});
    await sleep(3000);
    return true;
  }
  return false;
}

async function runGates(page, label) {
  await clickText(page, /Run client preQC|Re-run client preQC/i, `${label}-preqc`);
  await sleep(8000);
  // Dismiss only — never Confirm
  for (let i = 0; i < 10; i++) {
    if (!(await clickText(page, /^Dismiss$/i, `${label}-dismiss`))) break;
  }
  const started =
    (await clickText(page, /Re-run QC-Oracle-GLM/i, `${label}-rerun`)) ||
    (await clickText(page, /Run QC-Oracle-GLM/i, `${label}-run`));
  await sleep(5000);
  return started;
}

(async () => {
  fs.mkdirSync('tmp-pw', { recursive: true });
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--window-position=-32000,-32000', '--window-size=1280,900'],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  const results = [];

  try {
    for (const t of OPEN_AND_RUN) {
      console.log('\n=== GATES', t.short, '===');
      await page.goto(t.url, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(7000);
      const started = await runGates(page, t.short);
      const text = await page.locator('body').innerText();
      fs.writeFileSync(`tmp-pw/queue2-${t.short}.txt`, text);
      results.push({ short: t.short, phase: 'gates', started, url: page.url(), head: text.slice(0, 600) });
    }

    for (const item of REUPLOAD) {
      console.log('\n=== REUPLOAD', item.short, '===');
      await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(5000);
      const input = page.locator('input[type="file"]').first();
      if (!(await input.count())) {
        results.push({ short: item.short, ok: false, error: 'no file input' });
        continue;
      }
      await input.setInputFiles(item.zip);
      console.log('uploaded', item.short);
      // wait until we leave root or reading finishes
      for (let i = 0; i < 24; i++) {
        await sleep(2500);
        const u = page.url();
        const body = await page.locator('body').innerText();
        if (/#task=/.test(u) || /Upload new version|Evaluation|Client preQC/i.test(body)) {
          console.log('landed', item.short, u);
          break;
        }
        if (/reading the bundle/i.test(body)) continue;
      }
      const started = await runGates(page, item.short);
      const text = await page.locator('body').innerText();
      fs.writeFileSync(`tmp-pw/queue2-${item.short}.txt`, text);
      results.push({
        short: item.short,
        phase: 'reupload',
        ok: true,
        started,
        url: page.url(),
        head: text.slice(0, 700),
      });
    }
  } finally {
    fs.writeFileSync('tmp-pw/queue-upload-log2.json', JSON.stringify({ at: new Date().toISOString(), results }, null, 2));
    console.log('\n=== SUMMARY2 ===');
    console.log(JSON.stringify(results, null, 2));
    await browser.close().catch(() => {});
  }
})().catch((e) => {
  console.error('FATAL', e);
  process.exit(1);
});
