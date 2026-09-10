const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
  const outDir = 'tmp-pw/h40-harbor-report';
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || await browser.newPage();
  const url = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-0f5e7ea213cebcd75662f8b0281f1da7-v1';
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(5000);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(12000);
  const text = await page.locator('body').innerText();
  fs.writeFileSync(path.join(outDir, 'page.txt'), text);

  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 30000 }).catch(() => null),
    page.getByText(/Download the report folder/i).first().click().catch(() => null),
  ]);
  if (download) {
    const p = path.join(outDir, await download.suggestedFilename());
    await download.saveAs(p);
    console.log('DOWNLOADED', p);
  } else {
    // try report.zip link
    const [d2] = await Promise.all([
      page.waitForEvent('download', { timeout: 20000 }).catch(() => null),
      page.getByText(/^zip$/i).first().click().catch(() => null),
    ]);
    if (d2) {
      const p = path.join(outDir, await d2.suggestedFilename());
      await d2.saveAs(p);
      console.log('DOWNLOADED2', p);
    } else console.log('NO_DOWNLOAD');
  }
  console.log(text.slice(0, 8000));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
