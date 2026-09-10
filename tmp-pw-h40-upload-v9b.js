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
  await page.waitForTimeout(8000);

  // Wait until Upload new version is enabled
  const btn = page.locator('#newVersion, button:has-text("Upload new version")').first();
  await btn.waitFor({ state: 'visible', timeout: 60000 });
  for (let i = 0; i < 30; i++) {
    const disabled = await btn.isDisabled().catch(() => true);
    const title = await btn.getAttribute('title').catch(() => '');
    console.log('btn i', i, 'disabled', disabled, 'title', title);
    if (!disabled) break;
    await page.waitForTimeout(2000);
  }
  await btn.click({ timeout: 30000 });
  await page.waitForTimeout(2500);

  const input = page.locator('input[type="file"]').last();
  await input.setInputFiles(zipPath);
  console.log('FILE_SET');

  let settled = false;
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(2000);
    const text = await page.locator('body').innerText();
    const url = page.url();
    const uploading = /Uploading/i.test(text);
    const changed = url.includes('content-') && !url.includes('3cbc34e3bd3f145428b66eab552ec13b');
    console.log('i=' + i, 'uploading=' + uploading, 'changed=' + changed, 'url=' + url);
    if (changed) { settled = true; break; }
    if (!uploading && i > 8) { settled = true; break; }
  }

  // Open newest from root list
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(7000);
  let text = await page.locator('body').innerText();
  const ids = [...new Set([...text.matchAll(/health-h40-critical-result-acknowledgement#[a-f0-9]+/gi)].map(m => m[0]))];
  console.log('IDS', ids.slice(0, 6).join(' | '));
  await page.getByText(ids[0]).first().click();
  await page.waitForTimeout(12000);

  text = await page.locator('body').innerText();
  console.log('OPENED', page.url());
  console.log(text.slice(0, 1600));

  // Wait for Run button enabled, then start eval
  if (!/Running now|Oracle Running|running ·/i.test(text)) {
    const run = page.getByText(/Re-run QC-Oracle-GLM|Run QC-Oracle-GLM/i).first();
    await run.waitFor({ state: 'visible', timeout: 30000 }).catch(() => null);
    for (let i = 0; i < 20; i++) {
      const dis = await run.isDisabled().catch(() => false);
      if (!dis && await run.count()) break;
      await page.waitForTimeout(1500);
    }
    if (await run.count()) {
      console.log('CLICK_RUN');
      await run.click();
      await page.waitForTimeout(15000);
    }
  }

  text = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/h40-v9-upload-ok.txt', `URL=${page.url()}\n\n${text}`);
  console.log('FINAL', page.url());
  console.log(text.slice(0, 2800));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
