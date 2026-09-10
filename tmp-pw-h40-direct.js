const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const profiles = [
    'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile',
    'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40',
  ];
  let browser;
  for (const p of profiles) {
    try {
      browser = await chromium.launchPersistentContext(p, {
        headless: false,
        channel: 'chrome',
        args: ['--disable-blink-features=AutomationControlled'],
      });
      console.log('USING', p);
      break;
    } catch (e) {
      console.log('skip', p, String(e).slice(0, 120));
    }
  }
  if (!browser) process.exit(1);
  const page = await browser.newPage();
  const url = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-0f5e7ea213cebcd75662f8b0281f1da7-v1';
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'networkidle', timeout: 120000 }).catch(() => null);
  await page.waitForTimeout(5000);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 120000 }).catch(() => null);
  await page.waitForTimeout(15000);
  // Force hash again
  await page.evaluate((u) => { location.hash = u.split('#')[1]; }, url);
  await page.waitForTimeout(10000);
  const text = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/h40-direct.txt', `URL=${page.url()}\n\n${text}`);
  console.log('URL', page.url());
  console.log(text.slice(0, 4000));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
