/**
 * Open a recent task by name substring and run PreQC + QC-Oracle-GLM.
 * node tmp-pw-open-run.js "gen-g857"
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const needle = process.argv[2];
if (!needle) { console.error('need task name substring'); process.exit(2); }
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const PORTAL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
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
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
    ignoreDefaultArgs: ['--enable-automation'],
    args: ['--window-position=-32000,-32000', '--window-size=1280,900', '--profile-directory=Profile 10'],
  });
  await sleep(2500);
  const page = browser.pages()[0] || (await browser.newPage());
  try {
    await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(5000);
    for (let i = 0; i < 8; i++) { await page.mouse.wheel(0, 1200); await sleep(400); }
    const link = page.getByText(new RegExp(needle, 'i')).first();
    console.log('link count', await link.count());
    if (!(await link.count())) throw new Error('task not found in recent list: ' + needle);
    await link.click();
    await sleep(8000);
    console.log('url', page.url());
    await clickText(page, /Run client preQC|Re-run client preQC/i, 'preqc');
    await sleep(12000);
    for (let i = 0; i < 15; i++) {
      if (!(await clickText(page, /^Dismiss$/i, 'dismiss'))) break;
    }
    const started =
      (await clickText(page, /Re-run QC-Oracle-GLM/i, 'rerun')) ||
      (await clickText(page, /Run QC-Oracle-GLM/i, 'run'));
    await sleep(5000);
    const text = await page.locator('body').innerText();
    fs.writeFileSync(`tmp-pw/openrun-${needle}.txt`, text);
    console.log(JSON.stringify({ needle, started, url: page.url(), head: text.slice(0, 800) }, null, 2));
  } finally {
    await browser.close().catch(() => {});
  }
})().catch((e) => { console.error('FAIL', e); process.exit(1); });
