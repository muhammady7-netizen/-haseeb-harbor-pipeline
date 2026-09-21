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

  // Open latest known h40 task, then upload new version
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-3cbc34e3bd3f145428b66eab552ec13b-v1', {
    waitUntil: 'domcontentloaded',
    timeout: 90000,
  });
  await page.waitForTimeout(6000);

  // Click Upload new version
  const uploadBtn = page.getByText(/Upload new version/i).first();
  await uploadBtn.click({ timeout: 15000 });
  await page.waitForTimeout(2000);

  const input = page.locator('input[type="file"]').last();
  await input.setInputFiles(zipPath);
  console.log('FILE_SET');

  // Wait for upload success / new content id
  let urlBefore = page.url();
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(2000);
    const text = await page.locator('body').innerText();
    const url = page.url();
    if (/Upload successful|uploaded|new version|v2|Processing|ready/i.test(text) || url !== urlBefore) {
      console.log('UPLOAD_STATE', i, url);
      if (url.includes('content-') && !url.includes('3cbc34e3bd3f145428b66eab552ec13b')) {
        console.log('NEW_CONTENT_ID', url);
        break;
      }
    }
    if (i === 59) console.log('TIMEOUT_WAIT textHead', text.slice(0, 800));
  }

  await page.waitForTimeout(5000);
  let text = await page.locator('body').innerText();
  console.log('URL', page.url());
  console.log(text.slice(0, 2000));

  // If still on old page, go to root and open newest health-h40
  if (page.url().includes('3cbc34e3bd3f145428b66eab552ec13b')) {
    await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(6000);
    const latest = page.getByText(/health-h40-critical-result-acknowledgement#/i).first();
    await latest.click();
    await page.waitForTimeout(8000);
    text = await page.locator('body').innerText();
    console.log('OPENED_LATEST', page.url());
    console.log(text.slice(0, 2000));
  }

  // Start Oracle+GLM if not already running
  text = await page.locator('body').innerText();
  if (!/Running now|running ·/i.test(text)) {
    const run = page.getByText(/Re-run QC-Oracle-GLM|Run QC-Oracle-GLM/i).first();
    if (await run.count()) {
      console.log('START_EVAL');
      await run.click();
      await page.waitForTimeout(10000);
    }
  } else {
    console.log('ALREADY_RUNNING');
  }

  text = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/h40-v9-upload.txt', `URL=${page.url()}\n\n${text}`);
  console.log('FINAL', page.url());
  console.log(text.slice(0, 2500));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
