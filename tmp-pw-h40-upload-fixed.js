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
  const oldUrl = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-3cbc34e3bd3f145428b66eab552ec13b-v1';
  await page.goto(oldUrl, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(6000);

  // Upload new version
  await page.getByText(/Upload new version/i).first().click();
  await page.waitForTimeout(2500);
  const input = page.locator('input[type="file"]').last();
  await input.setInputFiles(zipPath);
  console.log('FILE_SET');

  // Wait until Uploading… goes away and/or URL changes
  let finalUrl = page.url();
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(2000);
    const text = await page.locator('body').innerText();
    finalUrl = page.url();
    const uploading = /Uploading…|Uploading\.\.\.|upload started/i.test(text);
    const changed = finalUrl.includes('content-') && !finalUrl.includes('3cbc34e3bd3f145428b66eab552ec13b');
    console.log('i=' + i, 'uploading=' + uploading, 'url=' + finalUrl);
    if (changed) break;
    if (!uploading && i > 5 && /Upload new version/i.test(text) && !/Uploading/i.test(text)) {
      // maybe stayed on same content id but package replaced — check digest/time
      if (/just now|seconds ago|a minute ago|Uploaded|✓\s*Upload/i.test(text)) {
        console.log('UPLOAD_UI_SETTLED');
        break;
      }
    }
  }

  // If URL unchanged, check recent tasks for a newer hash
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(6000);
  const root = await page.locator('body').innerText();
  const ids = [...new Set([...root.matchAll(/health-h40-critical-result-acknowledgement#[a-f0-9]+/gi)].map(m => m[0]))];
  console.log('IDS', ids.slice(0, 6).join(' | '));
  await page.getByText(ids[0]).first().click();
  await page.waitForTimeout(10000);

  let text = await page.locator('body').innerText();
  console.log('OPENED', page.url());
  console.log(text.slice(0, 1800));

  // Start eval if not running
  if (!/Running now|Oracle Running/i.test(text)) {
    const btn = page.getByText(/Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i).first();
    if (await btn.count()) {
      console.log('CLICK_RUN');
      await btn.click();
      await page.waitForTimeout(12000);
    }
  }
  text = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/h40-v9-final-upload.txt', `URL=${page.url()}\n\n${text}`);
  console.log('FINAL', page.url());
  console.log(text.slice(0, 2800));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
