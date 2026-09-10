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
  await page.waitForTimeout(5000);

  const snaps = [];
  for (let i = 0; i < 24; i++) { // ~4 min
    await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(4000);
    const text = await page.locator('body').innerText();
    const ids = [...text.matchAll(/health-h40-critical-result-acknowledgement#[a-f0-9]+/gi)].map(m => m[0]);
    const uniq = [...new Set(ids)];
    console.log('POLL', i, new Date().toISOString(), uniq.slice(0, 5).join(', '));
    snaps.push({ i, at: new Date().toISOString(), ids: uniq });
    await page.waitForTimeout(6000);
  }

  // Open newest id
  const latest = snaps[snaps.length - 1].ids[0];
  console.log('OPEN', latest);
  await page.getByText(latest).first().click();
  await page.waitForTimeout(10000);
  const body = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/h40-poll-latest.json', JSON.stringify({ snaps, url: page.url(), body: body.slice(0, 8000) }, null, 2));
  console.log('URL', page.url());
  console.log(body.slice(0, 3000));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
