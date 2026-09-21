const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const zipPath = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-health-h40.zip';
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || await browser.newPage();
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', {
    waitUntil: 'domcontentloaded',
    timeout: 90000,
  });
  await page.waitForTimeout(6000);
  const before = await page.locator('body').innerText();
  const beforeFirst = (before.match(/health-h40-critical-result-acknowledgement#[a-f0-9]+/i) || [])[0];
  console.log('BEFORE_TOP', beforeFirst);

  const input = page.locator('input[type="file"]').first();
  await input.setInputFiles(zipPath);
  console.log('ROOT_FILE_SET');

  let newId = null;
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(2000);
    const text = await page.locator('body').innerText();
    const m = text.match(/health-h40-critical-result-acknowledgement#[a-f0-9]+/i);
    if (m && m[0] !== beforeFirst) {
      newId = m[0];
      console.log('NEW_TOP', i, newId);
      break;
    }
    if (i % 10 === 0) console.log('wait', i, 'top', m && m[0]);
  }

  if (!newId) {
    console.log('NO_NEW_ID');
    fs.writeFileSync('tmp-pw/h40-root-upload.txt', await page.locator('body').innerText());
    await browser.close();
    process.exit(2);
  }

  await page.getByText(newId).first().click();
  await page.waitForTimeout(8000);
  let text = await page.locator('body').innerText();
  console.log('OPENED', page.url());
  console.log(text.slice(0, 1800));

  // Dismiss/skip PreQC; start Oracle+GLM
  const run = page.getByText(/Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i).first();
  if (await run.count()) {
    console.log('START_EVAL');
    await run.click();
    await page.waitForTimeout(12000);
  }
  text = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/h40-v9-root.txt', `URL=${page.url()}\nID=${newId}\n\n${text}`);
  console.log('FINAL', page.url());
  console.log(text.slice(0, 2500));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
