const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
  const zipPath = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-health-h40.zip';
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
  console.log('ROOT', page.url());
  console.log(text.slice(0, 600));
  if (!/muhammad\.y7@turing\.com/i.test(text)) {
    console.log('NEED_LOGIN');
    fs.writeFileSync('tmp-pw/h40-need-login.txt', text);
    await browser.close();
    process.exit(4);
  }

  const beforeIds = [...new Set([...text.matchAll(/health-h40-critical-result-acknowledgement#[a-f0-9]+/gi)].map(m => m[0]))];
  console.log('BEFORE', beforeIds.slice(0, 5).join(' | '));

  // Root upload creates a new content entry
  const input = page.locator('input[type="file"]').first();
  await input.setInputFiles(zipPath);
  console.log('ROOT_FILE_SET');

  let newId = null;
  for (let i = 0; i < 120; i++) {
    await page.waitForTimeout(2000);
    text = await page.locator('body').innerText();
    const ids = [...new Set([...text.matchAll(/health-h40-critical-result-acknowledgement#[a-f0-9]+/gi)].map(m => m[0]))];
    console.log('poll', i, ids[0] || 'none');
    if (ids[0] && (!beforeIds.length || ids[0] !== beforeIds[0] || i > 15)) {
      // Prefer an id not in before list
      newId = ids.find(id => !beforeIds.includes(id)) || (i > 20 ? ids[0] : null);
      if (newId) {
        console.log('NEW_ID', newId);
        break;
      }
    }
  }
  if (!newId) {
    fs.writeFileSync('tmp-pw/h40-root-fail.txt', text);
    console.log('NO_NEW_ID');
    await browser.close();
    process.exit(2);
  }

  await page.getByText(newId).first().click();
  await page.waitForTimeout(12000);
  text = await page.locator('body').innerText();
  console.log('OPENED', page.url());
  console.log(text.slice(0, 1800));

  // Start Oracle+GLM
  const run = page.getByText(/Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i).first();
  if (await run.count()) {
    for (let i = 0; i < 30; i++) {
      const dis = await run.isDisabled().catch(() => false);
      console.log('runBtn', i, 'disabled', dis);
      if (!dis) break;
      await page.waitForTimeout(2000);
    }
    console.log('CLICK_RUN');
    await run.click();
    await page.waitForTimeout(15000);
  } else {
    console.log('NO_RUN_BTN');
  }

  text = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/h40-v9-running.txt', `URL=${page.url()}\nID=${newId}\n\n${text}`);
  console.log('FINAL', page.url());
  console.log(text.slice(0, 3000));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
