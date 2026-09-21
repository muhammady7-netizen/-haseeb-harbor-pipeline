const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || await browser.newPage();
  page.setDefaultTimeout(60000);

  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(8000);
  let text = await page.locator('body').innerText();
  const ids = [...new Set([...text.matchAll(/health-h40-critical-result-acknowledgement#[a-f0-9]+/gi)].map(m => m[0]))];
  console.log('IDS', ids.slice(0, 8).join(' | '));
  const target = ids[0] || 'health-h40-critical-result-acknowledgement#1f1da7';
  console.log('OPEN', target);
  await page.getByText(target).first().click();
  await page.waitForTimeout(15000);
  text = await page.locator('body').innerText();
  console.log('URL', page.url());
  console.log(text.slice(0, 3500));

  const running = /Running now|Oracle Running|running ·/i.test(text);
  const failed = /Oracle Failed|below_1\.0/i.test(text) && !running;
  const ready = /READY_FOR_FINALIZATION|Oracle Passed/i.test(text);

  if (!running && !ready) {
    const run = page.getByText(/Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i).first();
    if (await run.count()) {
      for (let i = 0; i < 25; i++) {
        if (!(await run.isDisabled().catch(() => false))) break;
        await page.waitForTimeout(2000);
      }
      console.log('CLICK_RUN');
      await run.click();
      await page.waitForTimeout(12000);
      text = await page.locator('body').innerText();
    }
  }

  // If upload new version needed because this is still old fail — upload fixed zip
  if (/Oracle Failed|below_1\.0|0\.944/i.test(text) && !/Running now/i.test(text)) {
    console.log('STILL_FAILED_TRY_UPLOAD_NEW');
    const btn = page.locator('#newVersion').first();
    if (await btn.count()) {
      for (let i = 0; i < 20; i++) {
        if (!(await btn.isDisabled().catch(() => true))) break;
        await page.waitForTimeout(2000);
      }
      await btn.click();
      await page.waitForTimeout(2000);
      await page.locator('input[type="file"]').last().setInputFiles('C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-health-h40.zip');
      console.log('NEW_VERSION_FILE_SET');
      for (let i = 0; i < 60; i++) {
        await page.waitForTimeout(2000);
        text = await page.locator('body').innerText();
        if (!/Uploading/i.test(text) && i > 5) break;
        console.log('upload wait', i);
      }
      const run2 = page.getByText(/Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i).first();
      if (await run2.count()) {
        await run2.click();
        await page.waitForTimeout(10000);
      }
      text = await page.locator('body').innerText();
    }
  }

  fs.writeFileSync('tmp-pw/h40-track.txt', `URL=${page.url()}\nTARGET=${target}\n\n${text}`);
  console.log('FINAL', page.url());
  console.log(text.slice(0, 3000));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
