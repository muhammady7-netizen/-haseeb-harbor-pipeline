const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  let browser;
  try {
    browser = await chromium.launchPersistentContext(profile, { headless: false, channel: 'chrome' });
  } catch (e) {
    console.log('PRIMARY_FAIL', String(e).slice(0,200));
    // try non-persistent chromium with storage state if any
    throw e;
  }
  const page = browser.pages()[0] || await browser.newPage();
  const c251 = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-db0490a135ad1cc1e0d71549021ddef3-v1';
  await page.goto(c251, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(8000);
  for (const label of ['Run client preQC', 'Run QC-Oracle-GLM']) {
    const btn = page.getByRole('button', { name: new RegExp(label, 'i') });
    const n = await btn.count();
    console.log('BUTTON', label, n);
    if (n) {
      await btn.first().click();
      console.log('CLICKED', label);
      await page.waitForTimeout(4000);
    }
  }
  const text = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/c251-started.txt', text);
  console.log(text.slice(0, 2500));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
