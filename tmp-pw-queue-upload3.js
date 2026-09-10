/**
 * Finish remaining portal queue: reupload g734/g806/g857 + ensure gates on h40/c227.
 * Off-screen OpenCode chrome-profile. Never Confirm PreQC.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const PORTAL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const TASKS = [
  { short: 'health-h40', zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-health-h40.zip', url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-0f5e7ea213cebcd75662f8b0281f1da7-v1', mode: 'gates' },
  { short: 'code-c227', zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-code-c227.zip', url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-3a68a4668fe6d080ac4779cd324e6dc6-v1', mode: 'gates' },
  { short: 'gen-g734', zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g734.zip', mode: 'upload' },
  { short: 'gen-g806', zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g806.zip', mode: 'upload' },
];

async function clickText(page, re, label) {
  const loc = page.getByText(re).first();
  const n = await loc.count();
  const vis = n ? await loc.isVisible().catch(() => false) : false;
  console.log(`[${label}] n=${n} vis=${vis}`);
  if (n && vis) {
    await loc.click({ force: true }).catch(() => {});
    await sleep(2500);
    return true;
  }
  return false;
}

async function runGates(page, label) {
  await clickText(page, /Run client preQC|Re-run client preQC/i, `${label}-preqc`);
  await sleep(10000);
  for (let i = 0; i < 12; i++) {
    if (!(await clickText(page, /^Dismiss$/i, `${label}-dismiss`))) break;
  }
  return (
    (await clickText(page, /Re-run QC-Oracle-GLM/i, `${label}-rerun`)) ||
    (await clickText(page, /Run QC-Oracle-GLM/i, `${label}-run`))
  );
}

async function waitTaskPage(page, short) {
  for (let i = 0; i < 30; i++) {
    await sleep(2000);
    const u = page.url();
    const body = await page.locator('body').innerText();
    if (/#task=/.test(u)) return true;
    if (/Upload new version|Evaluation|Client preQC/i.test(body) && !/reading the bundle/i.test(body)) return true;
  }
  console.log(`[${short}] still not on task page:`, page.url());
  return false;
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
    for (const t of TASKS) {
      console.log(`\n=== ${t.mode.toUpperCase()} ${t.short} ===`);
      try {
        if (t.mode === 'gates') {
          await page.goto(t.url, { waitUntil: 'domcontentloaded', timeout: 120000 });
          await sleep(6000);
        } else {
          await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 120000 });
          await sleep(5000);
          const input = page.locator('input[type="file"]').first();
          if (!(await input.count())) throw new Error('no file input');
          await input.setInputFiles(t.zip);
          console.log('uploaded', t.short);
          await waitTaskPage(page, t.short);
        }
        const started = await runGates(page, t.short);
        await sleep(4000);
        const text = await page.locator('body').innerText();
        fs.writeFileSync(`tmp-pw/queue3-${t.short}.txt`, text);
        results.push({ short: t.short, ok: true, started, url: page.url(), head: text.slice(0, 500) });
      } catch (e) {
        console.error(t.short, e);
        results.push({ short: t.short, ok: false, error: String(e) });
      }
    }
  } finally {
    fs.writeFileSync('tmp-pw/queue-upload-log3.json', JSON.stringify({ at: new Date().toISOString(), results }, null, 2));
    console.log('\n=== SUMMARY3 ===');
    console.log(JSON.stringify(results, null, 2));
    await browser.close().catch(() => {});
  }
})().catch((e) => {
  console.error('FATAL', e);
  process.exit(1);
});
