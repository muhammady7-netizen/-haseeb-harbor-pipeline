/**
 * Upload remaining ready_final: g734, g806, g857. Off-screen profile. Never Confirm.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const PORTAL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const QUEUE = [
  { short: 'gen-g734', zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g734.zip' },
  { short: 'gen-g806', zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g806.zip' },
  { short: 'gen-g857', zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g857.zip' },
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
  await sleep(12000);
  for (let i = 0; i < 12; i++) {
    if (!(await clickText(page, /^Dismiss$/i, `${label}-dismiss`))) break;
  }
  return (
    (await clickText(page, /Re-run QC-Oracle-GLM/i, `${label}-rerun`)) ||
    (await clickText(page, /Run QC-Oracle-GLM/i, `${label}-run`))
  );
}

(async () => {
  fs.mkdirSync('tmp-pw', { recursive: true });
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
    ignoreDefaultArgs: ['--enable-automation'],
    args: [
      '--window-position=-32000,-32000',
      '--window-size=1280,900',
      '--profile-directory=Profile 10',
      '--disable-blink-features=AutomationControlled',
      '--no-first-run',
      '--no-default-browser-check',
    ],
  });
  // Prefer an existing page from Profile 10; otherwise open one.
  await new Promise((r) => setTimeout(r, 3000));
  const page = browser.pages().find((p) => !p.url().startsWith('chrome')) || browser.pages()[0] || (await browser.newPage());
  console.log('pages', browser.pages().length, 'url', page.url());
  const results = [];
  try {
    for (const item of QUEUE) {
      console.log('\n===', item.short, '===');
      try {
        await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 120000 });
        await sleep(5000);
        const body0 = await page.locator('body').innerText();
        if (/Sign in with Google/i.test(body0) || /accounts\.google\.com/i.test(page.url())) {
          results.push({ short: item.short, ok: false, error: 'login lost' });
          break;
        }
        const input = page.locator('input[type="file"]').first();
        if (!(await input.count())) throw new Error('no file input');
        await input.setInputFiles(item.zip);
        console.log('uploaded files set');
        for (let i = 0; i < 36; i++) {
          await sleep(2500);
          const u = page.url();
          const b = await page.locator('body').innerText();
          if (/#task=/.test(u)) { console.log('on task', u); break; }
          if (/Upload new version|Client preQC|Evaluation/i.test(b) && !/reading the bundle/i.test(b)) break;
        }
        const started = await runGates(page, item.short);
        await sleep(5000);
        const text = await page.locator('body').innerText();
        fs.writeFileSync(`tmp-pw/cont-${item.short}.txt`, text);
        results.push({ short: item.short, ok: true, started, url: page.url(), head: text.slice(0, 600) });
      } catch (e) {
        console.error(item.short, e);
        results.push({ short: item.short, ok: false, error: String(e) });
      }
    }
  } finally {
    fs.writeFileSync('tmp-pw/continue-upload-log.json', JSON.stringify({ at: new Date().toISOString(), results }, null, 2));
    console.log('\n=== CONTINUE SUMMARY ===');
    console.log(JSON.stringify(results, null, 2));
    await browser.close().catch(() => {});
  }
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
