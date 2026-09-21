const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const outDir = 'tmp-pw/h40-report';
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || await browser.newPage();
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-3cbc34e3bd3f145428b66eab552ec13b-v1', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(8000);

  // Click View report if present
  const viewReport = page.getByRole('button', { name: /View report/i }).first();
  if (await viewReport.count()) {
    await viewReport.click().catch(()=>{});
    await page.waitForTimeout(3000);
  }

  // Try download report folder zip
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 20000 }).catch(() => null),
    page.getByText(/Download the report folder/i).first().click().catch(() => null),
  ]);
  if (download) {
    const p = path.join(outDir, await download.suggestedFilename());
    await download.saveAs(p);
    console.log('DOWNLOADED', p);
  } else {
    console.log('NO_DOWNLOAD');
  }

  // Also dump body + try click report.json preview
  const text = await page.locator('body').innerText();
  fs.writeFileSync(path.join(outDir, 'page.txt'), text);
  console.log(text.slice(0, 3000));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
