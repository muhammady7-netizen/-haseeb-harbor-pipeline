const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const zipPath = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-health-h40.zip';
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || await browser.newPage();
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(5000);

  // Prefer uploading new version on existing h40 task page
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-3cbc34e3bd3f145428b66eab552ec13b-v1', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(6000);

  // Click Upload new version if present
  const uploadNew = page.getByText(/Upload new version/i).first();
  if (await uploadNew.count()) {
    await uploadNew.click().catch(()=>{});
    await page.waitForTimeout(2000);
  }

  // Find file input
  let input = page.locator('input[type="file"]').first();
  if (!(await input.count())) {
    // go root dropzone
    await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(4000);
    input = page.locator('input[type="file"]').first();
  }
  await input.setInputFiles(zipPath);
  console.log('FILE_SET');
  await page.waitForTimeout(15000);
  let text = await page.locator('body').innerText();
  console.log('AFTER_UPLOAD_URL', page.url());
  console.log(text.slice(0, 2500));

  // Dismiss PreQC if asked / skip running Confirm
  // Try Run QC-Oracle-GLM / Re-run
  const rerun = page.getByRole('button', { name: /Re-run QC-Oracle-GLM|Run QC-Oracle-GLM|QC-Oracle-GLM/i }).first();
  if (await rerun.count()) {
    console.log('CLICK_RERUN');
    await rerun.click();
    await page.waitForTimeout(8000);
  } else {
    // try text click
    const t = page.getByText(/Re-run QC-Oracle-GLM|Run QC-Oracle-GLM/i).first();
    if (await t.count()) {
      console.log('CLICK_RERUN_TEXT');
      await t.click();
      await page.waitForTimeout(8000);
    } else {
      console.log('NO_RERUN_BUTTON');
    }
  }

  text = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/h40-after-upload.txt', text);
  console.log('FINAL_URL', page.url());
  console.log(text.slice(0, 3500));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
