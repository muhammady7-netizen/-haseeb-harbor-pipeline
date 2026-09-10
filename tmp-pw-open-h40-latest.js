const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || await browser.newPage();
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(6000);

  // Click the latest health-h40 recent task (first match)
  const link = page.getByText('health-h40-critical-result-acknowledgement#2ec13b').first();
  await link.click();
  await page.waitForTimeout(10000);
  let text = await page.locator('body').innerText().catch(() => '');
  const result = { url: page.url(), snippet: text.slice(0, 8000) };
  fs.writeFileSync('tmp-pw/portal-h40-latest.json', JSON.stringify(result, null, 2));
  console.log('URL', page.url());
  console.log(text.slice(0, 5000));

  // Also try to find SWITCH VERSION / version list
  const versions = await page.locator('text=/v\\d+/i').allTextContents().catch(() => []);
  console.log('VERSION_TEXTS', JSON.stringify(versions.slice(0, 40)));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
