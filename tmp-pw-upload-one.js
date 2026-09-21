/**
 * Upload one zip at a time with fresh Playwright context (avoids mid-queue chrome death).
 * Usage: node tmp-pw-upload-one.js <short> <zipPath>
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const PORTAL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const short = process.argv[2];
const zip = process.argv[3];
if (!short || !zip) {
  console.error('usage: node tmp-pw-upload-one.js <short> <zip>');
  process.exit(2);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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
    ],
  });
  await sleep(2500);
  const page = browser.pages()[0] || (await browser.newPage());
  try {
    await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(5000);
    const body0 = await page.locator('body').innerText();
    if (/Sign in with Google/i.test(body0)) throw new Error('login lost');
    const input = page.locator('input[type="file"]').first();
    if (!(await input.count())) throw new Error('no file input');
    await input.setInputFiles(zip);
    console.log('uploaded', short);
    for (let i = 0; i < 40; i++) {
      await sleep(2000);
      if (/#task=/.test(page.url())) break;
      const b = await page.locator('body').innerText();
      if (/Upload new version|Client preQC|Evaluation/i.test(b) && !/reading the bundle/i.test(b)) break;
    }
    await clickText(page, /Run client preQC|Re-run client preQC/i, 'preqc');
    await sleep(10000);
    for (let i = 0; i < 12; i++) {
      if (!(await clickText(page, /^Dismiss$/i, 'dismiss'))) break;
    }
    const started =
      (await clickText(page, /Re-run QC-Oracle-GLM/i, 'rerun')) ||
      (await clickText(page, /Run QC-Oracle-GLM/i, 'run'));
    await sleep(5000);
    const text = await page.locator('body').innerText();
    fs.writeFileSync(`tmp-pw/one-${short}.txt`, text);
    const out = { short, ok: true, started, url: page.url(), head: text.slice(0, 700) };
    fs.writeFileSync(`tmp-pw/one-${short}.json`, JSON.stringify(out, null, 2));
    console.log(JSON.stringify(out, null, 2));
  } finally {
    await browser.close().catch(() => {});
  }
})().catch((e) => {
  console.error('FAIL', e);
  process.exit(1);
});
