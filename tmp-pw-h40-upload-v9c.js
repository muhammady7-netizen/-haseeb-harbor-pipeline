const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const profiles = [
    'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40',
    'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile',
  ];
  const zipPath = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-health-h40.zip';
  let browser = null;
  let used = null;
  for (const profile of profiles) {
    try {
      console.log('TRY', profile);
      browser = await chromium.launchPersistentContext(profile, {
        headless: false,
        channel: 'chrome',
        args: ['--disable-blink-features=AutomationControlled'],
      });
      used = profile;
      break;
    } catch (e) {
      console.log('FAIL_LAUNCH', profile, String(e).slice(0, 200));
    }
  }
  if (!browser) process.exit(1);
  console.log('USING', used);
  const page = browser.pages()[0] || await browser.newPage();
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-3cbc34e3bd3f145428b66eab552ec13b-v1', {
    waitUntil: 'domcontentloaded',
    timeout: 120000,
  });
  await page.waitForTimeout(10000);
  let text = await page.locator('body').innerText();
  console.log('LAND', page.url());
  console.log(text.slice(0, 400));
  if (/Sign in|accounts\.google/i.test(text) && !/muhammad\.y7@turing\.com/i.test(text)) {
    console.log('NEED_LOGIN');
    fs.writeFileSync('tmp-pw/h40-need-login.txt', text);
    await browser.close();
    process.exit(4);
  }

  const btn = page.locator('#newVersion').first();
  await btn.waitFor({ state: 'visible', timeout: 60000 });
  for (let i = 0; i < 40; i++) {
    const disabled = await btn.isDisabled().catch(() => true);
    console.log('btn', i, 'disabled', disabled);
    if (!disabled) break;
    await page.waitForTimeout(2000);
  }
  await btn.click({ timeout: 30000 });
  await page.waitForTimeout(2000);
  await page.locator('input[type="file"]').last().setInputFiles(zipPath);
  console.log('FILE_SET');

  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(2000);
    text = await page.locator('body').innerText();
    const uploading = /Uploading/i.test(text);
    const url = page.url();
    const changed = url.includes('content-') && !url.includes('3cbc34e3bd3f145428b66eab552ec13b');
    console.log('up', i, uploading, changed, url);
    if (changed || (!uploading && i > 10)) break;
  }

  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(7000);
  text = await page.locator('body').innerText();
  const ids = [...new Set([...text.matchAll(/health-h40-critical-result-acknowledgement#[a-f0-9]+/gi)].map(m => m[0]))];
  console.log('IDS', ids.slice(0, 6).join(' | '));
  await page.getByText(ids[0]).first().click();
  await page.waitForTimeout(12000);
  text = await page.locator('body').innerText();
  console.log('OPENED', page.url());
  console.log(text.slice(0, 1500));

  if (!/Running now|Oracle Running|running ·/i.test(text)) {
    const run = page.getByText(/Re-run QC-Oracle-GLM|Run QC-Oracle-GLM/i).first();
    if (await run.count()) {
      for (let i = 0; i < 20; i++) {
        if (!(await run.isDisabled().catch(() => false))) break;
        await page.waitForTimeout(1500);
      }
      console.log('CLICK_RUN');
      await run.click();
      await page.waitForTimeout(15000);
    }
  }
  text = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/h40-v9-upload-ok.txt', `PROFILE=${used}\nURL=${page.url()}\n\n${text}`);
  console.log('FINAL', page.url());
  console.log(text.slice(0, 2800));
  // Keep browser open? No - close and poll later
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
