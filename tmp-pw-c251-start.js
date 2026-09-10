const { chromium } = require('./tmp-pw/node_modules/playwright');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const url = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-db0490a135ad1cc1e0d71549021ddef3-v1';
  const browser = await chromium.launchPersistentContext(profile, { headless: false, channel: 'chrome' });
  const page = browser.pages()[0] || await browser.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(6000);
  const before = (await page.locator('body').innerText()).slice(0, 1500);
  // Run client preQC
  const preqc = page.getByRole('button', { name: /Run client preQC/i });
  if (await preqc.count()) {
    await preqc.first().click();
    console.log('CLICKED Run client preQC');
    await page.waitForTimeout(3000);
  } else {
    console.log('NO Run client preQC button', await page.getByText(/preQC/i).allTextContents());
  }
  // Run QC-Oracle-GLM (may be blocked by slot limit)
  const oracle = page.getByRole('button', { name: /Run QC-Oracle-GLM/i });
  if (await oracle.count()) {
    await oracle.first().click();
    console.log('CLICKED Run QC-Oracle-GLM');
    await page.waitForTimeout(5000);
  } else {
    console.log('NO Run QC-Oracle-GLM button');
  }
  await page.waitForTimeout(5000);
  const after = await page.locator('body').innerText();
  require('fs').writeFileSync('tmp-pw/c251-after-click.txt', after);
  console.log('AFTER_HEAD', after.slice(0, 2000));
  // detect running / slot messages
  const m = after.match(/slot|running|queued|limit|started|in progress|Wait/i);
  console.log('MATCH', m && m[0]);
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
